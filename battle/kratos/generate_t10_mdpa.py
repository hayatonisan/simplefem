"""
Generate cantilever_SmallDisplacementElement2D10N.mdpa
10-node cubic triangle (T10), SmallDisplacementElement2D10N

Strategy:
  - Base grid: 5 rows x 11 cols = 55 corner nodes (same as Q4 / T3)
    nid = r*11 + c + 1,  x = c*5,  y = r*0.5,  r=0..4, c=0..10
  - Each Q4 cell (r,c) -> 2 T3 triangles:
      T1 = (n1, n2, n3)  n1=BL, n2=BR, n3=TR
      T2 = (n1, n3, n4)  n4=TL
  - Each T3 -> T10 by adding 2 nodes per edge (at 1/3 and 2/3 positions) + 1 interior node

T10 node ordering used by Kratos SmallDisplacementElement2D10N:
  n1, n2, n3 (corner),
  n4=1/3 along n1->n2,  n5=2/3 along n1->n2,
  n6=1/3 along n2->n3,  n7=2/3 along n2->n3,
  n8=1/3 along n3->n1,  n9=2/3 along n3->n1,   (note: direction n3->n1)
  n10=interior centroid

Edge node registry:
  Each directed edge (na->nb) has nodes at positions 1/3 and 2/3.
  The reverse edge (nb->na) reuses them in swapped order.
  Key: (min(na,nb), max(na,nb)) -> (node_at_1/3_from_smaller, node_at_2/3_from_smaller)
  i.e., node closest to smaller nid, node closest to larger nid.

Interior nodes: one per triangle, not shared.
"""

import os

OUTPUT = os.path.join(os.path.dirname(__file__), "cantilever_SmallDisplacementElement2D10N.mdpa")

NCOLS = 11
NROWS = 5
NQ4_X = 10
NQ4_Y = 4

def corner_nid(r, c):
    return r * NCOLS + c + 1

def corner_coord(r, c):
    return c * 5.0, r * 0.5

# --- node registry ---
node_coords = {}  # nid -> (x, y)

# register corner nodes
for r in range(NROWS):
    for c in range(NCOLS):
        nid = corner_nid(r, c)
        x, y = corner_coord(r, c)
        node_coords[nid] = (x, y)

next_nid = [NROWS * NCOLS + 1]  # 56 onward

def new_node(x, y):
    nid = next_nid[0]
    next_nid[0] += 1
    node_coords[nid] = (x, y)
    return nid

# edge node registry: (minnid, maxnid) -> (nid_near_min, nid_near_max)
edge_registry = {}

def get_or_create_edge_nodes(na, nb):
    """Return (nid_at_1/3_from_na, nid_at_2/3_from_na).
    If edge already exists (possibly in reverse), return correctly oriented nodes."""
    xa, ya = node_coords[na]
    xb, yb = node_coords[nb]
    key = (min(na, nb), max(na, nb))
    if key not in edge_registry:
        # create two nodes at 1/3 and 2/3 from the SMALLER nid
        if na < nb:
            n13 = new_node(xa + (xb - xa) / 3.0, ya + (yb - ya) / 3.0)
            n23 = new_node(xa + (xb - xa) * 2.0 / 3.0, ya + (yb - ya) * 2.0 / 3.0)
        else:
            # nb < na; create from nb
            n13 = new_node(xb + (xa - xb) / 3.0, yb + (ya - yb) / 3.0)
            n23 = new_node(xb + (xa - xb) * 2.0 / 3.0, yb + (ya - yb) * 2.0 / 3.0)
        edge_registry[key] = (n13, n23)  # n13 near min(na,nb), n23 near max(na,nb)

    n13, n23 = edge_registry[key]
    if na <= nb:
        return n13, n23  # 1/3 from na, 2/3 from na
    else:
        return n23, n13  # 1/3 from na (which is far end), 2/3 from na

# --- build elements ---
# T10 connectivity (Kratos order as documented):
# c1,c2,c3, m4(1/3 c1->c2), m5(2/3 c1->c2), m6(1/3 c2->c3), m7(2/3 c2->c3),
# m8(1/3 c3->c1), m9(2/3 c3->c1), m10(interior)
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
        e12_a, e12_b = get_or_create_edge_nodes(n1, n2)  # 1/3, 2/3 from n1
        e23_a, e23_b = get_or_create_edge_nodes(n2, n3)  # 1/3, 2/3 from n2
        e31_a, e31_b = get_or_create_edge_nodes(n3, n1)  # 1/3, 2/3 from n3
        cx1 = (x1 + x2 + x3) / 3.0
        cy1 = (y1 + y2 + y3) / 3.0
        int1 = new_node(cx1, cy1)
        elements.append((eid, n1, n2, n3, e12_a, e12_b, e23_a, e23_b, e31_a, e31_b, int1))
        eid += 1

        # T2 = (n1, n3, n4)
        e13_a, e13_b = get_or_create_edge_nodes(n1, n3)  # 1/3, 2/3 from n1
        e34_a, e34_b = get_or_create_edge_nodes(n3, n4)  # 1/3, 2/3 from n3
        e41_a, e41_b = get_or_create_edge_nodes(n4, n1)  # 1/3, 2/3 from n4
        cx2 = (x1 + x3 + x4) / 3.0
        cy2 = (y1 + y3 + y4) / 3.0
        int2 = new_node(cx2, cy2)
        elements.append((eid, n1, n3, n4, e13_a, e13_b, e34_a, e34_b, e41_a, e41_b, int2))
        eid += 1

all_nids_sorted = sorted(node_coords.keys())
total_nodes = len(all_nids_sorted)
total_elements = len(elements)

print(f"Corner nodes : {NROWS * NCOLS}")
print(f"Total nodes  : {total_nodes}")
print(f"Total elements: {total_elements}")

# --- boundary conditions ---
fixed_nodes = [corner_nid(r, 0) for r in range(NROWS)]

# Tip nodes: right edge of the mesh (x=50, c=10)
# For each Q4 row (r=0..3), the right edge of T1 = edge n2->n3 = corner(r,10)->corner(r+1,10)
# That edge has nodes at 1/3 and 2/3 from n2 (bottom), plus n2 and n3.
# T10 consistent force for cubic edge (4 nodes: c0, p1/3, p2/3, c1):
# Lobatto/Simpson integration for cubic polynomial:
# F_corner = P_elem * 1/8, F_third = P_elem * 3/8
# (Standard result: corner 1/8, interior 3/8 each, total = 1/8+3/8+3/8+1/8 = 1)

P = 0.1
P_elem = P / NQ4_Y  # 0.025

load_corner_end    = P_elem / 8.0         # r=0 bottom, r=4 top: single element
load_corner_shared = 2.0 * P_elem / 8.0  # shared between 2 elements
load_third         = P_elem * 3.0 / 8.0  # 1/3 and 2/3 nodes

# Right edge nodes per row
# For Q4 row r: n_bot = corner(r,10), n_top = corner(r+1,10)
# edge from n_bot to n_top: nodes e_a (1/3 from bot), e_b (2/3 from bot)
right_edge_nodes_per_row = []  # list of (nid_bot, nid_thirda, nid_thirdb, nid_top)
for r in range(NQ4_Y):
    nb = corner_nid(r,   10)
    nt = corner_nid(r+1, 10)
    ea, eb = get_or_create_edge_nodes(nb, nt)
    right_edge_nodes_per_row.append((nb, ea, eb, nt))

# Collect all unique tip nodes in order (bottom to top)
# Bottom corner: corner(0,10)
# then 1/3, 2/3, corner(1,10), 1/3, 2/3, corner(2,10), ... corner(4,10)
tip_nodes_ordered = []
for r in range(NQ4_Y):
    nb, ea, eb, nt = right_edge_nodes_per_row[r]
    if r == 0:
        tip_nodes_ordered.append(nb)
    tip_nodes_ordered.append(ea)
    tip_nodes_ordered.append(eb)
    tip_nodes_ordered.append(nt)

# Compute loads
def tip_load(nid):
    # find which category
    corner_nids_tip = [corner_nid(r, 10) for r in range(NROWS)]
    third_nids = []
    for r in range(NQ4_Y):
        _, ea, eb, _ = right_edge_nodes_per_row[r]
        third_nids.extend([ea, eb])
    if nid in [corner_nids_tip[0], corner_nids_tip[NROWS-1]]:
        return load_corner_end
    elif nid in corner_nids_tip:
        return load_corner_shared
    elif nid in third_nids:
        return load_third
    else:
        raise ValueError(f"Unknown tip node {nid}")

cond_data = [(i+1, nid, tip_load(nid)) for i, nid in enumerate(tip_nodes_ordered)]

total_load = sum(load for _, _, load in cond_data)
print(f"Tip load check: {total_load:.6f} N  (expected {P})")

# Group sub model parts
corner_nids_tip = [corner_nid(r, 10) for r in range(NROWS)]
third_nids_tip = []
for r in range(NQ4_Y):
    _, ea, eb, _ = right_edge_nodes_per_row[r]
    third_nids_tip.extend([ea, eb])

tip_corner_end_nids   = [corner_nids_tip[0], corner_nids_tip[NROWS-1]]
tip_corner_shared_nids = corner_nids_tip[1:NROWS-1]

tip_corner_end_cids    = [c for c, n, _ in cond_data if n in tip_corner_end_nids]
tip_corner_shared_cids = [c for c, n, _ in cond_data if n in tip_corner_shared_nids]
tip_third_cids         = [c for c, n, _ in cond_data if n in third_nids_tip]

# --- write mdpa ---
lines = []
lines.append("Begin ModelPartData")
lines.append("End ModelPartData")
lines.append("")
lines.append("Begin Properties 1")
lines.append("End Properties")
lines.append("")

lines.append("Begin Nodes")
for nid in all_nids_sorted:
    x, y = node_coords[nid]
    lines.append(f"  {nid}  {x:.6f}  {y:.6f}  0.0")
lines.append("End Nodes")
lines.append("")

lines.append("Begin Elements SmallDisplacementElement2D10N")
for e in elements:
    eid_, c1, c2, c3, m4, m5, m6, m7, m8, m9, m10 = e
    lines.append(f"  {eid_} 1  {c1} {c2} {c3} {m4} {m5} {m6} {m7} {m8} {m9} {m10}")
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
for nid in all_nids_sorted:
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

# TipCorner (end corners only)
lines.append("Begin SubModelPart TipCorner")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_end_nids:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_end_cids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipMiddle (shared corner nodes)
lines.append("Begin SubModelPart TipMiddle")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_shared_nids:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_shared_cids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipMidside (1/3 and 2/3 nodes)
lines.append("Begin SubModelPart TipMidside")
lines.append("  Begin SubModelPartNodes")
for nid in third_nids_tip:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_third_cids:
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
