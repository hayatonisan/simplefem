"""
Kratos SmallDisplacementElement2D9N cantilever
9節点 Lagrange 四辺形, 189節点 / 40要素
先端中立軸: 21×9格子の iy=4, ix=20 → nid = 4*21+20+1 = 105
"""
import sys, os, time
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import KratosMultiphysics
import KratosMultiphysics.StructuralMechanicsApplication as SMA
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis

with open("ProjectParameters_SmallDisplacementElement2D9N.json") as f:
    params = KratosMultiphysics.Parameters(f.read())

model = KratosMultiphysics.Model()
simulation = StructuralMechanicsAnalysis(model, params)
simulation.Initialize()

t0 = time.perf_counter()
simulation.RunSolutionLoop()
elapsed = time.perf_counter() - t0
simulation.Finalize()

mp = model.GetModelPart("Structure")
# nid at ix=20, iy=4: 4*21 + 20 + 1 = 105
nid_tip = 105
node_tip = mp.GetNode(nid_tip)
uy = node_tip.GetSolutionStepValue(KratosMultiphysics.DISPLACEMENT_Y)

E=210000.0; H=2.0; T=0.01; L=50.0; P=0.1
delta_EB = P*L**3/(3.0*E*(T*H**3/12.0))
print(f"KRATOS_9N_TIP_UY={uy:.8f}")
print(f"Analytical EB:   {-delta_EB:.8f}")
print(f"Ratio:           {uy/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(results_dir, exist_ok=True)
with open(os.path.join(results_dir, "kratos_SmallDisplacementElement2D9N_uy.txt"), "w") as f:
    f.write(f"{uy:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
