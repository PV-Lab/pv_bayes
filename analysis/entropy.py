#!/usr/bin/env python

from __future__ import unicode_literals, division

__author__ = "Riley Brandt, Rachel Kurchin"
__date__ = "May 17, 2017"

import numpy as np
import pickle
import pandas as pd
import os

def make_df(probfile):
    """
    Make PMF into a DataFrame for easier manipulation
    """
    # load probability pickle file
    prob = pickle.load(open(probfile,'rb'))

    # Convert into dataframe
    mu_n_range = np.linspace(20,80,20)
    Nt_SnS_range = np.logspace(16,18,20)
    EA_ZnOS_range = np.linspace(3.4,4.3,15)
    Nt_i_range = np.logspace(10,14,16)

    probslist = np.zeros([len(prob),5])
    i = 0
    for mu_n in mu_n_range:
        for Nt in Nt_SnS_range:
            for EA in EA_ZnOS_range:
                for Nt_i in Nt_i_range:
                    probslist[i,0] = mu_n
                    probslist[i,1] = Nt
                    probslist[i,2] = EA
                    probslist[i,3] = Nt_i
                    probslist[i,4] = prob[i]
                    i += 1

    df = pd.DataFrame(probslist, columns=['mu','Nt','EA','Nt_i','prob'] )
    return df


def calc_entropy(pmf):
    """
    Calculate sum of P log P for entropy calculation. Assumes probabilities are propertly normalized
    """
    return -1.0 * np.sum([ pmf[k] * np.log(pmf[k]) for k in range(len(pmf)) if not pmf[k]==0]) / np.log(len(pmf))

if __name__ == "__main__":
    prob_files = os.listdir('probs/')
    prob_files.sort()

    num_obs = len(prob_files)

    # Parameter ranges used in the forward simulations
    num_mu, num_Nt, num_EA, num_Nt_i = 20, 20, 15, 16
    mu_n_range = np.linspace(20, 80, num_mu)
    Nt_SnS_range = np.logspace(16, 18, num_Nt)
    EA_ZnOS_range = np.linspace(3.4, 4.3, num_EA)
    Nt_i_range = np.logspace(10, 14, num_Nt_i)
    num_simulations = num_mu * num_Nt * num_EA * num_Nt_i

    # where the entropy numbers will go:
    total_entropies, mu_entropies, Nt_entropies, EA_entropies, Nt_i_entropies = np.zeros(num_obs), np.zeros(num_obs), \
                                                                np.zeros(num_obs), np.zeros(num_obs), np.zeros(num_obs)


    # Iterate over observations, for now in sequential order, update the Bayes inference and calculate entropy
    for i in range(num_obs):
        df = make_df('probs/'+prob_files[i])

        total_probs, mu_probs, Nt_probs, EA_probs, Nt_i_probs = df['prob'].to_dict().values(), \
                                                                dict.fromkeys(mu_n_range, 0), \
                                                                dict.fromkeys(Nt_SnS_range, 0), \
                                                                dict.fromkeys(EA_ZnOS_range, 0), \
                                                                dict.fromkeys(Nt_i_range, 0)

        # For all except total, sum out other dimensions.
        for j in range(num_simulations):
            # Pull values for each parameter
            mu_j, Nt_j, EA_j, Nt_i_j, prob_j = df.loc[j]['mu'], df.loc[j]['Nt'], df.loc[j]['EA'], \
                                                df.loc[j]['Nt_i'], df.loc[j]['prob']

            # Add probability to appropriate tally
            mu_probs[mu_j] += prob_j
            Nt_probs[Nt_j] += prob_j
            EA_probs[EA_j] += prob_j
            Nt_i_probs[Nt_i_j] += prob_j

        # Compute the entropies from marginalized PMF
        total_entropies[i] = calc_entropy(total_probs)
        mu_entropies[i] = calc_entropy(mu_probs.values())
        Nt_entropies[i] = calc_entropy(Nt_probs.values())
        EA_entropies[i] = calc_entropy(EA_probs.values())
        Nt_i_entropies[i] = calc_entropy(Nt_i_probs.values())

    # Save entropies
    if not os.path.exists('entropies'):
        os.mkdir('entropies')

    pickle.dump(total_entropies, open('entropies/total_entropies.pickle','wb'))
    pickle.dump(mu_entropies, open('entropies/mu_entropies.pickle','wb'))
    pickle.dump(Nt_entropies, open('entropies/Nt_entropies.pickle','wb'))
    pickle.dump(EA_entropies, open('entropies/EA_entropies.pickle','wb'))
    pickle.dump(Nt_i_entropies, open('entropies/Nt_i_entropies.pickle','wb'))
