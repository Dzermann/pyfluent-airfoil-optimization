# Aero-Opt

> **Automated CFD-based aerodynamic optimisation for airfoils, across subsonic, transonic, and supersonic flow regimes.**

Aero-Opt is a Python pipeline that automates meshing, solving, and adjoint-based shape optimisation of 2D/3D airfoils in Ansys Fluent. It was developed as the computational core of a BEng(Hons) thesis at South East Technological University Carlow, and is released here so that other researchers and students can replicate, extend, or adapt the workflow to their own aerodynamic-optimisation problems.

> **Note on authorship.** This README was drafted with AI assistance. All PyFluent / Python code in this repository, along with the thesis itself, was written manually by the author. This file is project documentation only — it is not part of the thesis submission — so AI involvement in its prose does not constitute plagiarism under the academic-integrity policy referenced in the thesis.

---

## What it does

Given an Excel table of input conditions, Aero-Opt will:

1. **Mesh** a SpaceClaim airfoil geometry in Ansys Fluent Meshing with configurable boundary-layer resolution, volume-fill method, and y⁺ targets.
2. **Solve** the flow field at specified altitude, Mach number, and angle of attack, computing drag and lift coefficients and exporting pressure/Mach contours, residuals, and y⁺ plots.
3. **Optimise** the airfoil shape using the Ansys Fluent Adjoint Solver, either preserving chord length or allowing it to vary.

Each step is driven from a single row in an Excel input table, so a batch of hundreds of simulations runs unattended.

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

Aero-Opt requires an active Ansys Fluent licence with access to the **Adjoint Solver** module. Not all academic licences include Adjoint — check with your Ansys administrator before running optimisation jobs.

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

Each row = one simulation. Leave any cell blank to use the function default (see `Appendix D` in the thesis for full default listings).

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
3. **2D → 3D verification is a manual workflow.** Optimisation is typically run in 2D first (to avoid left-handed faces caused by minute mesh changes at high boundary-layer resolution), then verified in 3D. The handoff is manual: collect the optimised coordinates from the `.dis` file, rebuild the 3D geometry from them in SolidWorks, then re-run the pipeline on the new geometry. The `.dis` output itself contains unsorted and sometimes-duplicate points, which need cleaning up before the geometry can be rebuilt — `src/airfoil_tools.html` has a Sorter tab that can help.
4. **Pressure-based solver during optimisation.** The Adjoint Solver only supports pressure-based solves, so all optimisation runs through it. The standalone `solve()` function exposes density-based as an option (and it may be more accurate at supersonic Mach), but combining density-based solves with adjoint optimisation was not investigated.

---

## File layout

```
.
├── src/
│   ├── Main_File_Meshing.py       # Driver: iterate meshing_table, call mesh()
│   ├── Main_File_Solution.py      # Driver: iterate solution_table, call solve()
│   ├── Main_File_Optimization.py  # Driver: iterate adjoint_table, call optimize()
│   ├── Meshing_Function.py        # mesh() — SpaceClaim → watertight mesh
│   ├── Solution_Function.py       # solve() — mesh → converged flow solution
│   ├── Adjoint_Function.py        # optimize() — case → optimised geometry
│   ├── dachis_tools.py            # shared utilities (IO, plotting, file moves)
│   └── airfoil_tools.html         # browser tool: plot, scale, sort, and compare airfoil coordinates
├── experimental/
│   └── response_analysis.py       # experimental Optuna sweep over meshing parameters (did not produce usable results)
├── example_files/                 # sample inputs and reference outputs
│   ├── NACA_0012.scdocx           # sample SpaceClaim geometry (3D)
│   ├── NACA_0012_2D.scdocx        # sample SpaceClaim geometry (2D)
│   ├── NACA_0012_final.msh.h5     # sample mesh output
│   ├── NACA_0012_final_inputs.txt # sample meshing input record
│   ├── NACA_0012_final_log.txt    # sample meshing log
│   ├── act_3D/                    # sample full solver output (optimised case)
│   └── ref_3D/                    # sample full solver output (reference case)
├── sim_data.xlsx                  # input tables (three sheets)
├── requirements.txt               # Python dependencies
├── Aero-Opt_thesis.pdf            # full thesis PDF
└── README.md                      # this file
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
