"""
01_geometry_objects.py
======================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Create every Shapely geometry type from scratch and inspect its key
    properties: WKT representation, area, length, centroid, and bounds.
    This script serves as a reference card for the Shapely geometry object model.

REAL-WORLD CONTEXT:
    Before running any spatial analysis, you need to know which geometry type
    holds your data and what properties are available:
      - IoT sensor location → Point
      - AGV planned travel path → LineString
      - Agricultural field boundary → Polygon
      - Set of discontiguous field parcels → MultiPolygon
      - Mixed query result from a GIS database → GeometryCollection

    Knowing the API for each type lets you write generic geometry-processing
    functions that handle any type gracefully.

USAGE:
    python 01_geometry_objects.py
"""

from shapely.geometry import (
    Point,
    LineString,
    LinearRing,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
)
from shapely import wkt as shapely_wkt


def print_section(title: str) -> None:
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def describe_geometry(label: str, geom) -> None:
    """
    Print a standardized inspection block for any Shapely geometry.
    Handles cases where area/length are not meaningful for certain types.
    """
    print(f"\n--- {label} ---")
    print(f"  geom_type : {geom.geom_type}")
    print(f"  WKT       : {geom.wkt[:80]}{'...' if len(geom.wkt) > 80 else ''}")
    print(f"  is_valid  : {geom.is_valid}")
    print(f"  is_empty  : {geom.is_empty}")
    print(f"  area      : {geom.area:.6f}   ← 0 for points and lines")
    print(f"  length    : {geom.length:.6f}  ← perimeter for polygons, 0 for points")
    print(f"  bounds    : ({geom.bounds[0]:.3f}, {geom.bounds[1]:.3f}, "
          f"{geom.bounds[2]:.3f}, {geom.bounds[3]:.3f})  ← (minx, miny, maxx, maxy)")
    centroid = geom.centroid
    print(f"  centroid  : ({centroid.x:.4f}, {centroid.y:.4f})")


# ---------------------------------------------------------------------------
# GEOMETRY 1: Point
# ---------------------------------------------------------------------------
print_section("1. Point — Single Coordinate")

# A Point represents a single location in 2D (or 3D) space.
# Arguments: Point(x, y) or Point(x, y, z)
# In geographic contexts: Point(longitude, latitude) for WGS84

# Example: An AGV's current GPS position on a warehouse campus
agv_position = Point(-121.6350, 36.6185)

# Example: A soil moisture sensor at a specific field location
soil_sensor = Point(597420.5, 4055812.3)  # UTM coordinates (meters)

# Example: A 3D point (x, y, z=elevation)
elevation_point = Point(-121.635, 36.618, 42.5)  # 42.5 meters elevation

describe_geometry("AGV GPS Position (WGS84)", agv_position)
describe_geometry("Soil Sensor (UTM meters)", soil_sensor)
describe_geometry("3D Elevation Point", elevation_point)

print("\nPoint-specific attributes:")
print(f"  agv_position.x = {agv_position.x}")
print(f"  agv_position.y = {agv_position.y}")
print(f"  elevation_point.z = {elevation_point.z}")
print(f"  agv_position.has_z = {agv_position.has_z}")
print(f"  elevation_point.has_z = {elevation_point.has_z}")

# ---------------------------------------------------------------------------
# GEOMETRY 2: LineString
# ---------------------------------------------------------------------------
print_section("2. LineString — Ordered Sequence of Points")

# A LineString is a 1D geometry: a sequence of connected line segments.
# It has length but NO area.
# Applications:
#   - AGV travel path (sequence of GPS waypoints)
#   - Crop row centerline (for autonomous tractor guidance)
#   - Irrigation canal centerline

# Example: AGV path through a warehouse aisle (in local metric coordinates)
agv_path = LineString([
    (0.0,   0.0),    # Starting position at entry
    (10.0,  0.0),    # Move 10 m east along aisle
    (10.0, 15.0),    # Turn and move 15 m north
    (20.0, 15.0),    # Continue 10 m east
    (20.0, 30.0),    # Continue 15 m north to destination
])

# Example: Crop row in a field (local field coordinate system)
crop_row_1 = LineString([
    (0.0,  5.0),
    (250.0, 5.0),
])

describe_geometry("AGV Path (warehouse coordinates, meters)", agv_path)
describe_geometry("Crop Row Centerline (field coords, meters)", crop_row_1)

print("\nLineString-specific attributes:")
print(f"  Number of vertices in AGV path: {len(agv_path.coords)}")
print(f"  Coordinate list: {list(agv_path.coords)}")
print(f"  First coordinate: {agv_path.coords[0]}")
print(f"  Last  coordinate: {agv_path.coords[-1]}")
print(f"  Is closed (ring): {agv_path.is_ring}")
print(f"  Is simple (no self-crossings): {agv_path.is_simple}")

# ---------------------------------------------------------------------------
# GEOMETRY 3: LinearRing
# ---------------------------------------------------------------------------
print_section("3. LinearRing — Closed LineString")

# A LinearRing is a LineString where the first and last coordinates are equal.
# It is closed and has an area (in the sense that it encloses a region),
# but LinearRing.area returns 0 — you need to wrap it in a Polygon first.
# LinearRing is mostly used as a building block for Polygon construction.

# Example: The exterior boundary of a rectangular field
field_exterior_ring = LinearRing([
    (0.0,   0.0),
    (300.0, 0.0),
    (300.0, 200.0),
    (0.0,   200.0),
    (0.0,   0.0),    # repeat first point to close the ring
])

describe_geometry("Field Exterior Ring (local coords, meters)", field_exterior_ring)
print(f"\n  LinearRing.is_ring = {field_exterior_ring.is_ring}")
print(f"  LinearRing.area = {field_exterior_ring.area}  ← 0! Wrap in Polygon for area.")

# ---------------------------------------------------------------------------
# GEOMETRY 4: Polygon
# ---------------------------------------------------------------------------
print_section("4. Polygon — Planar Surface (with optional holes)")

# A Polygon is a closed 2D region defined by:
#   - An exterior ring (boundary)
#   - Zero or more interior rings (holes — e.g., a pond inside a field)

# Simple rectangular polygon (no holes) — a warehouse floor plan
warehouse_boundary = Polygon([
    (0.0,   0.0),
    (100.0, 0.0),
    (100.0, 60.0),
    (0.0,   60.0),
    (0.0,   0.0),
])

# Polygon with a hole — a field with a pond in the middle
# Outer ring: the field boundary
outer_ring = [
    (0.0,   0.0),
    (500.0, 0.0),
    (500.0, 400.0),
    (0.0,   400.0),
    (0.0,   0.0),
]
# Inner ring: the pond (not plantable)
pond_hole = [
    (200.0, 150.0),
    (280.0, 150.0),
    (280.0, 220.0),
    (200.0, 220.0),
    (200.0, 150.0),
]
# Shapely Polygon constructor: Polygon(exterior_coords, [list_of_hole_coord_lists])
field_with_pond = Polygon(outer_ring, [pond_hole])

describe_geometry("Warehouse Boundary (100m × 60m)", warehouse_boundary)
describe_geometry("Agricultural Field with Pond Hole", field_with_pond)

print("\nPolygon-specific attributes:")
print(f"  warehouse_boundary.exterior type: {type(warehouse_boundary.exterior).__name__}")
print(f"  field_with_pond.interiors count: {len(list(field_with_pond.interiors))} hole(s)")
pond_area = abs(Polygon(pond_hole).area)
field_area = field_with_pond.area
print(f"  Total field area (minus pond): {field_area:.1f} m²")
print(f"  Pond area (hole): {pond_area:.1f} m²")
print(f"  Solid field area: {field_area + pond_area:.1f} m²  (hole reduces total area)")

# ---------------------------------------------------------------------------
# GEOMETRY 5: MultiPoint
# ---------------------------------------------------------------------------
print_section("5. MultiPoint — Collection of Points")

# A collection of Point objects treated as a single geometry.
# Use case: a set of soil sample locations across a field
soil_samples = MultiPoint([
    (50.0,  50.0),
    (150.0, 50.0),
    (250.0, 50.0),
    (50.0,  150.0),
    (150.0, 150.0),
    (250.0, 150.0),
    (150.0, 250.0),  # center sample
])

describe_geometry("Soil Sample Locations (7 points)", soil_samples)
print(f"\n  Number of points: {len(soil_samples.geoms)}")
print(f"  Individual points: {[f'({p.x:.0f},{p.y:.0f})' for p in soil_samples.geoms]}")

# ---------------------------------------------------------------------------
# GEOMETRY 6: MultiLineString
# ---------------------------------------------------------------------------
print_section("6. MultiLineString — Collection of LineStrings")

# A collection of LineStrings. Useful for:
#   - Multiple crop rows in a field (they don't connect but belong together)
#   - Road network for a farm (multiple road segments)

crop_rows = MultiLineString([
    [(0.0, 10.0), (500.0, 10.0)],   # Row 1
    [(0.0, 15.0), (500.0, 15.0)],   # Row 2 (5 m row spacing)
    [(0.0, 20.0), (500.0, 20.0)],   # Row 3
    [(0.0, 25.0), (500.0, 25.0)],   # Row 4
])

describe_geometry("Crop Rows (4 parallel rows, 500m long)", crop_rows)
print(f"\n  Number of lines: {len(crop_rows.geoms)}")
print(f"  Total row length: {crop_rows.length:.1f} m (sum of all rows)")

# ---------------------------------------------------------------------------
# GEOMETRY 7: MultiPolygon
# ---------------------------------------------------------------------------
print_section("7. MultiPolygon — Collection of Polygons")

# A collection of Polygon objects treated as one geometry.
# Use case: A single farm entity that owns non-contiguous parcels —
# common when a farmer has fields on opposite sides of a road.

parcel_north = Polygon([
    (100.0, 300.0),
    (400.0, 300.0),
    (400.0, 450.0),
    (100.0, 450.0),
    (100.0, 300.0),
])

parcel_south = Polygon([
    (100.0,   0.0),
    (400.0,   0.0),
    (400.0, 200.0),
    (100.0, 200.0),
    (100.0,   0.0),
])

farm_parcels = MultiPolygon([parcel_north, parcel_south])

describe_geometry("Farm Parcels (2 non-contiguous parcels)", farm_parcels)
print(f"\n  Number of polygons: {len(farm_parcels.geoms)}")
print(f"  Total area: {farm_parcels.area:.1f} m² = {farm_parcels.area / 10_000:.3f} ha")

# ---------------------------------------------------------------------------
# GEOMETRY 8: GeometryCollection
# ---------------------------------------------------------------------------
print_section("8. GeometryCollection — Mixed Geometry Types")

# A GeometryCollection holds geometries of different types.
# Often returned by spatial operations when the result type is ambiguous.
# For example: Polygon.difference(another_polygon) might return a mix
# of Polygons and LineStrings if the difference clips an edge perfectly.

mixed_collection = GeometryCollection([
    Point(50.0, 50.0),                     # sensor location
    LineString([(0.0, 25.0), (100.0, 25.0)]),  # access road
    Polygon([(70.0, 70.0), (120.0, 70.0),  # restricted zone
             (120.0, 100.0), (70.0, 100.0), (70.0, 70.0)]),
])

describe_geometry("Mixed GeometryCollection", mixed_collection)
print(f"\n  Number of sub-geometries: {len(mixed_collection.geoms)}")
for i, geom in enumerate(mixed_collection.geoms):
    print(f"  [{i}] {geom.geom_type}: {geom.wkt}")

# ---------------------------------------------------------------------------
# SECTION: WKT Round-Trip
# ---------------------------------------------------------------------------
print_section("WKT / WKB Round-Trip Serialization")

print("WKT (Well-Known Text) is the standard human-readable geometry format.")
print("WKB (Well-Known Binary) is used for efficient database storage.\n")

# Serialize to WKT
wkt_string = warehouse_boundary.wkt
print(f"WKT: {wkt_string}")

# Deserialize from WKT (e.g., when reading from a database column)
reconstructed = shapely_wkt.loads(wkt_string)
print(f"\nReconstructed from WKT: {reconstructed.geom_type}")
print(f"Area matches: {abs(reconstructed.area - warehouse_boundary.area) < 1e-9}")

# WKB bytes (used by PostGIS and SQLite/SpatiaLite)
wkb_bytes = warehouse_boundary.wkb
print(f"\nWKB bytes (first 20 of {len(wkb_bytes)} total): {wkb_bytes[:20].hex()}")
print("WKB is passed directly to database INSERT statements for geometry storage.")

print_section("Script Complete")
print("You now know how to create and inspect all 8 Shapely geometry types.")
print("Next: Run 02_geometric_operations.py to learn spatial algebra.")
