# -*- coding: utf-8 -*-
"""
Created on Tue Dec 23 21:37:07 2025

    This code runs the Ansys Fluent solution, and imports the mesh.
    Then it defines all boundary conditions/setup and runs the simulation.
    All numbers are specified as variables of the function.
    All variables are specified below.

    Works as a function on any airfoil, as long as the variables are specified

    Returns:
        the folder path
        name of the first (drag) report
        name of the second (lift) report

    Start Date:  16/10/2025
    Finish Date:
    - Dachi Dzeria, C00290924
"""


def solve(file_path,  # specify the mesh location
          nickname='',  # nickname - used in naming certain parts
          show_gui=False,  # show the user interface?
          processor_count=4,  # number of processors
          precision=None,  # use double precision?
          shut_down_when_done=True,  # shut down when done? (useful when testing)
          report_file=True,  # output report files?
          report_plot=True,  # output report plots?
          report_convergence=10**-5,  # convergence criterium for reports
          altitude=0,  # default altitude, m
          mach_num=0.6,  # default mach number
          aoa=0,  # default angle of attack, degrees
          chord_len=1,  # default chord len, m
          mesh_width=0.1,  # default mesh width (if 2d), m
          convergence_criteria=10**-7,  # convergence threshhold
          use_convergence_criteria=False,  # modify residuals to a custom number or not
          use_report_convergence=True,  # create report based convergence criteria or not
          iterations=300,  # number of iterations
          time_step_scale=5,  # time step scale
          report_1_name='C_d',  # name of the first solution report
          report_2_name='C_l',  # name of the second solution report
          operating_pres=0,  # operating pressure, default is 0
          solver_type='pressure-based',  # pressure vs density based solver
          visc_method='sutherland',
          visc_model='spalart-allmaras',  # viscous mode
          k_omega_model='geko',  # default k-omega model (if k-omega is being used)
          curvature_correction=False,  # use curvature correction?
          compressibility_effects=False,  # use compressibility effects (not recommended by ansys)
          farfield_name='farfield',  # name of farfield
          upper_name='upper',  # name of upper surface
          lower_name='lower',  # name of lower surface
          flux_report_name='flux_report',  # mass flow report name
          specification_method='Intensity and Viscosity Ratio',  # viscosity specification method
          turb_int=1,  # turbulence intencity, %
          turb_visc_ratio=1,  # turbulence viscousity ratio
          flow_scheme='Coupled',  # flow scheme
          gradient_scheme='least-square-cell-based',  # gradient scheme
          density_scheme='second-order-upwind',  # density scheme
          turb_kin_e_scheme='second-order-upwind',  # turulent kinetic energy scheme
          mom_scheme='second-order-upwind',  # momentum scheme
          pres_scheme='second-order',  # pressure scheme
          energy_scheme='second-order-upwind',  # energy scheme
          spec_diss_rate_scheme='second-order-upwind',  # heat dissipation rate scheme
          mod_turb_visc='second-order-upwind',
          pseudo_time_method='global-time-step',  # time step method
          hybrid_initialize=True,  # whether to use hybrid initialize or standard initialize, will default to standard if False
          high_order_term_relax=False,  # high order term relaxation
          relaxation_factor=0.75,  # relaxation factor to use if above is on
          courant_number=200,  # courant number to use for solving density-based solves
          warped_face_gradient=False,  # warped face gradient
          airfoil='not_specified',  # airfoil name
          symmetry_1_name='sym1',  # symmetry 1 name (used for contours)
          surface_name='surface',  # name for surface for 2D geometries
          contour_lines=False,  # contour lines on or off
          smooth_or_banded='banded',  # banded or smooth contours
          generate_mach_cont=True,  # generate the mach contours?
          generate_pres_cont=True,  # generate pressure contours?
          generate_yplus=True,  # generate y+ plot?
          generate_pres_plot=True,  # generate pressure plot?
          transient=False,  # use transient time?
          two_d_space='planar',  # two d space formulation type
          time_step_count=10,  # amount of time steps for transient solve
          time_step_size=0.0001,  # time step size, in s, for transient solve
          iters_per_time_step=20,  # iterations each time step, for transient solve
          pause_before_solve=False,  # if the program should pause before the main run (in case you need custom initialization)
          under_relaxation = 0.75, # under relaxation factor number in solution control tab
          ):

    logger = None
    try:
        # Starting the logger
        # importing the logger and file copier
        import math
        import os
        import time
        from datetime import datetime

        import ansys.fluent.core as pyfluent
        from ansys.fluent.core.solver import Graphics

        from dachis_tools import console_logger, new_folder_and_file

        # create and get the new file path and new folder name (based on the nickname)
        new_file_path, folder_path = new_folder_and_file(file_path, nickname, False)
        name = f"{airfoil}_{nickname}"  # get the file name
        logger = console_logger(folder_path=folder_path, file_name=name)
        logger.start()  # start the logger

        # Print the progress report
        print('--------------------------------------------------------\n')
        print(f'LOADING {name}\n')
        print('--------------------------------------------------------\n')


        # %% Starting the timer
        t0 = time.time()

        print("PASS: Timer On")


        # %% Check if 2D
        phrase = '2D'
        is3D = True
        if phrase.lower() in file_path.lower() or phrase.lower() in airfoil.lower():
            print("PASS: 2D Mesh Detected. Switching to 2D Meshing Mode...")
            is3D = False


        # %% Define default inputs, if they are left empty
        if precision == "Double":
            precision = pyfluent.Precision.DOUBLE
        else:
            precision = None


        # %% Starting the solution
        # Calculating reference values
        # Values taken from: https://en.wikipedia.org/wiki/Standard_sea-level_conditions
        # These are not inputs because they're constants
        temp_lapse_rate = 0.0065  # K/m
        sea_level_temp = 288.15  # K
        g = 9.80665  # m/s^2
        R_uni = 8.31432  # universal gas constant, J/ mol*K
        mol_mass = 0.028964420  # molar mass of air
        rho_0 = 1.225  # kg/m^3
        sea_level_pressure = 101325  # pa
        gamma = 1.4  # adiabatic index, ratio os specific heats
        mew_0 = 0.00001789  # Pa/s, dynamic viscousity at SL
        S = 110  # K, sutherland constant

        # Renaming the variables so it's easier to type the fomrulas
        h = altitude
        T_0 = sea_level_temp
        alpha = temp_lapse_rate  # defined as alpha instead of lambda because lambda is a python function
        p_0 = sea_level_pressure
        R_spec = R_uni / mol_mass  # J/kg, specific gas constant
        # c_p  = (gamma * R_spec) / (gamma - 1) # specific heat of air, J/kgC

        # Calculating the reference values
        temperature = T_0 - h * temp_lapse_rate
        density = rho_0 * (((T_0 - (alpha * h)) / (T_0)) ** ((g / (R_spec * alpha)) - 1))
        mach_at_altitude = math.sqrt(temperature * R_spec * gamma)
        velocity = mach_at_altitude * mach_num  # m / s
        dynamic_visc = mew_0 * ((temperature / T_0) ** (3 / 2)) * (T_0 + S) / (temperature + S)
        kinematic_visc = dynamic_visc / density  # kinematic viscosity, m^2/s
        RE = (chord_len * velocity) / kinematic_visc  # reynolds number
        pressure = p_0 * ((T_0) / (T_0 - alpha * h)) ** ((g * mol_mass) / (R_uni * -alpha))
        # d_T = temperature - sea_level_temp # change in temperature, K

        print("PASS: Reference values calculated...")
        print(f"Density [kg/m^3] [kg/m^3]: {density}...")
        print(f"Length [m]: {chord_len}...")
        print(f"Pressure [Pa]: {pressure}...")
        print(f"Temperature [K]: {temperature}...")
        print(f"Velocity [m/s]: {velocity}...")
        print(f"Dynamic Viscosity [kg/ms]: {dynamic_visc: e}...")
        print(f"Kinematic Viscosity [kg/ms]: {kinematic_visc: e}...")
        print(f"Reynolds Number: {RE: e}...")


        # %% Getting the x and y component of flow values
        aoa = math.radians(aoa)  # convert degrees to radians
        x_mach = math.cos(aoa)  # x component is cosine of angle of attack
        y_mach = math.sin(aoa)  # y component is sine of angle of attack
        x_vel = x_mach * velocity
        y_vel = y_mach * velocity


        # %% Opening the session
        if is3D:
            print("Launching 3D fluent session...")
            # --- Fluent launch settings ---
            ssn = pyfluent.launch_fluent(
                mode=pyfluent.FluentMode.SOLVER,  # meshing mode
                show_gui=show_gui,  # show the program running
                processor_count=processor_count,  # specify processor count
                precision=precision
            )
            print("PASS: Fluent session launched")

        else:
            print("Launching 2D fluent session...")
            # --- Fluent launch settings ---
            ssn = pyfluent.launch_fluent(
                mode=pyfluent.FluentMode.SOLVER,  # meshing mode
                show_gui=show_gui,  # show the program running
                processor_count=processor_count,  # specify processor count
                precision=precision,
                dimension=2
            )

        ssn.settings.file.read_mesh(file_name=file_path)  # read the mesh


        # %% Scaling the mesh
        scaling_factor = chord_len  # all airfoils are given with 1m chord length as standard
        # therefore, scaling factor is equal to the desired chord_length
        # area used is mesh width by chord len
        # the mesh is scaled by chord length
        # in x, y, and z dimensions, so the area becomes
        # chord_len ** 2 * mesh_width
        scaled_width = mesh_width * scaling_factor
        area = scaled_width * scaling_factor
        print(f"Area [M^2]: {area}...")

        if chord_len != 1:  # if the chord length isn't 1, the mesh needs to be scaled
            print("Scaling mesh...")
            
            ssn.settings.mesh.scale(x_scale=scaling_factor, y_scale=scaling_factor, z_scale=scaling_factor)
            print(f"PASS: Mesh scaled by {scaling_factor}...")


        # %% Operating conditions and material setup
        setup = ssn.settings.setup

        # Specifying solver type
        setup.general.solver.type = solver_type
        print(f"PASS: Solver type set to {solver_type}...")

        if not is3D:
            ssn.settings.setup.general.solver = {
                'two_dim_space': two_d_space
            }

        setup.materials.fluid["air"] = {  # define ideal gas law and sutherland viscousity
            "density": {"option": "ideal-gas"},
            "viscosity": {"option": "sutherland"},
            # "specific_heat": {"option": "piecewise-polynomial"}
        }

        setup.models.energy(enabled=True)  # enabling energy
        print("PASS: Enabled energy...")

        # set operating pressure
        setup.general.operating_conditions(operating_pressure=operating_pres)
        print("PASS: Operating conditions specified...")

        # set the viscous model
        setup.models.viscous.model = visc_model
        print("PASS: Viscous model specified...")

        if visc_model == 'k-omega':
            setup.models.viscous.k_omega_model = k_omega_model
            print(f"PASS: k-omega model set to {k_omega_model}...")


        # %% Setting up boundary conditions
        # specifying the boundary components
        if visc_model == 'k-omega':
            # specifying the boundary components
            setup.boundary_conditions.pressure_far_field['farfield'] = {
                'momentum': {
                    'gauge_pressure': pressure,  # gauge pressure
                    'mach_number': mach_num,  # mach number
                    'flow_direction': [x_mach, y_mach]  # x and y components of flow
                },
                'thermal': {
                    'temperature': temperature  # temperature
                },
                # this will only work with the default option for now. Will fix later.
                'turbulence': {  # turublence model
                    'turbulence_specification': specification_method,
                    'turbulent_intensity': turb_int / 100,  # convert to %
                    'turbulent_viscosity_ratio': turb_visc_ratio
                }
            }

            setup.models.viscous.options.curvature_correction = curvature_correction
            setup.models.viscous.options.compressibility_effects = compressibility_effects

        else:
            print('Specifying Boundary Conditions...')
            # specifying the boundary components
            setup.boundary_conditions.pressure_far_field['farfield'] = {
                'momentum': {
                    'gauge_pressure': pressure,  # gauge pressure
                    'mach_number': mach_num,  # mach number
                    'flow_direction': [x_mach, y_mach]  # x and y components of flow
                },
                'thermal': {
                    'temperature': temperature  # temperature
                },
                'turbulence': {  # turublence model
                    'turbulent_viscosity_ratio_profile': {
                        'option': 'value', 'value': turb_visc_ratio
                    }
                }
            }

        print("PASS: Boundary conditions specified...")
        print(f"Pressure [Pa] set to {pressure}...")
        print(f"Mach Number [M] set to {mach_num}...")
        print(f"Temperature [K] set to {temperature}...")


        # %% Solution methods
        print("Specifying solution methods...")
        solution = ssn.settings.solution

        if transient:  # add transient settings (if transient)

            ssn.settings.setup.general.solver = {
                'type': solver_type,
                'time': 'unsteady-1st-order'
            }

            print('PASS: Transient mode set...')

        solution.methods.high_order_term_relaxation.enable = True
        solution.methods.high_order_term_relaxation.relaxation_factor = relaxation_factor

        # Specify the solution methods
        solution.methods = {
            'spatial_discretization': {
                'gradient_scheme': gradient_scheme,
                'discretization_scheme': {
                    'density': density_scheme,
                    'k': turb_kin_e_scheme,
                    'mom': mom_scheme,
                    'omega': spec_diss_rate_scheme,
                    'pressure': pres_scheme,
                    'temperature': energy_scheme
                }
            },
            'pseudo_time_method': {
                'formulation': {'density_based_solver': pseudo_time_method}
            },
            'high_order_term_relaxation': {'enable': high_order_term_relax},
            'warped_face_gradient_correction': {'enable': warped_face_gradient}
        }

        if solver_type == 'pressure-based':  # specify settings unique to pressure-based solvers
            solution.methods = {
                'p_v_coupling': {
                    'flow_scheme': flow_scheme
                },
                'pseudo_time_method': {
                    'formulation': {
                        'coupled_solver': pseudo_time_method
                    }
                }
            }
        print("PASS: Solution settings specified...")


        # %% Creating Reports
        print("Creating reports...")

        # to avoid mixing up duplicate files
        timestamp = datetime.now().strftime('%M%S')

        # Initialize the drag report
        report_1 = f"{report_1_name}_{airfoil}_{nickname}_{timestamp}"

        solution.report_definitions.drag[f'{report_1}'] = {
            'force_vector': [x_mach, y_mach, 0],  # specify the force vector directions [x, y, z]
            'zones': [upper_name, lower_name],  # zones - only includes upper and lower
            'create_report_file': report_file,  # create report file?
            'create_report_plot': report_plot,  # create report plot?
        }

        # Define report output format
        print(f"PASS: {report_1} created...")
        report_1_file = report_1 + '-rfile.out'


        # %% Initialize the lift report
        report_2 = f"{report_2_name}_{airfoil}_{nickname}_{timestamp}"

        solution.report_definitions.lift[f'{report_2}'] = {
            'force_vector': [y_mach, x_mach, 0],
            'zones': [upper_name, lower_name],
            'create_report_file': report_file,
            'create_report_plot': report_plot,
        }

        print(f"PASS: {report_2} created...")
        report_2_file = report_2 + '-rfile.out'


        # %% Adjusting reference values
        print("Specifying the reference values...")

        # Inputing the reference values calculated above
        setup.reference_values = {  # input the reference values
            'area': area,
            'density': density,
            'length': chord_len,
            'pressure': pressure,
            'temperature': temperature,
            'velocity': velocity,
            'viscosity': dynamic_visc,
            'depth': scaled_width
        }
        print("PASS: Reference values specified...")


        # %% Modifying residuals
        if use_convergence_criteria:

            print("Specifying convergence criteria...")

            solution.monitor.residual = {
                'equations':  # change the convergence criteria
                    # all the convergence criteria are the same
                    {'continuity': {'absolute_criteria': convergence_criteria},
                     'energy': {'absolute_criteria': convergence_criteria},
                     'k': {'absolute_criteria': convergence_criteria},
                     'omega': {'absolute_criteria': convergence_criteria},
                     'x-velocity': {'absolute_criteria': convergence_criteria},
                     'y-velocity': {'absolute_criteria': convergence_criteria},
                     'z-velocity': {'absolute_criteria': convergence_criteria}}
            }

            print("PASS: Residuals specified...")


        # %% Adding convergence conditions of the reports
        if use_report_convergence:

            print("Adding convergence criteria based on reports...")

            solution.monitor.convergence_conditions = {
                'convergence_reports': {

                    f'{report_1_name}_convergence': {  # define name
                        'stop_criterion': report_convergence,  # define the criteria for stopping
                        'report_defs': f'{report_1}'  # define which output to watch
                    },

                    f'{report_2_name}_convergence': {
                        'stop_criterion': report_convergence,
                        'report_defs': f'{report_2}'
                    }
                }
            }

            print("PASS: Report convergence criteria added...")


        # %% Initialize
        if hybrid_initialize:
            print("Hybrid initialization...")
            solution.initialization.hybrid_initialize()  # initializing

        else:  # standard initialize
            print("Standard initialization...")
            # this computes the values from the farfield
            # but only some values, the x and y vel still must be
            # filled in manually. And while there let's replace
            # temperatrue and pressure with our values too
            solution.initialization.compute_defaults(from_zone_name=farfield_name)
            solution.initialization = {
                'defaults': {
                    'pressure': pressure,
                    'temperature': temperature,
                    'x-velocity': x_vel,
                    'y-velocity': y_vel
                }
            }

            solution.initialization.standard_initialize()  # standard initialize

        print("PASS: Initialization complete...")


        # %% Pause if pause_before_solve is on
        if pause_before_solve:
            while input('Continue? Type y to continue').strip().casefold() != 'y': pass


        # %% Specify solution settings
        if transient:  # if transient, specify time step count and size

            print('Transient solve detected. Specifying transient settings...')

            solution.run_calculation = {
                'transient_controls': {
                    'time_step_count': time_step_count,
                    'time_step_size': time_step_size,  # in seconds
                    'max_iter_per_time_step': iters_per_time_step,
                }
            }
            
            ssn.settings.solution.controls.p_v_controls.flow_courant_number = courant_number
            ssn.settings.solution.controls.p_v_controls.explicit_pressure_under_relaxation = under_relaxation
            ssn.settings.solution.controls.p_v_controls.explicit_momentum_under_relaxation = under_relaxation
            
        if not transient:

            solution.run_calculation = {
                'pseudo_time_settings': {  # specify time settings
                    'time_step_method': {
                        'time_step_size_scale_factor': time_step_scale  # specify the time step
                    }
                },
                'iter_count': iterations  # specify the number of iterations
            }

        print("PASS: Number of iterations specified...")


        # %% Calculating
        print(f"PASS: Starting solve for {iterations} iterations")
        solution.run_calculation.calculate()  # start the solve
        print("PASS: Solve finished...")

        # %% Pausing after the solve
        if not shut_down_when_done:  # if shut down when done is set to false, wait until the user types y
            while input('Shut down? Type y to continue').strip().casefold() != 'y': pass

        # %% Getting the mass flow to check simulation validity
        print('Calculating mass flow...')
        # define the file location
        flux_report_name = os.path.join(folder_path, f'{airfoil}_{nickname}_mass_flow.flp')

        results = ssn.settings.results

        # get the total mass flow number and save it as a file
        results.report.fluxes.mass_flow(
            zones=[farfield_name],
            write_to_file=True,
            file_name=flux_report_name)

        print(f"PASS: Mass flow saved as {flux_report_name}")


        # %% Cumulative plot info
        print("Drawing the cumulative plot...")
        results.plot.cumulative_plot = {
            'zones': {
                'name': f'{airfoil}_cumulative-plot',  # specify name
                'option': 'cumulative-force',  # specify the type
                'zones': [upper_name, lower_name],  # specify zones
                'split_direction': [x_mach, y_mach, 0.0],  # specify directions, calculated above
                'number_of_divisions': 50,  # specify resolution
                'force_direction': [x_mach, y_mach, 0.0],  # specify force direction, calculated above
                'x_axis_quantity': 'distance',  # specify x axis unit
            }
        }

        # write to file
        cumulative_plot_name = airfoil + '.xy'  # define file name
        # Join file name to folder path
        cumulative_plot_name = os.path.join(folder_path, cumulative_plot_name)
        # Plot and save the results
        results.plot.cumulative_plot.write(file_name=cumulative_plot_name)

        print(f"Cumulative plot saved as {cumulative_plot_name}")


        # %% Saving mach contour
        # importing
        if is3D:  # specify camera zoom and pan values
            zoom_value = 20  # these values are found via
            pan_value = 2.45  # trial and error
        else:
            zoom_value = 25
            pan_value = 3.35

        if generate_mach_cont:  # if the mach contours should be generated
            print("Generating the mach number contours...")

            graphics = Graphics(ssn)  # create a graphics object
            graphics.picture.x_resolution(resolution=1920)  # specify image dimensions
            graphics.picture.y_resolution(resolution=1080)  # only works when GUI is on

            if is3D:
                graphics.contour['mach_cont'] = {
                    'field': 'mach-number',  # field
                    "surfaces_list": [symmetry_1_name],  # specify surfaces
                    'contour_lines': contour_lines,  # specify if contour lines should be on
                    'coloring': {
                        'option': smooth_or_banded  # specify smooth or banded coloring
                    }
                }

            if not is3D:
                graphics.contour['mach_cont'] = {
                    'field': 'mach-number',  # field
                    # "surfaces_list": [surface_name], # specify surfaces
                    'contour_lines': contour_lines,  # specify if contour lines should be on
                    'coloring': {
                        'option': smooth_or_banded  # specify smooth or banded coloring
                    }
                }

            graphics.contour['mach_cont'].display()  # display (only works when GUI is on)
            graphics.views.restore_view(view_name="front")  # set the correct view

            # not sure if these should be inputs, probably not
            graphics.views.camera.zoom(factor=zoom_value)  # set zoom and pan
            graphics.views.camera.pan(right=pan_value)

            # save the picture
            mach_pic_name = os.path.join(folder_path, f'{airfoil}_{nickname}_mach_cont.png')
            graphics.picture.save_picture(file_name=mach_pic_name)

            print(f"PASS: Mach number contours generated and saved as {mach_pic_name}...")


        # %% Generate pressure contour
        if generate_pres_cont:
            print("Generating the pressure contours...")

            graphics = Graphics(ssn)  # define graphics object
            graphics.picture.x_resolution(resolution=1920)  # set the resolution, this only
            graphics.picture.y_resolution(resolution=1080)  # seems to work if GUI is on

            if is3D:  # if 3D, select the sym1 surface
                graphics.contour['pres_cont'] = {  # define name
                    'field': 'pressure',  # define the field
                    "surfaces_list": [symmetry_1_name],  # select surfaces
                    'contour_lines': contour_lines,  # create contours
                    'coloring': {
                        'option': smooth_or_banded  # smooth or banded contours
                    }
                }

            if not is3D:  # if 2D, then don't select any faces
                graphics.contour['pres_cont'] = {
                    'field': 'pressure',
                    # "surfaces_list": [symmetry_1_name],
                    'contour_lines': contour_lines,
                    'coloring': {
                        'option': smooth_or_banded  # smooth or banded contours
                    }
                }

            graphics.contour['pres_cont'].display()  # display the countours
            graphics.views.restore_view(view_name="front")  # change view

            graphics.views.camera.zoom(factor=zoom_value)  # set zoom and pan
            graphics.views.camera.pan(right=pan_value)

            # define picture path
            pres_pic_name = os.path.join(folder_path, f'{airfoil}_{nickname}_pres_cont.png')

            # Save the picture
            graphics.picture.save_picture(file_name=pres_pic_name)
            print(f"PASS: Pressure contours generated and saved as {pres_pic_name}...")


        # %% Creating iso Surface and y+ plot
        y_plus_plot_name = f"{airfoil}_{nickname}_y-plus"

        if generate_yplus:
            if is3D:  # if mesh is 3D a z-constant iso-surface is created
                iso_surface_name = 'z-constant-iso-surface'

                ssn.results.surfaces.iso_surface[iso_surface_name] = {
                    'surfaces': [upper_name, lower_name],
                    'field': 'z-coordinate',
                    'iso_values': [0]}

                ssn.results.plot.xy_plot[y_plus_plot_name] = {
                    'y_axis_function': 'y-plus',
                    'surfaces_list': [iso_surface_name]}

            else:  # if the mesh is 2D no need for a constant z iso-surface
                y_plus_plot_name = f"{airfoil}_{nickname}_y-plus"

                ssn.results.plot.xy_plot[y_plus_plot_name] = {
                    'y_axis_function': 'y-plus',
                    'surfaces_list': [upper_name, lower_name]}

            # ssn.results.plot[y_plus_plot_name.display()
            ssn.results.plot.xy_plot.display()

            graphics = Graphics(ssn)
            graphics.picture.x_resolution(resolution=1920)
            graphics.picture.y_resolution(resolution=1080)
            graphics.display()

            y_plus_pic_name = f"{y_plus_plot_name}.png"
            y_plus_pic_name = os.path.join(folder_path, y_plus_pic_name)
            graphics.picture.save_picture(file_name=y_plus_pic_name)

            print(f"PASS: y+ plot generated and saved as {y_plus_pic_name}")


        # %% Generating pressure plot
        if generate_pres_plot:

            pres_plot_name = f"{airfoil}_{nickname}_pres-plot"

            ssn.results.plot.xy_plot[pres_plot_name] = {
                'y_axis_function': 'pressure',
                'surfaces_list': [upper_name, lower_name]}

            ssn.results.plot.xy_plot.display()

            graphics = Graphics(ssn)
            graphics.picture.x_resolution(resolution=1920)
            graphics.picture.y_resolution(resolution=1080)
            graphics.display()

            pres_pic_name = f"{pres_plot_name}.png"
            pres_pic_name = os.path.join(folder_path, pres_pic_name)
            graphics.picture.save_picture(file_name=pres_pic_name)

            print(f"PASS: Pressure plot generated and saved as {pres_pic_name}")


        # %% Displaying and saving the residuals
        solution.monitor.residual.plot()  # show the residuals

        res_pic_name = f'{airfoil}_{nickname}_residuals'  # define name
        res_pic_name = os.path.join(folder_path, res_pic_name)
        graphics.picture.save_picture(file_name=res_pic_name)  # take screenshot3


        # %% Saving the case and data
        case_name = f"{airfoil}_{nickname}"

        case_name = os.path.join(folder_path, case_name)
        print(f"Saving files as {case_name}...")

        ssn.settings.file.write_case_data(
            file_name=case_name
        )

        print("PASS: Case and data saved...")


        # %% Stopping the timer and shutting down
        t1 = time.time()  # Stop timer
        total_time = t1 - t0

        minutes = int(total_time // 60)
        seconds = total_time % 60

        print("PASS: Timer Stopped.")
        print(f"Total time taken: {minutes} minutes and {seconds:.3f} seconds")
        print(f"Total time taken in seconds: {total_time}")


        ssn.exit()  # shutting down
        logger.flush()
        print("PASS: Complete")
        print("PASS: Session closed")

        return folder_path, report_1_file, report_2_file, name

    finally:

        # stopping the logger
        if logger is not None:
            logger.flush()
            logger.stop()
