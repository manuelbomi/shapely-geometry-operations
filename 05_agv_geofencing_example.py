"""
05_agv_geofencing_example.py
=============================
Author: Emmanuel Oyekanlu — Principal Data Engineer

PURPOSE:
    Implement a realistic AGV (Autonomous Ground Vehicle) geofencing system
    for a warehouse floor plan. Define a hierarchical zone structure, simulate
    AGV positions arriving in real-time, and determine zone membership and
    speed constraints for each position update.

REAL-WORLD CONTEXT:
    Modern warehouse AGV systems (e.g., Locus Robotics, 6 River Systems,
    Geek+, and custom-built systems using ROS/Nav2) require:

    1. ZONE DEFINITION: Define spatial zones from warehouse floor plan data
       (CAD drawings or facility management software exports).
       Each zone has properties: allowed speed, priority, access rules.

    2. POSITION CLASSIFICATION: For each incoming GPS/UWB position fix
       (arriving 1-10 Hz per AGV), determine:
         - Is the AGV inside the operational boundary?
         - Which specific zone is it in?
         - What is the speed limit for this zone?
         - Are there any safety warnings (near a no-go zone boundary)?

    3. INCIDENT DETECTION: If an AGV enters a no-go zone, raise an alert
       with the zone name, position, and timestamp.

    4. COMPLIANCE REPORTING: End-of-shift summary of zone visit counts,
       time spent per zone, and any violations.

    This script implements all four using pure Shapely — the same logic
    that runs inside production AGV fleet management services.

ZONE STRUCTURE (Hypothetical 80m × 50m warehouse):
    ┌────────────────────────────────────────────────────────────────────────┐
    │  WAREHOUSE BOUNDARY (80m × 50m)                                       │
    │  ┌──────┐                          ┌─────────────────┐                │
    │  │CHARGE│                          │   LOADING DOCK  │                │
    │  │ ZONE │                          │    (NO-GO)      │                │
    │  └──────┘                          └─────────────────┘                │
    │                                                                        │
    │                    [GENERAL OPERATIONAL ZONE]                          │
    │                                                                        │
    │  ┌──────────────────────────┐     ┌──────────────────┐               │
    │  │    SLOW ZONE             │     │  PEDESTRIAN      │               │
    │  │  (near pick station)     │     │  CROSSING (SLOW) │               │
    │  └──────────────────────────┘     └──────────────────┘               │
    └────────────────────────────────────────────────────────────────────────┘

USAGE:
    python 05_agv_geofencing_example.py
"""

import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from shapely.geometry import Point, Polygon, LineString
from shapely.strtree import STRtree


# ---------------------------------------------------------------------------
# Data classes: Zone and AGVPosition
# ---------------------------------------------------------------------------

@dataclass
class Zone:
    """
    Represents a named spatial zone in the warehouse.

    Attributes:
        name:           Human-readable zone name (e.g., "Charging Station A")
        zone_type:      Functional type: 'operational', 'slow', 'no_go', 'charging', 'loading'
        polygon:        Shapely Polygon defining the zone boundary
        speed_limit_ms: Maximum AGV speed in this zone (m/s). None = inherit from parent.
        priority:       Higher priority zones take precedence when zones overlap.
                        Zone with highest priority wins in zone assignment.
        description:    Plain-text description for reports and APIs.
    """
    name:           str
    zone_type:      str
    polygon:        Polygon
    speed_limit_ms: Optional[float]   # None = inherit from outer zone
    priority:       int
    description:    str = ""

    @property
    def area_m2(self) -> float:
        return self.polygon.area

    def contains_point(self, pt: Point) -> bool:
        """
        Check if a point is inside this zone.
        Uses .covers() instead of .contains() to include boundary points.
        This ensures an AGV exactly on a zone boundary is classified correctly.
        """
        return self.polygon.covers(pt)

    def distance_to_boundary(self, pt: Point) -> float:
        """
        Return the distance from a point to the zone's boundary (exterior ring).
        Positive = outside zone; 0 = on boundary; negative not possible here.
        Used to generate proximity warnings: "AGV is 2.3 m from no-go zone."
        """
        return pt.distance(self.polygon.exterior)


@dataclass
class AGVPositionFix:
    """
    A single position update from an AGV.

    Attributes:
        agv_id:      Unique vehicle identifier
        x, y:        Local coordinate position (meters, warehouse coordinate frame)
        speed_ms:    Current travel speed in m/s
        heading_deg: Travel direction in degrees (0=north, 90=east, 180=south)
        timestamp:   Epoch seconds (simplified; production would use datetime)
        sequence:    Sequential fix number for this AGV session
    """
    agv_id:      str
    x:           float
    y:           float
    speed_ms:    float
    heading_deg: float
    timestamp:   float
    sequence:    int

    @property
    def point(self) -> Point:
        """Return the position as a Shapely Point."""
        return Point(self.x, self.y)

    def __str__(self) -> str:
        return (f"AGV {self.agv_id} | seq={self.sequence:03d} | "
                f"pos=({self.x:.1f}, {self.y:.1f}) | "
                f"speed={self.speed_ms:.2f} m/s | "
                f"heading={self.heading_deg:.0f}°")


@dataclass
class ZoneStatusReport:
    """Result of a zone check for a single position fix."""
    fix:               AGVPositionFix
    in_operational:    bool
    current_zone:      Optional[Zone]     # highest-priority zone the AGV is in
    all_zones:         List[Zone]         # all zones containing this position
    speed_limit_ms:    float              # effective speed limit at this position
    speed_violation:   bool              # True if current speed > zone limit
    warnings:          List[str]          # proximity and compliance warnings
    violations:        List[str]          # hard violations (no-go zone entry, etc.)


# ---------------------------------------------------------------------------
# WarehouseGeofenceManager
# ---------------------------------------------------------------------------

class WarehouseGeofenceManager:
    """
    Manages zone definitions and classifies AGV position fixes.

    This class mimics a production service that would:
      - Load zone geometries from a PostGIS database or GeoJSON config file
      - Accept streaming position fixes via Kafka or MQTT
      - Emit zone-enriched events to a downstream monitoring system

    In production, this would be a long-running async service. Here we
    demonstrate the pure spatial logic in a synchronous, testable form.
    """

    # Default speed limit: general operational zone (m/s)
    DEFAULT_SPEED_MS = 1.5    # ~5.4 km/h — typical max for pedestrian-safe AGV

    def __init__(self):
        self.zones: List[Zone] = []
        self._strtree: Optional[STRtree] = None
        self._strtree_built = False

    def add_zone(self, zone: Zone) -> None:
        """Register a zone. Invalidates the spatial index (rebuilt on next query)."""
        self.zones.append(zone)
        self._strtree_built = False

    def _build_strtree(self) -> None:
        """
        Build an STR-tree spatial index over zone polygons.

        An STRtree (Sort-Tile-Recursive tree) is a spatial index structure
        that allows O(log n) query instead of O(n) linear scan. For large
        warehouses with dozens of zones and thousands of AGV fixes per second,
        this index is critical for throughput.

        In production with GeoPandas, you'd use gdf.sindex (GeoDataFrame's
        built-in spatial index) instead of constructing STRtree manually.
        """
        polygons = [z.polygon for z in self.zones]
        self._strtree = STRtree(polygons)
        self._strtree_built = True

    def classify_position(self, fix: AGVPositionFix) -> ZoneStatusReport:
        """
        Classify a position fix against all defined zones.

        Returns a ZoneStatusReport with:
          - Which zone(s) contain this position
          - Effective speed limit
          - Any speed violations or proximity warnings

        ALGORITHM:
          1. Quick bounding-box query via STRtree → candidate zones
          2. Exact geometry test on candidates → confirmed zones
          3. Sort by priority → highest priority = "current zone"
          4. Apply speed rules and generate warnings/violations
        """
        if not self._strtree_built:
            self._build_strtree()

        pt = fix.point
        warnings = []
        violations = []

        # Step 1: STRtree candidate query (fast bounding-box filter)
        candidate_indices = self._strtree.query(pt, predicate='intersects')

        # Step 2: Exact containment test on candidates
        containing_zones = []
        for idx in candidate_indices:
            zone = self.zones[idx]
            if zone.contains_point(pt):
                containing_zones.append(zone)

        # Step 3: Check outer boundary
        # The warehouse boundary is the first zone added (type='boundary')
        boundary_zone = next((z for z in self.zones if z.zone_type == 'boundary'), None)
        in_operational = boundary_zone.contains_point(pt) if boundary_zone else False

        if not in_operational:
            violations.append(
                f"OUTSIDE BOUNDARY: AGV {fix.agv_id} is outside the warehouse boundary "
                f"at ({fix.x:.1f}, {fix.y:.1f})"
            )

        # Step 4: Check for no-go zone violations
        no_go_zones_hit = [z for z in containing_zones if z.zone_type == 'no_go']
        for ngz in no_go_zones_hit:
            violations.append(
                f"NO-GO VIOLATION: AGV {fix.agv_id} entered '{ngz.name}' "
                f"at ({fix.x:.1f}, {fix.y:.1f})"
            )

        # Step 5: Determine effective speed limit
        # Priority order: no_go (0 m/s) > slow zones > charging > default
        if no_go_zones_hit:
            effective_speed_limit = 0.0   # must stop
        else:
            # Among containing zones, find the most restrictive speed limit
            speed_limits = [
                z.speed_limit_ms for z in containing_zones
                if z.speed_limit_ms is not None and z.zone_type != 'boundary'
            ]
            if speed_limits:
                effective_speed_limit = min(speed_limits)
            else:
                effective_speed_limit = self.DEFAULT_SPEED_MS

        # Step 6: Speed violation check
        speed_violation = fix.speed_ms > effective_speed_limit + 0.05  # 0.05 m/s tolerance
        if speed_violation:
            warnings.append(
                f"SPEED VIOLATION: {fix.speed_ms:.2f} m/s exceeds limit "
                f"{effective_speed_limit:.2f} m/s in zone "
                f"'{containing_zones[-1].name if containing_zones else 'default'}'"
            )

        # Step 7: Proximity warnings — check if AGV is near any no-go zone
        for zone in self.zones:
            if zone.zone_type == 'no_go' and not zone.contains_point(pt):
                dist = pt.distance(zone.polygon)
                if dist < 3.0:  # within 3 meters of a no-go boundary
                    warnings.append(
                        f"PROXIMITY WARNING: AGV is {dist:.2f} m from no-go zone "
                        f"'{zone.name}' — slow down and verify heading"
                    )

        # Step 8: Sort containing zones by priority (highest first)
        containing_zones.sort(key=lambda z: z.priority, reverse=True)
        current_zone = containing_zones[0] if containing_zones else None

        return ZoneStatusReport(
            fix=fix,
            in_operational=in_operational,
            current_zone=current_zone,
            all_zones=containing_zones,
            speed_limit_ms=effective_speed_limit,
            speed_violation=speed_violation,
            warnings=warnings,
            violations=violations,
        )

    def generate_shift_report(self, reports: List[ZoneStatusReport]) -> None:
        """Generate a summary compliance report for a shift's worth of fixes."""
        print("\n" + "=" * 70)
        print("  SHIFT COMPLIANCE REPORT")
        print("=" * 70)

        total_fixes = len(reports)
        violations_all = [r for r in reports if r.violations]
        speed_violations = [r for r in reports if r.speed_violation]
        outside_boundary = [r for r in reports if not r.in_operational]

        print(f"  Total position fixes processed: {total_fixes}")
        print(f"  Fixes with zone violations:     {len(violations_all)}")
        print(f"  Fixes with speed violations:    {len(speed_violations)}")
        print(f"  Fixes outside boundary:         {len(outside_boundary)}")

        # Zone visit count
        zone_counts: Dict[str, int] = {}
        for r in reports:
            zone_name = r.current_zone.name if r.current_zone else "Unknown"
            zone_counts[zone_name] = zone_counts.get(zone_name, 0) + 1

        print(f"\n  Zone visit distribution:")
        for zone_name, count in sorted(zone_counts.items(), key=lambda x: -x[1]):
            pct = count / total_fixes * 100
            bar = "#" * int(pct / 2)
            print(f"    {zone_name:<30} {count:>4} fixes  ({pct:5.1f}%)  {bar}")

        # Print violations
        if violations_all:
            print(f"\n  VIOLATIONS LOG ({len(violations_all)} events):")
            for r in violations_all[:10]:  # show first 10
                print(f"    Seq {r.fix.sequence:03d} | {r.fix}")
                for v in r.violations:
                    print(f"      !! {v}")


# ---------------------------------------------------------------------------
# Warehouse Setup
# ---------------------------------------------------------------------------
def print_section(title: str) -> None:
    width = 70
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


print_section("STEP 1: Define Warehouse Zones")

manager = WarehouseGeofenceManager()

# --- Main warehouse boundary (80m × 50m) ---
warehouse_boundary = Zone(
    name="Warehouse Boundary",
    zone_type="boundary",
    polygon=Polygon([
        (0.0,  0.0),
        (80.0, 0.0),
        (80.0, 50.0),
        (0.0,  50.0),
        (0.0,   0.0),
    ]),
    speed_limit_ms=None,  # no speed limit on the boundary zone itself
    priority=0,
    description="Outer boundary of the warehouse. AGV outside this = OOB error.",
)
manager.add_zone(warehouse_boundary)

# --- Charging station zone (SW corner, 8m × 6m) ---
charging_station = Zone(
    name="Charging Station A",
    zone_type="charging",
    polygon=Polygon([
        (1.0,  1.0),
        (9.0,  1.0),
        (9.0,  7.0),
        (1.0,  7.0),
        (1.0,  1.0),
    ]),
    speed_limit_ms=0.3,   # 0.3 m/s = very slow (docking approach speed)
    priority=10,
    description="Battery charging docks. AGV must approach at docking speed.",
)
manager.add_zone(charging_station)

# --- Loading dock (NE corner — no-go for standard AGVs) ---
loading_dock_nogo = Zone(
    name="Loading Dock (No-Go)",
    zone_type="no_go",
    polygon=Polygon([
        (58.0, 35.0),
        (79.0, 35.0),
        (79.0, 49.0),
        (58.0, 49.0),
        (58.0, 35.0),
    ]),
    speed_limit_ms=0.0,   # Zero speed — must not enter
    priority=20,
    description="Active truck loading area. Standard AGVs prohibited. Human workers only.",
)
manager.add_zone(loading_dock_nogo)

# --- Pick station slow zone (central south area) ---
pick_station_slow = Zone(
    name="Pick Station Slow Zone",
    zone_type="slow",
    polygon=Polygon([
        (10.0,  2.0),
        (45.0,  2.0),
        (45.0, 18.0),
        (10.0, 18.0),
        (10.0,  2.0),
    ]),
    speed_limit_ms=0.8,   # 0.8 m/s ≈ 2.9 km/h (pedestrian walking pace)
    priority=5,
    description="High-traffic pick station area. Reduced speed for worker safety.",
)
manager.add_zone(pick_station_slow)

# --- Pedestrian crossing (central, near aisle 3) ---
pedestrian_crossing = Zone(
    name="Pedestrian Crossing Aisle 3",
    zone_type="slow",
    polygon=Polygon([
        (38.0, 20.0),
        (46.0, 20.0),
        (46.0, 34.0),
        (38.0, 34.0),
        (38.0, 20.0),
    ]),
    speed_limit_ms=0.5,   # 0.5 m/s when pedestrians may be present
    priority=8,
    description="Pedestrian crossing zone. AGV must yield to workers.",
)
manager.add_zone(pedestrian_crossing)

# --- General operational zone (main aisle area) ---
# This zone fills the "rest" of the warehouse. Lower priority so specific
# zones (slow, charging, no-go) override it when an AGV is inside them.
main_operational = Zone(
    name="Main Operational Zone",
    zone_type="operational",
    polygon=Polygon([
        (0.0,  0.0),
        (80.0, 0.0),
        (80.0, 50.0),
        (0.0,  50.0),
        (0.0,   0.0),
    ]),
    speed_limit_ms=WarehouseGeofenceManager.DEFAULT_SPEED_MS,
    priority=1,
    description="General AGV travel zone. Standard operating speed.",
)
manager.add_zone(main_operational)

print(f"Registered {len(manager.zones)} zones:")
for z in manager.zones:
    print(f"  [{z.zone_type:>12}] {z.name:<35} area={z.area_m2:.1f} m²  "
          f"speed={str(z.speed_limit_ms):>5} m/s  priority={z.priority}")

# ---------------------------------------------------------------------------
# Simulate AGV position fixes
# ---------------------------------------------------------------------------
print_section("STEP 2: Simulate AGV Position Fixes")

# Simulate AGV-001 doing a route: start near charging, travel through pick area,
# cross a pedestrian zone, approach the no-go area boundary, exit boundary (bug).
# Each tuple: (x, y, speed_ms, heading_deg, description)
agv_route = [
    # (  x,    y, speed,  heading, note)
    ( 5.0,  4.0,  0.25,    90.0, "Departing charging station"),
    (12.0,  4.0,  0.80,    90.0, "In pick station slow zone"),
    (25.0,  8.0,  0.80,    90.0, "Still in pick station area"),
    (40.0, 12.0,  0.80,    90.0, "Exiting pick zone, entering operational"),
    (42.0, 25.0,  1.20,     0.0, "Traveling north in operational zone"),
    (42.0, 27.0,  1.20,     0.0, "Approaching pedestrian crossing"),
    (42.0, 28.0,  0.50,     0.0, "In pedestrian crossing — slow"),
    (42.0, 33.0,  0.50,     0.0, "Still in pedestrian crossing"),
    (42.0, 38.0,  1.40,     0.0, "North of crossing, approaching loading dock vicinity"),
    (60.0, 40.0,  1.50,    90.0, "Near loading dock boundary — proximity warning expected"),
    (62.0, 42.0,  1.50,    90.0, "VIOLATION: Entered no-go loading dock zone"),
    (70.0, 45.0,  1.50,    90.0, "Deep in no-go zone — multiple violations"),
    (82.0, 25.0,  2.00,    90.0, "OUTSIDE BOUNDARY — OOB condition"),
    (75.0, 25.0,  1.50,   270.0, "Returning to operational zone"),
    (50.0, 25.0,  1.50,   270.0, "Mid warehouse, nominal operation"),
    ( 5.0,  4.0,  0.25,   270.0, "Returning to charging station"),
]

all_reports = []
print(f"Processing {len(agv_route)} position fixes for AGV-001...")
print()

for seq, (x, y, speed, heading, note) in enumerate(agv_route):
    fix = AGVPositionFix(
        agv_id="AGV-001",
        x=x,
        y=y,
        speed_ms=speed,
        heading_deg=heading,
        timestamp=1700000000.0 + seq * 5,   # 5 seconds between fixes
        sequence=seq,
    )

    report = manager.classify_position(fix)
    all_reports.append(report)

    zone_name = report.current_zone.name if report.current_zone else "Unknown"
    status = "OK" if not report.violations and not report.speed_violation else "!!"

    print(f"  [{status}] Seq {seq:02d}: ({x:5.1f}, {y:4.1f}) "
          f"| speed={speed:.2f} m/s limit={report.speed_limit_ms:.2f} m/s "
          f"| zone='{zone_name}'")
    print(f"       note: {note}")

    for w in report.warnings:
        print(f"       [WARN] {w}")
    for v in report.violations:
        print(f"       [VIOL] {v}")
    print()

# ---------------------------------------------------------------------------
# Shift compliance report
# ---------------------------------------------------------------------------
manager.generate_shift_report(all_reports)

# ---------------------------------------------------------------------------
# Additional geofencing utilities
# ---------------------------------------------------------------------------
print_section("BONUS: Path Clearance Check (Pre-Route Validation)")

print("""
Before an AGV executes a planned route, a pre-validation step checks whether
the planned path intersects any no-go zones. If it does, the route planner
must find an alternative path.

This is the same pattern used in:
  - Warehouse AGV systems (route validation before dispatch)
  - Autonomous tractor path planning (check for pond/obstacle intersection)
  - Drone flight planning (check for restricted airspace intersection)
""")

# Define a planned path for AGV-002
planned_path = LineString([
    (15.0,  5.0),
    (55.0,  5.0),
    (55.0, 45.0),   # This path will cross the loading dock no-go zone
    (20.0, 45.0),
])

print(f"Planned path vertices: {list(planned_path.coords)}")
print(f"Planned path length: {planned_path.length:.1f} m")
print()

# Check path against all no-go zones
has_conflict = False
for zone in manager.zones:
    if zone.zone_type == 'no_go':
        if planned_path.intersects(zone.polygon):
            conflict_region = planned_path.intersection(zone.polygon)
            has_conflict = True
            print(f"  CONFLICT: Planned path intersects no-go zone '{zone.name}'")
            print(f"  Conflict geometry type: {conflict_region.geom_type}")
            print(f"  Conflict length in no-go zone: {conflict_region.length:.2f} m")
            print(f"  → Route planner must reroute to avoid '{zone.name}'")

if not has_conflict:
    print("  Path is clear of all no-go zones. Route approved for dispatch.")

# Check path against slow zones
print()
print("Checking planned path against slow zones:")
for zone in manager.zones:
    if zone.zone_type == 'slow':
        if planned_path.intersects(zone.polygon):
            slow_segment = planned_path.intersection(zone.polygon)
            seg_length = slow_segment.length if not slow_segment.is_empty else 0
            print(f"  Path enters slow zone '{zone.name}'")
            print(f"    Segment length in slow zone: {seg_length:.2f} m")
            print(f"    Required speed: ≤ {zone.speed_limit_ms:.2f} m/s")
            travel_time_extra = (seg_length / zone.speed_limit_ms -
                                 seg_length / WarehouseGeofenceManager.DEFAULT_SPEED_MS)
            print(f"    Extra travel time vs. default speed: +{travel_time_extra:.1f} s")

print_section("Script Complete — AGV Geofencing System Demonstrated")
print("Patterns demonstrated:")
print("  1. Hierarchical zone definition with priority + speed limits")
print("  2. STRtree spatial index for efficient multi-zone lookup")
print("  3. Point-in-polygon classification with boundary handling")
print("  4. Speed limit enforcement with tolerance")
print("  5. Proximity warnings for near-miss detection")
print("  6. Pre-route path validation against no-go zones")
print("  7. Shift compliance reporting with zone visit statistics")
print()
print("Production extensions:")
print("  - Load zones from PostGIS / GeoJSON config file")
print("  - Accept position fixes from Kafka consumer")
print("  - Emit enriched events to monitoring dashboard")
print("  - Build zone transition matrix (track zone entry/exit events)")
