"""
03_spatial_predicates.py
=========================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Demonstrate the full set of DE-9IM spatial predicates in Shapely:
    contains, within, intersects, touches, crosses, disjoint, overlaps,
    and equals. Use a systematic grid of test polygons plus specific
    geometric configurations that trigger each predicate uniquely.

REAL-WORLD CONTEXT:
    Spatial predicates are the boolean tests used to answer questions like:
      - Is this AGV position WITHIN the operational zone? → .within()
      - Does this planned path CROSS a restricted boundary? → .crosses()
      - Do two field polygons TOUCH at their boundary? → .touches()
      - Are these two sensor locations DISJOINT (no overlap)? → .disjoint()

    Understanding the subtle differences between predicates (especially
    contains vs. within, and intersects vs. overlaps) is essential for
    writing correct spatial queries in both Shapely and SQL/PostGIS.

USAGE:
    python 03_spatial_predicates.py
"""

from shapely.geometry import Point, LineString, Polygon, box


def print_section(title: str) -> None:
    width = 65
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def pred_result(a_name: str, predicate: str, b_name: str, result: bool,
                explanation: str = "") -> None:
    """Print a predicate test result in a consistent, readable format."""
    symbol = "TRUE " if result else "FALSE"
    print(f"  [{symbol}]  {a_name}.{predicate}({b_name})")
    if explanation:
        print(f"           → {explanation}")


# ---------------------------------------------------------------------------
# Define a set of reference geometries for testing
# ---------------------------------------------------------------------------
print_section("Reference Geometry Definitions")

# Zone polygon (like an AGV operational zone)
zone = Polygon([
    (0.0,   0.0),
    (100.0, 0.0),
    (100.0, 100.0),
    (0.0,   100.0),
    (0.0,   0.0),
])

# Sub-zone: entirely inside zone
sub_zone = Polygon([
    (20.0, 20.0),
    (60.0, 20.0),
    (60.0, 60.0),
    (20.0, 60.0),
    (20.0, 20.0),
])

# Adjacent zone: shares one edge with zone (no overlap, just touch)
adjacent_zone = Polygon([
    (100.0,  0.0),
    (180.0,  0.0),
    (180.0, 100.0),
    (100.0, 100.0),
    (100.0,  0.0),
])

# Overlapping zone: partially inside and partially outside
overlapping_zone = Polygon([
    (60.0,  60.0),
    (140.0, 60.0),
    (140.0, 140.0),
    (60.0,  140.0),
    (60.0,   60.0),
])

# Disjoint zone: entirely outside zone, not even touching
far_zone = Polygon([
    (200.0, 200.0),
    (280.0, 200.0),
    (280.0, 260.0),
    (200.0, 260.0),
    (200.0, 200.0),
])

# Points
pt_interior   = Point(50.0, 50.0)      # strictly inside zone
pt_boundary   = Point(100.0, 50.0)     # on the boundary edge of zone
pt_exterior   = Point(150.0, 50.0)     # entirely outside zone
pt_corner     = Point(0.0, 0.0)        # at a corner vertex of zone

# Lines
line_internal    = LineString([(10.0, 10.0), (90.0, 10.0)])   # entirely inside zone
line_crossing    = LineString([(50.0, -10.0), (50.0, 110.0)]) # enters and exits zone
line_on_boundary = LineString([(0.0, 0.0), (0.0, 100.0)])     # lies on zone boundary
line_external    = LineString([(110.0, 50.0), (190.0, 50.0)]) # entirely outside zone

print("  zone:            100×100 square at (0,0)-(100,100)")
print("  sub_zone:        40×40 square INSIDE zone")
print("  adjacent_zone:   80×100 rectangle sharing right edge of zone")
print("  overlapping_zone: 80×80 square partially overlapping zone")
print("  far_zone:        entirely outside zone, no touch")
print("  pt_interior:     Point(50, 50)   — inside zone")
print("  pt_boundary:     Point(100, 50)  — on zone edge")
print("  pt_exterior:     Point(150, 50)  — outside zone")
print("  line_internal:   line inside zone")
print("  line_crossing:   line crossing from outside to outside through zone")
print("  line_on_boundary: line lying exactly on zone boundary")

# ---------------------------------------------------------------------------
# PREDICATE 1: contains / within
# ---------------------------------------------------------------------------
print_section("PREDICATE 1: contains() and within()")

print("""
DEFINITION:
  A.contains(B) → True if ALL of B is inside A AND B's interior touches A's interior
                  A boundary point of B that only touches A's boundary does NOT satisfy
  A.within(B)   → True if ALL of A is inside B  (equivalent to B.contains(A))

IMPORTANT DISTINCTION:
  contains() and within() are INVERSES of each other:
    A.contains(B)  iff  B.within(A)

  BOUNDARY RULE: A point exactly ON the boundary of a polygon:
    polygon.contains(boundary_point) → FALSE  ← boundary point not "inside"
    polygon.covers(boundary_point)   → TRUE   ← .covers() includes the boundary
""")

pred_result("zone", "contains", "sub_zone",
            zone.contains(sub_zone),
            "All of sub_zone is strictly inside zone — TRUE")

pred_result("zone", "contains", "pt_interior",
            zone.contains(pt_interior),
            "Point(50,50) is inside zone — TRUE")

pred_result("zone", "contains", "pt_boundary",
            zone.contains(pt_boundary),
            "Point on boundary: contains() = FALSE (boundary ≠ interior)")

pred_result("zone", "contains", "overlapping_zone",
            zone.contains(overlapping_zone),
            "overlapping_zone extends outside zone — FALSE")

pred_result("zone", "contains", "adjacent_zone",
            zone.contains(adjacent_zone),
            "adjacent_zone only touches, doesn't sit inside — FALSE")

print()
print("  --- within() is the inverse ---")

pred_result("sub_zone", "within", "zone",
            sub_zone.within(zone),
            "sub_zone is entirely inside zone — TRUE (inverse of zone.contains(sub_zone))")

pred_result("pt_interior", "within", "zone",
            pt_interior.within(zone),
            "Point(50,50) is within zone — TRUE")

pred_result("pt_boundary", "within", "zone",
            pt_boundary.within(zone),
            "Boundary point: within() = FALSE (same boundary rule as contains)")

print()
print("  --- covers() includes boundary points ---")
pred_result("zone", "covers", "pt_boundary",
            zone.covers(pt_boundary),
            "covers() = TRUE even for boundary points — use when boundary membership matters")

pred_result("pt_boundary", "covered_by", "zone",
            pt_boundary.covered_by(zone),
            "covered_by() = inverse of covers() — TRUE for boundary points")

# ---------------------------------------------------------------------------
# PREDICATE 2: intersects
# ---------------------------------------------------------------------------
print_section("PREDICATE 2: intersects()")

print("""
DEFINITION:
  A.intersects(B) → True if A and B share ANY point (interior, boundary, or exterior)
                    It is the logical NOT of .disjoint()
                    Almost everything intersects something — this is the broadest predicate.

USE CASE: The first-pass filter in a spatial query:
    "Does this geometry share ANY space with the search region?"
    Because it's O(bounding-box) when combined with an STRtree, it's fast.
""")

pred_result("zone", "intersects", "sub_zone",     zone.intersects(sub_zone),     "contained → intersects")
pred_result("zone", "intersects", "adjacent_zone",zone.intersects(adjacent_zone),"shares an edge → intersects")
pred_result("zone", "intersects", "overlapping_zone", zone.intersects(overlapping_zone), "partial overlap → intersects")
pred_result("zone", "intersects", "far_zone",     zone.intersects(far_zone),     "no shared points → FALSE")
pred_result("zone", "intersects", "pt_interior",  zone.intersects(pt_interior),  "interior point → intersects")
pred_result("zone", "intersects", "pt_boundary",  zone.intersects(pt_boundary),  "boundary point → intersects")
pred_result("zone", "intersects", "line_crossing",zone.intersects(line_crossing), "line crosses zone → intersects")

# ---------------------------------------------------------------------------
# PREDICATE 3: disjoint
# ---------------------------------------------------------------------------
print_section("PREDICATE 3: disjoint()")

print("""
DEFINITION:
  A.disjoint(B) → True if A and B share NO points whatsoever (not even boundary)
                  Logical complement of intersects():
                  A.disjoint(B) == not A.intersects(B)

USE CASE: Verify that two AGV zones have no overlap or shared boundary,
          ensuring no ambiguity in zone assignment.
""")

pred_result("zone", "disjoint", "far_zone",        zone.disjoint(far_zone),        "no shared points → TRUE")
pred_result("zone", "disjoint", "adjacent_zone",   zone.disjoint(adjacent_zone),   "shared boundary → FALSE")
pred_result("zone", "disjoint", "overlapping_zone",zone.disjoint(overlapping_zone),"overlap → FALSE")
pred_result("zone", "disjoint", "sub_zone",        zone.disjoint(sub_zone),        "contained → FALSE")

# ---------------------------------------------------------------------------
# PREDICATE 4: touches
# ---------------------------------------------------------------------------
print_section("PREDICATE 4: touches()")

print("""
DEFINITION:
  A.touches(B) → True if A and B share boundary points BUT NOT interior points.
                 They "meet" at the edge but don't overlap.
                 - Polygon touching polygon: share an edge or a single corner
                 - Point on a polygon boundary: point.touches(polygon) = TRUE

USE CASE: Identify adjacent field parcels that share a fence line.
          In a spatial join of irrigation districts, detect which districts
          are neighbors (share a boundary) vs. truly separate.
""")

pred_result("zone", "touches", "adjacent_zone",
            zone.touches(adjacent_zone),
            "They share the edge at x=100 but interiors don't overlap — TRUE")

pred_result("pt_boundary", "touches", "zone",
            pt_boundary.touches(zone),
            "Point on boundary touches the polygon — TRUE")

pred_result("zone", "touches", "overlapping_zone",
            zone.touches(overlapping_zone),
            "They overlap (shared interior area) — touches = FALSE")

pred_result("zone", "touches", "sub_zone",
            zone.touches(sub_zone),
            "sub_zone is inside zone — no boundary-only contact — FALSE")

pred_result("zone", "touches", "far_zone",
            zone.touches(far_zone),
            "No contact at all — FALSE")

# ---------------------------------------------------------------------------
# PREDICATE 5: crosses
# ---------------------------------------------------------------------------
print_section("PREDICATE 5: crosses()")

print("""
DEFINITION:
  A.crosses(B) → True if A and B share some interior points BUT NOT all interior
                 points of either geometry.
                 Key rules:
                   - Point crosses nothing (zero dimension cannot "cross")
                   - Line crosses polygon: line enters and exits the polygon
                   - Line crosses line: two lines intersect at a single point
                   - Polygon crosses polygon: FALSE — use "overlaps" instead

USE CASE: Detect when an AGV planned path crosses a restricted zone boundary
          (enters and exits the forbidden area — needs rerouting).
          Detect when two field boundaries cross (invalid topology — data error).
""")

pred_result("line_crossing", "crosses", "zone",
            line_crossing.crosses(zone),
            "Line enters zone from south and exits from north — TRUE")

pred_result("line_internal", "crosses", "zone",
            line_internal.crosses(zone),
            "Line is entirely inside zone — crosses = FALSE (not an entry/exit)")

pred_result("line_on_boundary", "crosses", "zone",
            line_on_boundary.crosses(zone),
            "Line lies on boundary only — no interior crossing — FALSE")

# Two crossing lines
line1 = LineString([(0, 50), (100, 50)])    # horizontal
line2 = LineString([(50, 0), (50, 100)])    # vertical — they cross at (50,50)
pred_result("horizontal_line", "crosses", "vertical_line",
            line1.crosses(line2),
            "Lines intersect at one interior point — TRUE")

# ---------------------------------------------------------------------------
# PREDICATE 6: overlaps
# ---------------------------------------------------------------------------
print_section("PREDICATE 6: overlaps()")

print("""
DEFINITION:
  A.overlaps(B) → True if A and B have the SAME dimension, share some interior
                  points, but neither contains the other.
                  For two polygons: they partially overlap (like a Venn diagram).
                  For two lines: they share a collinear segment.

  DIFFERENT from intersects: overlaps requires same geometry dimension
  and that neither completely contains the other.

USE CASE: Identify when two field datasets partially overlap — used in
          conflicting land-use record detection for agricultural data audits.
""")

pred_result("zone", "overlaps", "overlapping_zone",
            zone.overlaps(overlapping_zone),
            "Two polygons partially overlap — TRUE")

pred_result("zone", "overlaps", "sub_zone",
            zone.overlaps(sub_zone),
            "zone contains sub_zone entirely — overlaps = FALSE (containment ≠ overlap)")

pred_result("zone", "overlaps", "adjacent_zone",
            zone.overlaps(adjacent_zone),
            "They only share a boundary, not interior — FALSE")

pred_result("zone", "overlaps", "far_zone",
            zone.overlaps(far_zone),
            "No contact — FALSE")

# ---------------------------------------------------------------------------
# PREDICATE 7: equals / equals_exact
# ---------------------------------------------------------------------------
print_section("PREDICATE 7: equals() and equals_exact()")

print("""
DEFINITION:
  A.equals(B)              → True if A and B are topologically equivalent
                             (same region, even if vertex order differs)
  A.equals_exact(B, tol)   → True if coordinates match within tolerance `tol`
                             (stricter — checks vertex-level equality)
""")

zone_copy = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
zone_different_start = Polygon([(50, 0), (100, 0), (100, 100), (0, 100), (0, 0), (50, 0)])

pred_result("zone", "equals", "zone_copy",
            zone.equals(zone_copy),
            "Identical geometry — TRUE")

pred_result("zone", "equals", "sub_zone",
            zone.equals(sub_zone),
            "Different geometries — FALSE")

print(f"\n  zone.equals_exact(zone_copy, tolerance=0.001): "
      f"{zone.equals_exact(zone_copy, tolerance=0.001)}")
print(f"  zone.equals_exact(zone, tolerance=0.001): "
      f"{zone.equals_exact(zone, tolerance=0.001)}")

# ---------------------------------------------------------------------------
# Summary matrix
# ---------------------------------------------------------------------------
print_section("SUMMARY: Predicate Results Matrix")

test_pairs = [
    ("sub_zone",        sub_zone),
    ("adjacent_zone",   adjacent_zone),
    ("overlapping_zone",overlapping_zone),
    ("far_zone",        far_zone),
]

predicates = ["contains", "intersects", "disjoint", "touches", "overlaps"]

header = f"{'Geometry':<20} " + " ".join(f"{p[:10]:^11}" for p in predicates)
print(f"\n  zone.PREDICATE(other):")
print(f"  {header}")
print(f"  {'-' * (20 + 12 * len(predicates))}")

for name, geom in test_pairs:
    results = [
        zone.contains(geom),
        zone.intersects(geom),
        zone.disjoint(geom),
        zone.touches(geom),
        zone.overlaps(geom),
    ]
    row = f"  {name:<20} " + " ".join(f"{'T' if r else 'F':^11}" for r in results)
    print(row)

print()
print("  T = True, F = False")

print_section("Script Complete")
print("Next: Run 04_affine_transformations.py to learn geometry alignment.")
