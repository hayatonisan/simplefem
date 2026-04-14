"""
Generate cantilever_SmallDisplacementElement2D9N.mdpa
9-node Lagrange quadrilateral (Q9), SmallDisplacementElement2D9N

Grid: ix=0..20, iy=0..8  (21 x 9 = 189 nodes)
Elements: ex=0..9, ey=0..3 (10 x 4 = 40 elements), each spanning 2 grid steps
"""

import os

OUTPUT = os.path.join(os.path.dirname(__file__), "cantilever_SmallDisplacementElement2D9N.mdpa")

# --- geometry parameters ---
L = 50.0   # length
H = 2.0    # height
NX = 20    # number of elements along x (grid points: NX+1=21)
NY = 8     # number of elements along y (grid points: NY+1=9)
# Q9 uses 2x2 sub-grid per element -> NEX = NX/2 = 10, NEY = NY/2 = 4
NEX = NX // 2   # 10
NEY = NY // 2   # 4

# node numbering: nid = iy*(NX+1) + ix + 1
def gnid(ix, iy):
    return iy * (NX + 1) + ix + 1

# coordinates
def gcoord(ix, iy):
    x = ix * (L / NX)
    y = iy * (H / NY)
    return x, y

total_nodes = (NX + 1) * (NY + 1)  # 21*9 = 189

# --- build node list ---
nodes = []
for iy in range(NY + 1):
    for ix in range(NX + 1):
        x, y = gcoord(ix, iy)
        nodes.append((gnid(ix, iy), x, y))

# --- build element list ---
# Q9 element connectivity (Kratos order: corner nodes CCW, then midside, then center)
# n1=gnid(bx,  by  )  bottom-left
# n2=gnid(bx+2,by  )  bottom-right
# n3=gnid(bx+2,by+2)  top-right
# n4=gnid(bx,  by+2)  top-left
# n5=gnid(bx+1,by  )  bottom mid
# n6=gnid(bx+2,by+1)  right mid
# n7=gnid(bx+1,by+2)  top mid
# n8=gnid(bx,  by+1)  left mid
# n9=gnid(bx+1,by+1)  center
elements = []
eid = 1
for ey in range(NEY):
    for ex in range(NEX):
        bx = 2 * ex
        by = 2 * ey
        n1 = gnid(bx,   by)
        n2 = gnid(bx+2, by)
        n3 = gnid(bx+2, by+2)
        n4 = gnid(bx,   by+2)
        n5 = gnid(bx+1, by)
        n6 = gnid(bx+2, by+1)
        n7 = gnid(bx+1, by+2)
        n8 = gnid(bx,   by+1)
        n9 = gnid(bx+1, by+1)
        elements.append((eid, n1, n2, n3, n4, n5, n6, n7, n8, n9))
        eid += 1

# --- boundary conditions ---
# FixedEnd: ix=0, all iy (0..8)
fixed_nodes = [gnid(0, iy) for iy in range(NY + 1)]

# Tip nodes (ix=NX=20): iy=0..8
# Load distribution using consistent nodal forces for Q9 edge (Gauss-Lobatto / Lagrange)
# For a uniform load q along an edge of length H with 3 nodes (corner,mid,corner):
# Consistent forces: F_corner = q*H/6, F_mid = q*H*4/6 = 2q*H/3
# Here q = P/H (force per length), so total:
# F_corner_each = P/6,  F_mid_each = 2P/3
# But we have NR=4 rows of Q9 elements sharing the tip edge.
# Each element edge contributes: corner gets P_elem/6, mid gets 4*P_elem/6
# P_elem = P/NEY = 0.1/4 = 0.025 N per element
# => corner shared between 2 elements gets: 2 * (0.025/6) = 0.025/3
# => pure corner (iy=0 and iy=8): single element contribution = 0.025/6
# => pure midside (iy=1,3,5,7): single element = 0.025 * 4/6
# => shared corner (iy=2,4,6): 2 * (0.025/6) = 0.025/3
#
# Verification:
# 2*(0.025/6) + 3*(0.025/3) + 4*(0.025*4/6)
# = 0.025/3 + 0.025 + 0.025*8/3
# = 0.025*(1/3 + 1 + 8/3) = 0.025*(1/3 + 3/3 + 8/3) = 0.025*(12/3) = 0.025*4 = 0.1  OK

P_elem = 0.1 / NEY  # 0.025

tip_corner_bot  = gnid(NX, 0)          # iy=0
tip_corner_top  = gnid(NX, NY)         # iy=8
tip_corner_shared = [gnid(NX, iy) for iy in range(2, NY, 2)]   # iy=2,4,6
tip_midside       = [gnid(NX, iy) for iy in range(1, NY, 2)]   # iy=1,3,5,7

load_corner_end    = P_elem / 6.0                  # 0.025/6
load_corner_shared = 2.0 * P_elem / 6.0           # 0.025/3
load_midside       = P_elem * 4.0 / 6.0           # 0.025*4/6

# conditions: one per tip node
tip_all_nodes = (
    [tip_corner_bot] +
    tip_midside[:1] +
    tip_corner_shared[:1] +
    tip_midside[1:2] +
    tip_corner_shared[1:2] +
    tip_midside[2:3] +
    tip_corner_shared[2:3] +
    tip_midside[3:4] +
    [tip_corner_top]
)
# order by iy: iy=0..8
tip_all_nodes_ordered = [gnid(NX, iy) for iy in range(NY + 1)]

conditions = [(i+1, tip_all_nodes_ordered[i]) for i in range(len(tip_all_nodes_ordered))]

def get_load(nid):
    iy_val = (nid - (NX + 1)) // (NX + 1)  # won't work cleanly; use lookup
    # determine iy from nid: nid = iy*(NX+1) + NX + 1  => iy = (nid-1)//21 if ix=NX
    ix_check = (nid - 1) % (NX + 1)
    iy_check = (nid - 1) // (NX + 1)
    assert ix_check == NX
    if iy_check == 0 or iy_check == NY:
        return load_corner_end
    elif iy_check % 2 == 0:
        return load_corner_shared
    else:
        return load_midside

# --- sub model part groupings ---
# TipCorner: iy=0,8 (pure corner nodes)
tip_corner_nodes = [gnid(NX, 0), gnid(NX, NY)]
# TipCornerShared: iy=2,4,6 (shared corner nodes between elements)
tip_corner_shared_nodes = [gnid(NX, iy) for iy in [2, 4, 6]]
# TipMidside: iy=1,3,5,7
tip_midside_nodes = [gnid(NX, iy) for iy in [1, 3, 5, 7]]

# condition IDs per group
# conditions are ordered iy=0..8, so cond_id = iy+1
tip_corner_cond_ids = [1, 9]                  # iy=0,8
tip_corner_shared_cond_ids = [3, 5, 7]        # iy=2,4,6
tip_midside_cond_ids = [2, 4, 6, 8]           # iy=1,3,5,7

# --- write mdpa ---
lines = []

lines.append("Begin ModelPartData")
lines.append("End ModelPartData")
lines.append("")
lines.append("Begin Properties 1")
lines.append("End Properties")
lines.append("")

# Nodes
lines.append("Begin Nodes")
for nid, x, y in nodes:
    lines.append(f"  {nid}  {x:.4f}  {y:.4f}  0.0")
lines.append("End Nodes")
lines.append("")

# Elements
lines.append("Begin Elements SmallDisplacementElement2D9N")
for e in elements:
    eid_ = e[0]
    ns = e[1:]
    ns_str = "  ".join(str(n) for n in ns)
    lines.append(f"  {eid_} 1  {ns_str}")
lines.append("End Elements")
lines.append("")

# Conditions
lines.append("Begin Conditions PointLoadCondition2D1N")
for cid, nid in conditions:
    lines.append(f"  {cid} 1  {nid}")
lines.append("End Conditions")
lines.append("")

# SubModelPart Parts_Solid
lines.append("Begin SubModelPart Parts_Solid")
lines.append("  Begin SubModelPartNodes")
for nid, _, _ in nodes:
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

# TipCorner (pure corner iy=0,8)
lines.append("Begin SubModelPart TipCorner")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_cond_ids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipCornerShared (iy=2,4,6)
lines.append("Begin SubModelPart TipCornerShared")
lines.append("  Begin SubModelPartNodes")
for nid in tip_corner_shared_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_corner_shared_cond_ids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

# TipMidside (iy=1,3,5,7)
lines.append("Begin SubModelPart TipMidside")
lines.append("  Begin SubModelPartNodes")
for nid in tip_midside_nodes:
    lines.append(f"    {nid}")
lines.append("  End SubModelPartNodes")
lines.append("  Begin SubModelPartConditions")
for cid in tip_midside_cond_ids:
    lines.append(f"    {cid}")
lines.append("  End SubModelPartConditions")
lines.append("End SubModelPart")
lines.append("")

with open(OUTPUT, "w") as f:
    f.write("\n".join(lines))

print(f"Written: {OUTPUT}")
print(f"  Nodes   : {total_nodes}")
print(f"  Elements: {len(elements)}")
print(f"  Conditions: {len(conditions)}")
# Verify load sum
total_load = sum(get_load(nid) for cid, nid in conditions)
print(f"  Total tip load: {total_load:.6f} N  (expected 0.1)")
