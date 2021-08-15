import tellurium as te
import numpy as np

## run function
def run(model,targets, duration):
    model.integrator.absolute_tolerance = 1e-9
    model.integrator.relatice_tolerance = 1e-9
    results = model.simulate(start = 0, end = duration,steps = duration,
                             selections = targets)
    return results


def average(stack_results):
    """
    Averages the stack results of all iterations
    """
    mean_results = {} # mean results for each target
    stack = [] 
    for tag in PARAMS.targets:
        for i in range(PARAMS.replica_n):
            stack.append(stack_results[i][tag])

        stack = np.array(stack)
        mean_results.update({tag:list(np.mean(stack,axis=0))})
        stack=[] 
    return mean_results
def initial_conditions(model,calib_params):
    keys = list(PARAMS.free_params.keys())
    for i in range(len(keys)):
        free_param_name = keys[i]
        model[free_param_name] = calib_params[i]

def reset(model,params = None): # resets the given model and also sets those that cannot be reset by default
    model.reset()
    model['Mg_e_mM'] = 0.8
    if params == None:
        pass
    else:
        for key,value in params.items():
            model[key] = value
    
class PARAMS:
    targets = ['NFKB', 'pIKK', 'TAK1']
    duration = 1500
    free_params_model = { 'NEMO_IKK':[0,1000],
                          'k301':[0,1], # Mg diffusion should be really slow
                          'k302':[0,1],
                          'k303':[0,1],
                          'k304':[0,1],
                          'k308':[0,1000],
                          'k309':[0,1], # degradation of Mg_NEMO
                          'k310':[0,1000], # saturation coeff of NEMO_IKK
                          'Mg_NEMO':[0,10000],
                          'Mg_copy':[0,10000]}
    free_params_model_n = len(free_params_model.keys())

    free_params_observations = {'Quao_2021':[0.001,1000]}
    free_params_observations_n = len(free_params_observations.keys())

    free_params = {**free_params_model, **free_params_observations}
    replica_n = 1

Zhao_2021 = te.loadSBMLModel("Zhao_2021.xml") 
Mg_M = te.loadSBMLModel("Mg_M.xml") 




