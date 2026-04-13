"""
OpenSees elasticBeamColumn cantilever
SIMPLEFEM と同じ問題: L=50mm, H=2mm, t=0.01mm, E=210000, nu=0, P=0.1N
Euler-Bernoulli 梁理論の基準解
"""
import sys, os, time
sys.path.insert(0, '/home/kz74l/.local/lib/python3.12/site-packages')
import openseespy.opensees as ops
import numpy as np

E      = 210000.0
H      = 2.0
T      = 0.01
L      = 50.0
P      = 0.1        # total tip load [N] downward

A_sec  = H * T      # 0.02 mm^2
I_sec  = T * H**3 / 12.0  # 0.006667 mm^4
delta_EB = P * L**3 / (3.0 * E * I_sec)

ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# 11 nodes along neutral axis y=1.0, x=0..50
xs = np.linspace(0.0, L, 11)
for i, x in enumerate(xs):
    ops.node(i + 1, x, 1.0)

# fix all 3 DOF at x=0
ops.fix(1, 1, 1, 1)

ops.geomTransf('Linear', 1)
for i in range(10):
    ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A_sec, E, I_sec, 1)

ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
ops.load(11, 0.0, -P, 0.0)  # tip load downward

ops.system('BandGeneral')
ops.numberer('RCM')
ops.constraints('Plain')
ops.integrator('LoadControl', 1.0)
ops.algorithm('Linear')
ops.analysis('Static')

t0 = time.perf_counter()
ops.analyze(1)
elapsed = time.perf_counter() - t0

uy_tip = ops.nodeDisp(11, 2)  # node 11 (x=50), DOF 2 = uy

print(f"OPENSEES_BEAM_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:        {-delta_EB:.8f}")
print(f"Ratio:                {uy_tip / (-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'beam_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
