# -*- coding: utf-8 -*-
"""
Created on Thu Jan 29 09:17:46 2026

@author: Dachi Dzeria

Code created to analyze the response surface using python for ansys fluent meshing

"""

import optuna
import math
from optuna.samplers import TPESampler
from Meshing_Function import mesh

file_path = "./airfoil/naca0012.scdocx" # replace with the path to your airfoil file, e.g. "./airfoils/naca0012.scdocx"
chord_len = 1
nickname = "normalized_2"
processor_count = 6
TARGET_TRIALS = 500

airfoil = file_path.rsplit('/', 1)[-1] # isolates the file name
airfoil = airfoil.rsplit('.', 1)[0]

# make a new database based on airfoil
storage_url = f"sqlite:///db.sqlite3_{airfoil}_{nickname}"

# Make a normalization function to normalize the results
# and avoid weighting one result over the other
def normalize(value, target, minimum):
    return (value - minimum) / (target - minimum)

# Define geometric constraints to prune invalid mesh settings
def constraints(trial):
    p = trial.params
    
    Surface_Min_Size = p["Boi_1_Size"] / p["Min_Max_Ratio"]
    c1 = Surface_Min_Size - p["Surface_Max_Size"]
    c2 = Surface_Min_Size - p["Boi_1_Size"]

    return [c1, c2] # Values > 0 are considered violations

def objective(trial):

    Boi_Surface_Ratio = trial.suggest_float("Min_Max_Ratio", 1, 5)
    Boi_1_Size = 1/100
    
    # Calculate derived variable
    Surface_Min_Size = Boi_1_Size / Boi_Surface_Ratio
    
    p = { # define the parameters to input into the meshing function
        "Boi_1_Size": Boi_1_Size,
        "Surface_Rate": trial.suggest_float("Surface_Rate", 1.01, 1.5),
        "Surface_Min_Size": Surface_Min_Size,
        "Surface_Max_Size": trial.suggest_float("Surface_Max_Size", 0.5, 2.5),
        "Surface_Curvature_Normal_Angle": trial.suggest_int("Surface_Curvature_Normal_Angle", 6, 15),
        "Bl_First_Height": 10**-5,
        "Bl_Rate": trial.suggest_float("Bl_Rate", 1.01, 2),
        "Volume_Fill_Size": trial.suggest_float("Volume_Fill_Size", 0.5, 5),
        "file_path": file_path,
        "nickname": nickname,
        "airfoil": airfoil,
        "processor_count": processor_count
    }
    try:
        # Execute your mesh function
        skewness, orth_quality, cell_count, time_taken, folder_path, name  = mesh(**p)
        
        # if any of the outputs are none the meshing failed
        # so it prunes the result
        if skewness is None or time_taken is None:
            # This tells Optuna the configuration was invalid/failed
            raise optuna.exceptions.TrialPruned()
        if orth_quality is None:
            orth_quality = 0 # assume orth_quality is 0 if it failed to read
        # changing the power gives this value more weight
        # by punishing bad  valeus and rewarding
        # good values more
        skewness = normalize(skewness, 0.7, 0) ** 4
        orth_quality = normalize(orth_quality, 0.1, 0)
        cell_count = normalize(cell_count, 100000, 0) / 100
        
        # overall_score = -skewness*2 + orth_quality - cell_count
        
    except Exception as e:
        # Catch "hard" crashes, print error for log, and prune trial
        print(f"Trial {trial.number} failed: {e}") 
        raise optuna.exceptions.TrialPruned()
    
    return skewness, orth_quality, cell_count

# Initialize the study - Genetic alg
sampler = TPESampler()

study = optuna.create_study(
    study_name=f"{airfoil}_{nickname}_study",  # Must keep this name consistent to resume
    storage=storage_url,
    load_if_exists=True, # Crucial: loads existing data if the file exists
    directions=["minimize", "maximize", "minimize"],
    sampler=sampler
)

# Queue the good parameters so it goes from there
good_params = {
    "Min_Max_Ratio": 4,
    "Boi_1_Size": 0.010552022465702419,
    "Surface_Rate": 1.1183946005073413,
    "Surface_Max_Size": 0.5094340457762154,
    "Surface_Curvature_Normal_Angle": 7,
    "Bl_First_Height": 8.706952010554701e-05,
    "Bl_Rate": 1.9964829715769288,
    "Volume_Fill_Size": 1.6340031133912438
}

# Count trials that are finished (Completed, Pruned, or Failed)
# We filter out 'WAITING' or 'RUNNING' to ensure accurate counting on resume
finished_trials = [t for t in study.trials if t.state.is_finished()]
n_current = len(finished_trials)

remaining = TARGET_TRIALS - n_current

if n_current == 0: # if this is the first trial
   print("Starting trials...")
   print("Queued good params...")
   study.enqueue_trial(good_params)
   study.optimize(objective, n_trials=remaining)
   
elif remaining > 0: # if there are more than 0 trials completed, execute the remaining ones
    print(f"Study has {n_current} finished trials. Executing {remaining} more...")
    study.optimize(objective, n_trials=remaining)
 
else: # if all trials have been completed
    print(f"Study limit reached ({n_current}/{TARGET_TRIALS} trials completed).")

# Extract relative importance of each input for Output 1
importance = optuna.importance.get_param_importances(study, target=lambda t: t.values[0])

best_trials = study.best_trials

best_skew_trial = min(best_trials, key=lambda t: t.values[0])
best_orth_trial = max(best_trials, key=lambda t: t.values[1])

# %%
# Plottingskewness = skewness * 2
from optuna.visualization import plot_param_importances
from optuna.visualization import plot_pareto_front
# import plotly.io as pio

plot_pareto_front(study).show()

plot_param_importances(study)
fig = plot_pareto_front(study)

# # Plot in browser
# pio.renderers.default = 'browser'
plot_pareto_front(study).show()

# # Plot in matplotlib
# from optuna.visualization.matplotlib import plot_pareto_front
# plot_pareto_front(study)