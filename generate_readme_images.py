"""
generate_readme_images.py — Repo 02: Shapely Geometry Operations
Generates all illustrative images for the README using only matplotlib + numpy.
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patches as patches
from matplotlib.patches import Polygon, Circle, FancyArrow, FancyBboxPatch
from matplotlib.collections import LineCollection, PatchCollection
import numpy as np
import os

os.makedirs("images", exist_ok=True)

# ─────────────────────────────────────────────────────────
# Helper: hexagon vertices
# ─────────────────────────────────────────────────────────
def hexagon(cx, cy, r):
    angles = np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6
    return np.column_stack([cx + r * np.cos(angles), cy + r * np.sin(angles)])


# ═══════════════════════════════════════════════════════════
# IMAGE 1: geometry_types.png
# ═══════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 4, figsize=(14, 8))
fig.suptitle("Shapely Geometry Types", fontsize=16, fontweight="bold", y=1.01)

PANEL_BG = "#f5f5f5"
AXIS_COLOR = "#333333"

def style_panel(ax, title):
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, fontsize=10, fontweight="bold", color=AXIS_COLOR, pad=6)
    ax.set_xlabel("X (m)", fontsize=8, color=AXIS_COLOR)
    ax.set_ylabel("Y (m)", fontsize=8, color=AXIS_COLOR)
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.6, color="#aaaaaa")
    ax.tick_params(labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")

# --- Panel 1: Point ---
ax = axes[0, 0]
style_panel(ax, "Point")
ax.scatter([0.5], [0.5], s=120, color="#2196F3", zorder=5, edgecolors="#0D47A1", linewidths=1.5)
ax.annotate("Point(0.5, 0.5)", xy=(0.5, 0.5), xytext=(0.55, 0.62),
            fontsize=8, color="#0D47A1",
            arrowprops=dict(arrowstyle="->", color="#0D47A1", lw=0.8))
ax.set_xlim(0, 1); ax.set_ylim(0, 1)

# --- Panel 2: LineString ---
ax = axes[0, 1]
style_panel(ax, "LineString")
xs = [0.1, 0.3, 0.5, 0.7, 0.9]
ys = [0.2, 0.7, 0.3, 0.8, 0.4]
ax.plot(xs, ys, color="#E91E63", linewidth=2, zorder=3)
ax.scatter(xs, ys, color="#880E4F", s=50, zorder=5, edgecolors="white", linewidths=0.8)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.05, "5-vertex polyline", ha="center", fontsize=7.5, color="#880E4F")

# --- Panel 3: LinearRing ---
ax = axes[0, 2]
style_panel(ax, "LinearRing")
ring_pts = np.array([[0.15, 0.2], [0.55, 0.15], [0.85, 0.4],
                     [0.75, 0.8], [0.3, 0.85], [0.15, 0.2]])
ax.plot(ring_pts[:, 0], ring_pts[:, 1], color="#FF9800", linewidth=2,
        linestyle="--", zorder=3)
ax.scatter(ring_pts[:-1, 0], ring_pts[:-1, 1], color="#E65100", s=40, zorder=5,
           edgecolors="white", linewidths=0.8)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.05, "Closed ring (no fill)", ha="center", fontsize=7.5, color="#E65100")

# --- Panel 4: Polygon (hexagon) ---
ax = axes[0, 3]
style_panel(ax, "Polygon")
hex_pts = hexagon(0.5, 0.5, 0.35)
poly = Polygon(hex_pts, closed=True, facecolor="#1565C0", edgecolor="#0D47A1",
               alpha=0.75, linewidth=2, zorder=3)
ax.add_patch(poly)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.05, "Hexagon polygon", ha="center", fontsize=7.5, color="#0D47A1")

# --- Panel 5: MultiPoint ---
ax = axes[1, 0]
style_panel(ax, "MultiPoint")
np.random.seed(42)
mpt_x = np.random.uniform(0.1, 0.9, 5)
mpt_y = np.random.uniform(0.1, 0.9, 5)
colors5 = ["#F44336", "#4CAF50", "#2196F3", "#FF9800", "#9C27B0"]
for i, (x, y) in enumerate(zip(mpt_x, mpt_y)):
    ax.scatter([x], [y], s=100, color=colors5[i], zorder=5,
               edgecolors="white", linewidths=1)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.05, "5 scattered points", ha="center", fontsize=7.5, color="#333333")

# --- Panel 6: MultiLineString ---
ax = axes[1, 1]
style_panel(ax, "MultiLineString")
lines_data = [
    ([0.1, 0.4], [0.2, 0.5]),
    ([0.5, 0.8], [0.3, 0.7]),
    ([0.2, 0.7], [0.7, 0.9]),
]
line_colors = ["#F44336", "#4CAF50", "#2196F3"]
for (lx, ly), lc in zip(lines_data, line_colors):
    ax.plot(lx, ly, color=lc, linewidth=2.5, zorder=3)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.05, "3 separate polylines", ha="center", fontsize=7.5, color="#333333")

# --- Panel 7: MultiPolygon ---
ax = axes[1, 2]
style_panel(ax, "MultiPolygon")
polys_data = [
    np.array([[0.05, 0.05], [0.35, 0.05], [0.35, 0.45], [0.05, 0.45]]),
    np.array([[0.45, 0.5], [0.75, 0.5], [0.9, 0.8], [0.6, 0.95], [0.4, 0.75]]),
    np.array([[0.55, 0.05], [0.95, 0.1], [0.9, 0.4], [0.55, 0.35]]),
]
poly_colors = ["#EF5350", "#42A5F5", "#66BB6A"]
for pts, pc in zip(polys_data, poly_colors):
    p = Polygon(pts, closed=True, facecolor=pc, edgecolor="white",
                alpha=0.75, linewidth=1.5, zorder=3)
    ax.add_patch(p)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.text(0.5, 0.03, "3 separate polygons", ha="center", fontsize=7.5, color="#333333")

# --- Panel 8: GeometryCollection ---
ax = axes[1, 3]
style_panel(ax, "GeometryCollection")
# Polygon part
gc_poly = Polygon(np.array([[0.05, 0.05], [0.45, 0.05], [0.45, 0.45], [0.05, 0.45]]),
                  closed=True, facecolor="#FFA726", edgecolor="#E65100",
                  alpha=0.6, linewidth=1.5, zorder=2)
ax.add_patch(gc_poly)
# Line part
ax.plot([0.5, 0.7, 0.9], [0.1, 0.5, 0.2], color="#7B1FA2", linewidth=2.5, zorder=3)
# Point part
ax.scatter([0.6, 0.75], [0.8, 0.7], s=80, color="#D32F2F", zorder=5,
           edgecolors="white", linewidths=1)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
handles = [
    mpatches.Patch(facecolor="#FFA726", label="Polygon"),
    plt.Line2D([0], [0], color="#7B1FA2", lw=2, label="LineString"),
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#D32F2F",
               markersize=7, label="Points"),
]
ax.legend(handles=handles, fontsize=6.5, loc="upper right", framealpha=0.85)

fig.tight_layout(pad=2.0)
fig.savefig("images/geometry_types.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved: images/geometry_types.png")


# ═══════════════════════════════════════════════════════════
# IMAGE 2: geometric_operations.png
# ═══════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(14, 9))
fig.suptitle("Shapely Geometric Operations", fontsize=15, fontweight="bold", y=1.01)

def style_op_panel(ax, title):
    ax.set_facecolor("#f8f9fa")
    ax.set_title(title, fontsize=11, fontweight="bold", color="#212121", pad=7)
    ax.set_aspect("equal")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.5, color="#aaaaaa")
    ax.tick_params(labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")

# ---- buffer ----
ax = axes[0, 0]
style_op_panel(ax, "buffer()")
orig = Circle((0.5, 0.5), 0.05, facecolor="#2196F3", edgecolor="#0D47A1",
              linewidth=2, zorder=5, label="Original point")
buf1 = Circle((0.5, 0.5), 0.2, facecolor="none", edgecolor="#90CAF9",
              linewidth=2, linestyle="--", zorder=3, label="buffer(0.2)")
buf2 = Circle((0.5, 0.5), 0.35, facecolor="#E3F2FD", edgecolor="#42A5F5",
              linewidth=2, linestyle="-", zorder=2, label="buffer(0.35)")
for p in [buf2, buf1, orig]:
    ax.add_patch(p)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

# ---- union ----
ax = axes[0, 1]
style_op_panel(ax, "union()")
c1 = Circle((0.4, 0.5), 0.25, facecolor="#EF9A9A", edgecolor="#B71C1C",
            alpha=0.6, linewidth=1.5, zorder=2, label="Geom A")
c2 = Circle((0.6, 0.5), 0.25, facecolor="#90CAF9", edgecolor="#0D47A1",
            alpha=0.6, linewidth=1.5, zorder=2, label="Geom B")
# Union outline approximation
theta = np.linspace(0, 2 * np.pi, 300)
union_x = np.concatenate([0.4 + 0.25 * np.cos(theta), 0.6 + 0.25 * np.cos(theta)])
union_y = np.concatenate([0.5 + 0.25 * np.sin(theta), 0.5 + 0.25 * np.sin(theta)])
for p in [c1, c2]:
    ax.add_patch(p)
ax.plot([], [], color="#4CAF50", linewidth=2.5, linestyle="-", label="Union boundary")
# Simple union outline (convex hull approximation with thick green ring)
union_outline = plt.Polygon(
    [[0.15, 0.5], [0.4, 0.17], [0.6, 0.17], [0.85, 0.5],
     [0.6, 0.83], [0.4, 0.83]], closed=True,
    facecolor="none", edgecolor="#2E7D32", linewidth=2.5, linestyle="-", zorder=5)
ax.add_patch(union_outline)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

# ---- intersection ----
ax = axes[0, 2]
style_op_panel(ax, "intersection()")
rect_a = mpatches.FancyBboxPatch((0.1, 0.25), 0.55, 0.5, boxstyle="square,pad=0",
                                  facecolor="#EF9A9A", edgecolor="#B71C1C",
                                  alpha=0.55, linewidth=1.5, zorder=2, label="Rect A")
rect_b = mpatches.FancyBboxPatch((0.35, 0.15), 0.55, 0.5, boxstyle="square,pad=0",
                                  facecolor="#90CAF9", edgecolor="#0D47A1",
                                  alpha=0.55, linewidth=1.5, zorder=2, label="Rect B")
intersection = mpatches.FancyBboxPatch((0.35, 0.25), 0.30, 0.40,
                                        boxstyle="square,pad=0",
                                        facecolor="#FFFF00", edgecolor="#F57F17",
                                        alpha=0.9, linewidth=2, zorder=4,
                                        label="Intersection")
for p in [rect_a, rect_b, intersection]:
    ax.add_patch(p)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

# ---- difference ----
ax = axes[1, 0]
style_op_panel(ax, "difference()")
# Full A rectangle
rect_a2 = mpatches.FancyBboxPatch((0.1, 0.2), 0.55, 0.6, boxstyle="square,pad=0",
                                   facecolor="#EF5350", edgecolor="#B71C1C",
                                   alpha=0.7, linewidth=1.5, zorder=2, label="A − overlap")
# Overlap region (masking B)
rect_b2 = mpatches.FancyBboxPatch((0.4, 0.2), 0.25, 0.6, boxstyle="square,pad=0",
                                   facecolor="#BDBDBD", edgecolor="#757575",
                                   alpha=0.85, linewidth=1.5, zorder=3, label="Subtracted (B)")
rect_b_full = mpatches.FancyBboxPatch((0.4, 0.15), 0.5, 0.7, boxstyle="square,pad=0",
                                      facecolor="none", edgecolor="#1565C0",
                                      linewidth=2, linestyle="--", zorder=4, label="Geom B")
for p in [rect_a2, rect_b2, rect_b_full]:
    ax.add_patch(p)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

# ---- convex_hull ----
ax = axes[1, 1]
style_op_panel(ax, "convex_hull()")
np.random.seed(7)
pts_x = np.random.uniform(0.15, 0.85, 14)
pts_y = np.random.uniform(0.15, 0.85, 14)
ax.scatter(pts_x, pts_y, s=50, color="#7B1FA2", zorder=5, edgecolors="white",
           linewidths=0.8, label="Points")
# Convex hull (approximate via sorted angles from centroid)
cx, cy = pts_x.mean(), pts_y.mean()
angles = np.arctan2(pts_y - cy, pts_x - cx)
hull_idx = np.argsort(angles)
hx = pts_x[hull_idx]
hy = pts_y[hull_idx]
hull_patch = Polygon(np.column_stack([hx, hy]), closed=True,
                     facecolor="#CE93D8", edgecolor="#4A148C",
                     alpha=0.4, linewidth=2, zorder=2, label="Convex Hull")
ax.add_patch(hull_patch)
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

# ---- simplify ----
ax = axes[1, 2]
style_op_panel(ax, "simplify()")
t = np.linspace(0, 1, 60)
jagged_x = t
jagged_y = 0.5 + 0.25 * np.sin(t * 8 * np.pi) + 0.08 * np.random.RandomState(3).randn(60)
ax.plot(jagged_x, jagged_y, color="#EF5350", linewidth=1.5, alpha=0.8,
        label="Original (jagged)")
# Simplified: fewer points
simp_t = np.linspace(0, 1, 8)
simp_y = 0.5 + 0.25 * np.sin(simp_t * 8 * np.pi)
ax.plot(simp_t, simp_y, color="#4CAF50", linewidth=2.5,
        marker="o", markersize=7, markerfacecolor="#1B5E20",
        markeredgecolor="white", label="Simplified")
ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)

fig.tight_layout(pad=2.5)
fig.savefig("images/geometric_operations.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved: images/geometric_operations.png")


# ═══════════════════════════════════════════════════════════
# IMAGE 3: agv_geofencing_warehouse.png
# ═══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(12, 8))
ax.set_facecolor("#ECEFF1")
fig.patch.set_facecolor("#FAFAFA")

# Warehouse boundary (200m × 100m)
warehouse = mpatches.FancyBboxPatch((0, 0), 200, 100,
                                     boxstyle="square,pad=0",
                                     facecolor="#F5F5F5", edgecolor="#212121",
                                     linewidth=3, zorder=1)
ax.add_patch(warehouse)

# Support columns (4 dark gray squares)
col_positions = [(15, 15), (15, 75), (185, 15), (185, 75)]
for (cx, cy) in col_positions:
    col = mpatches.FancyBboxPatch((cx - 2, cy - 2), 4, 4,
                                   boxstyle="square,pad=0",
                                   facecolor="#424242", edgecolor="#212121",
                                   linewidth=1.5, zorder=5)
    ax.add_patch(col)

# Loading docks (blue rectangles on south wall)
docks = [(30, 0, 25, 10), (80, 0, 25, 10)]
for (dx, dy, dw, dh) in docks:
    dock = mpatches.FancyBboxPatch((dx, dy), dw, dh,
                                    boxstyle="square,pad=0",
                                    facecolor="#1565C0", edgecolor="#0D47A1",
                                    linewidth=1.5, zorder=4, alpha=0.85)
    ax.add_patch(dock)
    ax.text(dx + dw / 2, dy + dh / 2, "DOCK", ha="center", va="center",
            fontsize=6.5, color="white", fontweight="bold", zorder=6)

# No-go zones (red hatched)
nogo_zones = [(5, 60, 30, 35), (165, 60, 30, 35)]
for (nx, ny, nw, nh) in nogo_zones:
    nogo = mpatches.FancyBboxPatch((nx, ny), nw, nh,
                                    boxstyle="square,pad=0",
                                    facecolor="#FFCDD2", edgecolor="#B71C1C",
                                    linewidth=2, zorder=3, hatch="///", alpha=0.8)
    ax.add_patch(nogo)
    ax.text(nx + nw / 2, ny + nh / 2, "NO-GO\nZONE", ha="center", va="center",
            fontsize=7, color="#B71C1C", fontweight="bold", zorder=6)

# Slow zones (yellow — pedestrian crossings)
slow_zones = [(40, 0, 10, 50), (120, 30, 10, 70)]
for (sx, sy, sw, sh) in slow_zones:
    slow = mpatches.FancyBboxPatch((sx, sy), sw, sh,
                                    boxstyle="square,pad=0",
                                    facecolor="#FFF176", edgecolor="#F9A825",
                                    linewidth=2, zorder=3, hatch="---", alpha=0.85)
    ax.add_patch(slow)
    ax.text(sx + sw / 2, sy + sh / 2, "SLOW\nZONE", ha="center", va="center",
            fontsize=6, color="#F57F17", fontweight="bold", rotation=90, zorder=6)

# AGV operating zone (green)
agv_zone = mpatches.FancyBboxPatch((55, 5), 100, 55,
                                    boxstyle="square,pad=0",
                                    facecolor="#C8E6C9", edgecolor="#2E7D32",
                                    linewidth=2.5, zorder=2, alpha=0.6)
ax.add_patch(agv_zone)
ax.text(105, 32, "AGV OPERATING\nZONE", ha="center", va="center",
        fontsize=9, color="#1B5E20", fontweight="bold", zorder=6)

# Charging stations (orange circles)
charge_positions = [(65, 90), (105, 90), (145, 90)]
for (chx, chy) in charge_positions:
    ch = Circle((chx, chy), 5, facecolor="#FF6F00", edgecolor="#E65100",
                linewidth=2, zorder=5, alpha=0.9)
    ax.add_patch(ch)
    ax.text(chx, chy, "⚡", ha="center", va="center", fontsize=9, zorder=7)

# Parking areas (purple rectangles)
parking_zones = [(55, 65, 20, 12), (100, 65, 20, 12), (145, 65, 20, 12)]
for (px, py, pw, ph) in parking_zones:
    park = mpatches.FancyBboxPatch((px, py), pw, ph,
                                    boxstyle="square,pad=0",
                                    facecolor="#CE93D8", edgecolor="#6A1B9A",
                                    linewidth=1.5, zorder=3, alpha=0.75)
    ax.add_patch(park)
    ax.text(px + pw / 2, py + ph / 2, "PARK", ha="center", va="center",
            fontsize=6.5, color="#4A148C", fontweight="bold", zorder=6)

# AGV positions (colored triangles)
agv_data = [
    (70, 20, "#F44336", "AGV-01"),
    (90, 40, "#2196F3", "AGV-02"),
    (110, 15, "#4CAF50", "AGV-03"),
    (130, 35, "#FF9800", "AGV-04"),
    (85, 25, "#9C27B0", "AGV-05"),
]
for (ax_x, ax_y, ac, alabel) in agv_data:
    ax.plot(ax_x, ax_y, marker="^", markersize=12, color=ac,
            markeredgecolor="white", markeredgewidth=1.2, zorder=8)
    ax.text(ax_x + 2, ax_y + 3, alabel, fontsize=6.5, color=ac,
            fontweight="bold", zorder=8)

# Legend
legend_elements = [
    mpatches.Patch(facecolor="#F5F5F5", edgecolor="#212121", linewidth=2,
                   label="Warehouse boundary"),
    mpatches.Patch(facecolor="#1565C0", label="Loading dock"),
    mpatches.Patch(facecolor="#FFCDD2", edgecolor="#B71C1C", hatch="///",
                   label="No-go zone"),
    mpatches.Patch(facecolor="#FFF176", edgecolor="#F9A825", hatch="---",
                   label="Slow / pedestrian zone"),
    mpatches.Patch(facecolor="#C8E6C9", edgecolor="#2E7D32",
                   label="AGV operating zone"),
    mpatches.Patch(facecolor="#FF6F00", label="Charging station"),
    mpatches.Patch(facecolor="#CE93D8", edgecolor="#6A1B9A",
                   label="Parking area"),
    mpatches.Patch(facecolor="#424242", label="Support column"),
    plt.Line2D([0], [0], marker="^", color="w", markerfacecolor="#2196F3",
               markersize=10, markeredgecolor="white", label="AGV position"),
]
ax.legend(handles=legend_elements, loc="lower right", fontsize=8,
          framealpha=0.92, ncol=1, title="Legend", title_fontsize=9,
          edgecolor="#BDBDBD")

ax.set_xlim(-5, 205)
ax.set_ylim(-5, 110)
ax.set_xlabel("X — East (meters)", fontsize=10)
ax.set_ylabel("Y — North (meters)", fontsize=10)
ax.set_title("Warehouse AGV/AMR Geofence Layout", fontsize=14,
             fontweight="bold", pad=10)
ax.set_aspect("equal")
ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4, color="#90A4AE")
ax.tick_params(labelsize=9)

# North arrow
ax.annotate("", xy=(198, 107), xytext=(198, 97),
            arrowprops=dict(arrowstyle="-|>", color="black", lw=2.5))
ax.text(198, 107.5, "N", ha="center", va="bottom", fontsize=11,
        fontweight="bold", color="black")

fig.tight_layout()
fig.savefig("images/agv_geofencing_warehouse.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved: images/agv_geofencing_warehouse.png")

print("\nAll images generated successfully in images/")
