import arcpy
from arcpy.sa import Raster
import os

clip_inputs_for_testing = True
clipping_features = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Intermediate.gdb\ecoregion_subset_extent"

above_ground_carbon = r"\\loxodonta\gis\Source_Data\biota\global\Global_Aboveground_and_Belowground_Biomass_Carbon_Density\2010\Global_Maps_C_Density_2010_1763\data\aboveground_biomass_carbon_2010.tif"
below_ground_carbon = r"\\loxodonta\gis\Source_Data\biota\global\Global_Aboveground_and_Belowground_Biomass_Carbon_Density\2010\Global_Maps_C_Density_2010_1763\data\belowground_biomass_carbon_2010.tif"

forest = r"\\loxodonta\gis\Source_Data\biota\global\Mackey_Global_Forest_Data_FAO_Structural_Forms\FAO_structural_forms\Structural_forms_for_FAO_report.tif"
biomes_and_ecoregions = r"\\loxodonta\gis\Source_Data\boundaries\global\RESOLVE_Biomes_and_Ecoregions\2017\RESOLVE_Feature_Service_Export.gdb\RESOLVE_Biomes_and_Ecoregions_2017"

input_dir = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs"
input_gdb = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs"

intermediate_dir = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate"
intermediate_gdb = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Intermediate.gdb"

output_dir = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Outputs"
output_gdb = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Outputs\Outputs.gdb"

scratch_dir = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs\Scratch"
scratch_gdb = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs\Scratch\Scratch.gdb"

# Final Output:
version_label = "50th_percentile"

if clip_inputs_for_testing:
    version_label += "_subset"

high_priority_forest_carbon_output = output_gdb + os.sep + "high_priority_forest_carbon_" + version_label

arcpy.env.overwriteOutput = True
arcpy.env.snapRaster = forest


def create_clipped_inputs(above_ground_carbon, below_ground_carbon, forest, clipping_features):

    """ Clips the carbon and the forest pixels to a subset of ecoregions for testing on a smaller extent. """

    print("\nClipping data testing for testing...")

    arcpy.env.extent = clipping_features
    arcpy.env.mask = clipping_features

    above_ground_carbon_clip = input_dir + os.sep + "aboveground_biomass_carbon_2010_forest_clip_" + version_label + ".tif"
    below_ground_carbon_clip = input_dir + os.sep + "belowground_biomass_carbon_2010_forest_clip_" + version_label + ".tif"
    forest_clip = input_dir + os.sep + "Structural_forms_for_FAO_report_clip_" + version_label + ".tif"

    print(" -> Creating clipped aboveground carbon...")
    above_ground_carbon_r = arcpy.sa.ExtractByMask(above_ground_carbon, clipping_features)
    above_ground_carbon_r.save(above_ground_carbon_clip)

    print(" -> Creating clipped belowground carbon...")
    below_ground_carbon_r = arcpy.sa.ExtractByMask(below_ground_carbon, clipping_features)
    below_ground_carbon_r.save(below_ground_carbon_clip)

    print(" -> Creating clipped forest...")
    arcpy.env.snapRaster = forest
    forest_r = arcpy.sa.ExtractByMask(forest, clipping_features)
    forest_r.save(forest_clip)

    return above_ground_carbon_clip, below_ground_carbon_clip, forest_clip


combined_carbon = intermediate_dir + os.sep + "combined_carbon_" + version_label + ".tif"


def combine_above_and_below_carbon(above_ground_carbon, below_ground_carbon):

    """ Combines above and below ground carbon """

    print("\nCombining aboveground and belowground carbon...")

    combined_carbon_r = arcpy.sa.Plus(above_ground_carbon, below_ground_carbon)
    combined_carbon_r.save(combined_carbon)


combined_forest_carbon = input_dir + os.path.sep + "combined_forest_carbon_" + version_label + ".tif"


def clip_carbon_to_forest_pixels(carbon, forest):

    print("\nClipping carbon to forest pixels....")

    arcpy.env.cellSize = 0.00277777777777778
    d = arcpy.Describe(carbon)
    cell_size = d.children[0].meanCellHeight
    arcpy.env.cellSize = cell_size
    arcpy.env.snapRaster = carbon
    forest_carbon_r = arcpy.sa.ExtractByMask(carbon, forest)
    forest_carbon_r.save(combined_forest_carbon)


forest_reclassified = intermediate_gdb + os.path.sep + "forest_reclassified_" + version_label


def reclassify_forests(forest):

    print("\nReclassifying forest...")

    forest_reclasified_r = arcpy.sa.Reclassify(
        in_raster=forest,
        reclass_field="Value",
        remap="1 1;2 1;3 1;4 2;5 2;6 2;7 3;8 3;9 3;10 4;11 4;12 4",
        missing_values="DATA"
    )
    forest_reclasified_r.save(forest_reclassified)


zones = intermediate_gdb + os.sep + "ecoregions_and_forest_zones_" + version_label


def create_zones(biomes_and_ecoregions, value_field, forest_reclassified):

    print("\nCreating zones by combining rasterized ecoregions and reclassified forests...")

    arcpy.env.snapRaster = forest_reclassified
    ecoregions_raster = intermediate_gdb + os.sep + "ecoregions_raster_" + version_label

    if not arcpy.Exists(ecoregions_raster):

        print(" -> Converting ecoregions to raster...")

        arcpy.conversion.PolygonToRaster(
            in_features=biomes_and_ecoregions,
            value_field=value_field,
            out_rasterdataset=ecoregions_raster,
            cell_assignment="CELL_CENTER",
            priority_field="NONE",
            cellsize=0.008983152841195217,
            build_rat="BUILD"
        )

    print(" -> Combining rasterized ecoregions and reclassified forests...")

    zones_r = arcpy.sa.Combine([ecoregions_raster, forest_reclassified])
    zones_r.save(zones)


thresholds_raster = intermediate_gdb + os.sep + "combined_carbon_thresholds_" + version_label


def calc_percentile_threshold(zones, zone_field, input_value_raster, percentile_threshold):

    print("\nCalculating percentile threshold within each zone...")

    arcpy.env.snapRaster = zones

    percentile_r = arcpy.ia.ZonalStatistics(
        in_zone_data=zones,
        zone_field=zone_field,
        in_value_raster=input_value_raster,
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

    print("\nCalculating carbon in each forest cell....")

    arcpy.env.snapRaster = forest

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

    print("\nCreating High Priority Forest Carbon....")
    arcpy.env.snapRaster = forest
    high_priority_forest_carbon_r = arcpy.sa.Con(Raster(carbon_in_each_forest_cell) > Raster(thresholds_raster), carbon_in_each_forest_cell)
    high_priority_forest_carbon_r.save(high_priority_forest_carbon_output)


if clip_inputs_for_testing:
    above_ground_carbon, below_ground_carbon, forest = create_clipped_inputs(above_ground_carbon, below_ground_carbon, forest, clipping_features)

combine_above_and_below_carbon(above_ground_carbon, below_ground_carbon)
clip_carbon_to_forest_pixels(combined_carbon, forest)
reclassify_forests(forest)
create_zones(biomes_and_ecoregions, "ECO_NAME", forest_reclassified)
calc_percentile_threshold(zones, "Value", combined_carbon, percentile_threshold=50)
calc_carbon_in_each_forest_cell(forest, combined_carbon)
find_carbon_above_threshold(carbon_in_each_forest_cell, thresholds_raster)

