"""
OpenSees SSPquad (Stabilized Single Point) PlaneStrain cantilever
SIMPLEFEM quad4 と同じ 55節点×40要素メッシュ、同じ荷重
SSPquad は enhanced assumed strain により shear locking を低減する
"""
import sys, os, time
sys.path.insert(0, '/home/kz74l/.local/lib/python3.12/site-packages')
import openseespy.opensees as ops
import numpy as np

E     = 210000.0
NU    = 0.0
T     = 0.01   # thickness [mm]
L     = 50.0
H     = 2.0

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 2)

# --- 節点: 5行 x 11列 グリッド (1-indexed) ---
# row r (0..4): y = r*0.5,  col c (0..10): x = c*5
# node id = r*11 + c + 1
for r in range(5):
    for c in range(11):
        nid = r * 11 + c + 1
        x = c * 5.0
        y = r * 0.5
        ops.node(nid, x, y)

# --- 固定端 x=0: nodes 1,12,23,34,45 ---
for r in range(5):
    nid = r * 11 + 1
    ops.fix(nid, 1, 1)

# --- 材料: 等方弾性 ---
ops.nDMaterial('ElasticIsotropic', 1, E, NU)

# --- 要素: SSPquad PlaneStrain ---
# SSPquad signature: element('SSPquad', eleTag, nd1,nd2,nd3,nd4, matTag, type, thick, b1, b2)
# row r(0..3), col c(0..9): 4節点 (bottom-left → bottom-right → top-right → top-left)
# n1=r*11+c+1, n2=r*11+c+2, n3=(r+1)*11+c+2, n4=(r+1)*11+c+1
eid = 1
for r in range(4):
    for c in range(10):
        n1 = r * 11 + c + 1
        n2 = r * 11 + c + 2
        n3 = (r + 1) * 11 + c + 2
        n4 = (r + 1) * 11 + c + 1
        ops.element('SSPquad', eid, n1, n2, n3, n4, 1, 'PlaneStrain', T, 0.0, 0.0)
        eid += 1

# --- 荷重: x=50 (col 10) の 5 節点 (SIMPLEFEM と同じ分布) ---
# nodes 11(y=0), 22(y=0.5), 33(y=1.0), 44(y=1.5), 55(y=2.0)
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
load_map = {11: -0.0125, 22: -0.025, 33: -0.025, 44: -0.025, 55: -0.0125}
for nid, fy in load_map.items():
    ops.load(nid, 0.0, fy)

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

t0 = time.perf_counter()
ops.analyze(1)
elapsed = time.perf_counter() - t0

# 中立軸先端: node 33 (row 2, col 10) = (x=50, y=1.0)
uy_tip = ops.nodeDisp(33, 2)

delta_EB = 0.1 * 50.0**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"OPENSEES_SSP_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:       {-delta_EB:.8f}")
print(f"Ratio:               {uy_tip / (-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'quad_ssp_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
