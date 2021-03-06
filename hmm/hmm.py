import numpy as np
import matplotlib.pyplot as plt

# TODOO 
# tranpose transition matrix

# #########
# ## HMM ##
# #########

# X_t = discrete hidden variable with N distinct values
# P(X_t | X_{t-1}) is independent of t

# time-independent transition probabilites (N * N matrix):
# A = {a_ij} = P(X_t = j | X_{t-1} = i)

# initial distribution
# pi_i = P(X_1 = i)

# Y_t = observation date points with K distinct values

# emission probabilities (N * K matrix)
# B = {b_j(y_i)} = P(Y_t = y_i | X_t = j)

# theta = (A, B, pi) = (p_transition, p_emission, p_initial)

# ##########################
# ## Baum-Welch algorithm ##
# ##########################

# Finds a local maximum for argmax_theta P(Y | theta)

# ----------------
# Expectation step
# ----------------

# alpha: forward probabilities, the probability of seeing y1, y2, ... , yt and being in state i at time t  (calculated recursively from initial estimate of the hidden state at the first data observation)

# alpha_i(t) = P(Y1 = y1, ... Yt = yt, Xt = i | theta)

# alpha_i(1) = pi_i * b_i(y_1)
# alpha_i(t+1) = b_i(y_{t+1}) * sum_{j=1}^N alpha_j(t) * a_ji

# -------------

# beta: backward probabilities, the probability of the ending partial sequence y_{t+1},...,y_{T} given starting state i at time t (calculated as conditional probability from the final data observation)

# beta_i(t) = P(Y_{t+1} = y_{t+1}, ... Y_T = y_T | X_t = i, theta)

# beta_i(T) = 1
# beta_i(t) = sum_{j=1}^N beta_j(t+1) * a_ij * b_j(y_{t+1})

# -------------

# gamma: estimate of probability of being in state i at t and j at t+1 given the observed sequence and parameters (combine forward and backward probabilities)

# gamma_ij(t) = P(X_t=i, X_{t+1}=j | Y, theta) / P(Y | theta) = alpha_i(t) * a_ij * beta_j(t+1) * b_j(y_{t+1}) / (sum over i and j)

# -------------

# delta: estimate of probability of being in state i at t given the observed sequence and parameters

# delta_i(t) = P(X_t=i ? Y ? theta) / P(Y | theta) = alpha_i(t) * beta_i(t) / (sum over i)

# -----------------
# Maximization step
# -----------------

# probability to be in state i in initial step
# pi_i = delta_i(t=1)

# transition probabilities
# a_ij = sum_{t=1}^{T-1} gamma_ij(t) / sum_{t=1}^{T-1} delta_i(t)

# emission probabilites
# b_i(v_k) = sum_{t=1}^T dirac(v_k, y_t) * delta_i(t) / sum_{t=1}^T delta_i(t)


class HMM():

    def __init__(self, p_transition, p_emission):
        '''
        Hidden Markov Model

        input:
            p_transition: initial transition probabilites, np.array of dimensions (n_hidden_states + 1) * (n_hidden_states + 1) (+1 is because of START/STOP state)
            p_emission: initial emission probabilities, np.array of dimensions n_observation_classes * n_hidden_states

        n_hidden_states is the number of different classes of hidden states
        n_observation_classes is the number of different classes of observations
        '''

        self.p_transition = p_transition
        self.p_emission = p_emission
        self.n_hidden_states = p_transition.shape[0] - 1
        self.n_observation_classes = p_emission.shape[0]

        # check probabilities sum to 1
        assert(np.allclose(np.sum(self.p_emission, axis=0), np.ones((self.n_hidden_states), dtype=np.float64)))
        assert(np.allclose(np.sum(self.p_transition, axis=0), np.ones((self.n_hidden_states + 1), dtype=np.float64)))

    def train(self, observations, n_iterations):
        '''
        input:
            observations: sequence of observations, 1D np.array of integers
            n_iterations: number of EM iterations, integer
        '''

        self.observations = np.asarray(observations)
        self.n_observations = len(observations)

        # convert observation datapoints to indices starting from 0
        self.observation_indices = self.renumber_observations(self.observations)

        # all unique observation labels
        self.observation_labels = list(np.unique(observations))
        assert len(self.observation_labels) <= self.n_observation_classes

        print('Training a HMM with {} hidden states and {} observation classes, using {} observation data points'.format(self.n_hidden_states, self.n_observation_classes, self.n_observations))

        # initialise
        self.forward = np.zeros((self.n_observations, self.n_hidden_states), dtype=np.float64)
        self.backward = np.zeros((self.n_observations, self.n_hidden_states), dtype=np.float64)
        self.gamma = np.zeros((self.n_observations, self.n_hidden_states, self.n_hidden_states), dtype=np.float64)
        self.delta = np.zeros((self.n_observations, self.n_hidden_states), dtype=np.float64)

        for i in range(n_iterations):
            self.expectation()
            self.maximization()

    def expectation(self):
        '''
        expectation step of Baum-Welch algorithm
        '''
        self.calc_forward_probabilities()
        self.calc_backward_probabilities()
        self.calc_gamma()
        self.calc_delta()

    def maximization(self):
        '''
        maximization step of Baum-Welch algorithm
        '''
        self.update_p_transition()
        self.update_p_emission()

    def calc_forward_probabilities(self):
        '''
        calculate forward probabilities (alpha)
        alpha has dimensions: self.n_observations * self.n_hidden_states
        '''

        # alpha_i(1) = pi_i * b_i(y_1)
        # P(x|START) probabilities are in final column of transition matrix
        self.forward[0] = self.p_transition[:-1, -1] * self.p_emission[self.observation_indices[0]]

        # alpha_i(t+1) = b_i(y_{t+1}) * sum_{j=1}^N alpha_j(t) * a_ji
        # don't use final row and column of p_transition because these are for STOP and START states
        for t in range(1, self.n_observations):
            self.forward[t] = self.p_emission[self.observation_indices[t]] * np.dot(self.p_transition[:-1, :-1], self.forward[t-1])

    def calc_backward_probabilities(self):
        '''
        calculate backward probabilities (beta)
        beta has dimensions: self.n_observations * self.n_hidden_states
        '''

        # beta_i(T) = 1
        self.backward[self.n_observations-1] = 1.0

        # beta_i(t) = sum_{j=1}^N beta_j(t+1) * a_ij * b_j(y_{t+1})
        for t in range(self.n_observations-2, -1, -1):
            self.backward[t] = np.sum(self.backward[t+1] * self.p_emission[self.observation_indices[t+1]] * np.transpose(self.p_transition[:-1, :-1]), axis=1)

    def calc_gamma(self):
        '''
        calculate gamma from forward and backward probabilites
        '''
        # don't include last observation because this is the terminal step,
        # therefore no transition to estimate
        for t in range(self.n_observations - 1):
            for i in range(self.n_hidden_states):
                for j in range(self.n_hidden_states):
                    self.gamma[t,i,j] = self.forward[t,i] * self.p_transition[j,i] * self.backward[t+1,j] * self.p_emission[self.observation_indices[t+1],j]
            denom = np.dot(self.forward[t], self.backward[t])
            self.gamma[t,:,:] /= denom
            #print(self.gamma[t,:,:])

    def calc_delta(self):
        '''
        calculate delta by summing over gamma
        '''

        self.delta = np.sum(self.gamma, axis=2)
        self.delta[-1] = self.forward[-1] / np.sum(self.forward[-1])
        #print(self.delta)

    def update_p_transition(self):
        '''
        update transition probabilities using the
        outputs of the expectation step
        '''

        # update pi (expected probability to be in state i at time 1
        self.p_transition[:-1, -1] = self.delta[0]

        # a_ij = sum_{t=1}^{T-1} gamma_ij(t) / sum_{t=1}^{T-1} delta_i(t)
        self.p_transition[:-1, :-1] = np.sum(self.gamma[:-1], axis=0) / np.sum(self.delta[:-1], axis=0).reshape((-1, 1))

        # print('self.p_transition')
        # print(self.p_transition)

    def update_p_emission(self):
        '''
        update emission probabilities using the
        outputs of the expectation step
        '''

        # b_i(v_k) = sum_{t=1}^T dirac(v_k, y_t) * delta_i(t) / sum_{t=1}^T delta_i(t)
        # make one-hot encoder (dirac delta) of observation data points
        dirac = np.zeros((self.n_observations, self.n_observation_classes), dtype=np.float64)
        dirac[np.arange(self.n_observations), self.observation_indices] = 1.0
        # TODOO vectorize
        temp = np.zeros((self.n_observations, self.n_hidden_states, self.n_observation_classes))
        for t in range(self.n_observations):
            temp[t] = np.outer(self.delta[t, :], dirac[t, :])

        self.p_emission = np.transpose(np.sum(temp, axis=0) / np.sum(self.delta, axis=0).reshape((-1, 1)))
        # print('self.p_emission')
        # print(self.p_emission)

    def renumber_observations(self, observations):
        '''
        we want to use observation data points directly as indices of the emission matrix
        returns set of observation data points numbered starting at 0
        '''

        return observations - min(observations)

    def print_parameters(self):
        '''
        pretty print model parameters
        '''

        columns = list(range(self.n_hidden_states)) + ['START']
        rows = list(range(self.n_hidden_states)) + ['STOP']
        self.pprint_matrix('transition probabilities', columns, rows, self.p_transition)

        columns = list(range(self.n_hidden_states))
        rows = self.observation_labels
        self.pprint_matrix('emission probabilities', columns, rows, self.p_emission)

    def pprint_matrix(self, title, columns, rows, values):
        '''
        pretty print a single matrix
        '''

        hstring = 'p(...|{})  '
        rstring = 'p({}|...)  '
        indexformatstring = '{{:{}s}}'
        entryformatstring = '{{:{}f}}'
       
        print() 
        print(title)

        header = ''.join([hstring.format(c) for c in columns])
        indices = [rstring.format(r) for r in rows]

        ave_header_width = int(len(header) / float(len(columns)))
        max_index_width = max(len(r) for r in indices)
        padding = ' ' * max_index_width

        print(padding + header)

        rowformatstring = ''.join([indexformatstring.format(max_index_width)] + [entryformatstring.format(ave_header_width) for c in columns])
        
        for index, p in zip(indices, values):
            print(rowformatstring.format(index, *p))

        print() 

    def viterbi(self, observations, plot=False):
        '''
        given transition and emission probabilities and a sequence of observed events,
        find the most likely sequence of hidden states
        input:
            observations (list of int): sequence of observed events
        The observations used to train the hmm (self.observations) are not used
        '''

        observations = np.asarray(observations)
        n_observations = len(observations)
        observation_indices = self.renumber_observations(observations)

        # check there aren't more unique values in the data than in the model
        assert(len(set(observation_indices))) <= self.n_observation_classes

        t1 = np.zeros((self.n_hidden_states, n_observations), dtype=np.float64)
        t2 = np.zeros((self.n_hidden_states, n_observations), dtype=np.int64)

        states = np.zeros(n_observations, dtype=np.int64)

        # t1_{i,1} = pi_i * b_i(y_1)
        t1[:, 0] = self.p_transition[:-1, -1] * self.p_emission[observation_indices[0], :]

        for t in range(1, n_observations):
            s = t1[:, t-1] * self.p_transition[:-1, :-1] * self.p_emission[observation_indices[t]].reshape(-1, 1)
            t1[:, t] = np.max(s, axis=1)
            t2[:, t] = np.argmax(s, axis=1)

        states[-1] = np.argmax(t1[:, -1])
        for t in range(n_observations-1, 0, -1):
            states[t-1] = t2[states[t], t]

        if plot:
            plt.plot(states, label='hidden states from viterbi')
            plt.plot(observations, label='observations')
            plt.legend()
            plt.show()

        return states
