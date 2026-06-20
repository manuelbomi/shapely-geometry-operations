"""
02_geometric_operations.py
===========================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate the core spatial algebra operations in Shapely:
    buffer, union, intersection, difference, symmetric_difference,
    convex_hull, envelope (bounding box), and simplify.
    Each operation includes practical use-case commentary.

REAL-WORLD CONTEXT:
    These operations are the verbs of geospatial data engineering.
    They appear constantly in:
      - Agricultural zone computation (buffer field boundaries inward
        for headland definition)
      - AGV geofencing (buffer a no-go polygon outward to create a slow-down zone)
      - Irrigation district analysis (union of overlapping district polygons)
      - Data cleaning (simplify over-detailed polygon boundaries for web display)
      - Coverage analysis (intersection of two datasets to find overlap area)

USAGE:
    python 02_geometric_operations.py
"""

import math
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, box
from shapely.ops import unary_union
from shapely import affinity


def print_section(title: str) -> None:
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_op_result(operation: str, result, context: str = "") -> None:
    """Print a standardized operation result block."""
    print(f"\n  Operation: {operation}")
    print(f"  Result type: {result.geom_type}")
    print(f"  Area:   {result.area:.4f}")
    print(f"  Length: {result.length:.4f}")
    print(f"  Valid:  {result.is_valid}")
    print(f"  Empty:  {result.is_empty}")
    if context:
        print(f"  Use case: {context}")


# ---------------------------------------------------------------------------
# Setup: Define reference geometries
# ---------------------------------------------------------------------------
# We use meter-scale coordinates to make area/distance values intuitive.
# Imagine these as UTM coordinates on a portion of a farm or warehouse floor.

# Field A: A rectangular field (northwest parcel)
field_a = Polygon([
    (0.0,    0.0),
    (200.0,  0.0),
    (200.0, 150.0),
    (0.0,  150.0),
    (0.0,    0.0),
])

# Field B: Partially overlapping rectangular field (southeast parcel)
field_b = Polygon([
    (100.0,  80.0),
    (300.0,  80.0),
    (300.0, 220.0),
    (100.0, 220.0),
    (100.0,  80.0),
])

# A point cloud (AGV positions or sensor readings)
agv_position = Point(150.0, 100.0)

# A travel path
agv_path = LineString([
    (50.0,  10.0),
    (50.0, 120.0),
    (180.0, 120.0),
    (180.0,  10.0),
])

# A pond polygon (obstacle / no-go zone)
pond = Polygon([
    (120.0, 20.0),
    (170.0, 20.0),
    (170.0, 70.0),
    (120.0, 70.0),
    (120.0, 20.0),
])

print(f"Field A area:  {field_a.area:.0f} m²  ({field_a.area / 10000:.4f} ha)")
print(f"Field B area:  {field_b.area:.0f} m²  ({field_b.area / 10000:.4f} ha)")
print(f"Pond area:     {pond.area:.0f} m²")

# ---------------------------------------------------------------------------
# OPERATION 1: buffer()
# ---------------------------------------------------------------------------
print_section("OPERATION 1: buffer(distance, resolution=16)")

# buffer() expands (positive distance) or contracts (negative distance) a geometry.
# The result is always a Polygon or MultiPolygon.
# `resolution` sets how many line segments approximate a quarter-circle arc.
#   Higher = smoother circles, more vertices, more memory.
#   Typical values: 8 (fast), 16 (default), 32 (smooth)

# --- Buffer a polygon outward (danger zone around a pond) ---
pond_danger_zone = pond.buffer(10.0)   # 10 m buffer around the pond
print_op_result(
    "pond.buffer(10.0)",
    pond_danger_zone,
    "10 m slow-down zone around a pond obstacle — AGV should decelerate here"
)
print(f"  Original pond area:   {pond.area:.1f} m²")
print(f"  Buffered zone area:   {pond_danger_zone.area:.1f} m²")
print(f"  Buffer ring area:     {pond_danger_zone.area - pond.area:.1f} m²")

# --- Buffer inward (negative) — compute plantable area after headland ---
# Agricultural headlands: the region inside a field boundary where machinery
# turns around. The "plantable" zone is the field contracted by headland width.
headland_width = 15.0  # meters (typical for a 12-row planter with margin)
plantable_zone = field_a.buffer(-headland_width)
print_op_result(
    f"field_a.buffer(-{headland_width})",
    plantable_zone,
    f"Plantable area after removing {headland_width} m headland — used in row crop planning"
)
print(f"  Field A area:       {field_a.area:.1f} m²")
print(f"  Plantable area:     {plantable_zone.area:.1f} m²")
print(f"  Headland loss:      {field_a.area - plantable_zone.area:.1f} m²  "
      f"({(field_a.area - plantable_zone.area) / field_a.area * 100:.1f}%)")

# --- Buffer a point → create a circular zone ---
circular_zone = agv_position.buffer(25.0, resolution=32)
print_op_result(
    "agv_position.buffer(25.0, resolution=32)",
    circular_zone,
    "Circular 25 m awareness zone around an AGV position"
)
print(f"  Expected circle area (π r²): {math.pi * 25**2:.2f} m²")
print(f"  Shapely buffer area:         {circular_zone.area:.2f} m²")
print(f"  Approximation error:         {abs(circular_zone.area - math.pi*25**2) / (math.pi*25**2)*100:.3f}%")

# --- Buffer a LineString → create a corridor (AGV path clearance zone) ---
path_corridor = agv_path.buffer(3.0)  # 3 m clearance on each side of path
print_op_result(
    "agv_path.buffer(3.0)",
    path_corridor,
    "6 m wide clearance corridor along AGV travel path — flag obstacles in this zone"
)

# ---------------------------------------------------------------------------
# OPERATION 2: union() and unary_union()
# ---------------------------------------------------------------------------
print_section("OPERATION 2: union() — Merge Geometries")

# union() combines two geometries into one, including all their area.
# The boundary between them is dissolved.
# Use case: Merge adjacent field parcels into a single management unit.

combined_field = field_a.union(field_b)
print_op_result(
    "field_a.union(field_b)",
    combined_field,
    "Merge two adjacent/overlapping parcels into one management unit"
)
print(f"  Field A area:          {field_a.area:.1f} m²")
print(f"  Field B area:          {field_b.area:.1f} m²")
print(f"  Sum of areas:          {field_a.area + field_b.area:.1f} m²")
print(f"  Union area:            {combined_field.area:.1f} m²")
overlap = field_a.area + field_b.area - combined_field.area
print(f"  Overlap (counted once): {overlap:.1f} m²  (union doesn't double-count)")

# unary_union: merge a list of many geometries at once (much more efficient
# than chaining .union() in a loop for large datasets)
many_small_zones = [Point(i * 20, j * 20).buffer(8)
                    for i in range(6) for j in range(4)]
merged_zones = unary_union(many_small_zones)
print(f"\n  unary_union of {len(many_small_zones)} small circle zones:")
print(f"  Result type: {merged_zones.geom_type}")
print(f"  Result area: {merged_zones.area:.1f} m²")

# ---------------------------------------------------------------------------
# OPERATION 3: intersection()
# ---------------------------------------------------------------------------
print_section("OPERATION 3: intersection() — Shared Area")

# intersection() returns the region that is common to BOTH geometries.
# Use case: Find the overlapping area between two field polygons
#   (e.g., to resolve a disputed parcel boundary in a land registry)
# Use case: Find which crop rows fall within a specific irrigation zone

overlap_region = field_a.intersection(field_b)
print_op_result(
    "field_a.intersection(field_b)",
    overlap_region,
    "Shared area between two parcels — resolve overlap in land registry data"
)
print(f"  Overlap area: {overlap_region.area:.1f} m²")
print(f"  Overlap as % of Field A: {overlap_region.area / field_a.area * 100:.1f}%")
print(f"  Overlap as % of Field B: {overlap_region.area / field_b.area * 100:.1f}%")

# Intersection of a path with a zone (returns LineString portion inside zone)
path_in_pond_zone = agv_path.intersection(pond_danger_zone)
print_op_result(
    "agv_path.intersection(pond_danger_zone)",
    path_in_pond_zone,
    "Portion of AGV path that enters the pond danger zone — must be rerouted"
)
print(f"  Total path length:              {agv_path.length:.1f} m")
print(f"  Path in danger zone:            {path_in_pond_zone.length:.1f} m")

# ---------------------------------------------------------------------------
# OPERATION 4: difference()
# ---------------------------------------------------------------------------
print_section("OPERATION 4: difference() — Subtract One from Another")

# difference(other) returns the part of `self` that is NOT in `other`.
# Use case: Remove a no-go zone from a field's plantable area
# Use case: Remove an irrigation canal from a field boundary polygon

field_a_minus_pond = field_a.difference(pond)
print_op_result(
    "field_a.difference(pond)",
    field_a_minus_pond,
    "Field area after subtracting the pond — net plantable area calculation"
)
print(f"  Field A area:     {field_a.area:.1f} m²")
print(f"  Pond area:        {pond.area:.1f} m²")
print(f"  Net field area:   {field_a_minus_pond.area:.1f} m²")
print(f"  Check: {field_a.area:.1f} - {pond.area:.1f} = {field_a.area - pond.area:.1f}  "
      f"({'match' if abs(field_a_minus_pond.area - (field_a.area - pond.area)) < 0.01 else 'mismatch'})")

# Difference with non-overlapping geometry → returns original
no_overlap_zone = Polygon([(500, 500), (600, 500), (600, 600), (500, 600), (500, 500)])
result_no_overlap = field_a.difference(no_overlap_zone)
print(f"\n  field_a.difference(far_away_polygon):")
print(f"  Area unchanged: {result_no_overlap.area:.1f} m²  (no overlap to subtract)")

# ---------------------------------------------------------------------------
# OPERATION 5: symmetric_difference()
# ---------------------------------------------------------------------------
print_section("OPERATION 5: symmetric_difference() — XOR of Areas")

# symmetric_difference() returns the area in EITHER geometry but NOT BOTH.
# It is the set-theoretic XOR: (A ∪ B) - (A ∩ B)
# Use case: Find the "unique" area in each of two overlapping datasets —
#   useful for change detection (new field boundaries vs. old database records)

sym_diff = field_a.symmetric_difference(field_b)
print_op_result(
    "field_a.symmetric_difference(field_b)",
    sym_diff,
    "Area in A or B but not both — identify unique vs shared regions (change detection)"
)
print(f"  = union_area - overlap_area = {combined_field.area:.1f} - {overlap_region.area:.1f} = "
      f"{combined_field.area - overlap_region.area:.1f} m²")
print(f"  sym_diff.area = {sym_diff.area:.1f} m²  ← should match above")

# ---------------------------------------------------------------------------
# OPERATION 6: convex_hull()
# ---------------------------------------------------------------------------
print_section("OPERATION 6: convex_hull — Tightest Convex Envelope")

# convex_hull returns the smallest convex polygon that contains the geometry.
# A polygon is "convex" if the line between any two interior points stays inside.
# Use case: Approximate field boundary from scatter of GPS points (tractors
#   driving through a field log GPS, hull gives rough field shape for planning)

# Create an irregular field polygon (concave — has indentations)
irregular_field = Polygon([
    (0.0,    0.0),
    (200.0,  0.0),
    (200.0,  80.0),
    (130.0,  80.0),   # ← concavity here
    (130.0, 120.0),
    (200.0, 120.0),
    (200.0, 200.0),
    (0.0,   200.0),
    (0.0,     0.0),
])

hull = irregular_field.convex_hull
print_op_result(
    "irregular_field.convex_hull",
    hull,
    "Convex approximation for path planning — simpler shape for bounding box queries"
)
print(f"  Original field area: {irregular_field.area:.1f} m²")
print(f"  Convex hull area:    {hull.area:.1f} m²")
print(f"  Concavity fills:     {hull.area - irregular_field.area:.1f} m²  "
      f"({(hull.area - irregular_field.area)/hull.area*100:.1f}% of hull is void in original)")

# ---------------------------------------------------------------------------
# OPERATION 7: envelope (bounding box)
# ---------------------------------------------------------------------------
print_section("OPERATION 7: envelope — Axis-Aligned Bounding Box")

# envelope returns the smallest axis-aligned rectangle (AABB) containing the geometry.
# This is equivalent to box(minx, miny, maxx, maxy).
# Use case: Quick spatial index query — check bounding box before expensive intersection
# Use case: Clip a raster layer to the spatial extent of a polygon layer

envelope = irregular_field.envelope
print_op_result(
    "irregular_field.envelope",
    envelope,
    "Bounding box for spatial index queries and raster clip operations"
)
print(f"  Bounds (minx, miny, maxx, maxy): {envelope.bounds}")

# The `box()` constructor creates the same thing directly from bounds
from shapely.geometry import box as shapely_box
minx, miny, maxx, maxy = irregular_field.bounds
bbox_direct = shapely_box(minx, miny, maxx, maxy)
print(f"  shapely.geometry.box() equivalent area: {bbox_direct.area:.1f} m²  ← same result")

# ---------------------------------------------------------------------------
# OPERATION 8: simplify()
# ---------------------------------------------------------------------------
print_section("OPERATION 8: simplify(tolerance) — Reduce Vertex Count")

# simplify() reduces the number of vertices in a geometry while preserving
# the overall shape. Uses the Douglas-Peucker algorithm.
# tolerance: maximum deviation allowed from the original shape (in coord units)
# preserve_topology=True ensures no holes or parts are accidentally removed

# Create a complex polygon (many vertices — like a detailed field boundary
# digitized from high-resolution imagery)
import math as _math
# Approximate a circle with many points (simulates a curvy field boundary)
n_vertices = 100
complex_polygon = Polygon([
    (100 + 80 * _math.cos(2 * _math.pi * i / n_vertices),
     100 + 80 * _math.sin(2 * _math.pi * i / n_vertices))
    for i in range(n_vertices)
])

simplified_5m  = complex_polygon.simplify(tolerance=5.0, preserve_topology=True)
simplified_15m = complex_polygon.simplify(tolerance=15.0, preserve_topology=True)

print(f"  Original polygon vertices:   {len(complex_polygon.exterior.coords)}")
print(f"  Simplified (5 m tol) verts:  {len(simplified_5m.exterior.coords)}")
print(f"  Simplified (15 m tol) verts: {len(simplified_15m.exterior.coords)}")
print(f"\n  Original area:               {complex_polygon.area:.2f} m²")
print(f"  Simplified (5m) area:        {simplified_5m.area:.2f} m²  "
      f"(error: {abs(simplified_5m.area - complex_polygon.area)/complex_polygon.area*100:.2f}%)")
print(f"  Simplified (15m) area:       {simplified_15m.area:.2f} m²  "
      f"(error: {abs(simplified_15m.area - complex_polygon.area)/complex_polygon.area*100:.2f}%)")
print()
print("  USE CASE: When serving field boundaries to a web map (Leaflet/Mapbox),")
print("  simplify with 5-10 m tolerance to reduce JSON payload size by 10×+")
print("  without visible degradation at zoom levels < 17.")

print_section("Script Complete")
print("Key operations covered:")
print("  buffer()                — expand/contract geometry by distance")
print("  union()                 — merge two geometries")
print("  unary_union()           — merge a list of many geometries")
print("  intersection()          — shared area/overlap")
print("  difference()            — subtract B from A")
print("  symmetric_difference()  — XOR (unique to each, not shared)")
print("  convex_hull             — smallest convex enclosure")
print("  envelope                — axis-aligned bounding box")
print("  simplify()              — reduce vertex count")
print("\nNext: Run 03_spatial_predicates.py to learn spatial relationship testing.")
