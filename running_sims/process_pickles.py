#!/usr/bin/env python
"""
This code joins all the pickled outputs from the forward simulations into a more processable format
"""

from __future__ import unicode_literals, division

__author__ = "Rachel Kurchin, Riley Brandt, Daniil Kitchaev"
__date__ = "May 17, 2017"

import numpy as np
from copy import deepcopy
import pickle
import multiprocessing
import os
import json

NPROCS = 24 # Number of processes to use to load data in parallel

if __name__ == "__main__":
    temperatures = np.array([280, 300, 320])
    illuminations = np.array([31, 108])
    mu_n_range = np.linspace(20, 80, 20)
    Nt_SnS_range = np.logspace(16, 18, 20)
    EA_ZnOS_range = np.linspace(3.4, 4.3, 15)
    Nt_i_range = np.logspace(10, 14, 16)

    baseline_run = {'def': "SnS_base.scaps",
                        'mu_n_l': 60,
                        'Nt_SnS_l': 1e17,
                        'EA_ZnOS_l': 4.0,
                        'Nt_i_l': 1e10,
                        "V_max": 1.0}

    inputs = {}
    i = 0

    lookup_dict = {}
    print("Regenerating inputs")
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
                            lookup_dict[(Nt_i,mu_n,Nt,EA,temp,ill)] = i
                            i += 1

    missing_sims = {}
    missing_inputs = {}

    def load_simulation(inputfile):
        sim = pickle.load(open(os.path.join(inputfile[0], inputfile[1]),'rb'))
        return sim

    simulations = []
    save_files = []
    print("Searching for pickles")
    for root, dirs, files in os.walk(os.getcwd()):
        for inputfile in files:
            if '.pickle' in inputfile:
                save_files.append([root,inputfile])

    print("Loading pickles")
    simulations = multiprocessing.Pool(NPROCS).map(load_simulation, save_files)

    print("Merging pickles")
    all_results = {}
    for sim in simulations:
        all_results.update(sim)

    print("Reorganizing pickles")
    i = 0
    results = {}
    resultslookup = {}
    for mu_n in mu_n_range:
        for Nt in Nt_SnS_range:
            for EA in EA_ZnOS_range:
                for Nt_i in Nt_i_range:
                    run = deepcopy(baseline_run)
                    run['mu_n_l']=mu_n
                    run['Nt_SnS_l']=Nt
                    run['EA_ZnOS_l']=EA
                    run['Nt_i_l']=Nt_i

                    for T in temperatures:
                        run[T] = {}
                        for ill in illuminations:
                            run[T][ill] = {}
                    results[i] = run
                    resultslookup[(mu_n, Nt, EA, Nt_i)] = i
                    i=i+1

    for sim_i, sim_data in all_results.items():
        sim_T = inputs[sim_i]['T_l']
        sim_ill = inputs[sim_i]['ill_l']
        results_index = resultslookup[(inputs[sim_i]['mu_n_l'],
                                      inputs[sim_i]['Nt_SnS_l'],
                                      inputs[sim_i]['EA_ZnOS_l'],
                                      inputs[sim_i]['Nt_i_l'])]
        results[results_index][sim_T][sim_ill] = sim_data
        if sim_i % 10000 == 0:
            print('{}'.format(str(sim_i)))

    pickle.dump(results,open('results_redux.pickle',"wb"))

    for cond_i, cond_data in results.items():
        for T in temperatures:
            for ill in illuminations:
                if cond_data[T][ill] == {}:
                    if i in missing_sims.keys():
                        missing_sims[cond_i].append([T,ill])
                    else:
                        missing_sims[cond_i]=[[T,ill]]

    print("Number missing {}".format(len(missing_sims.keys())))
    pickle.dump(missing_sims,open('missing_sims.pickle','wb'))
