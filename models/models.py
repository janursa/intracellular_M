import tellurium as te
import numpy as np
from pathlib import Path
import os
import sys
import random
import json
dir_file = Path(__file__).resolve().parent
main_dir = os.path.join(dir_file,'..')
sys.path.insert(0,main_dir)
from tools import common,dirs
from data import observations
def retrieve_activation_stimuli():
    with open(dirs.dir_activation_stimuli) as ff:
      activation_s = json.load(ff)
    return activation_s


class Macrophage:
  @staticmethod
  def create_sbml_model(model_t):
    if model_t == 'M1':
      return te.loadSBMLModel(dirs.dir_M1_model)
    elif model_t == 'IL8':
      return te.loadSBMLModel(dirs.dir_IL8_model)
    elif model_t == 'combined':
      return te.loadSBMLModel(dirs.dir_model)
    elif model_t == 'LPS':
        return te.loadSBMLModel(dirs.dir_LPS_model)
    elif model_t == 'Zhao':
        return te.loadSBMLModel(dirs.dir_Zhao_model)
    elif model_t == 'IL6':
        return te.loadSBMLModel(dirs.dir_IL6_model)
    elif model_t == 'ILs':
        return te.loadSBMLModel(dirs.dir_ILs_model)
    else:
      raise ValueError('{} is not defined'.format(model_t))

  activation_s = retrieve_activation_stimuli()

  def __init__(self,model_t):
    self.model = Macrophage.create_sbml_model(model_t)


    
  def simulate_studies(self,params,studies):
      """
      Simulate all studies
      """
      sims = {}
      for study_tag,study_item in studies.items():
          try:
            results = self.simulate_study(study_tag=study_tag,study=study_item,params=params)
          except common.InvalidParams:
            raise common.InvalidParams()
          sims[study_tag]= results
      # print(results)
      # sys.exit(2)
      return sims

  def simulate_study(self,study_tag,study,params):
      """
      Simulte one study
      """
      selections = study['selections']
      duration = study['duration']
      IDs = study['IDs']
      results = {}
      for ID in IDs:
          inputs = study[ID]['inputs']
          try:
            ID_results = self.simulate(study_tag = study_tag,params=params,inputs=inputs,selections=selections,duration=duration,activation=study['activation'])
          except common.InvalidParams:
            raise common.InvalidParams()
          results[ID] = ID_results
      
      return results
  # def cost_study(self,study,study_results):
  #     """
  #     calculates cost values for each ID of the given study
  #     """
  #     selections = self.observations[study]['selections']
  #     errors = {}
  #     for ID, ID_results in study_results.items():
  #         ID_observations = self.observations[study][ID]['expectations']
  #         target_errors = {}
  #         for target in selections.keys():
  #             abs_diff =abs(np.array(ID_results[target])-np.array(ID_observations[target]['mean']))
  #             means = [ID_observations[target]['mean'],ID_results[target]]
  #             mean = np.mean(means)
  #             target_error = abs_diff/mean
  #             target_errors[target] = target_error
  #         errors[ID] = target_errors
  #     return errors
  # def cost_studies(self,studies_results):
  #     """
  #     Calculates cost values for all studies
  #     """
  #     errors = {}
  #     for study,study_results in studies_results.items():
  #         errors[study] = self.cost_study(study,study_results)
  #     return errors
  def sort_sim_vs_exp(self,sims,studies):
      """
      sort simulation results along side the experiments
      """
      sorted_results = {}
      for study_tag in studies.keys():
        study_item = studies[study_tag]
        sims_results = sims[study_tag]

        sorted_results[study_tag] = {}
        for ID, ID_results in sims_results.items():
            for target,target_results in ID_results.items():
              if target not in sorted_results[study_tag]:
                sorted_results[study_tag][target] = {'sim' : [],'exp':[]}

              sorted_results[study_tag][target]['sim'] += list(target_results)
              sorted_results[study_tag][target]['exp'] += study_item[ID]['expectations'][target]['mean']
              
      return sorted_results
  @staticmethod
  def quantitative_cost_func(exp,sim): # calculates error for quantitative measurements
    diff = abs(exp - sim)
    # mean = 0.5*(exp+sim)
    mean = exp
    errors = diff/mean
    error = np.mean(errors)
    if error <0:
      error = 1000
      # raise ValueError()
    if error == None:
      raise ValueError('none error')
    return error
  @staticmethod
  def limit_cost_func(exp,sim): # calculates error for given limits 
    error_upper = 0
    error_lower = 0
    if max(sim)>exp[1]:
      diff = abs(max(sim)-exp[1])
      mean = exp[1]
      error_upper = diff/mean
    if min(sim)<exp[0]:
      diff = abs(min(sim)-exp[0])
      mean = exp[0]
      error_lower = diff/mean
    error = error_upper + error_lower
    return error
  @staticmethod
  def run_sbml_model(model_sbml,selections,duration,params={},study_tag='',activation=False,steps=None):
    """ run sbml model
    """

    model_sbml.resetToOrigin()   
    if activation == True:
      params = {**params,**Macrophage.activation_s}
    for key,value in params.items():
      model_sbml[key] = value
    if steps == None:
        steps = duration
    results = model_sbml.simulate(start = 0,end = duration,steps =steps,selections = ['TIME']+selections)
    return results
  @staticmethod
  def run_sbml_model_recursive(model_sbml,selections,duration,params={},study_tag='',activation=False):
    """ run sbml model in a recursive way by change the step size
    """

    attp = 0
    steps = duration
    while True:
      try:
        results = Macrophage.run_sbml_model(model_sbml=model_sbml,selections=selections,duration=duration,params=params,study_tag=study_tag,activation=activation, steps = steps)
        break
      except RuntimeError:
        attp+=1
          
      if attp > 2 :
          print('Invalid parameter set')
          print(params)
          raise common.InvalidParams('run model didnt converge')
      steps = random.randint(int(duration/2),duration)
    
    return results
  def calculate_cost(self,results,studies):
    costs = {}
    for study_tag,study_result in results.items():
      
      costs[study_tag] = {}
      for target,target_results in study_result.items():          
        exps,sims = np.array(target_results['exp']),np.array(target_results['sim'])
        ##---- for certain studies, the simulation results should be normalized ----##
        if study_tag in observations.normalized_obs:
            n_sims,n_exps = common.normalize(study_tag=study_tag,target=target,sims=sims,exps=exps)
        else:
            n_sims,n_exps = sims,exps
            
        error = self.quantitative_cost_func(exp=n_exps,sim=n_sims)
        if (target == 'nTRPM_n' or target == 'nTRPM' or target == 'nM7CK_n' or target == 'anH3S10') and max(sims)>10: # to control the max values these factors can have
            error = max(sims)
        
        costs[study_tag][target] = error
    mean_errors = []

    for study_tag,study_costs in costs.items():
      study = studies[study_tag]
      errors = list(study_costs.values())
      if 'weight' in study:
        weight = study['weight']
      else:
        weight = 1
      mean_errors.append(np.mean(errors)*weight)
    return costs,np.mean(mean_errors)

  def simulate(self,study_tag,params,inputs,selections,duration,activation):
      
    if duration == None:
      raise ValueError('Value of duration is none')
    target_keys = list(selections.keys())
    params = {**params,**inputs}
    try:
      # results_raw = Macrophage.run_sbml_model(model_sbml=self.model,params = params,duration=duration+1,selections=target_keys,study_tag=study_tag,activation=activation)

      results_raw = Macrophage.run_sbml_model_recursive(model_sbml=self.model,params = params,duration=duration+1,selections=target_keys,study_tag=study_tag,activation=activation)
    except common.InvalidParams:
      raise common.InvalidParams()
    results ={}
    for key in target_keys:
      measured_times = selections[key]
      measured_times_indices = []
      for measured_time in measured_times:
        measured_times_indices.append(common.indexing(measured_time,results_raw['time'])) 
      results[key] = results_raw[key][measured_times_indices]
    return results
  def run(self,params,studies):
    flag = 1
    try:
      sims = self.simulate_studies(params,studies)
    except common.InvalidParams:
      # mean_cost = 1+random.random()
      mean_cost = 100
      target_costs =None
      flag = 0
    if flag == 1:
      sims_vs_exps = self.sort_sim_vs_exp(sims,studies)
      target_costs,mean_cost = self.calculate_cost(sims_vs_exps,studies)
    # print(sims)
    return mean_cost,target_costs
