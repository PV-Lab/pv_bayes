#!/usr/bin/env python

from __future__ import unicode_literals, division

__author__ = "Riley Brandt, Rachel Kurchin"
__date__ = "May 17, 2017"

import numpy as np
import pickle
import math
import os

def normalize(array):
    """
    This function normalizes a numpy array to sum up to 1 (L1 norm)
    """
    return array/array.cumsum()[-1]

def likelihood(I_meas, V_meas, T_meas, ill_meas, I_model, I_error):
    """
    Takes observation J(V,T,i) and calculation results and compute likelihood
    using an assumed error in the current
    """

    # Take a uniform initial pdf
    lkl = normalize(np.ones(len(I_model)))

    # Assume we feed in an observation at exactly a bias we simulated at
    # TODO: Implement interpolation for biases

    # Iiterate over each point in parameter space to calculate a likelihood, assuming a Gaussian distribution
    for i in range(len(lkl)):
        V_index = np.where(I_model[i][T_meas][ill_meas][1] == V_meas)[0][0]
        lkl[i]= 1.0/(1.772 * I_error) * math.exp(-1.0 * (I_meas - I_model[i][T_meas][ill_meas][0][V_index])**2 /
                                                 (2*I_error**2))

    return lkl

def read_obs(obs_file):
    """
    Function to read in observation data from text file
    each line should be formatted as "T   ill   V   J"
    """
    f = open(obs_file, 'r' )
    f.readline() # there's a header with column labels
    obs_T, obs_ill, obs_V, obs_J = [], [], [], []
    for line in f:
        l=line.split()
        obs_T.append(float(l[0]))
        obs_ill.append(float(l[1]))
        obs_V.append(float(l[2]))
        obs_J.append(float(l[3]))
    f.close()
    return (obs_T, obs_ill, obs_V, obs_J)

if __name__ == "__main__":
    # Read in simulation results (produced by process_pickles.py)
    print 'Reading in results file...'
    results = pickle.load(open('../running_sims/pickles/simulation_all_results.pickle','rb'))

    # make a uniform prior
    print 'Making (uniform) prior...'
    prob = normalize(np.ones(len(results)))

    # T_ill conditions based on observation files
    print 'Reading in observations and running inference...'
    conds = ['280_31', '280_108', '300_31', '300_108', '320_31', '320_108']

    if not os.path.exists('probs'):
        os.mkdir('probs')

    for i, cond in enumerate(conds):
        # read in observations
        obs_T, obs_ill, obs_V, obs_J = read_obs('observation_data/obs_'+cond+'.txt')

        # Run Bayesian analysis
        for j in range(len(obs_J)):

            # Estimate error, noting that since J(V) is roughly exponential, it should be proportional
            # (ultimate PMF's are not terribly sensitive to these parameters)
            Jerr = np.amax(np.array([0.5, np.abs((obs_J[j]+19.5)*0.15)]))

            prob = normalize(np.multiply(prob, likelihood(obs_J[j], obs_V[j], obs_T[j], obs_ill[j], results, Jerr)))

            # Save a pickle for each observation fed in - each "probability frame"
            pickle.dump(prob, open('probs/prob_%(#)03d'%{"#":14*i+j}+'_'+cond+'_obs_'+str(j)+'.pickle','wb'))

