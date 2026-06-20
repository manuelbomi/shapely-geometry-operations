"""
04_affine_transformations.py
=============================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate all four affine transformations available in shapely.affinity:
    translate, rotate, scale, and skew. Show how these operations are used
    in real data engineering workflows, specifically for aligning warehouse
    floor plans to real-world coordinate systems.

REAL-WORLD CONTEXT:
    When commissioning an AGV system in a new warehouse or agricultural facility:

    1. The architect provides a CAD floor plan in "local" coordinates
       (origin at bottom-left of building, units in feet or meters).
    2. A GPS survey gives you 3–4 ground control points (GCPs) — known
       corners measured in UTM or WGS84.
    3. You need to ALIGN the CAD geometry to the GPS coordinate system so
       that your fleet management software can compare AGV GPS positions
       (in UTM) against zone polygons (from CAD).

    The alignment process uses exactly the transforms demonstrated here:
      1. translate  → shift origin from CAD origin to survey origin
      2. rotate     → correct for building orientation (magnetic north vs grid north)
      3. scale      → handle unit conversion (feet → meters) and distortion

    Understanding these transforms also helps when:
      - Visualizing data from multiple sensors in the same coordinate frame
      - Normalizing field polygons from different survey epochs
      - Generating symmetric geofence zones (scale + translate a template)

USAGE:
    python 04_affine_transformations.py
"""

import math
from shapely.geometry import Point, LineString, Polygon
from shapely import affinity


def print_section(title: str) -> None:
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_coords(label: str, geom) -> None:
    """Print geometry coordinates for inspection."""
    if geom.geom_type == 'Point':
        print(f"  {label}: ({geom.x:.4f}, {geom.y:.4f})")
    elif geom.geom_type in ('LineString', 'LinearRing'):
        coords = list(geom.coords)
        print(f"  {label}: {[(round(x,4), round(y,4)) for x,y in coords]}")
    elif geom.geom_type == 'Polygon':
        coords = list(geom.exterior.coords)
        print(f"  {label}: {[(round(x,2), round(y,2)) for x,y in coords]}")


# ---------------------------------------------------------------------------
# Reference geometry: a simplified warehouse floor plan in CAD coordinates
# ---------------------------------------------------------------------------
# Imagine this is a warehouse section in local CAD space:
#   - Origin (0,0) is the southwest corner of the building
#   - Units: meters
#   - Building is 50 m × 30 m
#   - Has a loading dock cutout at the east end

# Main building polygon (with loading dock notch)
cad_building = Polygon([
    (0.0,   0.0),
    (50.0,  0.0),
    (50.0, 10.0),
    (42.0, 10.0),   # ← notch for loading dock
    (42.0, 20.0),
    (50.0, 20.0),
    (50.0, 30.0),
    (0.0,  30.0),
    (0.0,   0.0),
])

# A charging station zone (small square in NW corner)
cad_charging = Polygon([
    (2.0,  22.0),
    (10.0, 22.0),
    (10.0, 28.0),
    (2.0,  28.0),
    (2.0,  22.0),
])

# Reference point (centroid of building)
cad_centroid = cad_building.centroid

print(f"Original CAD building:")
print(f"  centroid:   ({cad_centroid.x:.2f}, {cad_centroid.y:.2f})")
print(f"  area:       {cad_building.area:.1f} m²")
print(f"  bounds:     {cad_building.bounds}")

# ---------------------------------------------------------------------------
# TRANSFORM 1: translate()
# ---------------------------------------------------------------------------
print_section("TRANSFORM 1: translate(xoff, yoff)")

# translate() shifts ALL coordinates by (xoff, yoff).
# The shape, size, and orientation are preserved — only position changes.
#
# USE CASE: The CAD floor plan origin (0,0) needs to map to the GPS survey
# reference point for the SW corner of the building.
# GPS survey gives SW corner: UTM Easting=596800.0 m, Northing=4055200.0 m

survey_sw_easting  = 596800.0   # UTM Zone 10N Easting
survey_sw_northing = 4055200.0  # UTM Zone 10N Northing

# xoff = target_x - source_x = 596800.0 - 0.0
# yoff = target_y - source_y = 4055200.0 - 0.0
building_translated = affinity.translate(
    cad_building,
    xoff=survey_sw_easting,
    yoff=survey_sw_northing,
)

charging_translated = affinity.translate(
    cad_charging,
    xoff=survey_sw_easting,
    yoff=survey_sw_northing,
)

print("Shift CAD geometry to match GPS survey origin:")
print(f"  CAD SW corner:       (0.0, 0.0)")
print(f"  GPS survey SW:       ({survey_sw_easting:.1f}, {survey_sw_northing:.1f})")
print()
new_centroid = building_translated.centroid
print(f"  Original centroid:   ({cad_centroid.x:.2f}, {cad_centroid.y:.2f})")
print(f"  Translated centroid: ({new_centroid.x:.2f}, {new_centroid.y:.2f})")
print(f"  Expected centroid:   ({survey_sw_easting + cad_centroid.x:.2f}, "
      f"{survey_sw_northing + cad_centroid.y:.2f})")
print(f"  Area preserved:      {building_translated.area:.1f} m²  "
      f"(same as {cad_building.area:.1f} m²)")

# Also: translate a single point
agv_local = Point(25.0, 15.0)   # AGV in CAD coordinates
agv_utm = affinity.translate(agv_local, xoff=survey_sw_easting, yoff=survey_sw_northing)
print(f"\n  AGV local position:   ({agv_local.x:.1f}, {agv_local.y:.1f})")
print(f"  AGV in UTM:           ({agv_utm.x:.1f}, {agv_utm.y:.1f})")

# ---------------------------------------------------------------------------
# TRANSFORM 2: rotate()
# ---------------------------------------------------------------------------
print_section("TRANSFORM 2: rotate(angle, origin)")

# rotate() rotates a geometry by `angle` degrees (counter-clockwise positive).
# `origin` can be:
#   - 'centroid'  → rotate around the geometry's centroid (default)
#   - 'center'    → rotate around the bounding box center
#   - Point(x, y) → rotate around a specific point
#   - (x, y)      → tuple form
#
# USE CASE: The warehouse building is rotated 15° clockwise relative to
# true north (the building faces a road at an angle). The GPS survey
# captured corner points in UTM, but the CAD aligns to the building's
# own local X-axis. We need to rotate the CAD geometry to match UTM north.
#
# Note: In GIS, north is typically the +Y axis. A building rotated 15° CW
# relative to north means the CAD X-axis is 15° clockwise from UTM East.
# To align: rotate by -15° (clockwise = negative in math convention).

building_angle_deg = -15.0  # -15° → 15° clockwise rotation

# Rotate around the SW corner (the GPS survey reference point we used in step 1)
# This keeps the origin anchor point fixed while the rest of the building rotates.
rotation_origin = Point(survey_sw_easting, survey_sw_northing)

building_rotated = affinity.rotate(
    building_translated,
    angle=building_angle_deg,
    origin=rotation_origin,
)

charging_rotated = affinity.rotate(
    charging_translated,
    angle=building_angle_deg,
    origin=rotation_origin,
)

print(f"Rotate building by {building_angle_deg}° around SW corner:")
print(f"  Rotation point:   ({rotation_origin.x:.1f}, {rotation_origin.y:.1f})")
print(f"  Angle:            {building_angle_deg}° (negative = clockwise)")
print()
before_c = building_translated.centroid
after_c  = building_rotated.centroid
print(f"  Centroid before:  ({before_c.x:.3f}, {before_c.y:.3f})")
print(f"  Centroid after:   ({after_c.x:.3f}, {after_c.y:.3f})")
print(f"  Area preserved:   {building_rotated.area:.4f} m²  "
      f"(rotation preserves area, change is float precision)")

# Demonstrate rotation around centroid (default)
small_polygon = Polygon([(0,0), (4,0), (4,3), (0,3), (0,0)])
rotated_45 = affinity.rotate(small_polygon, 45, origin='centroid')
print(f"\n  4×3 rectangle rotated 45° around centroid:")
print_coords("  before", small_polygon)
print_coords("  after ", rotated_45)
print(f"  Area preserved: {small_polygon.area:.1f} = {rotated_45.area:.4f}")

# ---------------------------------------------------------------------------
# TRANSFORM 3: scale()
# ---------------------------------------------------------------------------
print_section("TRANSFORM 3: scale(xfact, yfact, origin)")

# scale() multiplies coordinates by xfact and yfact independently.
# `origin` is the anchor point that stays fixed during scaling.
#
# USE CASES:
#   1. UNIT CONVERSION: CAD in feet → convert to meters (1 ft = 0.3048 m)
#   2. SYMMETRIC ZONE TEMPLATE: define a 1×1 m template zone and scale
#      to specific sizes at deployment time
#   3. NON-UNIFORM SCALING: stretch or compress along one axis
#      (less common in geospatial, more common in visualization)

# --- Use case 1: Unit conversion from feet to meters ---
FT_TO_M = 0.3048

# Simulate a CAD floor plan delivered in feet (common in US construction)
building_in_feet = Polygon([
    (0.0,    0.0),
    (164.0,  0.0),   # 164 ft ≈ 50 m
    (164.0,  98.4),  # 98.4 ft ≈ 30 m
    (0.0,    98.4),
    (0.0,    0.0),
])

building_in_meters = affinity.scale(
    building_in_feet,
    xfact=FT_TO_M,
    yfact=FT_TO_M,
    origin=(0.0, 0.0),  # scale from origin so origin stays at (0,0)
)

print(f"Unit conversion — CAD in feet → meters:")
print(f"  Original (feet):    bounds={tuple(round(v,2) for v in building_in_feet.bounds)}")
print(f"  Converted (meters): bounds={tuple(round(v,4) for v in building_in_meters.bounds)}")
print(f"  Original area (ft²): {building_in_feet.area:.1f}")
print(f"  Converted area (m²): {building_in_meters.area:.4f}")
print(f"  Expected area (m²):  {164 * 0.3048 * 98.4 * 0.3048:.4f}")

# --- Use case 2: Template zone scaling ---
# A 1×1 m "unit template" zone that can be scaled to any size
unit_template = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])

# Create a 5m × 8m charging station zone
charging_zone = affinity.scale(unit_template, xfact=5.0, yfact=8.0, origin=(0, 0))
# Move to position in the warehouse
charging_zone = affinity.translate(charging_zone, xoff=2.0, yoff=22.0)

print(f"\nTemplate scaling:")
print(f"  unit_template area:   {unit_template.area:.1f} m²")
print(f"  charging_zone (5×8): {charging_zone.area:.1f} m²")
print_coords("  charging_zone", charging_zone)

# --- Non-uniform scaling (stretch/compress) ---
circle_approx = Point(50, 50).buffer(10, resolution=16)  # circle with r=10
ellipse_approx = affinity.scale(circle_approx, xfact=2.0, yfact=1.0, origin=circle_approx.centroid)
print(f"\nNon-uniform scale (make circle into ellipse):")
print(f"  circle area:      {circle_approx.area:.2f} m²")
print(f"  ellipse area:     {ellipse_approx.area:.2f} m²")
print(f"  Ellipse bounds:   {tuple(round(v, 2) for v in ellipse_approx.bounds)}")
print("  Width doubled (20m), height unchanged (10m)")

# ---------------------------------------------------------------------------
# TRANSFORM 4: skew()
# ---------------------------------------------------------------------------
print_section("TRANSFORM 4: skew(xs, ys, origin)")

# skew() applies a shear transformation: slides one axis relative to the other.
# xs: shear angle in degrees along the X-axis
# ys: shear angle in degrees along the Y-axis
# origin: anchor point (default centroid)
#
# USE CASES:
#   - Correcting map projection shear distortion
#   - Simulating perspective view of a floor plan for a 3D-ish visualization
#   - Less common than the other transforms, but useful for specific corrections

reference_rect = Polygon([(0, 0), (40, 0), (40, 20), (0, 20), (0, 0)])

# Skew by 20° along X (shear the top edge to the right)
skewed_x = affinity.skew(reference_rect, xs=20, ys=0, origin=(0, 0))

# Skew by 15° along Y (shear the right edge upward)
skewed_y = affinity.skew(reference_rect, xs=0, ys=15, origin=(0, 0))

print(f"Reference 40×20 rectangle:")
print_coords("  original", reference_rect)
print()
print(f"Skewed 20° along X:")
print_coords("  skewed_x", skewed_x)
print()
print(f"Skewed 15° along Y:")
print_coords("  skewed_y", skewed_y)
print()
print("  Areas after skew:")
print(f"    original:   {reference_rect.area:.1f} m²")
print(f"    skewed_x:   {skewed_x.area:.1f} m²  ← skew preserves area")
print(f"    skewed_y:   {skewed_y.area:.1f} m²  ← skew preserves area")

# ---------------------------------------------------------------------------
# Full alignment workflow summary
# ---------------------------------------------------------------------------
print_section("FULL WORKFLOW: CAD Floor Plan → UTM Alignment")

print("""
COMPLETE 4-STEP ALIGNMENT WORKFLOW:
====================================

Given:
  - CAD floor plan in feet, origin at building SW corner, aligned to building axis
  - GPS survey: SW corner at UTM (596800.0, 4055200.0), building rotated 15° CW

Step 1: SCALE — convert CAD feet to meters
  aligned = affinity.scale(cad_geom, xfact=0.3048, yfact=0.3048, origin=(0,0))

Step 2: ROTATE — align building axis to UTM north
  aligned = affinity.rotate(aligned, angle=-15.0, origin=(0, 0))
  # -15° because building is 15° clockwise from UTM north

Step 3: TRANSLATE — move from CAD origin to GPS survey reference point
  aligned = affinity.translate(aligned, xoff=596800.0, yoff=4055200.0)

Step 4: VERIFY — check that GPS ground control points match transformed CAD points
  # Compare GCP coordinates to the transformed vertices
  # Accept if error < 0.1 m (depends on survey accuracy requirements)

This workflow is implemented in AGV commissioning tools and is exactly how
warehouse zone maps are generated for fleet management software.

PRODUCTION NOTE:
  For higher accuracy, use a full affine transformation matrix from 3+ GCPs
  (least-squares fit). The affinity.affine_transform() function accepts a
  [a, b, d, e, xoff, yoff] matrix for this purpose:
  aligned = affinity.affine_transform(geom, [a, b, d, e, xoff, yoff])
  where the matrix is solved from GCP pairs using numpy.linalg.lstsq.
""")

# Demonstrate affine_transform() with a known 2D affine matrix
# Identity-equivalent matrix: [1, 0, 0, 1, tx, ty] = translate only
identity_translate = affinity.affine_transform(
    cad_building,
    matrix=[1, 0, 0, 1, 100.0, 50.0]
    # format: [a, b, d, e, xoff, yoff]
    # transforms: x_new = a*x + b*y + xoff
    #             y_new = d*x + e*y + yoff
)
print(f"affine_transform() with translate matrix [1,0,0,1,100,50]:")
print(f"  Original centroid:  ({cad_building.centroid.x:.2f}, {cad_building.centroid.y:.2f})")
print(f"  Transformed:        ({identity_translate.centroid.x:.2f}, {identity_translate.centroid.y:.2f})")
print(f"  Expected:           ({cad_building.centroid.x + 100:.2f}, {cad_building.centroid.y + 50:.2f})")

print_section("Script Complete")
print("All four affine transforms demonstrated:")
print("  affinity.translate(geom, xoff, yoff)         → shift position")
print("  affinity.rotate(geom, angle, origin)         → rotate around point")
print("  affinity.scale(geom, xfact, yfact, origin)   → resize / unit convert")
print("  affinity.skew(geom, xs, ys, origin)          → shear transformation")
print("  affinity.affine_transform(geom, [matrix])    → general 2D affine")
print("\nNext: Run 05_agv_geofencing_example.py for the capstone use case.")
