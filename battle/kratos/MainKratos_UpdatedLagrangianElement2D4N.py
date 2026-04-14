"""
Kratos UpdatedLagrangianElement2D4N cantilever
"""
import sys, os, time
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import KratosMultiphysics
import KratosMultiphysics.StructuralMechanicsApplication as SMA
from KratosMultiphysics.StructuralMechanicsApplication.structural_mechanics_analysis import StructuralMechanicsAnalysis

with open("ProjectParameters_UpdatedLagrangianElement2D4N.json") as f:
    params = KratosMultiphysics.Parameters(f.read())

model = KratosMultiphysics.Model()
simulation = StructuralMechanicsAnalysis(model, params)
simulation.Initialize()

t0 = time.perf_counter()
simulation.RunSolutionLoop()
elapsed = time.perf_counter() - t0
simulation.Finalize()

mp = model.GetModelPart("Structure")
node_33 = mp.GetNode(33)
uy = node_33.GetSolutionStepValue(KratosMultiphysics.DISPLACEMENT_Y)

E=210000.0; H=2.0; T=0.01; L=50.0; P=0.1
delta_EB = P*L**3/(3.0*E*(T*H**3/12.0))
print(f"KRATOS_UpL_4N_TIP_UY={uy:.8f}")
print(f"Analytical EB:   {-delta_EB:.8f}")
print(f"Ratio:           {uy/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(results_dir, exist_ok=True)
fname = "UpdatedLagrangianElement2D4N".lower().replace("element","").replace("2d","").replace("n","n")
with open(os.path.join(results_dir, "kratos_UpdatedLagrangianElement2D4N_uy.txt"), "w") as f:
    f.write(f"{uy:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
