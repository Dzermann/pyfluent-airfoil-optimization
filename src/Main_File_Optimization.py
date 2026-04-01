"""
Created on Fri Feb 13 14:19:34 2026

@author: Dachi Dzeria

This file reads the sim_data.xlsx file, finds the adjoint_data
sheet and adjoint_table table, then runs the optimize function.
It saves the inputs and does nothing else.
"""

import os
import traceback
from time import time

import pandas as pd

from dachis_tools import (
    read_table,
    move_file,
    save_inputs,
    plot_and_save_steady,
    plot_and_save_transient
)
from Adjoint_Function import optimize

# %%
# Define the table address
file_loc = "./sim_data.xlsx"
sheet_name = "adjoint_data"
table_name = "adjoint_table"

# Read the table
table = read_table(file_loc, sheet_name, table_name)

total_rows = len(table)  # get the total number of rows
start_time = time()  # start the overall timer

# Remove trailing spaces
table.columns = table.columns.str.strip()

current_address = os.path.dirname(os.path.abspath(__file__))

# Turn it into usable data for solving
for count, row in enumerate(table.itertuples(index=False), start=1):
    try:
        # Convert row to dictionary, removing the empty values
        keyword_args = {k: v for k, v in row._asdict().items() if pd.notna(v)}

        progress = f"Initializing optimization - {count}/{total_rows}"
        print(progress)

        # Call the function using a dictionary
        folder_path, report_1_name, report_2_name, name = optimize(**keyword_args)

        # Saving the inputs
        inputs_file = f"{name}_inputs.txt"
        save_inputs(folder_path, inputs_file, keyword_args)

        # Call the function to move the reports to the right folder
        report_1_address = os.path.join(current_address, report_1_name)
        report_2_address = os.path.join(current_address, report_2_name)

        # Graph the reports
        if keyword_args.get('transient', False):
            plot_paths = plot_and_save_transient([report_1_address, report_2_address])
            print(f"PASS: Transient plots generated at {report_1_address}")
        else:
            plot_paths = plot_and_save_steady([report_1_address, report_2_address])
            print(f"PASS: Steady state plots generated at {report_1_address}")

        # move the c_d/c_l files to the folder path
        # this will leave a copy of those files in the
        # directory where the .py file is stored
        # I could make it delete the old files but I
        # did not want to programically delete random things
        move_file(report_1_address, folder_path)
        move_file(report_2_address, folder_path)

        elapsed = time() - start_time  # get elapsed time and print progress
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        
        for path in plot_paths:
            move_file(path, folder_path)
        
        progress = f"PASS: Row {count}/{total_rows} completed — {minutes} minutes and {seconds:.3f} seconds elapsed"
        print(progress)

    except Exception as e:
        # skip to next row
        print(f"FAIL: Row {count}/{total_rows} skipped. Error: {e}")
        print(traceback.format_exc())
