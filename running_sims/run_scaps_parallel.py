#!/usr/bin/env python
"""
This module runs SCAPS in parallel in a series of WINE VMs
"""

from __future__ import unicode_literals, division

__author__ = "Daniil Kitchaev"
__version__ = "1.0"
__maintainer__ = "Daniil Kitchaev"
__email__ = "dkitch@mit.edu"
__status__ = "Development"
__date__ = "July 20, 2016"

import os
import shutil
import subprocess
from multiprocessing import Process, Queue
import time
from copy import deepcopy
import random

class SCAPSrunner:
    ##################################################################################################################
    # Change these defaults as necessary depending on system configuration
    MAX_CORENUM = 32 # Should be roughly doubly the number of physical cores, and equal to the number of proc folders
                     # in the SCAPS exec folder

    ROOTDIR = os.environ['HOME']
    SCAPS_PARAM_DEF_DIR = '{}/pv_bayes/running_sims/scaps_dat/def'.format(ROOTDIR)
    SCAPS_PARAM_ABS_DIR = '{}/pv_bayes/running_sims/scaps_dat/absorption'.format(ROOTDIR)
    SCAPS_PARAM_FTR_DIR = '{}/pv_bayes/running_sims/scaps_dat/filter'.format(ROOTDIR)
    SCAPS_INSTALL_DIR = '{}/pv_bayes/running_sims/wine_reference'.format(ROOTDIR)
    SCAPS_EXEC_DIR = '{}/scaps_exec'.format(ROOTDIR)
    ##################################################################################################################

    SCAPS_ROOT = '#/drive_c/Program Files/Scaps3302'
    SCAPS_CMD = 'WINEDEBUG=-all WINEPREFIX=# WINEARCH=win32 xvfb-run -a wine #/drive_c/Program\ Files/Scaps3302/scaps3303.exe'

    def __init__(self,
                 input_processor,
                 output_processor,
                 ncores = MAX_CORENUM,
                 scaps_param_def_dir=SCAPS_PARAM_DEF_DIR,
                 scaps_param_abs_dir=SCAPS_PARAM_ABS_DIR,
                 scaps_param_ftr_dir=SCAPS_PARAM_FTR_DIR,
                 scaps_install_dir=SCAPS_INSTALL_DIR,
                 scaps_exec_dir=SCAPS_EXEC_DIR):
        """
        Initialize the SCAPS parallel processor.

        input_processor: a python method that takes in a dictionary of run parameters and outputs a string corresponding
                         to a SCAPS input script

        output_processor: a python method that takes a path to a SCAPS output file and returns a python object
                          representation of the output

        ncores: number of processes used to run
        """
        self.ncores = ncores
        if ncores > self.MAX_CORENUM:
            raise ValueError("Number of cores exceeds MAX_CORENUM={}. Either modify the " + \
                             "limit, or use fewer cores".format(SCAPSrunner.MAX_CORENUM))
        self.input_processor = input_processor
        self.output_processor = output_processor
        self.scaps_param_def_dir = scaps_param_def_dir
        self.scaps_param_abs_dir = scaps_param_abs_dir
        self.scaps_param_ftr_dir = scaps_param_ftr_dir
        self.scaps_install_dir = scaps_install_dir
        self.scaps_exec_dir = scaps_exec_dir

    def sync_parameters(self):
        """
        Syncs the contents of the reference def and absorption directories with all SCAPS execution proc folders. Does
        not modify the refence VM however.
        """
        def copytree(src, dst, symlinks=False, ignore=None):
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, symlinks, ignore)
                else:
                    shutil.copy2(s, d)

        for core in range(self.ncores):
            copytree(self.scaps_param_def_dir,
                     "{}/def".format(self.SCAPS_ROOT.replace('#','{}/proc{}'.format(self.scaps_exec_dir, core))))
            copytree(self.scaps_param_abs_dir,
                     "{}/absorption".format(self.SCAPS_ROOT.replace('#','{}/proc{}'.format(self.scaps_exec_dir, core))))
            copytree(self.scaps_param_ftr_dir,
                     "{}/filter".format(
                         self.SCAPS_ROOT.replace('#', '{}/proc{}'.format(self.scaps_exec_dir, core))))

    def run_inputs(self, inputs, print_progress=True):
        """
        Process SCAPS run parameters in parallel. Takes in a dictionary of inputs, structured as
        {'id1':run_params_1, 'id2':run_params_2, ...}
        where run_params_1, run_params_2, ... should be the argument to the pre-specified input processor method.

        Returns a dictionary structured as
        {'id1':output_1, 'id2':output_2, ...}
        where output_1, output_2, ... are the objectrs returned by the pre-specified output processor method
        """

        inq = Queue()
        outq = Queue()
        output_dict = {}
        num_total = len(inputs.keys())
        num_done = 0

        proc_list = []
        config_all = {'SCAPS_ROOT':self.SCAPS_ROOT, 'SCAPS_CMD':self.SCAPS_CMD,
                      'SCAPS_EXEC_DIR':self.scaps_exec_dir, 'INPUT_PROC':self.input_processor,
                      'OUTPUT_PROC':self.output_processor}
        for proc_i in range(self.ncores):
            config_proc = deepcopy(config_all)
            config_proc['CORE'] = proc_i
            proc = Process(target=SCAPSrunner.run_process, args=(config_proc, inq, outq))
            proc.start()
            proc_list.append(proc)

        inputiter = inputs.iteritems()
        while True:
            running = any(proc.is_alive() for proc in proc_list)
            if not running:
                break
            while inq.empty():
                try:
                    (id, input) = inputiter.next()
                    inq.put({'id':id,'calc_param':input})
                except:
                    inq.put({'id':'done'})

            while not outq.empty():
                pt = outq.get()
                output_dict[pt['id']] = pt['output']
                num_done += 1
                if print_progress:
                    print("Finished input ID{} [{}/{} total]".format(pt['id'], num_done, num_total))

        for proc_i, proc in enumerate(proc_list):
            proc.join()

        # Garbage collect
        while not inq.empty():
            inq.get()
        while not outq.empty():
            outq.join()
        # Give queues time to close
        time.sleep(5)

        if not (set(inputs.keys())==set(output_dict.keys())):
            print("Warning: Not all inputs seem to have gotten outputs")

        return output_dict

    def time_inputs(self, inputs, sample_size=216):
        sample_inputs = {}
        ids = list(inputs.keys())
        random.shuffle(ids)
        for sample in range(sample_size):
            sample_inputs[ids[sample]] = inputs[ids[sample]]
        startTime = time.time()
        self.run_inputs(sample_inputs, print_progress=True)
        endTime = time.time()
        return (endTime-startTime)/sample_size

    @staticmethod
    def run_scaps_thread(config, run_params):
        """
        Executes SCAPS on a single thread. Needs a configuration dictionary and a run_parameters dictionary.

        The config dictionary specifies the directories where SCAPS is running, the commands needed to launch it, the
        process number (which VM is running this process), an 'INPUT_PROC' field specifying a python method that can
        take the run parameters and generate a SCAPS input script, and an 'OUTPUT_PROC' field specifying a python
        method that can take a SCAPS output and generate a python object representation of it.

        The run_params dictionary has two fields - 'id' which uniquely identifies this run, and 'calc_params', which
        are the arguments passed to the input_processor to generate the SCAPS inputs for this run.

        For the purposes of the script generator, the python runscript is always called 'pythonscript.script' and the
        output file is always called 'pythonresult.txt'
        """
        script_name = "pythonscript.script"
        script_dir = os.path.join(config['SCAPS_ROOT'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])), 'script')
        script_file = os.path.join(script_dir, script_name)

        result_name = "pythonresult.txt"
        result_dir = os.path.join(config['SCAPS_ROOT'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])), 'results')
        result_file = os.path.join(result_dir, result_name)

        script = config['INPUT_PROC'](run_params['calc_param']) + "\nsave results.iv {}\n".format(result_name)
        with open(script_file,"w") as fout: fout.write(script)

        subprocess.call(config['SCAPS_CMD'].replace('#','{}/proc{}'.format(config['SCAPS_EXEC_DIR'], config['CORE'])) + " " + script_name, shell=True)
        return {'id':run_params['id'], 'output': config['OUTPUT_PROC'](result_file)}

    @staticmethod
    def run_process(config, inputs, outq):
        """
        Runs a thread that pulls inputs from the input queue and calls the SCAPS thread processor to get an output.
        Terminates when it receives an input with the id 'done'. The config dictionary is defined analogously to that
        detailed in run_scaps_thread, while the inputs queue gives a pointer to the root-level queue that distributes
        SCAPS inputs to the various running processes.
        """

        while True:
            if not inputs.empty():
                param = inputs.get()
                if param['id'] == 'done':
                    break
                else:
                    outq.put(SCAPSrunner.run_scaps_thread(config, param))
        return

