"""
simple_fem.py - 第2章: シンプルなFEMプログラム
三角形1次要素 / 平面ひずみ / 6節点4要素

VBA原本: 2_simple_fem_Module1.vb
"""
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from fem_core import (
    make_D_plane_strain,
    apply_boundary_conditions,
    solve_fem,
    assemble_global_K,
    print_result_nodes,
    print_result_ip,
)

# --- 定数 ---
NODES = 6
ELEMENTS = 4
COMPONENTS = 3
NODES_TRIA3 = 3
DOF_NODE = 2
DOF_TOTAL = DOF_NODE * NODES      # 12
DOF_TRIA3 = DOF_NODE * NODES_TRIA3  # 6
THICKNESS = 1.0
YOUNG = 210000.0
POISSON = 0.3


def initialize():
    """配列を初期化 - VBA: initialize()

    Returns:
        connectivity: 要素内節点番号 0-indexed (4, 3)
        x, y:         節点座標 (6,)
        U_presc:      規定変位 (12,)
        F:            荷重ベクトル (12,)
        constrained:  拘束フラグ (12,)
    """
    # VBA 1-indexed → Python 0-indexed (1→0, 2→1, ...)
    connectivity = np.array([
        [0, 1, 4],   # VBA: (1, 2, 5)
        [1, 2, 3],   # VBA: (2, 3, 4)
        [1, 3, 4],   # VBA: (2, 4, 5)
        [0, 4, 5],   # VBA: (1, 5, 6)
    ], dtype=int)

    x = np.array([0.0, 1.0, 2.0, 2.0, 1.0, 0.0])
    y = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])

    U_presc = np.zeros(DOF_TOTAL)
    F = np.zeros(DOF_TOTAL)

    # VBA: F(8) = -100  → node 4 (1-indexed), y-DOF → Python: (4-1)*2+1 = 7
    F[7] = -100.0

    # VBA: Um(1)=True → node1 x → Python DOF 0
    # VBA: Um(2)=True → node1 y → Python DOF 1
    # VBA: Um(11)=True → node6 x → (6-1)*2+0=10 → Python DOF 10
    constrained = np.zeros(DOF_TOTAL, dtype=bool)
    constrained[0] = True   # node 1 x
    constrained[1] = True   # node 1 y
    constrained[10] = True  # node 6 x

    return connectivity, x, y, U_presc, F, constrained


def make_B(connectivity, x, y):
    """Bマトリックスと要素面積を計算 - VBA: make_B()

    Returns:
        B:            (ELEMENTS, 3, 6)
        area_element: (ELEMENTS,)
    """
    B_mat = np.zeros((ELEMENTS, COMPONENTS, DOF_TRIA3))
    area_element = np.zeros(ELEMENTS)

    for e in range(ELEMENTS):
        n1, n2, n3 = connectivity[e]
        x1, y1 = x[n1], y[n1]
        x2, y2 = x[n2], y[n2]
        x3, y3 = x[n3], y[n3]

        area_element[e] = (
            x1 * y2 - x1 * y3 + x2 * y3 - x2 * y1 + x3 * y1 - x3 * y2
        ) / 2.0

        coef = 1.0 / area_element[e] / 2.0

        # ε_xx = ∂u/∂x
        B_mat[e, 0, 0] = coef * (y2 - y3)
        B_mat[e, 0, 1] = 0.0
        B_mat[e, 0, 2] = coef * (y3 - y1)
        B_mat[e, 0, 3] = 0.0
        B_mat[e, 0, 4] = coef * (y1 - y2)
        B_mat[e, 0, 5] = 0.0
        # ε_yy = ∂v/∂y
        B_mat[e, 1, 0] = 0.0
        B_mat[e, 1, 1] = coef * (x3 - x2)
        B_mat[e, 1, 2] = 0.0
        B_mat[e, 1, 3] = coef * (x1 - x3)
        B_mat[e, 1, 4] = 0.0
        B_mat[e, 1, 5] = coef * (x2 - x1)
        # γ_xy = ∂u/∂y + ∂v/∂x
        B_mat[e, 2, 0] = B_mat[e, 1, 1]
        B_mat[e, 2, 1] = B_mat[e, 0, 0]
        B_mat[e, 2, 2] = B_mat[e, 1, 3]
        B_mat[e, 2, 3] = B_mat[e, 0, 2]
        B_mat[e, 2, 4] = B_mat[e, 1, 5]
        B_mat[e, 2, 5] = B_mat[e, 0, 4]

    return B_mat, area_element


def make_Ke(B_mat, area_element, D):
    """要素剛性マトリックスを計算 - VBA: make_Ke()

    Ke = B^T * D * B * area * thickness
    Returns:
        Ke: (ELEMENTS, 6, 6)
    """
    Ke = np.zeros((ELEMENTS, DOF_TRIA3, DOF_TRIA3))
    for e in range(ELEMENTS):
        Be = B_mat[e]  # (3, 6)
        Ke[e] = Be.T @ D @ Be * area_element[e] * THICKNESS
    return Ke


def simple_fem():
    """メインプロシージャ - VBA: simple_fem()

    Returns:
        U:           変位ベクトル (12,)
        Fr:          反力ベクトル (12,)
        strain_elem: 要素ひずみ (4, 3)
        stress_elem: 要素応力 (4, 3)
    """
    connectivity, x, y, U_presc, F, constrained = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    B_mat, area_element = make_B(connectivity, x, y)
    Ke = make_Ke(B_mat, area_element, D)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_TRIA3)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)

    # 節点反力: Fr = K * U
    Fr = K @ U

    # 要素ひずみ: strain = B * Ue
    strain_elem = np.zeros((ELEMENTS, COMPONENTS))
    for e in range(ELEMENTS):
        Ue = np.zeros(DOF_TRIA3)
        for n in range(NODES_TRIA3):
            Ue[n * 2]     = U[connectivity[e, n] * 2]
            Ue[n * 2 + 1] = U[connectivity[e, n] * 2 + 1]
        strain_elem[e] = B_mat[e] @ Ue

    # 要素応力: stress = D * strain
    stress_elem = (D @ strain_elem.T).T

    return U, Fr, strain_elem, stress_elem


def print_result(U, Fr, strain, stress, output_file=None):
    """結果を出力 - VBA: print_result() に相当"""
    out = open(output_file, "w") if output_file else None
    try:
        target = out if out else sys.stdout
        print_result_nodes(U, Fr, file=target)

        # 要素値を (n_elem, 1, 3) に整形して共通出力
        print_result_ip(
            strain[:, np.newaxis, :],
            stress[:, np.newaxis, :],
            section_label="Element",
            file=target,
        )
    finally:
        if out:
            out.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="第2章 simple_fem")
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス")
    args = parser.parse_args()

    U, Fr, strain, stress = simple_fem()
    print_result(U, Fr, strain, stress, args.output)
