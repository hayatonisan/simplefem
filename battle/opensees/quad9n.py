"""
OpenSees quad9n cantilever
9-node Lagrangian Quad (3×3 Gauss 積分)
完全2次補間 → せん断ロッキング根本解消

メッシュ: 21×9 節点格子 (189 節点) / 10×4 要素 = 40 要素
  x: 0, 2.5, 5, 7.5, ... 50  (step=2.5, 21 points)
  y: 0, 0.25, 0.5, ...  2.0  ( step=0.25, 9 points)
要素ごとに 9 節点 (コーナー4+ミッドサイド4+センター1) を使用

quad9n arg order: eleTag nd1..nd9 thick type matTag
  節点順: n1(--) n2(+-) n3(++) n4(-+) n5(0-) n6(+0) n7(0+) n8(-0) n9(00)
"""
import sys, os, time
sys.path.insert(0, '/home/kz74l/.local/lib/python3.12/site-packages')
import openseespy.opensees as ops

E  = 210000.0
NU = 0.0
T  = 0.01
L  = 50.0
H  = 2.0

# 格子サイズ
NX = 10   # 要素数 (x方向)
NY = 4    # 要素数 (y方向)
GX = 2*NX + 1   # = 21 (節点格子 x)
GY = 2*NY + 1   # =  9 (節点格子 y)

dx = L / NX   # = 5.0
dy = H / NY   # = 0.5

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 2)

# --- 節点 (1-indexed: nid = iy*GX + ix + 1) ---
for iy in range(GY):
    for ix in range(GX):
        nid = iy * GX + ix + 1
        ops.node(nid, ix * (dx/2.0), iy * (dy/2.0))

# --- 固定端 (ix=0 の全節点) ---
for iy in range(GY):
    nid = iy * GX + 0 + 1
    ops.fix(nid, 1, 1)

# --- 材料 ---
ops.nDMaterial('ElasticIsotropic', 1, E, NU)

# --- quad9n 要素 ---
# 要素 (ex,ey): コーナー節点は格子(2ex, 2ey)
# 節点順: 1=(-,-) 2=(+,-) 3=(+,+) 4=(-,+)  (コーナー)
#         5=(0,-) 6=(+,0) 7=(0,+) 8=(-,0)  (ミッドサイド)
#         9=(0,0)                            (センター)
def gnid(ix, iy):
    return iy * GX + ix + 1

eid = 1
for ey in range(NY):
    for ex in range(NX):
        bx = 2 * ex
        by = 2 * ey
        n1 = gnid(bx,   by  )   # コーナー(-,-)
        n2 = gnid(bx+2, by  )   # コーナー(+,-)
        n3 = gnid(bx+2, by+2)   # コーナー(+,+)
        n4 = gnid(bx,   by+2)   # コーナー(-,+)
        n5 = gnid(bx+1, by  )   # ミッドサイド(0,-)
        n6 = gnid(bx+2, by+1)   # ミッドサイド(+,0)
        n7 = gnid(bx+1, by+2)   # ミッドサイド(0,+)
        n8 = gnid(bx,   by+1)   # ミッドサイド(-,0)
        n9 = gnid(bx+1, by+1)   # センター
        ops.element('quad9n', eid,
                    n1, n2, n3, n4, n5, n6, n7, n8, n9,
                    T, 'PlaneStrain', 1)
        eid += 1

# --- 荷重: 先端 ix=20 の節点に分散集中荷重 ---
# Q9 の端荷重分布: コーナー=P/(6*H), ミッドサイド=2P/(3*H), 総和=P=0.1N
# y方向ノード数: コーナー(iy=0,8)=3節点, ミッドサイド(iy=2,4,6)=3節点, コーナー中間(iy=1,3,5,7)は不要
# 正確な荷重分布 (1D 2次形状関数 + 数値積分):
#   端節点 (iy=0,8): P * (1/6) / 4 = P/24 per node
#   中間節点 (iy=2,4,6): P * (4/6) / 3... ← 実は要素ごとに計算が必要
#
# 簡便法: 端面 4 要素に均等配分し各要素の端荷重を正確に分配
# 各要素 y-span = 0.5mm, 合計 P=0.1N
# Q9 端面(η=+1)の荷重: Ni(ξ=+1,η=+1) の形状関数重みで分配
#
# 端面 ix=20 の節点:
#   コーナー(iy=0): nid = gnid(20,0)
#   コーナー(iy=2): nid = gnid(20,2)  ... iy=0,2,4,6,8 (コーナー)
#   ミッドサイド(iy=1): nid = gnid(20,1) ... iy=1,3,5,7 (ミッドサイド)
#
# 1次元 3点 (ξ=-1,0,+1) の形状関数:
#   N1(-1) = 0, N2(0) = 0, N3(+1) = 1  (端ξ=+1 の寄与のみ考慮)
# → 一様荷重 p=P/H を積分:
#   コーナー (端節点): p*H * (1/6) = 0.1/2 * 1/6 = 1/120 N ×上下角= 1/120
#   中間 (ミッドサイド): p*H * (4/6) /NY... ここはNG
#
# 直接法: 4 要素の各端荷重を 0.025N として
#   各要素端: コーナー 0.025*(1/6)=1/240, ミッドサイド 0.025*(4/6)=1/60
#   共有コーナー(iy=2,4,6)は2要素分 → 2 * 0.025*(1/6) = 1/120
#   端コーナー(iy=0,8): 1要素 → 0.025*(1/6) = 1/240

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)

pe = 0.1 / NY   # 各要素が分担する荷重 = 0.025 N

tip_loads = {}
for ey in range(NY):
    by = 2 * ey
    # この要素の端節点 ix=20
    nc_lo = gnid(2*NX, by)       # コーナー下
    nc_hi = gnid(2*NX, by+2)     # コーナー上
    nm    = gnid(2*NX, by+1)     # ミッドサイド

    fc = pe * (1.0/6.0)   # コーナー寄与
    fm = pe * (4.0/6.0)   # ミッドサイド寄与

    tip_loads[nc_lo] = tip_loads.get(nc_lo, 0.0) + fc
    tip_loads[nc_hi] = tip_loads.get(nc_hi, 0.0) + fc
    tip_loads[nm]    = tip_loads.get(nm,    0.0) + fm

# 符号: 下向き = 負
for nid, fy in tip_loads.items():
    ops.load(nid, 0.0, -fy)

# 荷重合計確認
total = sum(tip_loads.values())
assert abs(total - 0.1) < 1e-12, f"Load sum error: {total}"

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

t0 = time.perf_counter()
ops.analyze(1)
elapsed = time.perf_counter() - t0

# 先端中立軸: x=50, y=1.0
# 格子 ix=20, iy=4 → gnid(20,4) = 4*21+20+1 = 105
nid_tip = gnid(2*NX, 2*(NY//2))   # iy=4, ix=20
uy_tip = ops.nodeDisp(nid_tip, 2)

delta_EB = 0.1 * 50.0**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"OPENSEES_QUAD9N_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:          {-delta_EB:.8f}")
print(f"Ratio:                  {uy_tip/(-delta_EB):.6f}")
print(f"Tip node ID: {nid_tip}  Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'quad9n_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
