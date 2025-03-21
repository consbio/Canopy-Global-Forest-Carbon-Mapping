import arcpy
from arcpy.sa import Raster
import os

clipping_raster = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Intermediate.gdb\ecoregion_subset_extent"

arcpy.env.extent = clipping_raster
arcpy.env.mask = clipping_raster

above_ground_carbon_full_extent = r"\\loxodonta\gis\Source_Data\biota\global\Global_Aboveground_and_Belowground_Biomass_Carbon_Density\2010\Global_Maps_C_Density_2010_1763\data\aboveground_biomass_carbon_2010.tif"
forest_full_extent = r"\\loxodonta\gis\Source_Data\biota\global\Mackey_Global_Forest_Data_FAO_Structural_Forms\FAO_structural_forms\Structural_forms_for_FAO_report.tif"
biomes_and_ecoregions = r"\\loxodonta\gis\Source_Data\boundaries\global\RESOLVE_Biomes_and_Ecoregions\2017\RESOLVE_Feature_Service_Export.gdb\RESOLVE_Biomes_and_Ecoregions_2017"

input_dir = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs"
input_gdb = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs"

intermediate_dir = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate"
intermediate_gdb = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Intermediate.gdb"

output_dir = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Outputs"
output_gdb = "P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Outputs\Outputs.gdb"

scratch_dir = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs\Scratch"
scratch_gdb = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs\Scratch\Scratch.gdb"


arcpy.env.overwriteOutput = True


above_ground_carbon = input_dir + os.sep + "aboveground_biomass_carbon_2010_forest_clip.tif"
forest = input_dir + os.sep + "Structural_forms_for_FAO_report_clip.tif"

arcpy.env.snapRaster = forest_full_extent

def create_clipped_inputs(above_ground_carbon_full_extent, forest_full_extent):
    print("Creating clipped carbon...")
    above_ground_carbon_r = arcpy.sa.ExtractByMask(above_ground_carbon_full_extent, clipping_raster)
    above_ground_carbon_r.save(above_ground_carbon)

    print("Creating clipped forest...")
    arcpy.env.snapRaster = forest_full_extent
    forest_r = arcpy.sa.ExtractByMask(forest_full_extent, clipping_raster)
    forest_r.save(forest)


above_ground_forest_carbon = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Inputs\Carbon\aboveground_biomass_carbon_2010_forest.tif"


def clip_carbon_to_forest(above_ground_carbon, forest):

    print("Creating above ground forest carbon....")

    arcpy.env.cellSize = 0.00277777777777778
    d = arcpy.Describe(above_ground_carbon)
    cell_size = d.children[0].meanCellHeight
    arcpy.env.cellSize = cell_size
    arcpy.env.snapRaster = above_ground_carbon
    above_ground_forest_carbon_r = arcpy.sa.ExtractByMask(above_ground_carbon, forest)
    above_ground_forest_carbon_r.save(above_ground_forest_carbon)


forest_reclassified = r"P:\Projects3\Canopy_Global_Forest_Carbon_Mapping_mike_gough\Tasks\High_Priority_Carbon_Forests_Analysis\Data\Intermediate\Intermediate.gdb\forest_reclassified"


def reclassify_forests(forest):

    print("Reclassifying forest...")

    forest_reclasified_r = arcpy.sa.Reclassify(
        in_raster=forest,
        reclass_field="Value",
        remap="1 1;2 1;3 1;4 2;5 2;6 2;7 3;8 3;9 3;10 4;11 4;12 4",
        missing_values="DATA"
    )
    forest_reclasified_r.save(forest_reclassified)


zones = intermediate_gdb + os.sep + "ecoregions_and_forest_zones"


def create_zones(biomes_and_ecoregions, value_field, forest_reclassified):

    print("Creating zones by combining rasterized ecoregions and reclassified forests")

    arcpy.env.snapRaster = forest_reclassified
    ecoregions_raster = intermediate_gdb + os.sep + "ecoregions_raster"

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

    print(" -> Combining rasterized ecoregions and forests...")

    zones_r = arcpy.sa.Combine([ecoregions_raster, forest_reclassified])

    zones_r.save(zones)


thresholds_raster = intermediate_gdb + os.sep + "carbon_thresholds_50th_percentile"


def calc_percentile_threshold(zones, zone_field, input_value_raster, percentile_threshold):

    print("Calculating percentile threshold within each zone...")

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


carbon_in_each_forest_cell = intermediate_gdb + os.sep + "carbon_in_each_forest_cell"


def calc_carbon_in_each_forest_cell(forest, above_ground_forest_carbon):

    print("Calculating carbon in each forest cell....")

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
        in_value_raster=above_ground_forest_carbon,
        statistics_type="MEAN",
        ignore_nodata="DATA",
    )
    carbon_in_each_forest_cell_r.save(carbon_in_each_forest_cell)


high_priority_forest_carbon = output_gdb + os.sep + "high_priority_forest_carbon_50th_percentile"


def find_carbon_above_threshold(carbon_in_each_forest_cell, thresholds_raster):

    print("Creating High Priority Forest Carbon....")
    arcpy.env.snapRaster = forest
    high_priority_forest_carbon_r = arcpy.sa.Con(Raster(carbon_in_each_forest_cell) > Raster(thresholds_raster), carbon_in_each_forest_cell)
    high_priority_forest_carbon_r.save(high_priority_forest_carbon)

#create_clipped_inputs(above_ground_carbon_full_extent, forest_full_extent)
#clip_carbon_to_forest(above_ground_carbon, forest)
reclassify_forests(forest)
create_zones(biomes_and_ecoregions, "ECO_NAME", forest)
calc_percentile_threshold(zones, "Value", above_ground_forest_carbon, percentile_threshold=50)
calc_carbon_in_each_forest_cell(forest, above_ground_forest_carbon)
find_carbon_above_threshold(carbon_in_each_forest_cell, thresholds_raster)

