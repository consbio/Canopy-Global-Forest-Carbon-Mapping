########################################################################################################################
# Author: Mike Gough
# Organization: Conservation Biology Institute
# Date: 04/15/2025
# Description: Identifies forested regions that warrant conservation prioritization on the basis of their high carbon
# density. This determination is made by identifying forested pixels that have a combined above and below-ground carbon
# density value in the upper 50th percentile of pixels in the same forest class and ecoregion (units are Mg C/ha).
# The final results are filtered to only include ecoregions in biomes where industrial forestry is occurring or in
# ecoregions outside of these biomes where the carbon density would be high enough to support commercial logging.
#
# To run from Python window in ArcGIS Pro:
# with open(script_path, 'r') as f:
#    script_code = f.read()
#    exec(script_code)
########################################################################################################################

import arcpy
from arcpy.sa import Raster
import datetime
import os
import csv

# Source Data
above_ground_carbon = r"\\loxodonta\gis\Source_Data\biota\global\Global_Aboveground_and_Belowground_Biomass_Carbon_Density\2010\Global_Maps_C_Density_2010_1763\data\aboveground_biomass_carbon_2010.tif"
below_ground_carbon = r"\\loxodonta\gis\Source_Data\biota\global\Global_Aboveground_and_Belowground_Biomass_Carbon_Density\2010\Global_Maps_C_Density_2010_1763\data\belowground_biomass_carbon_2010.tif"
forest = r"\\loxodonta\gis\Source_Data\biota\global\Mackey_Global_Forest_Data_FAO_Structural_Forms\FAO_structural_forms\Structural_forms_for_FAO_report.tif"
biomes_and_ecoregions = r"\\loxodonta\gis\Source_Data\boundaries\global\RESOLVE_Biomes_and_Ecoregions\2017\RESOLVE_Feature_Service_Export.gdb\RESOLVE_Biomes_and_Ecoregions_2017"

# Input Parameters
clip_inputs_for_testing = False
percentile_threshold = 50
version_label = "50th_percentile"
biomes_to_include = (
    "Boreal Forests/Taiga",
    "Temperate Broadleaf & Mixed Forests",
    "Temperate Conifer Forests",
    "Tropical & Subtropical Coniferous Forests",
    "Tropical & Subtropical Dry Broadleaf Forests",
    "Tropical & Subtropical Moist Broadleaf Forests",
)

ecoregions_of_interest_csv = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Docs\ecoregions_of_interest.csv"
carbon_for_ecoregion_selection = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Additional_Ecoregion_Selection.gdb\carbon_in_each_forest_cell_1ha_res"

# Data Directory
data_dir = os.path.join(r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data")

if clip_inputs_for_testing:
    # Set Test Directory
    data_dir = os.path.join(data_dir, "Test")
    # Clipping Features for Testing
    clipping_features = os.path.join(data_dir, "Inputs\Inputs.gdb\ecoregion_subset_extent")
    # Append to version label
    version_label += "_subset"

# Data Sub-Directories
input_dir = os.path.join(data_dir, "Inputs")
input_gdb = os.path.join(data_dir, "Inputs")

intermediate_dir = os.path.join(data_dir, "Intermediate")
intermediate_gdb = os.path.join(data_dir, r"Intermediate\Intermediate.gdb")

output_dir = os.path.join(data_dir, "Outputs")
output_gdb = os.path.join(data_dir, r"Outputs\Outputs.gdb")

scratch_dir = os.path.join(data_dir, r"Inputs\Scratch")
scratch_gdb = os.path.join(data_dir, r"Inputs\Scratch\Scratch.gdb")

# Final Output
final_output = output_dir + os.sep + "high_priority_forest_carbon_" + version_label + ".tif"
final_output_filtered = output_dir + os.sep + "high_priority_forest_carbon_filtered_" + version_label + ".tif"

arcpy.env.overwriteOutput = True
#arcpy.env.snapRaster = forest

start_time = datetime.datetime.now()
print("\nStart Time: " + str(start_time))


def clip_for_testing(above_ground_carbon, below_ground_carbon, forest, clipping_features):

    """ Clips the carbon and the forest pixels to a subset of ecoregions for testing on a smaller extent. """

    print("\nClipping data testing for testing...")

    #arcpy.env.extent = clipping_features
    #arcpy.env.mask = clipping_features

    with arcpy.EnvManager(snapRaster=above_ground_carbon):

        above_ground_carbon_clip = input_dir + os.sep + "aboveground_biomass_carbon_2010_forest_clip_" + version_label + ".tif"
        below_ground_carbon_clip = input_dir + os.sep + "belowground_biomass_carbon_2010_forest_clip_" + version_label + ".tif"
        forest_clip = input_dir + os.sep + "Structural_forms_for_FAO_report_clip_" + version_label + ".tif"

        print(" -> Creating clipped aboveground carbon...")
        above_ground_carbon_r = arcpy.sa.ExtractByMask(above_ground_carbon, clipping_features)
        above_ground_carbon_r.save(above_ground_carbon_clip)

        print(" -> Creating clipped belowground carbon...")
        below_ground_carbon_r = arcpy.sa.ExtractByMask(below_ground_carbon, clipping_features)
        below_ground_carbon_r.save(below_ground_carbon_clip)

    with arcpy.EnvManager(snapRaster=forest):

        print(" -> Creating clipped forest...")
        forest_r = arcpy.sa.ExtractByMask(forest, clipping_features)
        forest_r.save(forest_clip)

    return above_ground_carbon_clip, below_ground_carbon_clip, forest_clip


combined_carbon = intermediate_dir + os.sep + "combined_carbon_" + version_label + ".tif"


def combine_above_and_below_carbon(above_ground_carbon, below_ground_carbon):

    """ 1. Combines above and below ground carbon by adding them together. """

    print("\nCombining aboveground and belowground carbon...")

    with arcpy.EnvManager(snapRaster=above_ground_carbon):
        combined_carbon_r = arcpy.sa.Plus(above_ground_carbon, below_ground_carbon)
        combined_carbon_r.save(combined_carbon)


combined_forest_carbon = intermediate_dir + os.path.sep + "combined_forest_carbon_" + version_label + ".tif"


def clip_carbon_to_forest_pixels(carbon, forest):

    """ 2. Clips carbon to the forest pixels. """

    print("\nClipping carbon to forest pixels....")

    d = arcpy.Describe(carbon)
    cell_size = d.children[0].meanCellHeight

    with arcpy.EnvManager(cellSize=cell_size, snapRaster=carbon):

        arcpy.env.cellSize = cell_size
        arcpy.env.snapRaster = carbon
        forest_carbon_r = arcpy.sa.ExtractByMask(carbon, forest)
        forest_carbon_r.save(combined_forest_carbon)


forest_reclassified = intermediate_gdb + os.path.sep + "forest_reclassified_" + version_label


def reclassify_forests(forest):


    """ 3. Reclassifies the forest pixels into classes specified by Jim Strittholt. """

    print("\nReclassifying forest...")

    with arcpy.EnvManager(snapRaster=forest):

        forest_reclassified_r = arcpy.sa.Reclassify(
            in_raster=forest,
            reclass_field="Value",
            remap="1 1;2 1;3 1;4 2;5 2;6 2;7 3;8 3;9 3;10 4;11 4;12 4",
            missing_values="DATA"
        )
        forest_reclassified_r.save(forest_reclassified)


zones = intermediate_gdb + os.sep + "ecoregions_and_forest_zones_" + version_label


def create_zones(biomes_and_ecoregions, value_field, forest_reclassified):

    """ 4. Creates zones by combining rasterized ecoregions and reclassified forests. """

    print("\nCreating zones by combining rasterized ecoregions and reclassified forests...")

    d = arcpy.Describe(forest)
    cell_size = d.children[0].meanCellHeight

    with arcpy.EnvManager(snapRaster=forest_reclassified, cellSize=cell_size):

        ecoregions_raster = intermediate_gdb + os.sep + "ecoregions_raster_" + version_label

        if not arcpy.Exists(ecoregions_raster):

            print(" -> Converting ecoregions to raster...")

            arcpy.conversion.PolygonToRaster(
                in_features=biomes_and_ecoregions,
                value_field=value_field,
                out_rasterdataset=ecoregions_raster,
                cell_assignment="CELL_CENTER",
                priority_field="NONE",
                cellsize=cell_size,
                build_rat="BUILD"
            )

        print(" -> Combining rasterized ecoregions and reclassified forests...")

        zones_r = arcpy.sa.Combine([ecoregions_raster, forest_reclassified])
        zones_r.save(zones)


thresholds_raster = intermediate_gdb + os.sep + "combined_carbon_thresholds_" + version_label


def calc_percentile_threshold(zones, zone_field, carbon, percentile_threshold):

    """ 5. Calculating percentile threshold within each zone using zonal statistics. """

    print("\nCalculating percentile threshold within each zone...")

    arcpy.env.snapRaster = zones

    with arcpy.EnvManager(snapRaster=zones):

        percentile_r = arcpy.ia.ZonalStatistics(
            in_zone_data=zones,
            zone_field=zone_field,
            in_value_raster=carbon,
            statistics_type="PERCENTILE",
            ignore_nodata="DATA",
            process_as_multidimensional="CURRENT_SLICE",
            percentile_value=percentile_threshold,
            percentile_interpolation_type="AUTO_DETECT",
            circular_calculation="ARITHMETIC",
            circular_wrap_value=360,
        )

        percentile_r.save(thresholds_raster)


carbon_in_each_forest_cell = intermediate_gdb + os.sep + "carbon_in_each_forest_cell_" + version_label


def calc_carbon_in_each_forest_cell(forest, combined_forest_carbon):

    """ 6. Calculates carbon in each forest cell using zonal statistics (MEAN). """

    arcpy.env.snapRaster = forest

    print("\nCalculating carbon in each forest cell....")

    print(" -> Converting forest pixels to points...")


    forest_points = scratch_gdb + os.sep + "forest_points"
    arcpy.conversion.RasterToPoint(
        in_raster=forest,
        out_point_features=forest_points,
        raster_field="Value"
    )

    print(" -> Converting points to raster...")
    forest_raster = scratch_gdb + os.sep + "forest_raster"

    with arcpy.EnvManager(snapRaster=forest):
        arcpy.conversion.PointToRaster(
            in_features=forest_points,
            value_field="OBJECTID",
            out_rasterdataset=forest_raster,
            cell_assignment="MOST_FREQUENT",
            priority_field="NONE",
            cellsize=forest,
            build_rat="BUILD"
        )

        print(" -> Calculating zonal statistics (carbon in each forest cell)...")
        carbon_in_each_forest_cell_r = arcpy.sa.ZonalStatistics(
            in_zone_data=forest_raster,
            zone_field="Value",
            in_value_raster=combined_forest_carbon,
            statistics_type="MEAN",
            ignore_nodata="DATA",
        )

        carbon_in_each_forest_cell_r.save(carbon_in_each_forest_cell)


def find_carbon_above_threshold(carbon_in_each_forest_cell, thresholds_raster):

    """ 7. Creates High Priority Forest Carbon (Final Output) by selecting carbon pixels above the threshold. """

    print("\nCreating High Priority Forest Carbon....")

    with arcpy.EnvManager(snapRaster=carbon_in_each_forest_cell):

        high_priority_forest_carbon_r = arcpy.sa.Con(Raster(carbon_in_each_forest_cell) > Raster(thresholds_raster), carbon_in_each_forest_cell)
        high_priority_forest_carbon_r.save(final_output)


def filter_output(final_output, combined_forest_carbon, biomes_to_include, ecoregions_and_biomes, ecoregions_of_interest_csv):

    """ Filters the final output to a subset of biomes and ecoregions. Biomes and candidate ecoregions provided by
        Jim Strittholt. Ecoregions to use are selected from the candidate ecoregions. Those with total carbon > MEDIAN
        are kept. Carbon is first projected to an equal area projection at a 1ha resolution so that the original cell
        value units of Mg C/ha become Mg C.
        """

    # Get BIOMES to use (Select biomes specified in the input parameter):
    biomes_to_use_fc = os.path.join(intermediate_gdb, "biomes_to_use_" + version_label)
    query = "BIOME_NAME IN {}".format(biomes_to_include)
    arcpy.Select_analysis(ecoregions_and_biomes, biomes_to_use_fc, query)

    # Get ECOREGIONS to use (Select ecoregions of interest in the CSV that have > MEDIAN combined forest carbon value among ecoregions of interest)

    # Get Ecoregions of Interest from the CSV
    ecoregions_of_interest = []
    with open(ecoregions_of_interest_csv) as f:
        reader = csv.reader(f)
        for row in reader:
            ecoregion = row[0]
            ecoregions_of_interest.append(ecoregion)
        print("Ecoregions of interest from CSV: " + str(ecoregions_of_interest))

    ecoregions_of_interest_tuple = tuple(ecoregions_of_interest)

    # Create an Ecoregions of Interest Feature Class
    query = "ECO_NAME IN {}".format(ecoregions_of_interest_tuple)
    ecoregions_of_interest_fc = os.path.join(intermediate_gdb, "ecoregions_of_interest_" + version_label)
    arcpy.Select_analysis(biomes_and_ecoregions, ecoregions_of_interest_fc, query)

    # Calc ZONAL STATS to get the SUM of the COMBINED FOREST CARBON DENSITY values within each ecoregion
    ecoregions_of_interest_zonal_stats = os.path.join(intermediate_gdb, "ecoregions_of_interest_zonal_stats_" + version_label)
    #arcpy.sa.ZonalStatisticsAsTable(ecoregions_of_interest_fc, "ECO_NAME", final_output, ecoregions_of_interest_zonal_stats, "DATA")
    arcpy.sa.ZonalStatisticsAsTable(ecoregions_of_interest_fc, "ECO_NAME", combined_forest_carbon, ecoregions_of_interest_zonal_stats, "DATA")

    # Calculate the MEDIAN from the Zonal stats table created above (single number).
    median_zonal_carbon_table = os.path.join(intermediate_gdb, "median_zonal_carbon_table_" + version_label)
    arcpy.analysis.Statistics(
        in_table=ecoregions_of_interest_zonal_stats,
        out_table=median_zonal_carbon_table,
        statistics_fields="SUM MEDIAN",
        case_field=None,
        concatenation_separator=""
    )

    # Get the MEDIAN value out of the table (table only has one record).
    with arcpy.da.SearchCursor(median_zonal_carbon_table, "MEDIAN_SUM") as sc:  # field MEDIAN_SUM stores the MEDIAN of the SUMs
        for row in sc:
            median_zonal_carbon = row[0]
        print("Median Zonal Value Threshold: " + str(median_zonal_carbon))

    # Get a list of the ecoregions that are > MEDIAN

    # Create a table view that has the ecoregion names of those > MEDIAN
    query = "SUM > {}".format(median_zonal_carbon)
    median_zonal_carbon_table_view = arcpy.MakeTableView_management(ecoregions_of_interest_zonal_stats)

    ecoregions_of_interest_to_use = arcpy.management.SelectLayerByAttribute(
        in_layer_or_view=median_zonal_carbon_table_view,
        selection_type="NEW_SELECTION",
        where_clause=query,
        invert_where_clause=None
    )

    # Get a list of the ecoregion names where the SUM of the forest carbon is > MEDIAN
    list_of_ecoregions_to_use = []
    with arcpy.da.SearchCursor(ecoregions_of_interest_to_use, "ECO_NAME") as sc:
        for row in sc:
            ecoregion_region_to_use_name = row[0]
            list_of_ecoregions_to_use.append(ecoregion_region_to_use_name)

    # Ecoregions to Use: Select the ecoregions of interest where the SUM of the forest carbon > MEDIAN to create a new feature class
    query = "ECO_NAME in {}".format(tuple(list_of_ecoregions_to_use))
    ecoregions_of_interest_to_use_fc = os.path.join(intermediate_gdb, "ecoregions_of_interest_to_use_" + version_label)
    arcpy.Select_analysis(biomes_and_ecoregions, ecoregions_of_interest_to_use_fc, query)

    # Combine (Union) the Ecoregions to Use with the Biomes to use to create the final mask.
    biome_and_ecoregion_mask = os.path.join(intermediate_gdb, "biome_and_ecoregion_mask_" + version_label)
    arcpy.Union_analysis([biomes_to_use_fc, ecoregions_of_interest_to_use_fc], biome_and_ecoregion_mask)

    # Extract carbon values within the final mask.
    final_output_filtered_l = arcpy.sa.ExtractByMask(final_output, biome_and_ecoregion_mask)
    final_output_filtered_l.save(final_output_filtered)


def calculate_density(final_output_filtered):
    """ (Unused) Test function for calculating point density map from final output. """

    raster_to_point_fc = os.path.join(intermediate_dir, "Scratch/Scratch.gdb/raster_to_point_test")
    arcpy.conversion.RasterToPoint( in_raster=final_output_filtered, out_point_features=raster_to_point_fc, raster_field="Value" )
    d = arcpy.Describe(final_output_filtered)
    cell_size = d.children[0].meanCellHeight * 10

    carbon_density_output = arcpy.sa.PointDensity(
        in_point_features=raster_to_point_fc,
        population_field="grid_code",
        cell_size=cell_size,
        neighborhood="Circle 4.23914982576003 MAP",
        area_unit_scale_factor="SQUARE_MAP_UNITS"
    )

    carbon_density_output_raster = os.path.join(output_dir, "carbon_density_" + version_label + ".tif")
    carbon_density_output.save(carbon_density_output_raster)


if clip_inputs_for_testing:
    above_ground_carbon, below_ground_carbon, forest = clip_for_testing(above_ground_carbon, below_ground_carbon, forest, clipping_features)

#combine_above_and_below_carbon(above_ground_carbon, below_ground_carbon)
#clip_carbon_to_forest_pixels(combined_carbon, forest)
#reclassify_forests(forest)
#create_zones(biomes_and_ecoregions, "ECO_NAME", forest_reclassified)
#calc_percentile_threshold(zones, "Value", combined_carbon, percentile_threshold)
#calc_carbon_in_each_forest_cell(forest, combined_carbon)
#find_carbon_above_threshold(carbon_in_each_forest_cell, thresholds_raster)
filter_output(final_output, carbon_for_ecoregion_selection, biomes_to_include, biomes_and_ecoregions, ecoregions_of_interest_csv)
#calculate_density(final_output_filtered)


end_time = datetime.datetime.now()
duration = end_time - start_time
print("Start Time: " + str(start_time))
print("End Time: " + str(end_time))
print("Duration: " + str(duration))
