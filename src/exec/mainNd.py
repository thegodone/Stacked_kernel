#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 10:08:28 2017

@author: bradley gram-hansen
"""
"""
1input dimension:  Deep GP for testing
Pseudo diagram:

input X, k1(x,x), h (hidden targets), x* test input

---------------- X -------------------
                 |
                 K1 | X hyperparams \theta1
                 |
                 K1, K2 | X kernel = K1 + K2 hyperparams \theta1 and \theta2
                 |
                 K1, K2, K3 | X kernel = K1 + K2 + K3 hyperparams \theta1, \theta2, \theta3
                 |
                 :
                 :    
When to stop: Using auto-correlation when the difference between 
the posterior mean and the orginba; data , is around the 0 axis, i.e
the abs(input data - posterior mean of layer) < 1 - white noise

The current model:

The current model now selects a new kernel optimises over that , then if there has been previous
kernels, adds its optimised self to that. Then we select a new kernel for the new layer ,
combine all the previous kernels and then repeat.
To do:
Add auto-correlation between the posterior mean and NRMSE function

"""


import GPy
import os
import platform
if(platform.system() != 'Darwin'):
    os.environ["CUDA_VISIBLE_DEVICES"]="2"
    import pycuda
from matplotlib import pyplot as plt
import numpy as np
import dataprocessing as dp
import import2d as impdata
import intialisations as intial
np.random.seed (seed = 1)
plt.style.use('ggplot')

try:
    plt.close("all")
except:
    pass


def combine_kernels(K1,K2):
    """Creates the composite kernel"""
    return K1 + K2

def regression(input_data,prev_k, parameters):
    """GP regression module - uses GPy
       - Generates a new kernel, made from the previous
       kernel. 
       - Carries out GP regression + optimisation
       - Does the prediction for the output of the layer
       - () represents for single input model
       
       Inputs:
           
       Xtrain     - N  x 3 (2) - split% training data
                           
       Ytrain     - N  x 1  - split% output from training data
                          
       Xval       - N* x 3 (2) - Future times to predict
       
       Yval       - N* x 1  - So that it can be passed to plotting() for 
                            verification
                   
       prev_k     - Linear combination of the previous kernels
       
      parameters   - contains all user and specified model parameters
       
       Output:
           
       input_data   - Updated Xtrain, Xtest data
       kernel       - linear combination of all previous kernels
   """
    no_points    = parameters[0]
    option       = parameters[1]
    no_dims      = parameters[2]
    model        = parameters[3]
    data_keys    = parameters[4]
    layer_no     = parameters[5]
    kernel_name  = parameters[6]
    
    if layer_no == 0:
        Xtest, Ytest,size_data   = impdata.import_data(no_points,option,no_dims,predict_points=True)
        parameters.append(size_data)
        Xtrain                   = input_data['train']
        input_data['val']        = Xtest
        Ytrain,mean,std          = dp.norm_data(input_data[data_keys[0]])
        input_data[data_keys[0]] = Ytrain
        Ytest                    = (Ytest - mean) / (std)
        input_data[data_keys[1]] = Ytest
    else:
        Xtrain                   = input_data['train']
        Ytrain                   = input_data[data_keys[0]]
        Xtest                    = input_data['val']
        Ytest                    = input_data[data_keys[1]]
#==============================================================================
    if layer_no >0:
        k,k_name,parameters[7][0],parameters[7][1]   = dp.select_kernel(no_dims)
        k_add                = combine_kernels(prev_k,k)
        parameters[6]        = kernel_name + ' ' +k_name
    else:
        k_add = prev_k
#==============================================================================
    dp.plot_cov_ft(k_add,Xtrain,parameters)
#==============================================================================
# Enables us to get kernel parameters
    kernel_params = k_add.param_array
#==============================================================================
    m = GPy.models.GPRegression(Xtrain, Ytrain, k_add) 
    if layer_no == 0:
        k_samp = k_add.K(Xtrain,Xtrain)
        m['Gaussian_noise.variance'] = 0.0001*np.amax(k_samp)
        
    m.optimize(max_iters = 1000)
    print(prev_k.param_array)
    post_mean, post_var = m.predict(Xtest)
    post_mean, full_cov = m.predict(Xtest,full_cov=True)
#    m.plot()
#==============================================================================
#    To stop information about what the mean thinks it is predicting from
#    disrupting future predictions, we instead return post_mean2 which is 
#    only based on the data that the observer knows about.
    if model == 'Aug_Duvenaud':
        post_mean2  = post_mean[0:no_points]
        post_mean2  = post_mean2
        if layer_no == 0:
            temp1 = Xtrain[0:no_points,:]
        else:
            temp1 = Xtrain[:,1:]
        input_data['train'] = np.column_stack((post_mean2,temp1))
        if layer_no == 0:
            temp2 = Xtest[:,:]
        else:
            temp2 = Xtest[:,1:]
        input_data['val']   = np.column_stack((post_mean,temp2))

#==============================================================================
#   Plotting, error and saving 
#==============================================================================
    nrmse = dp.error(post_mean,Ytest)
    data  = [input_data['train'], Ytrain, input_data['val'], Ytest, post_mean, post_var]

    dp.plotting2d(data,nrmse,parameters,full_cov)
    dp.save_data2d(input_data,nrmse,kernel_params,post_mean,post_var,parameters)
    return k_add,input_data

def layers(input_data, prev_kernel,parameters):
    """ 
        - Do GP regression + optimization
        - Make prediction for layer_output
    Inputs:
        
        input_data         - Dictionary containing all training and validation
                             data arrays for X inputs and Y outputs
        prev_Kernel        - Either composite or if first layer non-composite
        parameters
           
    Outputs:
            
        kernel             - composed of all previous kernels
        input_data 
     """    
    kernel,input_data = regression(input_data,prev_kernel,parameters)

    return input_data, kernel


def main():

#==============================================================================
# Initialisations
#==============================================================================
     Options      = ['2d','stock2d']
     option       = Options[0]
     Models       = ['Aug_Duvenaud','Single_inputs']
     model        = Models[0]
#==============================================================================
#    User intialiations

#    Split the perectage of training points that you want. 
     split        = 0.7
     runs         = 8
     # how many coloumns is your input data - will automate later
     no_x_dims    = 2
     no_dims      = 0
#==============================================================================

     if model == 'Single_inputs':
         no_dims  =  no_x_dims
     elif model  == 'Aug_Duvenaud':
         no_dims   = no_x_dims + 1 # if intial input is 2d --> prediction is 2d
     
     input_data, data_keys,no_points = intial.get_initial(split,option,no_dims,is2d = True)
     
     
     layer_no     =  0
     init_kernel,k_name,var,ls = dp.select_kernel(no_x_dims)
     parameters   = [no_points,option,no_dims ,model,data_keys,layer_no,k_name,[var,ls]]
#==============================================================================
# Stacked DeepGP loop
#==============================================================================

#NOTE: Layer_output contains the new outputs coloumn '0' and the original inputs
#      will always be in column '1' - python indexing.

     for ii in range(runs):
         layer_no = ii
         if ii > 0:
             print("Now in layer number {0}".format(layer_no))
             parameters[5]      = ii
             input_data, kernel = layers(input_data,kernel,parameters)

         else:
             input_data, kernel = layers(input_data, init_kernel,parameters)


main()

