"""
OpenSees quad8n cantilever
8節点セレンディピティ (Serendipity Q8)
引数: element('quad8n', eid, n1..n8, thick, 'PlaneStrain', matTag)

SIMPLEFEM quad8 / Kratos SmallDisplacement2D8N と同等 → ~100.0%
149 節点 / 40 要素 メッシュ (cantilever_q8.mdpa と同一レイアウト)

節点順 (OpenSees quad8n):
  n1=(-,-) n2=(+,-) n3=(+,+) n4=(-,+)  コーナー
  n5=(0,-) n6=(+,0) n7=(0,+) n8=(-,0)  ミッドサイド
"""
import sys, os, time
sys.path.insert(0, '/home/kz74l/.local/lib/python3.12/site-packages')
import openseespy.opensees as ops

E  = 210000.0
NU = 0.0
T  = 0.01
L  = 50.0
H  = 2.0

# Q8 メッシュ: 4×10 要素, 5×11 コーナー + ミッドサイド = 149 節点
# SIMPLEFEM cantilever_quad8.py と同一レイアウト
NR = 4; NC = 10

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 2)

# コーナー節点 1-55: 5×11 格子
for r in range(NR+1):
    for c in range(NC+1):
        nid = r * (NC+1) + c + 1
        ops.node(nid, float(c * 5), float(r) * 0.5)

# 水平ミッドサイド節点 56-: 各行間 × 10 列
mid_h_start = (NR+1) * (NC+1) + 1   # = 56
for r in range(NR):
    for c in range(NC):
        nid = mid_h_start + r * NC + c
        x = (c + 0.5) * 5.0
        y_lo = r * 0.5; y_hi = (r+1) * 0.5
        # 下ミッドサイド (各要素の n5)
        ops.node(nid, x, y_lo)

# 垂直ミッドサイド節点: 各列間 × 4 行 (各要素の n6, n8 を担う)
# 各要素について右辺 n6 と左辺 n8
# → n6: 右辺中点, 各列c(=1..10)に対して nid
# → n8: 左辺中点 = 前要素の n6
# 簡便のため全要素の右辺ミッドサイドを登録し、左辺は参照
# vert[r][c] = 列 c の右辺ミッドサイド (行r の右辺中点)
vert_start = mid_h_start + NR * NC   # = 56 + 40 = 96

# vert_nid[r][c]: x=c*5, y=(r+0.5)*0.5
for r in range(NR):
    for c in range(NC+1):
        nid = vert_start + r * (NC+1) + c
        ops.node(nid, float(c * 5), (r + 0.5) * 0.5)

# 上ミッドサイド節点 (各要素 n7): 行r+1 の水平中点 = 下行の上辺
# → 各要素 (r,c) の n7 は行 r+1 の列 c の下ミッドサイド
# n7 = mid_h_start + (r+1)*NC + c ... ただし r=NR では行なし → 追加登録
top_mid_start = vert_start + NR * (NC+1)   # 上辺行 (r=NR) の水平中点
for c in range(NC):
    nid = top_mid_start + c
    x = (c + 0.5) * 5.0
    ops.node(nid, x, H)

# --- 節点番号アクセサ ---
def corner(r, c):
    return r * (NC+1) + c + 1

def mid_bot(r, c):   # 要素(r,c)の n5: 下辺中点
    return mid_h_start + r * NC + c

def mid_top(r, c):   # 要素(r,c)の n7: 上辺中点
    if r + 1 < NR:
        return mid_h_start + (r+1) * NC + c
    else:
        return top_mid_start + c

def mid_right(r, c):  # 要素(r,c)の n6: 右辺中点
    return vert_start + r * (NC+1) + (c+1)

def mid_left(r, c):   # 要素(r,c)の n8: 左辺中点
    return vert_start + r * (NC+1) + c

# 固定端 (c=0 の全節点)
fixed = set()
for r in range(NR+1):
    fixed.add(corner(r, 0))
for r in range(NR):
    fixed.add(mid_left(r, 0))
for n in fixed:
    ops.fix(n, 1, 1)

ops.nDMaterial('ElasticIsotropic', 1, E, NU)

# quad8n 要素: n1(--) n2(+-) n3(++) n4(-+) n5(0-) n6(+0) n7(0+) n8(-0)
eid = 1
for r in range(NR):
    for c in range(NC):
        n1 = corner(r,   c)
        n2 = corner(r,   c+1)
        n3 = corner(r+1, c+1)
        n4 = corner(r+1, c)
        n5 = mid_bot(r,   c)
        n6 = mid_right(r, c)
        n7 = mid_top(r,   c)
        n8 = mid_left(r,  c)
        ops.element('quad8n', eid, n1,n2,n3,n4, n5,n6,n7,n8, T, 'PlaneStrain', 1)
        eid += 1

# 荷重: 先端 (c=NC) の Q8 分散荷重
# 端辺の荷重積分 (1D Gauss): コーナー P/6, ミッドサイド 2P/3 per span
# 4要素×0.5mm span, pe=P/4=0.025N per element
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

pe = 0.1 / NR
tip_loads = {}
for r in range(NR):
    nc_lo = corner(r,   NC)
    nc_hi = corner(r+1, NC)
    nm    = mid_right(r, NC-1)   # 右辺中点
    tip_loads[nc_lo] = tip_loads.get(nc_lo, 0.0) + pe/6
    tip_loads[nc_hi] = tip_loads.get(nc_hi, 0.0) + pe/6
    tip_loads[nm]    = tip_loads.get(nm,    0.0) + pe*2/3

for nid, fy in tip_loads.items():
    ops.load(nid, 0.0, -fy)

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

t0 = time.perf_counter()
ops.analyze(1)
elapsed = time.perf_counter() - t0

# 先端中立軸: corner(2, 10) = node 33
uy_tip = ops.nodeDisp(corner(2, NC), 2)
delta_EB = 0.1 * 50.0**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"OPENSEES_QUAD8N_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:          {-delta_EB:.8f}")
print(f"Ratio:                  {uy_tip/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'quad8n_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
