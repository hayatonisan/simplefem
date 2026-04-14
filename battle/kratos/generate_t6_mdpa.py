"""
Generate cantilever_SmallDisplacementElement2D6N.mdpa
6-node quadratic triangle (T6), SmallDisplacementElement2D6N

Strategy:
  - Base grid: 5 rows x 11 cols = 55 corner nodes (same as Q4)
    nid = r*11 + c + 1,  x = c*5,  y = r*0.5,  r=0..4, c=0..10
  - Each Q4 cell (r,c) is split into 2 T3 triangles:
      T1 = (n1, n2, n3)  where n1=BL, n2=BR, n3=TR
      T2 = (n1, n3, n4)  where n4=TL
  - Each T3 gets 3 midside nodes -> T6
  - Midside nodes are shared between adjacent triangles / elements where possible

T6 node ordering used by Kratos SmallDisplacementElement2D6N:
  n1, n2, n3 (corner nodes CCW), n4 (midside n1-n2), n5 (midside n2-n3), n6 (midside n1-n3)

Midside node catalog (keyed by sorted edge tuple):
  - Horizontal edges:  between (r,c) and (r,c+1)  -> midpoint at x=c*5+2.5, y=r*0.5
  - Vertical edges:    between (r,c) and (r+1,c)   -> midpoint at x=c*5,     y=r*0.5+0.25
  - Diagonal edges:    between (r,c) and (r+1,c+1) -> midpoint at x=c*5+2.5, y=r*0.5+0.25
"""

import os

OUTPUT = os.path.join(os.path.dirname(__file__), "cantilever_SmallDisplacementElement2D6N.mdpa")

# --- base grid ---
NCOLS = 11   # c = 0..10
NROWS = 5    # r = 0..4
NQ4_X = 10  # Q4 cells along x
NQ4_Y = 4   # Q4 cells along y

def corner_nid(r, c):
    return r * NCOLS + c + 1

def corner_coord(r, c):
    return c * 5.0, r * 0.5

# --- midside node registry ---
# key: frozenset or tuple (nid_a, nid_b) with nid_a < nid_b
midside_registry = {}   # edge_key -> (midside_nid, x, y)
next_mid_nid = [NROWS * NCOLS + 1]  # start after 55 corner nodes

def get_or_create_midside(na, nb, xa, ya, xb, yb):
    key = (min(na, nb), max(na, nb))
    if key not in midside_registry:
        mx = (xa + xb) / 2.0
        my = (ya + yb) / 2.0
        midside_registry[key] = (next_mid_nid[0], mx, my)
        next_mid_nid[0] += 1
    return midside_registry[key][0]

# --- build T6 elements ---
# For Q4 cell (r, c):
#   n1 = corner(r,   c)   BL
#   n2 = corner(r,   c+1) BR
#   n3 = corner(r+1, c+1) TR
#   n4 = corner(r+1, c)   TL
#
# T1 = (n1, n2, n3)
#   m4 = midside(n1,n2)   bottom edge
#   m5 = midside(n2,n3)   right diagonal (bottom-right to top-right... wait: n2=BR n3=TR -> vertical right edge)
#   m6 = midside(n1,n3)   diagonal BL->TR
#
# T2 = (n1, n3, n4)
#   m4 = midside(n1,n3)   diagonal (shared with T1 m6)
#   m5 = midside(n3,n4)   top edge (right to left, but we use sorted key)
#   m6 = midside(n1,n4)   left vertical edge

elements = []
eid = 1

for r in range(NQ4_Y):
    for c in range(NQ4_X):
        n1 = corner_nid(r,   c)
        n2 = corner_nid(r,   c+1)
        n3 = corner_nid(r+1, c+1)
        n4 = corner_nid(r+1, c)

        x1, y1 = corner_coord(r,   c)
        x2, y2 = corner_coord(r,   c+1)
        x3, y3 = corner_coord(r+1, c+1)
        x4, y4 = corner_coord(r+1, c)

        # T1 = (n1, n2, n3)
        # Kratos T6: corners first (n1,n2,n3), then midsides: n4=mid(n1-n2), n5=mid(n2-n3), n6=mid(n1-n3)
        m12 = get_or_create_midside(n1, n2, x1, y1, x2, y2)
        m23 = get_or_create_midside(n2, n3, x2, y2, x3, y3)
        m13 = get_or_create_midside(n1, n3, x1, y1, x3, y3)
        elements.append((eid, n1, n2, n3, m12, m23, m13))
        eid += 1

        # T2 = (n1, n3, n4)
        # midsides: mid(n1-n3)=m13 (shared), mid(n3-n4), mid(n1-n4)
        m34 = get_or_create_midside(n3, n4, x3, y3, x4, y4)
        m14 = get_or_create_midside(n1, n4, x1, y1, x4, y4)
        elements.append((eid, n1, n3, n4, m13, m34, m14))
        eid += 1

# --- collect all nodes ---
# corner nodes
corner_nodes = []
for r in range(NROWS):
    for c in range(NCOLS):
        nid = corner_nid(r, c)
        x, y = corner_coord(r, c)
        corner_nodes.append((nid, x, y))

# midside nodes sorted by nid
midside_nodes = sorted(
    [(nid, x, y) for (nid, x, y) in midside_registry.values()],
    key=lambda t: t[0]
)

all_nodes = corner_nodes + midside_nodes
total_nodes = len(all_nodes)
total_elements = len(elements)

print(f"Corner nodes : {len(corner_nodes)}")
print(f"Midside nodes: {len(midside_nodes)}")
print(f"Total nodes  : {total_nodes}")
print(f"Total elements: {total_elements}")

# --- boundary conditions ---
# FixedEnd: x=0 -> c=0, all rows -> nid = r*11+1
fixed_nodes = [corner_nid(r, 0) for r in range(NROWS)]

# Tip nodes: x=50 -> c=10, all rows
# For T6 tip edge (right side), we also need midside nodes on right edge
# Right edge of last column: vertical edges between corner(r,10) and corner(r+1,10)
# These are midside nodes on the right boundary.
# Consistent nodal forces for a parabolic (quadratic) edge with 3 nodes (corner,mid,corner):
#   F_corner = P_elem/6, F_mid = P_elem*4/6
# per Q4 row (NQ4_Y=4 rows -> P_elem = P/4 = 0.025)

# Right edge tip: corner nodes at c=10
tip_corner_node_list = [corner_nid(r, 10) for r in range(NROWS)]  # r=0..4
# Midside nodes on right edge: between corner(r,10) and corner(r+1,10), r=0..3
tip_midside_node_list = []
for r in range(NQ4_Y):
    na = corner_nid(r,   10)
    nb = corner_nid(r+1, 10)
    key = (min(na, nb), max(na, nb))
    mid_nid = midside_registry[key][0]
    tip_midside_node_list.append(mid_nid)

# Load magnitudes
P = 0.1
P_elem = P / NQ4_Y  # 0.025

# Corner tip nodes: r=0 and r=4 have only one adjacent element edge
# r=1,2,3 are shared between two element edges
load_tip_corner_end    = P_elem / 6.0         # r=0 and r=4
load_tip_corner_shared = 2.0 * P_elem / 6.0  # r=1,2,3
load_tip_midside       = P_elem * 4.0 / 6.0  # midside nodes

# Assign condition IDs
# Order: corner r=0, mid r=0-1, corner r=1, mid r=1-2, corner r=2, mid r=2-3, corner r=3, mid r=3-4, corner r=4
# Conditions:
cond_data = []  # (cond_id, node_id, load_y)
cid = 1
# interleave corners and midsides
for i in range(NQ4_Y):
    cond_data.append((cid, tip_corner_node_list[i], None))  # will set load below
    cid += 1
    cond_data.append((cid, tip_midside_node_list[i], load_tip_midside))
    cid += 1
# last corner
cond_data.append((cid, tip_corner_node_list[NQ4_Y], None))
cid += 1

# Set corner loads
# r=0: first entry, only one neighbor -> end corner
# r=4: last entry, only one neighbor -> end corner
# r=1,2,3: two neighbors -> shared corner
for idx, (c_id, nid, load) in enumerate(cond_data):
    if load is None:
        # corner node, determine which
        corner_idx = tip_corner_node_list.index(nid)
        if corner_idx == 0 or corner_idx == NQ4_Y:
            cond_data[idx] = (c_id, nid, load_tip_corner_end)
        else:
            cond_data[idx] = (c_id, nid, load_tip_corner_shared)

# Verify load sum
total_load = sum(load for _, _, load in cond_data)
print(f"Total tip load check: {total_load:.6f} N  (expected {P})")

# Group conditions for sub_model_parts
tip_corner_end_cids    = [c for c, n, _ in cond_data if n in [tip_corner_node_list[0], tip_corner_node_list[NQ4_Y]]]
tip_corner_shared_cids = [c for c, n, _ in cond_data if n in tip_corner_node_list[1:NQ4_Y]]
tip_midside_cids       = [c for c, n, _ in cond_data if n in tip_midside_node_list]

# --- write mdpa ---
lines = []
lines.append("Begin ModelPartData")
lines.append("End ModelPartData")
lines.append("")
lines.append("Begin Properties 1")
lines.append("End Properties")
lines.append("")

lines.append("Begin Nodes")
for nid, x, y in all_nodes:
    lines.append(f"  {nid}  {x:.4f}  {y:.4f}  0.0")
lines.append("End Nodes")
lines.append("")

lines.append("Begin Elements SmallDisplacementElement2D6N")
for e in elements:
    eid_, n1, n2, n3, m12, m23, m13 = e
    lines.append(f"  {eid_} 1  {n1} {n2} {n3} {m12} {m23} {m13}")
lines.append("End Elements")
lines.append("")

lines.append("Begin Conditions PointLoadCondition2D1N")
for c_id, nid, _ in cond_data:
    lines.append(f"  {c_id} 1  {nid}")
lines.append("End Conditions")
lines.append("")

# Parts_Solid
lines.append("Begin SubModelPart Parts_Solid")
lines.append("  Begin SubModelPartNodes")
for nid, _, _ in all_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartElements")
for e in elements:
    lines.append(f"    {e[0]}")
lines.append("  End SubModelPartElements")
lines.append("End SubModelPart")
lines.append("")

# FixedEnd
lines.append("Begin SubModelPart FixedEnd")
lines.append("  Begin SubModelPartNodes")
for nid in fixed_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("End SubModelPart")
lines.append("")

# TipCorner (end corners r=0, r=4)
tip_corner_end_nodes = [tip_corner_node_list[0], tip_corner_node_list[NQ4_Y]]
lines.append("Begin SubModelPart TipCorner")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_end_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_end_cids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipMiddle (shared corners r=1,2,3)
tip_corner_shared_nlist = tip_corner_node_list[1:NQ4_Y]
lines.append("Begin SubModelPart TipMiddle")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_shared_nlist:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_shared_cids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipMidside
lines.append("Begin SubModelPart TipMidside")
lines.append("  Begin SubModelPartNodes")
for nid in tip_midside_node_list:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_midside_cids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

with open(OUTPUT, "w") as f:
    f.write("\n".join(lines))

print(f"Written: {OUTPUT}")
print(f"  Nodes   : {total_nodes}")
print(f"  Elements: {total_elements}")
print(f"  Conditions: {len(cond_data)}")
