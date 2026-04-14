"""
OpenSees bbarQuad cantilever
B-bar Quad (体積ロッキング対策 Q4)
引数: element('bbarQuad', eid, n1,n2,n3,n4, thick, matTag)
type 引数なし (3D構造向けだがplane問題でも使用可)

bbarQuad は体積ロッキング (nearly-incompressible) 対策。
せん断ロッキングには本質的な対策なし → ν=0 では quad と同値になるはず。
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

for r in range(5):
    for c in range(11):
        nid = r * 11 + c + 1
        ops.node(nid, float(c * 5), float(r) * 0.5)

for r in range(5):
    ops.fix(r * 11 + 1, 1, 1)

ops.nDMaterial('ElasticIsotropic', 1, E, NU)

# bbarQuad: (eid, n1,n2,n3,n4, thick, matTag) — type 引数なし
eid = 1
for r in range(4):
    for c in range(10):
        n1 = r * 11 + c + 1
        n2 = r * 11 + c + 2
        n3 = (r+1) * 11 + c + 2
        n4 = (r+1) * 11 + c + 1
        ops.element('bbarQuad', eid, n1, n2, n3, n4, T, 1)
        eid += 1

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

uy_tip = ops.nodeDisp(33, 2)
delta_EB = 0.1 * 50.0**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"OPENSEES_BBAR_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:        {-delta_EB:.8f}")
print(f"Ratio:                {uy_tip/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'bbar_quad_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
