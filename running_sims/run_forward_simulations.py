#!/usr/bin/env python

from __future__ import unicode_literals, division

__author__ = "Rachel Kurchin, Riley Brandt, Daniil Kitchaev"
__date__ = "May 17, 2017"

from run_scaps_parallel import SCAPSrunner
import numpy as np
from copy import deepcopy
import pickle
import os
import argparse
import json

def scaps_output_processor(return_path):
    """
    Convert output of a SCAPS simulation to a numpy format for further processing
    """
    ii, simList, summaryList, dataLines = 0, [], [], []
    with open(return_path,'r') as f:
        for line in f:
            if 'jtot' in line: simList.append(ii)
            elif 'deduced' in line: summaryList.append(ii)
            ii += 1

    for xi, x in enumerate(simList):
        dataLines.extend(list(range(x + 2, summaryList[xi] - 1)))

    JArray, VArray = np.zeros(len(dataLines)), np.zeros(len(dataLines))

    ii = 0
    with open(return_path,'r') as f:
        for jj, line in enumerate(f):
            if jj in dataLines:
                floats = [float(x) for x in line.split("\t")]
                JArray[ii] = floats[1]
                VArray[ii] = floats[0]
                ii += 1

    return (JArray, VArray)

def scaps_script_generator(calc_param):
    """
    Generate SCAPS simulation input script as a string.
    """
    return "\n".join(["//Script file made by Python",
                       "set quitscript.quitSCAPS",
                       "load allscapssettingsfile {}".format(calc_param['def']),
                       "set errorhandling.overwritefile",
                       "set layer1.mun %f" % calc_param['mu_n_l'],
                       "set layer1.defect1.Ntotal %f" % calc_param['Nt_SnS_l'],
                       "set layer2.chi %f" % calc_param['EA_ZnOS_l'],
                       "set interface1.IFdefect1.Ntotal %f" % calc_param['Nt_i_l'],
                       "action workingpoint.temperature %f" % calc_param['T_l'],
                        "action iv.startv %f" % 0.0,
                        "action iv.stopv %f" % calc_param['V_max'],
                        "action iv.increment %f" % 0.02,
                        "action intensity.T %f" % calc_param['ill_l'],
                        "calculate"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-si', help="Start index for this run", type=int, default=0)
    parser.add_argument('-ni', help="Number of inputs to run here", type=int, default=0)
    parser.add_argument('-node', help="Node index (proc index offset)", type=int, default=0)
    args = parser.parse_args()

    node = args.node

    # Initialize SCAPS runner object
    scaps_runner = SCAPSrunner(ncores=32,
                               input_processor=scaps_script_generator,
                               output_processor=scaps_output_processor)

    baseline_run = {'def': "SnS_base.scaps",
                    'mu_n_l': 60,
                    'Nt_SnS_l': 1e17,
                    'EA_ZnOS_l': 4.0,
                    'Nt_i_l': 1e10,
                    "V_max": 0.5}

    temperatures = np.array([280, 300, 320])
    illuminations = np.array([31, 108])
    mu_n_range = np.linspace(20, 80, 20)
    Nt_SnS_range = np.logspace(16, 18, 20)
    EA_ZnOS_range = np.linspace(3.4, 4.3, 15)
    Nt_i_range = np.logspace(10, 14, 16)

    inputs = {}
    i = 0

    for temp in temperatures:
        for ill in illuminations:
            for Nt_i in Nt_i_range:
                for mu_n in mu_n_range:
                    for Nt in Nt_SnS_range:
                        for EA in EA_ZnOS_range:
                            run=deepcopy(baseline_run)
                            baseline_run['Nt_i_l'] = Nt_i
                            run['mu_n_l'] = mu_n
                            run['Nt_SnS_l'] = Nt
                            run['EA_ZnOS_l'] = EA
                            run['T_l'] = temp
                            run['ill_l'] = ill
                            inputs[i] = run
                            i += 1

    with open("input_parameters.json", 'w') as fout:fout.write(json.dumps(inputs))

    n_batches = 16
    for batch_i in range(n_batches):
        batch_size = int((args.si + args.ni)/n_batches)
        batch_inputs = {}
        for pt_i in range(args.si + batch_i * batch_size, args.si + batch_i * batch_size + batch_size):
            batch_inputs[pt_i] = inputs[pt_i]

        # Run the inputs
        print("[Batch {}] Starting SCAPS runs ({}-{})".format(batch_i, args.si + batch_i * batch_size, args.si + batch_i * batch_size + batch_size))
        outputs = scaps_runner.run_inputs(batch_inputs, print_progress=True)

        # Save outputs
        print("[Batch {}] Saving outputs as pickles...".format(batch_i))
        pickle.dump(outputs, open("simulation_{}_{}_n{}_b{}.pickle".format(args.si + batch_i * batch_size,
                                                                           args.si + batch_i * batch_size + batch_size,
                                                                           node,
                                                                           batch_i),"wb"))
