# Bayesian inference for materials parameter extraction, based on JVTi data and SCAPS simulations
This package contains code in support of the manuscript "Rapid semiconductor device characterization through Bayesian parameter estimation" (*insert full citation*). The code implements a workflow for running large amounts of SCAPS simulations for a range of materials parameters, temperatures, and illuminations, as well as a Bayesian inference approach to using these simulations to extract materials parameters from experimental JVTi data.

This code is provided under the MIT license, except the xdummy package redistributed here, which is released under the GPLv2. If you use this package for research purposes, please cite *paper citation* 

# Setting up WINE for running SCAPS in parallel (Ubuntu Linux)

## Setting up 32-bit WINE
You will need to first install WINE (32 bit since SCAPS is old), and the packages necessary for running the dummy graphics.

For WINE, you need to add the 32-bit libraries and the custom wine repository.
$:~# dpkg --add-architecture i386
$:~# add-apt-repository ppa:ubuntu-wine/ppa
$:~# apt-get update
$:~# apt-get dist-upgrade
$:~# apt-get install wine1.7

For the dummy graphics, install:
$:~# apt-get install xvfb x11vnc xserver-xorg-video-dummy

## Creating reference and execution WINE emulators for SCAPS
Then, you need to create a baseline WINE VM with SCAPS installed in it - this will serve as the "reference VM":
$:~# WINEPREFIX=$HOME/pv\_bayes/running\_sims/wine\_reference WINEARCH=win32 winecfg

Install SCAPS within this VM so we have a working reference configuration. During the Windows installation, click through all the default setup options.
WINEPREFIX=$HOME/pv\_bayes/running\_sims/wine\_reference WINEARCH=win32 wine pv\_bayes/running_sims/scaps\_src/setup.exe

Now create a folder that will contain the execution VMs for SCAPS, each a clone of the reference setup. There needs to be enough of these for all the threads you want to run - in this example, there will be 32, each in a folder called proc0, proc1, ..., proc31
$:~# mkdir $HOME/scaps\_exec
$:~# for i in \`seq 0 31\`; do cp –r $HOME/pv\_bayes/running\_sims/wine\_reference $HOME/scaps\_exec/proc$i; done`

The reason this is necessary is SCAPS has hardcoded paths so parallel SCAPS processes overwrite each other. The easy solution is then to run them in separate emulators.

## Starting dummy video driver
Since SCAPS also requires access to a display, even in script-mode, you have to run a display emulator. This is provided either by xvfb or by the xdummy script.

By default, the system is set to use xvfb-run to launch the headless wine instances. If xvfb is not available however, you can take the following route to use the xdummy script instead. In this case, you will need to remove the section 'xvfb-run -a' from the wine run command in run_scaps_parallel.py:

First, compile xdummy:
$:~# cd ~/pv\_bayes/running\_sims
$:running\_sims# ./xdummy -install

Afterwards, start the dummy X-server and give it a display number (here, it is :99)
$:~# ~/pv_bayes/running\_sims/xdummy :99

The X-server will continue running until you kill it, either using ctrl-C or by killing the process:
$:~# pkill Xorg

# Foward simulations: Running SCAPS in parallel
SCAPS can be run through a python script once the dummy x-server is running or xvfb is set up.

To start the simulation, you need to write a small script, based on the example provided (run\_forward\_simulations.py), although its a good idea to first try a smaller set of simulations. The general structure of the run is as such:

1. Create a dictionary of input parameters, where each set of parameters has a unique id assigned to it:
`inputs = {id1: params1, id2: params2, …}`

2. Create a python method that will take one set of inputs (such as params1), and return a string corresponding to a SCAPS input script – see scaps\_script\_generator()

3. Create a python method that will take a filepath pointing to the SCAPS output file, read it in, and return some sort of python representation of the output – see scaps\_output\_processor()

4. Create a SCAPSrunner object, specifying the input and output processor functions you just wore and the number of cores you would like to use (this shouldn’t exceed the number of VM folders you created earlier – in this example, this is 32)

5. Sync the def and absorption files to the run directories by calling the sync\_parameters() method. The contents of the reference def/ and absorption/ directories (currently pv\_bayes/scaps\_dat/def and pv\_bayes/scaps\_dat/absorption) will then go to all the VMs.

6. Run SCAPS in parallel over all the inputs you specified by calling the run_inputs(inputs) method. The outputs are returned as a dictionary with the outputs labelled by the same ids as you had in the inputs:
outputs = {id1: output1, id2: output2, …}

Finally, to run the script you just wrote (or the example script), you need to tell python to use the dummy graphics driver, so as to suppress the SCAPS GUI. The run command is:

$:~# cd ~/pv\_bayes/running\_sims
$:running\_sims# DISPLAY=:99 python run\_forward\_simulations.py

where the DISPLAY=:99 section is not necessary if using xvfb.

A useful function is the time\_inputs(inputs) function – it takes a random sample of the input parameters and estimates the average amount of time per SCAPS run this simulation will take, allowing you to estimate the total amount of time it will take to run through all the parameters. You can see a usage example in run\_forward\_simulations.py

After the simulations are done, there will be a folder called pickles containing the raw outputs of all the simulations.

In the current implementation of run\_forward\_simulations.py, runs are batched by several parameters, saving run outputs several times through the simulation. In general, this should be automated based on the type of computational resources available, scheduling and queuing system, etc. Currently, these batched outputs need to be combined after the fact into a single datafile, using process\_pickles.py:

$:~# cd ~/pv\_bayes/running\_sims
$:running\_sims# python process_pickles.py

# Bayesian inference
The outputs of the simulations first need to be batched together for easier processing - the process\_pickles.py script takes care of this step, but can take a long time.

After the data is batched together, the Bayesian inference is implemented in analysis/bayes.py. The code assumes that you create a folder inside pv\_bayes/analysis called observation\_data that contains experimental JVTi data with the first row being column headers, followed by JVTi data in space-delimited format. See read_obs() in bayes.py for details.

$:~# cd ~/pv\_bayes/analysis
$:analysis# python bayes.py

After the code is run, there will be a folder called probs that will contain the probabilities obtained for each parameter based on each observation. These probabilities can be further processed into entropies using entropy.py

$:~# cd ~/pv\_bayes/analysis
$:analysis# python entropy.py


