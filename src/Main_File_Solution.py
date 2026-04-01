# -*- coding: utf-8 -*-
"""
    Created on Thu Dec 25
    This is the file that uses all the functions created
    Reads the excel file, gets the values, then runs the solution function for each
    row in the excel file, using the appropriate values.
    Blank values in the file are removed, so default values are used in the function

    The results are written into a separate file - including C_l and C_d values

    - Dachi Dzeria

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
from Solution_Function import solve


# %%
# Define the table address
file_loc = "./sim_data.xlsx"
sheet_name = "solution_data"
table_name = "solution_table"

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

        progress = f"Initializing solution - {count}/{total_rows}"
        print(progress)

        # Call the function using a dictionary
        folder_path, report_1_name, report_2_name, name = solve(**keyword_args)

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

        # all of these files are generated in the python directory
        # this function copies them to the correct folder
        move_file(report_1_address, folder_path)
        move_file(report_2_address, folder_path)

        for path in plot_paths:
            move_file(path, folder_path)

        elapsed = time() - start_time  # get elapsed time and print progress
        minutes = int(elapsed // 60)
        seconds = elapsed % 60

        progress = f"PASS: Row {count}/{total_rows} completed — {minutes} minutes and {seconds:.3f} seconds elapsed"
        print(progress)

    except Exception as e:
        # skip to next row
        print(f"FAIL: Row {count}/{total_rows} skipped. Error: {e}")
        print(traceback.format_exc())