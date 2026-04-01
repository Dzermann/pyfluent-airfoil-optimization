# -*- coding: utf-8 -*-
"""
Created on Fri Oct 31 23:49:14 2025

    This code runs an Ansys Fluent instance, imports geometry, and creates the mesh.
    All variables are specified below.

    Works as a function on any airfoil, as long as the variables are specified

    Start Date:  16/10/2025
    Finish Date:
    - Dachi Dzeria, C00290924
"""


def mesh(file_path,  # specify the file path
         nickname='',  # nicknames get added to folder names for easier identification
         airfoil='not_specified',  # specify which airfoil is being used
         show_gui=False,  # show/hide the fluent app when meshing. It's faster when set to false
         processor_count=4,  # amount of processors to use
         precision=None,  # single/double precision
         chord_len=1,  # default chord length
         te_len=0.005,  # default trailing edge length
         shut_down_when_done=True,  # shut the program down once finished?
         # Useful if the user needs to look at a specific airfoil - DOESN'T WORK CURRENTLY
         has_te=False,  # Does the airfoil have an open te?
         upper_name="upper",  # upper surface name
         lower_name="lower",  # lower surface name
         te_name="te",  # trailing edge name
         farfield_name="farfield",  # farfield name
         symmetry_1_name="sym1",  # symmetry names
         symmetry_2_name="sym2",
         Boi_1=True,  # add local sizing?
         Boi_1_Control_Name="airfoil_max",  # local sizing name
         Boi_1_Execution="Face Size",  # local sizing type
         Boi_1_Size=None,  # local sizing isze
         Boi_2_Control_Name="airfoil_te",  # local sizing name
         Boi_2_Execution="Proximity",  # local sizing type
         Boi_2_Min_Size=None,  # minimum size
         Boi_2_Cells_Per_Gap=2,  # cells per gap
         Boi_2_Scope_To="edges",  # scope to
         Surface_Rate=1.2,  # growth rate
         Surface_Min_Size=None,  # surface mesh min size
         Surface_Max_Size=None,  # surface mesh max size
         Surface_Size_Function="Curvature",  # surface mesh type
         Surface_Curvature_Normal_Angle=12,  # surface mesh normal angle
         Bl_Control_Name="uniform",  # boundary layer control name
         Bl_First_Height=2*10**-5,  # first height
         Bl_Number_Of_Layers=20,  # number of layers
         Bl_Rate=1.2,  # growth rate
         Volume_Fill_Type="polyhedra",  # volume fill type
         Volume_Fill_Size=None,  # volume fill size
         Volume_Fill_Rate=1.2,  # growth rate of the volume fill
         Units="m"):  # units

    logger = None
    try:
        # Starting the logger
        # importing the logger and file copier
        import os
        import time

        import ansys.fluent.core as pyfluent

        from dachis_tools import console_logger, new_folder_and_file, find_result, find_delimited

        # create and get the new file path and new folder name (based on the nickname)
        new_file_path, folder_path = new_folder_and_file(file_path, nickname, True)
        name = f"{airfoil}_{nickname}"  # get the file name
        logger = console_logger(folder_path=folder_path, file_name=name)
        logger.start()  # start the logger

        # Print the progress report
        print('--------------------------------------------------------------------------------------------')
        print(f'LOADING {name}')
        print('--------------------------------------------------------------------------------------------')


        # %%
        # Defining the "None" Variables
        # Define default inputs, if they are left empty
        if precision == "Double":
            precision = pyfluent.Precision.DOUBLE
        else:
            precision = None

        if Boi_1_Size is None:
            Boi_1_Size = chord_len / 100  # 1% of chord length

        if Boi_2_Min_Size is None:
            Boi_2_Min_Size = te_len / 2  # half of te length (so two cells per gap can be maintained)

        if Surface_Min_Size is None and has_te:  # default min surface mesh size
            Surface_Min_Size = te_len / 2  # half of te length
        elif Surface_Min_Size is None:  # if the airfoil doesn't have a te
            Surface_Min_Size = Bl_First_Height * 20 
        
        # print("===============================================")
        # print(f"SURFACE MIN SIZE IS: {Surface_Min_Size}")
        # print("===============================================")

        if Surface_Max_Size is None:  # default max surface mesh size
            Surface_Max_Size = chord_len / 2  # half of chord length

        if Volume_Fill_Size is None:
            Volume_Fill_Size = chord_len / 2


        # %%
        # Starting the timer
        t0 = time.time()

        print("PASS: Timer On")


        # %%
        # Check if 2D
        phrase = '2D'
        is3D = True
        if phrase.lower() in file_path.lower() or phrase.lower() in airfoil.lower():
            print("PASS: 2D Mesh Detected. Switching to 2D Meshing Mode...")
            is3D = False


        # %%
        # Opening Watertight Geometry Workflow
        print("Launching fluent session...")

        # --- Fluent launch settings ---
        ssn = pyfluent.launch_fluent(
            mode=pyfluent.FluentMode.MESHING,  # meshing mode
            show_gui=show_gui,  # show the program running
            processor_count=processor_count,  # specify processor count
            precision=precision  # double precision
        )
        print("PASS: Fluent session launched")


        location = os.path.join(folder_path, f'{airfoil}_{nickname}.msh.h5')

        # %%
        # Watertight Geometry and Mesh Importing
        if is3D:

            print("Importing geometry...")

            # Create watertight geometry
            wt = ssn.watertight()
            wt.import_geometry.file_name.set_state(new_file_path)  # import the file
            wt.import_geometry.length_unit.set_state(Units)  # set units
            wt.import_geometry()  # run import

            print("PASS: Geometry imported")


            # %%
            # Adding Local Sizing to upper/lower
            print("Adding local sizing to upper/lower...")
            if Boi_1:
                ls = wt.add_local_sizing  # add local sizing
                ls.add_child = "yes"  # add local sizing as child
                ls.boi_execution = Boi_1_Execution  # specify type
                ls.boi_face_label_list = [lower_name, upper_name]  # specify the list of faces
                ls.boi_size = Boi_1_Size  # specify size
                ls.boi_control_name = Boi_1_Control_Name  # name the local sizing

                ls.add_child_and_update()  # run the update

                print("PASS: Local sizing added to upper/lower")
            else:
                print("PASS: Local sizing skipped")


            # %%
            # Adding local sizing to te
            if has_te:
                print("Adding local sizing to te...")

                ls = wt.add_local_sizing  # same as above
                ls.add_child = "yes"
                ls.boi_execution = Boi_2_Execution
                ls.boi_scope_to = Boi_2_Scope_To  # scope to
                ls.boi_face_label_list = [te_name]
                ls.boi_min_size = Boi_2_Min_Size
                ls.boi_control_name = Boi_2_Control_Name
                ls.boi_cells_per_gap = Boi_2_Cells_Per_Gap  # specify cells per gap

                ls.add_child_and_update()

                print("PASS: Local sizing added to te")


            # %%
            # Generating the surface mesh
            print("Generating the surface mesh...")

            sf = wt.create_surface_mesh.cfd_surface_mesh_controls  # generating surface mesh
            sf.size_functions = Surface_Size_Function  # specify size function
            sf.growth_rate = Surface_Rate  # specify growth rate
            sf.max_size = Surface_Max_Size  # specify max and min size
            sf.min_size = Surface_Min_Size
            sf.curvature_normal_angle = Surface_Curvature_Normal_Angle  # specify normal angle

            wt.create_surface_mesh()  # generate

            print("PASS: Surface mesh generated")


            # %% Improving the surface mesh
            print("Improving surface mesh...")
            ssn.meshing.ImproveSurfaceMesh()
            print("PASS: Surface mesh improved...")


            # %%
            # Describing Geometry
            print("Describing Geometry...")

            dg = wt.describe_geometry  # describe geometry
            dg.setup_type.set_state("The geometry consists of only fluid regions with no voids")

            dg()

            print("Geometry description complete")


            # %%
            # Updating boundaries
            print("Updating boundaries...")

            ub = wt.update_boundaries  # updating boundaries

            # get the list of names and rename them
            ub.boundary_label_list.set_state(
                [farfield_name,
                 symmetry_1_name,
                 symmetry_2_name,
                 upper_name,
                 lower_name]
            )
            ub.boundary_label_type_list.set_state(
                ["pressure-far-field",
                 "symmetry",
                 "symmetry",
                 "wall",
                 "wall"]
            )
            ub.old_boundary_label_list.set_state(
                [farfield_name,
                 symmetry_1_name,
                 symmetry_2_name,
                 upper_name,
                 lower_name]
            )
            ub.old_boundary_label_type_list.set_state(
                ["pressure-far-field",
                 "symmetry",
                 "symmetry",
                 "wall",
                 "wall"]
            )

            ub()

            print("PASS: Boundaries updated")


            # %%
            # Updating regions
            # This should ideally rename the region to fluid, but I don't know how to do that
            # The code below works only for a specified name - need to figure out how to make it work for a wildcard
            print("Updating regions...")

            ur = wt.update_regions  # update regions
            # ur.Arguments.set_state(
            #     {
            #     r'OldRegionNameList': [r'*'],
            #     r'OldRegionTypeList': [r'fluid'],
            #     r'RegionNameList': [r'fluid'],
            #     r'RegionTypeList': [r'fluid'],
            #     }
            #         )
            ur()

            print("PASS: Regions updated")


            # %%
            # Adding boundary layers
            print("Adding boundary layers...")

            bl = wt.add_boundary_layer  # add boundary layers
            bl.first_height = Bl_First_Height  # specify the first height
            bl.offset_method_type = Bl_Control_Name  # specify bl method
            bl.bl_control_name = Bl_Control_Name  # specify the name
            bl.number_of_layers = Bl_Number_Of_Layers  # specify number of layer
            if Bl_Control_Name != "last-ratio":  # other than last raito, all others have growth rate
                bl.rate = Bl_Rate  # specify growth rate

            bl.add_child_and_update()  # update

            print("PASS: Boundary layers added")


            # %%
            # Generating the volume mesh
            print("Generating the volume mesh...")

            vm = wt.create_volume_mesh

            vm.Arguments.set_state(  # using the old method because the new one couldn't work
                {
                 "VolumeFill": Volume_Fill_Type,
                 "VolumeFillControls": {
                    "TetPolyMaxCellLength": Volume_Fill_Size,
                    "GrowthRate": Volume_Fill_Rate
                    }
                 })

            vm()
            print("PASS: Volume mesh generated")

            # Improve volume mesh
            print("Improving volume mesh...")
            ssn.meshing.ImproveVolumeMesh()
            print("PASS: Volume mesh improved...")


            # %%
            # Writing the mesh
            ssn.meshing.File.WriteMesh(  # writing the mesh
                FileName=location
            )
            print("PASS: Mesh Saved")


        else:
            # %% If it's 2D
            # 2D Geometry and Mesh Importing

            print("Importing geometry...")
            # Create watertight geometry
            two_d = ssn.two_dimensional_meshing()
            two_d.load_cad_geometry_2d.file_name.set_state(new_file_path)  # import the file
            two_d.load_cad_geometry_2d.length_unit.set_state(Units)  # set units
            two_d.load_cad_geometry_2d()  # run import

            print("PASS: Geometry imported")


            # %% Works
            # Updating regions
            # This should ideally rename the region to fluid, but I don't know how to do that
            print("Updating regions...")

            ur = two_d.update_regions_2d  # update regions
            ur()

            print("PASS: Regions updated")


            # %% Works
            # Updating boundaries
            print("Updating boundaries...")

            ub = two_d.update_boundaries_2d  # updating boundaries
            ub()

            print("PASS: Boundaries updated")


            # %%
            # Defining global sizing
            print("Updating Global Sizing")

            gs = two_d.define_global_sizing_2d
            gs.size_functions = Surface_Size_Function  # specify size function
            gs.grotwo_dh_rate = Surface_Rate  # specify grotwo_dh rate
            gs.max_size = Surface_Max_Size  # specify max and min size
            gs.min_size = Surface_Min_Size
            gs.curvature_normal_angle = Surface_Curvature_Normal_Angle  # specify normal angle

            gs()

            print("PASS: Global sizing updated")


            # %%
            # Adding Local Sizing to upper/lower
            print("Adding local sizing to upper/lower...")

            if Boi_1:  # check if local sizing should be added
                if Boi_1_Execution == "Face Size":
                    Boi_1_Execution = "Edge Size"

                ls = two_d.add_local_sizing_2d  # add local sizing
                ls.add_child = "yes"  # add local sizing as child
                ls.edge_label_list = [lower_name, upper_name]  # specify the list of faces
                ls.boi_execution = Boi_1_Execution  # specify type
                ls.boi_size = Boi_1_Size  # specify size
                ls.boi_control_name = Boi_1_Control_Name  # name the local sizing

                ls.add_child_and_update()  # run the update

                print("PASS: Local sizing added to upper/lower")
            else:
                print("PASS: Local sizing skipped")


            # %%
            # Adding local sizing to te
            if has_te:
                print("Adding local sizing to te...")

                if Boi_2_Execution == "Face Size":
                    Boi_2_Execution = "Edge Size"

                ls = two_d.add_local_sizing_2d  # same as above
                ls.add_child = "yes"
                ls.boi_execution = Boi_2_Execution
                ls.boi_scope_to = Boi_2_Scope_To  # scope to
                ls.boi_edge_label_list = [te_name]
                ls.boi_min_size = Boi_2_Min_Size
                ls.boi_control_name = Boi_2_Control_Name
                ls.boi_cells_per_gap = Boi_2_Cells_Per_Gap  # specify cells per gap

                ls.add_child_and_update()

                print("PASS: Local sizing added to te")


            # %%
            # Adding boundary layers
            print("Adding boundary layers...")

            bl = two_d.add_2d_boundary_layers  # add boundary layers
            bl.add_child = 'yes'
            bl.offset_method_type = Bl_Control_Name  # specify bl method
            bl.bl_control_name = Bl_Control_Name  # specify the name
            bl.first_layer_height = Bl_First_Height  # specify the first height
            bl.number_of_layers = Bl_Number_Of_Layers  # specify number of layer
            if Bl_Control_Name != "last-ratio":  # other than last raito, all others have growth rate
                bl.rate = Bl_Rate  # specify growth rate

            bl.add_child_and_update()  # update

            print("PASS: Boundary layers added")


            # %%
            # Generating the surface mesh
            print("Generating the surface mesh...")

            # Generate the surface mesh
            two_d.generate_initial_surface_mesh()

            print("PASS: Surface mesh generated")


            # %%
            # Writing the mesh
            two_d.write_2d_mesh(  # writing the mesh
                FileName=location
            )
            print("PASS: Mesh Saved")


        # %%
        # Stopping the timer
        t1 = time.time()  # Stop timer
        total_time = t1 - t0

        minutes = int(total_time // 60)
        seconds = total_time % 60


        # %% Get the results
        print("Reading results...")
        logger.flush()

        phrase1 = "The final maximum surface skewness is  "
        phrase2 = "he final minimum Orthogonal Quality is "
        phrase3 = "Overall Summary"

        skewness = find_result(folder_path, phrase1)
        orth_quality = find_result(folder_path, phrase2)
        cell_count = find_delimited(folder_path, phrase3)

        time_taken = total_time


        # %%
        # Print final results
        print("PASS: Timer Stopped.")
        print(f"Total time taken: {minutes} minutes and {seconds:.3f} seconds")
        print(f"Total time taken in seconds: {total_time}")
        print(f"Maximum skweness value: {skewness}")
        print(f"Mininum orhtagonal quality: {orth_quality}")
        print(f"Cell count: {cell_count}")

        # %% Shutting down
        if not shut_down_when_done:  # if shut down when done is set to false, wait until the user types y
            while input('Shut down? Type y to continue').strip().casefold() != 'y': pass

        ssn.exit()  # shutting down
        logger.flush()
        print("PASS: Complete")
        print("PASS: Session closed")

        return skewness, orth_quality, cell_count, time_taken, folder_path, name

    finally:

        # stopping the logger
        if logger is not None:
            logger.flush()
            logger.stop()
