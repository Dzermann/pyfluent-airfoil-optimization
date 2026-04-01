# -*- coding: utf-8 -*-
"""
    Created on Sat Nov  1 17:16:39 2025

    This is the file that uses all the functions created
    Reads the excel file, gets the values, then runs the mesh function for each
    row in the excel file, using the appropriate values.
    Blank values in the file are removed, so default values are used in the function

    The results will be written into a separate file - including time taken to mesh, C_d and quality

    - Dachi Dzeria

"""

import traceback
from time import time

import pandas as pd

from dachis_tools import read_table, save_inputs
from Meshing_Function import mesh

# Define the table address
file_loc = "./sim_data.xlsx"
sheet_name = "meshing_data"
table_name = "meshing_table"

# Read the table
table = read_table(file_loc, sheet_name, table_name)

total_rows = len(table)  # get the total number of rows
start_time = time()  # start the overall timer

# Remove trailing spaces
table.columns = table.columns.str.strip()

# Turn it into usable data for meshing
for count, row in enumerate(table.itertuples(index=False), start=1):
    try:
        # Convert row to dictionary, removing the empty values
        keyword_args = {k: v for k, v in row._asdict().items() if pd.notna(v)}

        progress = f"Initializing meshing - {count}/{total_rows}"
        print(progress)

        # Call the function using a dictionary
        skewness, orth_quality, cell_count, time_taken, folder_path, name = mesh(**keyword_args)
        inputs_file = f"{name}_inputs.txt"
        save_inputs(folder_path, inputs_file, keyword_args)

        elapsed = time() - start_time  # get elapsed time and print progress
        minutes = int(elapsed // 60)
        seconds = elapsed % 60

        progress = f"PASS: Row {count}/{total_rows} completed — {minutes} minutes and {seconds:.3f} seconds elapsed"
        print(progress)

    except Exception as e:
        # skip to next row
        print(f"FAIL: Row {count}/{total_rows} skipped. Error: {e}")
        print(traceback.format_exc())