"""
cantilever_quad4.py - 第3.3章: 片持ち梁 四角形1次要素
平面ひずみ / 55節点 / 40要素 / 2×2 ガウス積分

VBA原本: 3.3_片持ち梁_四角形1次要素_四角形1次.vb
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
THICKNESS = 0.01
YOUNG = 210000.0
POISSON = 0.0
NODES = 55
ELEMENTS = 40
INTEGRAL_POINTS = 4    # 2×2
NODES_QUAD4 = 4
COMPONENTS = 3
DOF_NODE = 2
DOF_TOTAL = NODES * DOF_NODE        # 110
DOF_QUAD4 = NODES_QUAD4 * DOF_NODE  # 8


def initialize():
    """配列を初期化 - VBA: initialize()"""
    # 要素内節点番号 0-indexed (VBA値 - 1)
    conn_vba = [
        (1,2,13,12),(2,3,14,13),(3,4,15,14),(4,5,16,15),(5,6,17,16),
        (6,7,18,17),(7,8,19,18),(8,9,20,19),(9,10,21,20),(10,11,22,21),
        (12,13,24,23),(13,14,25,24),(14,15,26,25),(15,16,27,26),(16,17,28,27),
        (17,18,29,28),(18,19,30,29),(19,20,31,30),(20,21,32,31),(21,22,33,32),
        (23,24,35,34),(24,25,36,35),(25,26,37,36),(26,27,38,37),(27,28,39,38),
        (28,29,40,39),(29,30,41,40),(30,31,42,41),(31,32,43,42),(32,33,44,43),
        (34,35,46,45),(35,36,47,46),(36,37,48,47),(37,38,49,48),(38,39,50,49),
        (39,40,51,50),(40,41,52,51),(41,42,53,52),(42,43,54,53),(43,44,55,54),
    ]
    connectivity = np.array(conn_vba, dtype=int) - 1

    # 節点座標 (5行×11列: y=0,0.5,1,1.5,2)
    xs, ys = [], []
    for yv in [0.0, 0.5, 1.0, 1.5, 2.0]:
        for xv in [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]:
            xs.append(xv)
            ys.append(yv)
    x = np.array(xs)
    y = np.array(ys)

    U_presc = np.zeros(DOF_TOTAL)
    F = np.zeros(DOF_TOTAL)
    constrained = np.zeros(DOF_TOTAL, dtype=bool)

    for nv in [1, 12, 23, 34, 45]:
        n = nv - 1
        constrained[n * DOF_NODE]     = True
        constrained[n * DOF_NODE + 1] = True

    # 荷重ベクトル (y方向)
    for nv, fval in {11: -0.0125, 22: -0.025, 33: -0.025, 44: -0.025, 55: -0.0125}.items():
        F[(nv - 1) * DOF_NODE + 1] = fval

    # 2×2 ガウス積分点座標と重み
    g = 1.0 / np.sqrt(3.0)
    ip_xi = np.array([-g,  g, -g,  g])
    ip_et = np.array([-g, -g,  g,  g])
    ip_wi = np.ones(INTEGRAL_POINTS)
    ip_wj = np.ones(INTEGRAL_POINTS)

    return connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj


def _shape_deriv_quad4(xi: float, et: float):
    """四角形1次要素の形状関数偏微分 ∂N/∂ξ, ∂N/∂η

    節点順: 1(-1,-1), 2(+1,-1), 3(+1,+1), 4(-1,+1)
    """
    dN_dxi = np.array([
        -(1 - et) / 4,
         (1 - et) / 4,
         (1 + et) / 4,
        -(1 + et) / 4,
    ])
    dN_det = np.array([
        -(1 - xi) / 4,
        -(1 + xi) / 4,
         (1 + xi) / 4,
         (1 - xi) / 4,
    ])
    return dN_dxi, dN_det


def make_B(connectivity, x, y, ip_xi, ip_et):
    """全要素のBマトリックスとdetJを計算 - VBA: make_B()

    Returns:
        B_mat: (ELEMENTS, 4, 3, 8)
        detJ:  (ELEMENTS, 4)
    """
    B_mat = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS, DOF_QUAD4))
    detJ  = np.zeros((ELEMENTS, INTEGRAL_POINTS))

    for e in range(ELEMENTS):
        xn = x[connectivity[e]]  # (4,)
        yn = y[connectivity[e]]  # (4,)

        for ip in range(INTEGRAL_POINTS):
            xi = ip_xi[ip]
            et = ip_et[ip]

            dN_dxi, dN_det = _shape_deriv_quad4(xi, et)

            dX_dxi = dN_dxi @ xn
            dY_dxi = dN_dxi @ yn
            dX_det = dN_det @ xn
            dY_det = dN_det @ yn

            detJ[e, ip] = dX_dxi * dY_det - dY_dxi * dX_det

            inv_detJ = 1.0 / detJ[e, ip]
            dN_dx = (dN_dxi * dY_det - dN_det * dY_dxi) * inv_detJ
            dN_dy = (-dN_dxi * dX_det + dN_det * dX_dxi) * inv_detJ

            # B行列 (3, 8)
            Be = np.zeros((COMPONENTS, DOF_QUAD4))
            for i in range(NODES_QUAD4):
                Be[0, i * 2]     = dN_dx[i]
                Be[1, i * 2 + 1] = dN_dy[i]
                Be[2, i * 2]     = dN_dy[i]
                Be[2, i * 2 + 1] = dN_dx[i]

            B_mat[e, ip] = Be

    return B_mat, detJ


def make_Ke(B_mat, detJ, D, ip_wi, ip_wj):
    """要素剛性マトリックスを計算 - VBA: make_Ke()

    Ke = Σ_ip (B^T * D * B * detJ * wi * wj * t)
    Returns:
        Ke: (ELEMENTS, 8, 8)
    """
    Ke = np.zeros((ELEMENTS, DOF_QUAD4, DOF_QUAD4))
    for e in range(ELEMENTS):
        for ip in range(INTEGRAL_POINTS):
            Be = B_mat[e, ip]  # (3, 8)
            w = detJ[e, ip] * ip_wi[ip] * ip_wj[ip] * THICKNESS
            Ke[e] += Be.T @ D @ Be * w
    return Ke


def cantilever_quad4():
    """メインプロシージャ - VBA: simple_fem_quad4()

    Returns:
        U:         変位ベクトル (110,)
        Fr:        反力ベクトル (110,)
        strain_ip: (40, 4, 3)
        stress_ip: (40, 4, 3)
    """
    connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    B_mat, detJ = make_B(connectivity, x, y, ip_xi, ip_et)
    Ke = make_Ke(B_mat, detJ, D, ip_wi, ip_wj)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_QUAD4)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)

    Fr = K @ U

    strain_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))
    stress_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))

    for e in range(ELEMENTS):
        # 要素内節点変位 (8,)
        dof_map = np.array([
            connectivity[e, n] * 2 + d
            for n in range(NODES_QUAD4) for d in range(DOF_NODE)
        ])
        Ue = U[dof_map]
        for ip in range(INTEGRAL_POINTS):
            strain_ip[e, ip] = B_mat[e, ip] @ Ue
            stress_ip[e, ip] = D @ strain_ip[e, ip]

    return U, Fr, strain_ip, stress_ip


def print_result(U, Fr, strain_ip, stress_ip, output_file=None):
    """結果出力 - VBA: print_result()"""
    out = open(output_file, "w") if output_file else None
    try:
        target = out if out else sys.stdout
        print_result_nodes(U, Fr, file=target)
        print_result_ip(strain_ip, stress_ip, file=target)
    finally:
        if out:
            out.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="第3.3章 片持ち梁 四角形1次要素")
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス")
    args = parser.parse_args()

    U, Fr, strain_ip, stress_ip = cantilever_quad4()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
