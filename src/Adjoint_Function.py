"""
Created on Wed Feb 11 15:20:52 2026

@author: O
"""


def optimize(
    file_path,  # file path of the case/data file (already solved)
    nickname='',  # nickname to give the file to distinguish it
    airfoil="not_specified",  # airfoil name, eg. NACA_0012
    contour_lines=False,  # use contour lines on mach/pressure plot?
    smooth_or_banded='banded',  # smooth or banded lines on mach/pressure plot
    save_screenshots=True,  # save screenshot between each iteration?
    transient=False,  # transient solve or not

    # solver type at the end
    # doesn't actually affect adjoint solve because adjoint only
    # supports pressure-based non-transient solves, but at the final
    # solve these settings will be applied
    solver_type='pressure-based',
    visc_model='k-omega',

    show_gui=True,  # show user interface or not. Yes by default so the screenshots look good
    processor_count=4,  # processor core count
    upper_name='upper',  # name of upper surface of airfoil
    lower_name='lower',  # name of lower surface of airfoil
    aoa=0,  # angle of attack, in deg
    convergence_criteria=10**-5,  # convergence criteria
    use_convergence_criteria=True,  # specify convergence criteria or leave as default
    use_energy=False,  # use adjoint energy?
    use_turbulence=False,  # use adjoint turbulence?
    # this copies the flow scheme settings from the solution file
    use_best_match=False,  # ansys recommends it as false
    apply_preconditioning=False,  # helps more difficult solves converge
    target_change=10,  # target change per iteration, in percentage
    use_percentage = True, # is target change percentage?
    optimize_target='lift-to-drag',  # which observable to optimize: 'lift-to-drag', 'lift', or 'drag'
    mach_num=0.5,  # default mach number

    # these are used at the very end for a better solution
    time_step_scale=5,  # pseudo time step scale, if steady-state
    time_step_size=0.001,  # time step size, in seconds, if transient
    time_step_count=100,  # amount of time steps
    iters_per_time_step=20,  # iterations for each time step
    final_iterations=300,  # total number of iterations, if steady-state

    # infinite mode runs until the cell quality drops below the warning level
    infinite_mode=False,  # technically not infinite, does 999 iteration
    min_orth_quality_limit=0.06,  # minimum orthogonal quality, at which the infinite mode should end
    maintain_len=True,  # if the length of the airfoil should stay the same (recommended)
    adjoint_iterations=20,  # setting for adjoint iterations
    optimization_loop_count=5,  # how many optimization loops should be used
    # these are temporary numbers only used for adjoint solves
    pseudo_time_method = 'off', # this is never changed at the end
    temp_iterations=200,  # num of iterations, if steady-state
    temp_time_step_scale=None,  # pseudo time step scale, if steady-state
    temp_time_step_size=None,  # time step size, in seconds
    temp_time_step_count=10,  # amount of time steps
    temp_iters_per_time_step=20,  # iterations for each time step

    farfield_name='farfield',  # name of pressure far field
    shut_down_when_done=True,  # shut down when done?
    generate_yplus=True,  # generate yplus plot or not
    generate_pres_plot=True,  # generate pres plot or not

    report_1_name='C_d',  # name of the drag report
    report_2_name='C_l',  # name of the lift report
    report_plot=True,  # plot results?
    report_file=True,  # export the results to a file?
    make_gifs=True,  # make all screenshots into gifs?
    gif_duration=100,  # duration, in ms, per frame of the gif

    change_boundary_conditions=False,  # change the boundary conditions from solution?
    altitude=0,  # height above sea level, in m
    mesh_width=0.1,  # width of the mesh, in m
    infinite_mode_max = 999, # maximum number of iterations in infinite mode, so it doesn't get stuck forever
    custom_mode = False, # custom mode if false by default
    custom_path = [] # empty by default, must be user-specified
):

    logger = None
    try:  # importing stuff
        import math
        import os
        import time
        from datetime import timedelta
        from pathlib import Path

        import ansys.fluent.core as pyfluent
        from ansys.fluent.core.solver import Graphics, Mesh

        from dachis_tools import console_logger, new_folder_and_file, make_gif, find_result

        # create and get the new file path and new folder name (based on the nickname)
        new_file_path, folder_path = new_folder_and_file(file_path, nickname, False)
        name = f"{airfoil}_{nickname}"  # get the file name
        logger = console_logger(folder_path=folder_path, file_name=name)
        logger.start()  # start the logger

        # Print the progress report
        print('--------------------------------------------------------')
        print(f'LOADING {name}')
        print('--------------------------------------------------------\n')


        # %% Starting the timer
        t0 = time.time()

        print("PASS: Timer On")


        # %% Check if temp values are none, apply the same settings if they are
        if temp_time_step_scale is None:
            temp_time_step_scale = time_step_scale

        if temp_time_step_size is None:
            temp_time_step_size = time_step_size


        # %% enable infinite mode
        if infinite_mode:  # if infinity mode is on, set loop count to 999
            print(f"PASS: Infinite mode ON. Mesh will run until orthagonal quality is less than {min_orth_quality_limit}")
            optimization_loop_count = infinite_mode_max
        
        # %% Parse custom_path from string to list of floats
        if custom_mode and isinstance(custom_path, str):
            custom_path = [float(x.strip().replace("'", "").replace(" ", "")) for x in custom_path.split(',') if x.strip()]


        # %% Check if 2D
        phrase = '2D'
        is3D = True
        if phrase.lower() in file_path.lower() or phrase.lower() in airfoil.lower():
            print("PASS: 2D Mesh Detected. Switching to 2D Meshing Mode...")
            is3D = False

        if is3D:
            dimensions = 3
        else:
            dimensions = 2
        

        # %% Calculate x and y components of velocity
        aoa = math.radians(aoa)  # convert degrees to radians
        x_mach = math.cos(aoa)  # x component is cosine of angle of attack
        y_mach = math.sin(aoa)  # y component is sine of angle of attack


        # %% Calculating the alternate values
        if change_boundary_conditions:

            print("Calculating the new reference values...")

            # Values taken from: https://en.wikipedia.org/wiki/Standard_sea-level_conditions
            # These are not inputs because they're constants
            temp_lapse_rate = 0.0065  # K/m
            sea_level_temp = 288.15  # K
            g = 9.80665  # m/s^2
            R_uni = 8.31432  # universal gas constant, J/ mol*K
            mol_mass = 0.028964420  # molar mass of air
            rho_0 = 1.225  # kg/m^3
            sea_level_pressure = 101325  # pa
            gamma = 1.4  # adiabatic index, ratio of specific heats
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
            pressure = p_0 * ((T_0) / (T_0 - alpha * h)) ** ((g * mol_mass) / (R_uni * -alpha))
            # d_T = temperature - sea_level_temp # change in temperature, K

            print("PASS: Reference values calculated...")
            print(f"Density [kg/m^3]: {density}...")
            print(f"Pressure [Pa]: {pressure}...")
            print(f"Temperature [K]: {temperature}...")
            print(f"Velocity [m/s]: {velocity}...")
            print(f"Dynamic Viscosity [kg/ms]: {dynamic_visc: e}...")
            print(f"Kinematic Viscosity [kg/ms]: {kinematic_visc: e}...")


        # %% Adjoint Part
        ssn = pyfluent.launch_fluent(
            mode=pyfluent.FluentMode.SOLVER,  # meshing mode
            show_gui=show_gui,  # show the program running
            processor_count=processor_count,  # specify processor count
            precision=pyfluent.Precision.DOUBLE,  # single or double precision
            dimension=dimensions  # 2d or 3d?
        )


        # %% Reading the case and file
        print("PASS: Session launched. Reading case and data files...")
        ssn.settings.file.read_case_data(file_name=file_path)


        # %% Specify the temporary settings
        # set viscousity model to k-omega GEKO
        ssn.settings.setup.models.viscous.model = "k-omega"
        ssn.settings.setup.models.viscous.k_omega_model = "geko"

        # make sure it's pressure-based and steady-state
        # adjoint doesn't work otherwise
        ssn.settings.setup.general.solver = {
            'type': 'pressure-based',
            'time': 'steady'
        }
        
        ssn.settings.solution.methods.pseudo_time_method.formulation.coupled_solver = pseudo_time_method

        # set the number of iterations and time scale
        ssn.settings.solution.run_calculation = {
            'pseudo_time_settings': {  # specify time settings
                'time_step_method': {
                    'time_step_size_scale_factor': temp_time_step_scale  # specify the time step
                }
            },
            'iter_count': temp_iterations  # specify the number of iterations
        }
        

        # %% Creating Observables
        print("PASS: Case and data files read...")
        ssn.tui.adjoint.observable.create()  # this activates the adjoint solver
        # don't know why but it doesn't work otherwise
        ad = ssn.settings.design.gradient_based



        # %% Setting up the observables
        print("PASS: Adjoint solver active. Defining observables...")
        ssn.settings.design.gradient_based.observables = {
            'named_expressions': {},
            'definition': {
                'drag': {
                    'name': 'drag',  # define the drag observable
                    'type': 'force',
                    'walls': [upper_name, lower_name],  # select the zones
                    'vector': [x_mach, y_mach, 0.0]  # vectors is based on aoa
                },
                'lift': {
                    'name': 'lift',  # define the lift observable
                    'type': 'force',
                    'walls': [upper_name, lower_name],
                    'vector': [-y_mach, x_mach, 0.0]
                },
                'lift-to-drag': {
                    'name': 'lift-to-drag',  # define the lift-to-drag ratio
                    'type': 'ratio',
                    'numerator': 'lift',
                    'denominator': 'drag'
                }
            },
        }


        # %% Maximising lift-to-drag
        # select the lift-to-drag to optimize it
        ad.observables.selection = {  # select the observable to optimize
            'adjoint_observable': optimize_target  # without this step the next one doesn't work
        }

        ad.calculation = {  # change the adjoint iteration setting
            'iteration_count': adjoint_iterations
        }

        print("PASS: Observables defined. Defining objectives...")

        # define the objectives
        ssn.settings.design.gradient_based.design_tool.objectives = {
            'include_current_data': True,
            'objectives': {
                optimize_target: {
                    'observable': optimize_target,
                    'step_direction': 'target-change-in-value',
                    'target_change': target_change,
                    'change_as_percentage': use_percentage,  # set change as percentage
                    'weight': 1.0
                }
            },
            'manage_data': {}
        }

        ad.design_tool.objectives.objectives.update()  # update the objectives


        # %% Changing the convergence criteria
        print("PASS: Objectives defined. Specifying the convergence criteria...")

        if use_convergence_criteria:  # specifying the convergence criteria
            ssn.settings.design.gradient_based.monitors = {
                'adjoint_equations': {
                    'continuity': {
                        'check_convergence': True,
                        'absolute_criteria': convergence_criteria
                    },
                    'energy': {
                        'check_convergence': use_energy,
                        'absolute_criteria': convergence_criteria
                    },
                    'local-flow-rate': {
                        'check_convergence': True,
                        'absolute_criteria': convergence_criteria
                    },
                    'velocity': {
                        'check_convergence': True,
                        'absolute_criteria': convergence_criteria
                    }
                },
                'options': {
                    'print': True, 'plot': True,
                    'n_display': 1000
                }
            }


        # %% Disable energy and enable turbulence
        # this setting enables the solver to match the flow methods specified
        # previously in the solution (most things will be second-order)
        if use_best_match:
            ssn.settings.design.gradient_based.methods.best_match()
            print("PASS: Best match applied...")

        print("Specifying solution methods...")
        ssn.settings.design.gradient_based.methods = {
            'energy': {'adjoint_activation': use_energy},
            'turbulence': {'adjoint_activation': use_turbulence}
        }
        print("PASS: Solution methods specified...")


        # %% Apply preconditioning
        # this selects the 'complex case' method in solution controls
        # which automatically sets the 1st scheme to residual minimisation quick
        # do I know what that actually does? no.
        # But it helps the difficult ones converge, I think
        if apply_preconditioning:
            ssn.settings.design.gradient_based.controls.stabilization.complex_case()
            print("PASS: Preconditioning applied")


        # %% Specifying the design tool parameters
        x_points = 50 # WIP TRYING 50, SEE WHAT HAPPENS.
        y_points = 50

        print("PASS: Convergence criteria specified. Specifying design tool settings...")

        ad.design_tool = {
            "region": {
                "modifiable_zones": [upper_name, lower_name],
                'cartesian': {
                    'conditions': {
                        'x': {'points': x_points},  # specify the number of points
                        'y': {'points': y_points}
                    },
                }
            },
            'objectives': {
                'objectives': {
                    optimize_target: {
                        'observable': optimize_target,
                        'step_direction': 'target-change-in-value',
                        'target_change': target_change
                    }
                }
            }
        }


        # %% Setting the bounding box size
        dt = ad.design_tool

        # establish boundary box size
        print("Getting bounds...")
        dt.region.get_bounds()

        if maintain_len:  # if length should be maintained, do everything below
            print("Length will remain unchanged...")
            dt.region.smaller_region()  # smaller region snaps the bounds right to the edges of the airfoil

            # then the x coordinates are noted, and larger_region() is ran twice
            # this expands the boundary box in all directions
            x_coords = dt.region.cartesian.extent.x()
            dt.region.larger_region()
            dt.region.larger_region()
            dt.region.larger_region()
            dt.region.larger_region()

            # finally the x coordinates are replacd with the old, small x coordinates
            # this way the y coordinates are larger, but the length will not change.
            dt.region.cartesian.extent.x = x_coords

        else:  # expand the region otherwise
            dt.region.larger_region()
            dt.region.larger_region()
            dt.region.larger_region()
            dt.region.larger_region()
        print("PASS: Boundary box established...")


        # %%
        # Set number of iterations again - because the full amount isn't needed when testing
        solution = ssn.settings.solution

        print("PASS: Design tool settings specified. Specifying temporary solution settings...")

        if transient:  # if transient, specify time step count and size

            print('Transient solve detected. Specifying transient settings...')

            ssn.settings.solution.run_calculation = {
                'transient_controls': {
                    'time_step_count': temp_time_step_count,
                    'time_step_size': temp_time_step_size,  # in seconds
                    'max_iter_per_time_step': temp_iters_per_time_step,
                }
            }

        else:

            ssn.settings.solution.run_calculation = {
                'pseudo_time_settings': {  # specify time settings
                    'time_step_method': {
                        'time_step_size_scale_factor': temp_time_step_scale  # specify the time step
                    }
                },
                'iter_count': temp_iterations  # specify the number of iterations
            }


        # %% Defining the contours
        graphics = Graphics(ssn)

        graphics.contour['mach_cont'] = {
            'field': 'mach-number',  # field
            # "surfaces_list": [symmetry_1_name], # specify surfaces
            'contour_lines': contour_lines,  # specify if contour lines should be on
            'coloring': {
                'option': smooth_or_banded  # specify smooth or banded coloring
            }
        }

        graphics.contour['pres_cont'] = {  # define name
            'field': 'pressure',  # define the field
            # "surfaces_list": [symmetry_1_name], # select surfaces
            'contour_lines': contour_lines,  # create contours
            'coloring': {
                'option': smooth_or_banded  # smooth or banded contours
            }
        }


        # %% Defining values for the display functions
        mesh = Mesh(ssn)
        mesh.surfaces_list = mesh.surfaces_list.allowed_values()

        graphics.picture.x_resolution(resolution=1920)  # set the resolution, this only
        graphics.picture.y_resolution(resolution=1080)  # seems to work if GUI is on

        if is3D:  # specify camera zoom and pan values
            zoom_value = 25  # these values are found via
            pan_value = 2.45  # trial and error
        else:
            zoom_value = 20
            pan_value = 3.32


        # %% initialize the drag and lift reports
        # Initialize the drag report
        report_1 = f"{report_1_name}_{airfoil}_{nickname}"

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
        report_2 = f"{report_2_name}_{airfoil}_{nickname}"

        solution.report_definitions.lift[f'{report_2}'] = {
            'force_vector': [-y_mach, x_mach, 0],
            'zones': [upper_name, lower_name],
            'create_report_file': report_file,
            'create_report_plot': report_plot,
        }

        print(f"PASS: {report_2} created...")
        report_2_file = report_2 + '-rfile.out'


        # %% Specifying custom reference values, if necessary
        if change_boundary_conditions:

            print("Specifying the new reference values...")

            # Inputing the reference values calculated above
            ssn.settings.setup.reference_values = {  # input the reference values
                'density': density,
                'pressure': pressure,
                'temperature': temperature,
                'velocity': velocity,
                'viscosity': dynamic_visc,
            }
            
            # change material settings
            # specifying the boundary components
            ssn.settings.setup.boundary_conditions.pressure_far_field['farfield'] = {
                'momentum': {
                    'gauge_pressure': pressure,  # gauge pressure
                    'mach_number': mach_num,  # mach number
                    'flow_direction': [x_mach, y_mach]  # x and y components of flow
                },
                'thermal': {
                    'temperature': temperature  # temperature
                    }}
            print("PASS: Reference values specified...")

            
            # %% if boundary conditions were changed, re-initialize
            print("Initializing...")
            ssn.settings.solution.initialization.standard_initialize()  # standard initialize
            print("PASS: Initialization complete...")
            
                
            # %% and re-solve
            print("PASS: Starting initial solve...")
            ssn.settings.solution.run_calculation.calculate()  # start the solve
            print("PASS: Solve finished...")
            

        # %% Defining the save_mesh, save_mach, and save_pres functions
        def save_mesh(path, name=f'{airfoil}_{nickname}_mesh.png'):

            mesh.display()
            graphics.views.restore_view(view_name="front")  # set the correct view
            graphics.views.camera.zoom(factor=zoom_value)  # set zoom and pan
            graphics.views.camera.pan(right=pan_value)

            pic_name = os.path.join(path, name)  # set the name and screenshot
            graphics.picture.save_picture(file_name=pic_name)

        def save_mach(path, name=f'{airfoil}_{nickname}_mach_cont.png'):

            graphics.contour['mach_cont'].display()  # display (only works when GUI is on)
            graphics.views.restore_view(view_name="front")  # set the correct view

            # not sure if these should be inputs, probably not
            graphics.views.camera.zoom(factor=zoom_value)  # set zoom and pan
            graphics.views.camera.pan(right=pan_value)

            pic_name = os.path.join(path, name)  # set the name and screenshot
            graphics.picture.save_picture(file_name=pic_name)

        def save_pres(path, name=f'{airfoil}_{nickname}_pres_cont.png'):

            graphics.contour['pres_cont'].display()  # display (only works when GUI is on)
            graphics.views.restore_view(view_name="front")  # set the correct view

            # not sure if these should be inputs, probably not
            graphics.views.camera.zoom(factor=zoom_value)  # set zoom and pan
            graphics.views.camera.pan(right=pan_value)

            pic_name = os.path.join(path, name)  # set the name and screenshot
            graphics.picture.save_picture(file_name=pic_name)


        # %% Defining the optimization_loop function
        def optimization_loop(loop_count=5, save=True):

            phrase = "Minimum Orthogonal Quality = "
            obs_phrase = "Observable Value [dimensionless]: "
            obs_file_path = os.path.join(folder_path, f'{airfoil}_{nickname}_observable_values.txt')

            # write the header for the observable values file
            with open(obs_file_path, 'w') as obs_file:
                obs_file.write(f"Observable: {optimize_target}\n")
                obs_file.write("---\n")

            # Determine what to iterate over
            if custom_mode:
                iterations = list(enumerate(custom_path, start=1))
                total_iterations = len(custom_path)
                print("PASS: Starting Adjoint in custom mode...")
            else:
                iterations = list(enumerate(range(1, loop_count + 1), start=1))
                total_iterations = loop_count 
                
            start_time = time.time()  # start the timer
            i = 0
            print(f'Starting {loop_count} loops...')

            print("Initializing adjoint solve...")
            ad.calculation.initialize()  # initialize the adjoint
            print("PASS: Adjoint solve initialized...")

            mesh_path = Path(folder_path) / "mesh"
            pres_path = Path(folder_path) / "pres_cont"
            mach_path = Path(folder_path) / "mach_cont"

            if save:  # if the screenshots should be saved
                # create folder paths
                mesh_path.mkdir(parents=True, exist_ok=True)
                pres_path.mkdir(parents=True, exist_ok=True)
                mach_path.mkdir(parents=True, exist_ok=True)

            for i, iter_value in iterations:

                print('--------------------------------------------------')
                print(f"          Starting Loop {i}/{total_iterations}...")
                print('--------------------------------------------------')
                
            # Update target change if custom_mode
                if custom_mode:
                    ssn.settings.design.gradient_based.design_tool.objectives = {
                        'include_current_data': True,
                        'objectives': {
                            optimize_target: {
                                'observable': optimize_target,
                                'step_direction': 'target-change-in-value',
                                'target_change': iter_value,
                                'change_as_percentage': use_percentage,
                                'weight': 1.0
                            }
                        },
                        'manage_data': {}
                    }
                    ad.design_tool.objectives.objectives.update()
                    print(f"PASS: Design change target set to {iter_value}")
                
                # calculate the design change
                ad.design_tool.design_change.calculate_design_change()
                print('PASS: Design Change calculated. Starting adjoint solve...')

                # calculate the new values
                ad.calculation.calculate()
                print('PASS: Solved...')

                # morph the mesh
                ad.design_tool.design_change.modify()
                print("PASS: Mesh morphed...")

                # Remeshing
                # I don't know where this function comes from
                # but ANSYS itself suggested it and it works
                # doing it multiple times because the results improve
                # unfortunately it tops out after ~3 iterations
                # so there's no point in making a loop for this
                print("Remeshing...")
                ssn.mesh.repair_improve.improve_quality()
                ssn.mesh.repair_improve.improve_quality()
                ssn.mesh.repair_improve.improve_quality()
                # input
                # ('') # temporary. Pause for troubleshooting
                ad.design_tool.design_change.remesh()
                print("PASS: Remeshed...")

                ad.observables.selection.evaluate()  # evaluate the current value

                ssn.settings.solution.run_calculation.calculate()  # calculate the new solution
                print("PASS: Solution complete. Remeshing...")

                print(f"PASS: Loop {i}/{loop_count} complete...")

                # find the orthagonal quality and observable value
                logger.flush()  # flush the logger to the .txt file so that the values can be read
                current_orth_quality = find_result(folder_path, phrase)
                print(f'Current orthagonal quality: {current_orth_quality}')

                observable_value = find_result(folder_path, obs_phrase)
                print(f'Current {optimize_target} value: {observable_value}')

                with open(obs_file_path, 'a') as obs_file:
                    obs_file.write(f"Iteration {i}: {observable_value}\n")

                # calculate the elapsed time and average time, to estimate
                # the remaining time
                elapsed_time = time.time() - start_time
                average_time = elapsed_time / i

                iters_remaining = total_iterations - i
                estimated_time = average_time * iters_remaining
                formatted_time = str(timedelta(seconds=round(estimated_time)))

                print(f'Estimated time remaining: {formatted_time}')

                if save:

                    mesh_name = f'mesh_{i:0{len(str(loop_count))}}.png'  # save mesh
                    save_mesh(mesh_path, mesh_name)

                    pres_name = f'pres_cont_{i:0{len(str(loop_count))}}.png'  # save pressure contours
                    save_pres(pres_path, pres_name)

                    mach_name = f'mach_cont_{i:0{len(str(loop_count))}}.png'  # save mach countours
                    save_mach(mach_path, mach_name)

                if infinite_mode and current_orth_quality < min_orth_quality_limit:

                    print("Orthagonal quality limit reached. Starting final solve...")
                       
                    ssn.mesh.repair_improve.improve_quality()
                    ssn.mesh.repair_improve.improve_quality()
                    ssn.mesh.repair_improve.improve_quality()
                    ad.design_tool.design_change.remesh()  
                     
                    ad.design_tool.design_change.revert()
                    print("PASS: Reverted to last acceptable mesh...")

                   
                    break

            # these are used to make gifs down the line
            return mesh_path, pres_path, mach_path
        
        # %% call the optimization loop here
        mesh_path, pres_path, mach_path = optimization_loop(optimization_loop_count, save_screenshots)


        # %% Re-specify the settings once adjoint is done
        # set the viscous model
        # ssn.settings.setup.models.viscous.model = visc_model

        # if transient:  # if transient, specify time step count and size

            # print('Transient solve detected. Specifying transient settings...')

            # ssn.settings.setup.general.solver = {
                # 'time': 'unsteady-1st-order'
            # }

            # solution.run_calculation = {
                # 'transient_controls': {
                    # 'time_step_count': time_step_count,
                    # 'time_step_size': time_step_size,  # in seconds
                    # 'max_iter_per_time_step': iters_per_time_step,
                # }
            # }

        # if not transient:

        solution.run_calculation = {
            'pseudo_time_settings': {  # specify time settings
                'time_step_method': {
                    'time_step_size_scale_factor': time_step_scale  # specify the time step
                }
            },
            'iter_count': final_iterations  # specify the number of iterations
        }

        # set pressure/density based
        # ssn.settings.setup.general.solver = {
            # 'type': solver_type
        # }


        # %% Save the residuals
        solution.monitor.residual.plot()  # show the residuals

        res_pic_name = f'{airfoil}_{nickname}_optimizing_residuals'  # define name
        res_pic_name = os.path.join(folder_path, res_pic_name)
        graphics.picture.save_picture(file_name=res_pic_name)  # take screenshot


        # %% Re-run the actual solution
        solution = ssn.settings.solution

        print("PASS: Initializing...")
        solution.initialization.hybrid_initialize()  # initializing
        print("PASS: Initialization complete...")

        print("Starting solve...")
        solution.run_calculation.calculate()  # start the solve
        print("PASS: Solve finished...")


        # %% Saving the final residuals
        solution.monitor.residual.plot()  # show the residuals
        res_pic_name = f'{airfoil}_{nickname}_final_residuals'  # define name
        res_pic_name = os.path.join(folder_path, res_pic_name)
        graphics.picture.save_picture(file_name=res_pic_name)  # take screenshot


        # %% Getting the mass flow to check simulation validity
        # add the default flux report file extension
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


        # %% Saving the cumulative plot
        print("Drawing the cumulative plot...")
        results.plot.cumulative_plot = {
            'zones': {
                'name': f'{airfoil}_{nickname}_optimized_cumulative_plot',  # specify name
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
                ssn.results.plot.xy_plot[y_plus_plot_name] = {
                    'y_axis_function': 'y-plus',
                    'surfaces_list': [upper_name, lower_name]}

            # ssn.results.plot[y_plus_plot_name.display()
            ssn.results.plot.xy_plot.display()
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
            graphics.display()

            pres_pic_name = f"{pres_plot_name}.png"
            pres_pic_name = os.path.join(folder_path, pres_pic_name)
            graphics.picture.save_picture(file_name=pres_pic_name)

            print(f"PASS: Pressure plot generated and saved as {pres_pic_name}")


        # %% Save the case and data files
        case_name = f"{airfoil}_{nickname}"
        case_name = os.path.join(folder_path, case_name)

        print(f"Saving files as {case_name}...")

        ssn.settings.file.write_case_data(
            file_name=case_name
        )

        print("PASS: Case and data saved...")


        # %% Save the displacement file
        # this file includes coordinates for the modified airfoil
        disp_name = f"{airfoil}_{nickname}_optimized_displacements.dis"
        disp_path = os.path.join(folder_path, disp_name)

        ad.design_tool.design_change.export.optimal_displacements(
            file_name=disp_path
        )


        # %% Making gifs
        if make_gifs and save_screenshots:
            print("Creating gifs...")

            # define the gif names
            mesh_gif_name = f'{airfoil}_{nickname}_mesh.gif'
            mach_gif_name = f'{airfoil}_{nickname}_mach_cont.gif'
            pres_gif_name = f'{airfoil}_{nickname}_pres_cont.gif'

            # join the names to folder path
            mesh_gif_path = os.path.join(folder_path, mesh_gif_name)
            mach_gif_path = os.path.join(folder_path, mach_gif_name)
            pres_gif_path = os.path.join(folder_path, pres_gif_name)

            # run the make_gif function
            make_gif(mesh_gif_path, mesh_path, gif_duration)
            make_gif(mach_gif_path, mach_path, gif_duration)
            make_gif(pres_gif_path, pres_path, gif_duration)


        # %% Stopping the timer and shutting down
        t1 = time.time()  # Stop timer
        total_time = t1 - t0

        minutes = int(total_time // 60)
        seconds = total_time % 60

        print("PASS: Timer Stopped.")
        print(f"Total time taken: {minutes} minutes and {seconds:.3f} seconds")
        print(f"Total time taken in seconds: {total_time}")

        # %% Shutting down
        if not shut_down_when_done:  # if shut down when done is set to false, wait until the user types y
            while input('Shut down? Type y to continue').strip().casefold() != 'y': pass

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