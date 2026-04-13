"""
OpenSees enhancedQuad cantilever
Enhanced Assumed Strain (EAS) 要素 — Wilson Q6 / IM 相当
同じ 55 節点 40 要素メッシュで bilinear Q4 のせん断ロッキングを解消

enhancedQuad = Enhanced Assumed Strain (Simo & Rifai 1990)
  内部非適合ひずみモードを追加し静的縮合で消去する
  SIMPLEFEM の quad4_im (Wilson Q6) とほぼ同等の精度
"""
import sys, os, time
sys.path.insert(0, '/home/kz74l/.local/lib/python3.12/site-packages')
import openseespy.opensees as ops

E  = 210000.0
NU = 0.0
T  = 0.01
L  = 50.0
H  = 2.0

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 2)

# --- 節点: 5行 × 11列 (quad と同一) ---
for r in range(5):
    for c in range(11):
        nid = r * 11 + c + 1
        ops.node(nid, float(c * 5), float(r) * 0.5)

# --- 固定端 ---
for r in range(5):
    ops.fix(r * 11 + 1, 1, 1)

# --- 材料 ---
ops.nDMaterial('ElasticIsotropic', 1, E, NU)

# --- enhancedQuad 要素 (同じ接続性) ---
eid = 1
for r in range(4):
    for c in range(10):
        n1 = r * 11 + c + 1
        n2 = r * 11 + c + 2
        n3 = (r+1) * 11 + c + 2
        n4 = (r+1) * 11 + c + 1
        ops.element('enhancedQuad', eid, n1, n2, n3, n4, T, 'PlaneStrain', 1)
        eid += 1

# --- 荷重 (quad.py と同一) ---
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

uy_tip = ops.nodeDisp(33, 2)   # 中立軸先端 node 33 (x=50, y=1.0)

delta_EB = 0.1 * 50.0**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"OPENSEES_ENH_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:        {-delta_EB:.8f}")
print(f"Ratio:                {uy_tip/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'quad_enhanced_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
