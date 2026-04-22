# Aero-Opt

> **Automated CFD-based aerodynamic optimisation for airfoils, across subsonic, transonic, and supersonic flow regimes.**

Aero-Opt is a Python pipeline that automates meshing, solving, and adjoint-based shape optimisation of 2D/3D airfoils in Ansys Fluent. It was developed as the computational core of a BEng(Hons) thesis at South East Technological University Carlow, and is released here so that other researchers and students can replicate, extend, or adapt the workflow to their own aerodynamic-optimisation problems.

> **Note on authorship.** This README and all files in the `supplementary_tools` folder (all `.html` files) are AI written. `dachis_tools.py` was written with AI assistance. All other scripts, along with the thesis itself, were written manually by the author. This file is project documentation only, and the AI written code are supplementary materials to the main code. It is not part of the thesis submission, so AI involvement in its prose does not constitute plagiarism under the academic-integrity policy referenced in the thesis.

---

## What it does

Given an Excel table of input conditions, Aero-Opt will:

1. **Mesh** a SpaceClaim airfoil geometry in Ansys Fluent Meshing with configurable boundary-layer resolution, volume-fill method, and y⁺ targets.
2. **Solve** the flow field at specified altitude, Mach number, and angle of attack, computing drag and lift coefficients and exporting pressure/Mach contours, residuals, and y⁺ plots.
3. **Optimise** the airfoil shape using the Ansys Fluent Adjoint Solver, either preserving chord length or allowing it to vary.

Each step is driven from a single row in an Excel input table, so batches of hundreds of simulations can run unattended.

---

## Why it exists

Adjoint-based airfoil optimisation is well-established in the literature, but existing workflows are (a) locked inside commercial GUIs, (b) tied to a single flow regime, or (c) not reproducible across runs. Aero-Opt was written to address all three:

- **GUI-free operation.** Every setting exposed in the Fluent/Meshing/Adjoint GUIs is parameterised. No mouse clicks after the input file is written.
- **Regime-agnostic.** The same three functions handle subsonic (M ≈ 0.2), transonic (M ≈ 0.85), and supersonic (M = 1.8) cases. Settings that depend on regime are selected automatically from the inputs.
- **Fully reproducible.** Every run saves its complete input dictionary to a `.txt` file alongside the results. Re-running a given input file produces an identical simulation.

The thesis this code supports used Aero-Opt to run ≈500 simulations in ≈400 computing hours on a single laptop, with no manual intervention after the input tables were populated.

---

## Headline results from the thesis

Aero-Opt was used to optimise four airfoils across five flight regimes. All five cases produced lift-to-drag-ratio improvements between 44% and 689%.

The most notable result was the **Boeing BACXXX airfoil** (used on the 747-400), where the variable-length optimisation:

- Reduced drag coefficient by **88.5%**
- Increased lift-to-drag ratio by **658%**
- **Eliminated the transonic shock wave entirely**

Projected to the active Boeing 747-400 and Cessna 172 fleets, these aerodynamic improvements correspond to approximately **1.9 million tonnes of CO₂ avoided per year** at global adoption. Full results, validation data, and discussion are in the thesis (see *Citation* below).

---

## Installation

### Prerequisites

| Dependency | Version used |
|---|---|
| Ansys Fluent (with Adjoint Solver licence) | 2025 R2 |
| Ansys SpaceClaim | 2025 R2 |
| Python | 3.11.9 |
| PyFluent | 0.37.1 |
| Windows PowerShell | 7.5.4 (any shell works) |

Earlier Ansys versions (2023 R2+) should work but are untested. PyFluent API changes between versions — pin the version specified above for guaranteed compatibility.

### Python dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` covers:

```
ansys-fluent-core==0.37.1
pandas
matplotlib
openpyxl
numpy
Pillow
```

### Ansys licence

Aero-Opt requires an active Ansys Fluent licence with access to the **Adjoint Solver** module. Not all academic licences include the Adjoint Solver — check with your Ansys administrator before running optimisation jobs.

---

## Quick start

### 1. Prepare the geometry

Import your airfoil coordinates into SolidWorks as an XYZ curve and wrap it in a domain bounded by a spline through `(−20, 15)`, `(10, 0)`, `(−20, −15)` (see thesis §3.2.2 Figure 3-2). Export as `.STEP`, then open in Ansys SpaceClaim and name the surfaces.

**3D cases** (extrude the domain 0.1 m in Z first — `mesh_width` in `solve()` must match whatever thickness you use):

- `upper`, `lower` — airfoil surfaces
- `te` — trailing-edge surface, only if the airfoil has an open trailing edge (set `has_te=True` in `meshing_table`)
- `farfield` — outer boundary
- `sym1`, `sym2` — the two XY symmetry planes

**2D cases**:

- `upper`, `lower` — upper and lower halves of the airfoil curve
- `farfield` — the edges of the XY face
- `surface` — the XY face itself

Save as `.scdocx`. See thesis §3.2.1–3.2.3 for screenshots.

> **2D vs 3D is auto-detected** from the substring `2D` (case-insensitive) in either the `airfoil` value or the `file_path`. Follow the thesis convention and append `_2D` to the airfoil name for 2D cases; omit it for 3D.

### 2. Populate the input table

Open `sim_data.xlsx`. Three sheets drive the three scripts:

| Sheet | Table | Used by |
|---|---|---|
| `meshing_data` | `meshing_table` | `Main_File_Meshing.py` |
| `solution_data` | `solution_table` | `Main_File_Solution.py` |
| `adjoint_data` | `adjoint_table` | `Main_File_Optimization.py` |

Each row = one simulation. Leave any cell blank to use the function default (see [Default values](#default-values) below for the full listing).

Minimum required columns for each stage:

- **Meshing** — `file_path` (path to `.scdocx`)
- **Solving** — `file_path` (path to `.msh.h5`), `altitude`, `mach_num`, `aoa`, `chord_len`
- **Optimisation** — `file_path` (path to `.cas.h5`; a same-stem `.dat.h5` must sit alongside it), `optimize_target`, `target_change`

### 3. Run

> **The three stages are sequential, not independent — you cannot launch them all at once.** Each stage consumes the files produced by the previous one: `Main_File_Meshing.py` emits a `.msh.h5` that `Main_File_Solution.py` needs, and `Main_File_Solution.py` emits a `.cas.h5` that `Main_File_Optimization.py` needs. After each stage finishes, open `sim_data.xlsx` and paste the output paths from the previous stage into the `file_path` column of the next sheet before launching the next script.
>
> Run all commands from the repo root (the scripts read `./sim_data.xlsx` from the current working directory):

```powershell
# Step 1: Generate meshes for every row in meshing_table
python src/Main_File_Meshing.py

# Step 2: Paste the generated .msh.h5 paths into solution_table, then:
python src/Main_File_Solution.py

# Step 3: Paste the generated .cas.h5 paths into adjoint_table, then:
python src/Main_File_Optimization.py
```

Each script iterates through its table, skipping any row that errors (so one bad row doesn't kill a 200-row batch). Progress is printed as each row completes.

---

## Output structure

Each simulation creates a timestamped folder in the working directory, named `{airfoil}_{nickname}_{identifier}_{timestamp}`. Contents vary by stage but include:

- **Meshing** — `.msh.h5` mesh file, input record (`.txt`), solver log (`.txt`)
- **Solving** — `.cas.h5` / `.dat.h5` case and data files, drag/lift reports (`.out`), Matplotlib plots of drag/lift convergence (`.png`), Mach and pressure contour screenshots (`.png`), residuals plot (`.png`), y⁺ plot (`.png`), mass-flow record (`.flp`), solver log (`.txt`)
- **Optimisation** — all of the above, plus: animated GIFs of mesh deformation and Mach/pressure evolution, optimised coordinates (`.dis`), per-iteration screenshots of mesh/Mach/pressure, final `.cas.h5`/`.dat.h5` of the optimised geometry

---

## Recommended solver settings

From the thesis's side-trials (§4.6):

| Setting | Recommended value | Reason |
|---|---|---|
| Volume mesh type (3D) | Polyhedra | Smallest cell count, fastest solve (§4.6.2) |
| y⁺ (2D) | < 1 | Solve time largely unaffected by first-layer height (§4.6.1) |
| y⁺ (3D, transonic) | < 1 | Buffer-region values cause convergence failures at transonic Mach |
| y⁺ (3D, subsonic/supersonic) | < 30 | ±5% accuracy, much faster than y⁺ < 1 |
| Flow scheme | Coupled | Only scheme that consistently converged in < 2000 iterations (§4.6.6) |
| Turbulence model (unknown flow) | k-ω GEKO | y⁺-insensitive, stable across regimes (§4.6.5) |
| Turbulence model (known-attached) | Spalart-Allmaras | Fastest convergence for attached flows |
| Solver type | Pressure-based | Required by Adjoint Solver; adequate for all tested regimes |
| Optimisation dimension | 2D first, verify in 3D | 3D optimisation is orders of magnitude slower; 2D results validated against 3D solve |

The above are defaults in the functions, so leave the relevant columns blank in the input sheet unless deviating.

---

## Default values

Every column in `sim_data.xlsx` maps to a keyword argument of the matching function. Leaving a cell blank falls back to the default listed below. Parameters and defaults are sourced from the function signatures in `src/`; the Notes column is condensed from the thesis's Appendix D (Tables 8-16 to 8-18).

<details>
<summary><code>mesh()</code> — <code>src/Meshing_Function.py</code> (37 optional parameters)</summary>

| Parameter | Default | Notes |
|---|---|---|
| `nickname` | `''` | User-specified identifier appended to output folder names |
| `airfoil` | `'not_specified'` | Airfoil designation |
| `show_gui` | `False` | Show the Fluent GUI during meshing |
| `processor_count` | `4` | Number of logical cores |
| `precision` | `None` | Single vs double precision; defaults to double if unspecified |
| `chord_len` | `1` | Chord length in metres |
| `te_len` | `0.005` | Trailing-edge size in metres |
| `shut_down_when_done` | `True` | Close Fluent when meshing finishes |
| `has_te` | `False` | Does the airfoil have an open trailing edge? `False` = closed |
| `upper_name` | `'upper'` | Upper surface boundary label |
| `lower_name` | `'lower'` | Lower surface boundary label |
| `te_name` | `'te'` | Trailing-edge boundary label |
| `farfield_name` | `'farfield'` | Farfield boundary label |
| `symmetry_1_name` | `'sym1'` | Symmetry plane 1 label |
| `symmetry_2_name` | `'sym2'` | Symmetry plane 2 label |
| `Boi_1` | `True` | Add local sizing to upper/lower surfaces |
| `Boi_1_Control_Name` | `'airfoil_max'` | Name of the local sizing task |
| `Boi_1_Execution` | `'Face Size'` | Sizing type for local sizing task |
| `Boi_1_Size` | `None` | Local sizing size; evaluates to `chord_len / 100` if unspecified |
| `Boi_2_Control_Name` | `'airfoil_te'` | Name of the local sizing task for the trailing edge |
| `Boi_2_Execution` | `'Proximity'` | Sizing type for trailing-edge task |
| `Boi_2_Min_Size` | `None` | Minimum size for trailing-edge task |
| `Boi_2_Cells_Per_Gap` | `2` | Cells per gap when trailing-edge task is proximity |
| `Boi_2_Scope_To` | `'edges'` | Scope proximity sizing to edges |
| `Surface_Rate` | `1.2` | Growth rate of surface mesh |
| `Surface_Min_Size` | `None` | Surface min size; defaults to `te_len / 2` if `has_te`, else `Bl_First_Height × 10` |
| `Surface_Max_Size` | `None` | Surface max size; defaults to `chord_len / 2` |
| `Surface_Size_Function` | `'Curvature'` | Curvature-based mesh sizing |
| `Surface_Curvature_Normal_Angle` | `12` | Normal angle for curvature, in degrees |
| `Bl_Control_Name` | `'uniform'` | Boundary-layer type |
| `Bl_First_Height` | `2e-5` | First boundary-layer height, in metres |
| `Bl_Number_Of_Layers` | `20` | Number of boundary layers |
| `Bl_Rate` | `1.2` | Boundary-layer growth rate |
| `Volume_Fill_Type` | `'polyhedra'` | Volume fill type |
| `Volume_Fill_Size` | `None` | Volume fill size; defaults to `chord_len / 2` |
| `Volume_Fill_Rate` | `1.2` | Volume mesh growth rate |
| `Units` | `'m'` | Metres (standard SI) |

`file_path` is the only required argument. Any `None` default is computed from geometry at runtime.

</details>

<details>
<summary><code>solve()</code> — <code>src/Solution_Function.py</code> (65 optional parameters)</summary>

| Parameter | Default | Notes |
|---|---|---|
| `nickname` | `''` | User-specified identifier |
| `show_gui` | `False` | Show the Fluent GUI during the solve |
| `processor_count` | `4` | Number of logical cores |
| `precision` | `None` | Single vs double precision; defaults to double if unspecified |
| `shut_down_when_done` | `True` | Close Fluent when the solve finishes |
| `report_file` | `True` | Export drag and lift reports to file |
| `report_plot` | `True` | Generate a plot of drag and lift reports |
| `report_convergence` | `1e-5` | Convergence threshold for drag/lift reports |
| `altitude` | `0` | Altitude above sea level, in metres |
| `mach_num` | `0.6` | Free-stream Mach number |
| `aoa` | `0` | Angle of attack, in degrees |
| `chord_len` | `1` | Chord length, in metres |
| `mesh_width` | `0.1` | Depth of mesh in z, in metres; used for area |
| `convergence_criteria` | `1e-7` | Convergence threshold for residuals |
| `use_convergence_criteria` | `False` | Override default residuals with `convergence_criteria` |
| `use_report_convergence` | `True` | Use report-based convergence as termination |
| `iterations` | `300` | Maximum number of iterations |
| `time_step_scale` | `5` | Pseudo-time step scale factor |
| `report_1_name` | `'C_d'` | Drag coefficient report name |
| `report_2_name` | `'C_l'` | Lift coefficient report name |
| `operating_pres` | `0` | Operating gauge pressure, in Pascals |
| `solver_type` | `'pressure-based'` | Solver algorithm |
| `visc_method` | `'sutherland'` | Viscosity calculation method |
| `visc_model` | `'spalart-allmaras'` | Turbulence model |
| `k_omega_model` | `'geko'` | Sub-model if k-ω is selected |
| `curvature_correction` | `False` | Apply curvature correction |
| `compressibility_effects` | `False` | Apply compressibility effects |
| `farfield_name` | `'farfield'` | Farfield boundary label |
| `upper_name` | `'upper'` | Upper surface label |
| `lower_name` | `'lower'` | Lower surface label |
| `flux_report_name` | `'flux_report'` | Name of the mass-flow report |
| `specification_method` | `'Intensity and Viscosity Ratio'` | Turbulence specification method |
| `turb_int` | `1` | Turbulence intensity, % |
| `turb_visc_ratio` | `1` | Turbulent viscosity ratio |
| `flow_scheme` | `'Coupled'` | Pressure-velocity coupling method |
| `gradient_scheme` | `'least-square-cell-based'` | Gradient computation method |
| `density_scheme` | `'second-order-upwind'` | Density discretisation |
| `turb_kin_e_scheme` | `'second-order-upwind'` | Turbulent kinetic energy discretisation |
| `mom_scheme` | `'second-order-upwind'` | Momentum discretisation |
| `pres_scheme` | `'second-order'` | Pressure discretisation |
| `energy_scheme` | `'second-order-upwind'` | Energy equation discretisation |
| `spec_diss_rate_scheme` | `'second-order-upwind'` | Specific dissipation rate discretisation |
| `mod_turb_visc` | `'second-order-upwind'` | Modified turbulent viscosity discretisation |
| `pseudo_time_method` | `'global-time-step'` | Pseudo-time method |
| `hybrid_initialize` | `True` | Use hybrid initialisation (otherwise standard) |
| `high_order_term_relax` | `False` | Apply high-order term relaxation |
| `relaxation_factor` | `0.75` | Relaxation factor when high-order relaxation is on |
| `courant_number` | `200` | Courant number for density-based / transient solves |
| `warped_face_gradient` | `False` | Apply warped-face gradient correction |
| `airfoil` | `'not_specified'` | Airfoil identifier |
| `symmetry_1_name` | `'sym1'` | Symmetry plane 1 label |
| `surface_name` | `'surface'` | Surface boundary label for 2D meshes |
| `contour_lines` | `False` | Show contour lines on Mach/pressure plots |
| `smooth_or_banded` | `'banded'` | Smooth or banded contours |
| `generate_mach_cont` | `True` | Generate Mach contour plot |
| `generate_pres_cont` | `True` | Generate pressure contour plot |
| `generate_yplus` | `True` | Generate y⁺ plot |
| `generate_pres_plot` | `True` | Generate pressure-distribution plot |
| `transient` | `False` | Use transient solver (otherwise steady-state) |
| `two_d_space` | `'planar'` | 2D solution formulation |
| `time_step_count` | `10` | Number of transient time steps |
| `time_step_size` | `0.0001` | Transient time-step size, in seconds |
| `iters_per_time_step` | `20` | Iterations per time step |
| `pause_before_solve` | `False` | Pause for manual inspection before solving |
| `under_relaxation` | `0.75` | Under-relaxation factor in the solution-controls panel |

`file_path` is the only required argument. Physical conditions (`altitude`, `mach_num`, `aoa`, `chord_len`) are listed with their defaults above but should almost always be supplied per row.

</details>

<details>
<summary><code>optimize()</code> — <code>src/Adjoint_Function.py</code> (55 optional parameters)</summary>

| Parameter | Default | Notes |
|---|---|---|
| `nickname` | `''` | User-specified identifier |
| `airfoil` | `'not_specified'` | Airfoil identifier |
| `contour_lines` | `False` | Show contour lines on Mach/pressure plots |
| `smooth_or_banded` | `'banded'` | Smooth or banded contours |
| `save_screenshots` | `True` | Save screenshots between adjoint iterations |
| `transient` | `False` | Use a transient solver |
| `solver_type` | `'pressure-based'` | Applied to the final post-adjoint solve (adjoint itself is pressure-based) |
| `visc_model` | `'k-omega'` | Viscous model for the final solve (adjoint itself uses k-ω GEKO) |
| `show_gui` | `True` | Show GUI — on by default so screenshots render |
| `processor_count` | `4` | Number of logical cores |
| `upper_name` | `'upper'` | Upper surface label |
| `lower_name` | `'lower'` | Lower surface label |
| `aoa` | `0` | Angle of attack, in degrees |
| `convergence_criteria` | `1e-5` | Convergence threshold for residuals |
| `use_convergence_criteria` | `True` | Override default convergence with value above |
| `use_energy` | `False` | Enable energy in the adjoint solver |
| `use_turbulence` | `False` | Enable turbulence effects in the adjoint solver |
| `use_best_match` | `False` | Copy flow settings from the solution file into the adjoint solve |
| `apply_preconditioning` | `False` | Apply preconditioning |
| `target_change` | `10` | Target design change per adjoint iteration |
| `use_percentage` | `True` | Treat `target_change` as a percentage |
| `optimize_target` | `'lift-to-drag'` | Observable to optimise: `lift-to-drag`, `lift`, or `drag` |
| `mach_num` | `0.5` | Free-stream Mach number |
| `time_step_scale` | `5` | Pseudo-time step scale factor |
| `time_step_size` | `0.001` | Transient time-step size, in seconds |
| `time_step_count` | `100` | Number of transient time steps |
| `iters_per_time_step` | `20` | Iterations per time step |
| `final_iterations` | `300` | Iterations for the final post-adjoint solve (thesis: `iterations`) |
| `infinite_mode` | `False` | Overrides `optimization_loop_count`; loops until mesh quality drops below threshold |
| `min_orth_quality_limit` | `0.06` | Minimum orthogonal quality for infinite-mode stop |
| `maintain_len` | `True` | Keep airfoil chord length constant |
| `adjoint_iterations` | `20` | Iterations of the adjoint solver per loop |
| `optimization_loop_count` | `5` | Number of adjoint design loops |
| `pseudo_time_method` | `'off'` | Pseudo-time method (applied during adjoint phase) |
| `temp_iterations` | `200` | Temporary max iterations while adjoint is running |
| `temp_time_step_scale` | `None` | Temp pseudo-time step scale; defaults to `0.001` if unspecified |
| `temp_time_step_size` | `None` | Temp transient time-step size; defaults to `0.001` if unspecified |
| `temp_time_step_count` | `10` | Temp transient time-step count while adjoint is running |
| `temp_iters_per_time_step` | `20` | Temp iterations per time step while adjoint is running |
| `farfield_name` | `'farfield'` | Farfield boundary label |
| `shut_down_when_done` | `True` | Close Fluent when optimisation finishes |
| `generate_yplus` | `True` | Generate y⁺ plot |
| `generate_pres_plot` | `True` | Generate pressure-distribution plot |
| `report_1_name` | `'C_d'` | Drag report name |
| `report_2_name` | `'C_l'` | Lift report name |
| `report_plot` | `True` | Plot drag/lift results |
| `report_file` | `True` | Export drag/lift reports to file |
| `make_gifs` | `True` | Build GIFs from mesh/Mach/pressure screenshots |
| `gif_duration` | `100` | GIF frame duration, in ms |
| `change_boundary_conditions` | `False` | Change the boundary conditions and re-solve |
| `altitude` | `0` | Altitude above sea level, in metres, for changed BCs |
| `mesh_width` | `0.1` | Depth of mesh in z, in metres; used for area |
| `infinite_mode_max` | `999` | Hard iteration cap for infinite mode |
| `custom_mode` | `False` | Custom optimisation mode (not in thesis) |
| `custom_path` | `[]` | User-supplied coordinate path used when `custom_mode=True` (not in thesis) |

`file_path` is the only required argument. `target_change` is interpreted as a percentage when `use_percentage=True`. `solver_type` and `visc_model` are applied only to the final post-adjoint solve — the adjoint solve itself is always pressure-based with the GEKO k-ω model.

</details>

---

## Validation

Each of the four airfoils was verified against published experimental or CFD data before optimisation:

| Airfoil | Reference | Agreement |
|---|---|---|
| NACA 0012 | Hasan et al. 2021 (CFD) | L/D within 3% |
| NACA 0012 | Ladson 1988 (wind tunnel) | L/D within 57% — discrepancy discussed in thesis §5.1.1 |
| NACA 2412 | Hasan et al. 2021 | L/D within 3% |
| BACXXX | Abdel-Raheem et al. 2019 | Reference appears to contain a non-dimensionalisation error; once corrected, agreement within 2% |
| NASA SC(2)-0714 | Sri et al. 2022, Jenkins (NASA TM) | Agreement against Jenkins; Sri reference appears unreliable at transonic M |

See thesis §5.1 for the full validation discussion.

---

## Known limitations

Documented honestly, in case you're considering building on this:

1. **Domain geometry is hard-coded.** The SolidWorks domain must roughly match the shape described in thesis §3.2.2. Other domains will fail at the meshing step.
2. **Single-point optimisation only.** The Adjoint Solver optimises for one operating condition. Off-design performance of optimised profiles is typically poor. Multi-point optimisation is achievable with the existing code but requires external scripting to loop across design points.
3. **2D → 3D verification is a manual workflow.** Optimisation is typically run in 2D first (to avoid left-handed faces caused by minute mesh changes at high boundary-layer resolution), then verified in 3D. The handoff is manual: collect the optimised coordinates from the `.dis` file, rebuild the 3D geometry from them in SolidWorks, then re-run the pipeline on the new geometry. The `.dis` output itself contains unsorted and sometimes-duplicate points, which need cleaning up before the geometry can be rebuilt — `supplementary_tools/airfoil_tools.html` has a Sorter tab that can help.
4. **Pressure-based solver during optimisation.** The Adjoint Solver only supports pressure-based solves, so all optimisation runs through it. The standalone `solve()` function exposes density-based as an option (and it may be more accurate at supersonic Mach), but combining density-based solves with adjoint optimisation was not investigated.

---

## File layout

```
.
├── src/
│   ├── Main_File_Meshing.py                     # Driver: iterate meshing_table, call mesh()
│   ├── Main_File_Solution.py                    # Driver: iterate solution_table, call solve()
│   ├── Main_File_Optimization.py                # Driver: iterate adjoint_table, call optimize()
│   ├── Meshing_Function.py                      # mesh() — SpaceClaim → watertight mesh
│   ├── Solution_Function.py                     # solve() — mesh → converged flow solution
│   ├── Adjoint_Function.py                      # optimize() — case → optimised geometry
│   └── dachis_tools.py                          # shared utilities (IO, plotting, file moves) [written with AI assistance]
├── supplementary_tools/                         # [all .html files in this folder are AI written]
│   ├── airfoil_tools.html                       # browser tool: plot, scale, sort, and compare airfoil coordinates [AI written]
│   ├── first_layer_height_calculator.html       # browser tool: calculate first boundary-layer heights from target y⁺ [AI written]
│   └── chart_studio.html                        # browser tool: make charts [AI written]
├── experimental/
│   └── response_analysis.py                     # experimental Optuna sweep over meshing parameters (did not produce usable results)
├── example_files/                               # sample inputs and reference outputs
│   ├── NACA_0012.scdocx                         # sample SpaceClaim geometry (3D)
│   ├── NACA_0012_2D.scdocx                      # sample SpaceClaim geometry (2D)
│   ├── NACA_0012_final.msh.h5                   # sample mesh output
│   ├── NACA_0012_final_inputs.txt               # sample meshing input record
│   ├── NACA_0012_final_log.txt                  # sample meshing log
│   ├── act_2D/                                  # sample output (2D, optimised airfoil) — root files are the solve; subfolders are optimisation runs
│   │   ├── NACA_0012_2D_act_2D.cas.h5 / .dat.h5 # [solve] case and data files
│   │   ├── C_{d,l}_*.out / *_steady.png         # [solve] drag/lift report files and convergence plots
│   │   ├── *_mach_cont.png / *_pres_cont.png    # [solve] Mach and pressure contours
│   │   ├── *_pres-plot.png / *_y-plus.png       # [solve] pressure distribution and y⁺ plots
│   │   ├── *_residuals.png / *_mass_flow.flp    # [solve] residuals plot and mass-flow record
│   │   ├── *_inputs.txt / *_log.txt             # [solve] input record and solver log
│   │   ├── NACA_0012_2D.xy                      # [solve] airfoil coordinates
│   │   ├── final_30_1241/                       # [optimisation run] finite-mode, 30 loops
│   │   ├── final_30_long_4331/                  # [optimisation run] finite-mode, 30 loops, long
│   │   ├── final_inf_5307/                      # [optimisation run] infinite-mode
│   │   ├── final_inf_long_5615/                 # [optimisation run] infinite-mode, long
│   │   └── max_downforce_3740/                  # [optimisation run] max-downforce target
│   ├── act_3D/                                  # sample solve output (3D, optimised airfoil)
│   │   ├── NACA_0012_act_3D.cas.h5 / .dat.h5    # case and data files
│   │   ├── C_{d,l}_*.out / *_steady.png         # drag/lift reports and convergence plots
│   │   ├── *_mach_cont.png / *_pres_cont.png    # Mach and pressure contours
│   │   ├── *_pres-plot.png / *_y-plus.png       # pressure distribution and y⁺ plots
│   │   ├── *_residuals.png / *_mass_flow.flp    # residuals plot and mass-flow record
│   │   ├── *_inputs.txt / *_log.txt             # input record and solver log
│   │   └── NACA_0012.xy                         # airfoil coordinates
│   ├── ref_2D/                                  # sample solve output (2D, reference airfoil) — same structure as act_2D root
│   └── ref_3D/                                  # sample solve output (3D, reference airfoil) — same structure as act_3D
├── sim_data.xlsx                                # input tables (three sheets)
├── requirements.txt                             # Python dependencies
├── Aero-Opt_thesis.pdf                          # full thesis PDF
└── README.md                                    # this file
```

---

## Citation

If you use Aero-Opt in published work, please cite the thesis:

```bibtex
@thesis{dzeria2026aeroopt,
  title   = {Aero-Opt: CFD-Based Aerodynamic Optimisation for Sustainable Engineering},
  author  = {Dzeria, Dachi},
  school  = {South East Technological University Carlow},
  year    = {2026},
  type    = {BEng(Hons) thesis},
  url     = {https://github.com/Dzermann/pyfluent-airfoil-optimization}
}
```

A copy of the full thesis is available [here](./Aero-Opt_thesis.pdf) and includes complete validation data, boundary conditions, and results for all optimisation cases.

---

## Contributing

Contributions welcome, particularly in the following areas:

- **Multi-point optimisation** extensions (the biggest open item)
- **Alternative solvers** (density-based, OpenFOAM adapter)
- **Domain-generation automation** (currently the only manual step left in the pipeline)
- **Structural constraints** during optimisation (to produce realistically-fabricable airfoils)

Open an issue to discuss before submitting a pull request.

---

## Licence

Released under the MIT Licence. See `LICENSE` for details.

```
Copyright (c) 2026 Dachi Dzeria

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND...
```

---

## Contact

Issues and questions: please use the GitHub issue tracker.

For correspondence about the thesis specifically: [dachi.dzeria@gmail.com](mailto:dachi.dzeria@gmail.com) / [LinkedIn](https://www.linkedin.com/in/dachidzeria/).
