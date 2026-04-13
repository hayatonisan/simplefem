"""
f90fem PLS_LIN cantilever
=========================
大坪英臣「有限要素法の作り方！」付属 Fortran90 FEM (f90fem) の
Python 訳要素 PLS_LIN (Bilinear Q4, 2×2 Gauss, 平面応力) を使用。

ν=0 では平面応力 D = 平面ひずみ D なので SIMPLEFEM quad4 と同一結果になるはず。
→ SIMPLEFEM / OpenSees / Kratos / f90fem の 4 独立実装による相互検証

メッシュ: 55 節点 / 40 要素 (5×11 節点格子, 4×10 要素)
問題: L=50mm, H=2mm, t=0.01mm, E=210000MPa, ν=0, P=0.1N, 線形静的

f90fem 元コード: /mnt/d/31_Analysis/05_f90fem/elements/pls_lin.py
"""
import sys, os, time
import numpy as np
from scipy.linalg import solve

# f90fem elements を参照
F90FEM_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', '05_f90fem')
sys.path.insert(0, os.path.abspath(F90FEM_PATH))

from elements.pls_lin import pls_lin
from state import State

# ── 問題パラメータ ──────────────────────────────────────────────────
E   = 210000.0
NU  = 0.0
T   = 0.01
L   = 50.0
H   = 2.0
P   = 0.1
NR  = 4    # 要素行数 (y方向)
NC  = 10   # 要素列数 (x方向)
NN  = (NR+1) * (NC+1)   # = 55 節点

# ── 節点座標 ────────────────────────────────────────────────────────
# node id (1-indexed): r*11 + c + 1  (r=0..4, c=0..10)
xyznod = np.zeros((3, NN))
for r in range(NR+1):
    for c in range(NC+1):
        nid = r * (NC+1) + c   # 0-indexed
        xyznod[0, nid] = c * (L / NC)      # x
        xyznod[1, nid] = r * (H / NR)      # y

# ── DOF マッピング (各節点 2 DOF: ux,uy) ──────────────────────────
NDOF = NN * 2

# ── 全体剛性行列 ────────────────────────────────────────────────────
KG = np.zeros((NDOF, NDOF))

state = State()
state.xyznod = xyznod
state.zero   = 1.0e-15

t0 = time.perf_counter()

eid = 0
for r in range(NR):
    for c in range(NC):
        # 節点番号 (0-indexed)
        n1 = r * (NC+1) + c        # 左下
        n2 = r * (NC+1) + c + 1   # 右下
        n3 = (r+1) * (NC+1) + c + 1  # 右上
        n4 = (r+1) * (NC+1) + c   # 左上

        # PLS_LIN は 1-indexed
        pls_lin(E, NU, T, n1+1, n2+1, n3+1, n4+1, state)

        # DOF インデックス (0-indexed): node n → dof 2n, 2n+1
        dof_map = [2*n1, 2*n1+1,
                   2*n2, 2*n2+1,
                   2*n3, 2*n3+1,
                   2*n4, 2*n4+1]

        # アセンブル
        for i, di in enumerate(dof_map):
            for j, dj in enumerate(dof_map):
                KG[di, dj] += state.elek[i, j]

# ── 荷重ベクトル ────────────────────────────────────────────────────
# 先端 (c=10) の各節点: 上下端=P/8, 中間=P/4 (台形則 5分割)
F = np.zeros(NDOF)
# SIMPLEFEM quad.py と同じ荷重分布
# node 11 (r=0,c=10): -P/8, node 22 (r=1,c=10): -P/4, ...
load_map = {
    0 * (NC+1) + NC: -0.0125,   # node 10 (0-indexed) = row0, col10
    1 * (NC+1) + NC: -0.025,
    2 * (NC+1) + NC: -0.025,
    3 * (NC+1) + NC: -0.025,
    4 * (NC+1) + NC: -0.0125,
}
for n0, fy in load_map.items():
    F[2*n0 + 1] += fy

# ── 境界条件: 左端固定 (c=0 の全節点) ──────────────────────────────
fixed_dofs = []
for r in range(NR+1):
    n0 = r * (NC+1) + 0
    fixed_dofs += [2*n0, 2*n0+1]

# ペナルティ法でなく行列縮約
free_dofs = [d for d in range(NDOF) if d not in fixed_dofs]
KF = KG[np.ix_(free_dofs, free_dofs)]
FF = F[free_dofs]

# ── 求解 ─────────────────────────────────────────────────────────────
U_free = solve(KF, FF)
elapsed = time.perf_counter() - t0

U = np.zeros(NDOF)
for i, d in enumerate(free_dofs):
    U[d] = U_free[i]

# 先端中立軸: r=2, c=10 → node (0-indexed) = 2*11+10 = 32
nid_tip = 2 * (NC+1) + NC   # = 32
uy_tip = U[2*nid_tip + 1]

delta_EB = P * L**3 / (3.0 * E * (T * H**3 / 12.0))
print(f"F90FEM_PLS_LIN_TIP_UY={uy_tip:.8f}")
print(f"Analytical EB:          {-delta_EB:.8f}")
print(f"Ratio:                  {uy_tip/(-delta_EB):.6f}")
print(f"Elapsed: {elapsed*1000:.1f} ms")

result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(result_dir, exist_ok=True)
with open(os.path.join(result_dir, 'f90fem_uy.txt'), 'w') as f:
    f.write(f"{uy_tip:.15E}\n")
    f.write(f"elapsed={elapsed:.4f}\n")
