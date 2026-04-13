"""
cantilever_quad8.py - 第3.3章: 片持ち梁 四角形2次要素
平面ひずみ / 149節点 / 40要素 / 3×3 ガウス積分

VBA原本: 3.3_片持ち梁_四角形2次要素_四角形2次.vb
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
NODES = 149
ELEMENTS = 40
INTEGRAL_POINTS = 9    # 3×3
NODES_QUAD8 = 8
COMPONENTS = 3
DOF_NODE = 2
DOF_TOTAL = NODES * DOF_NODE        # 298
DOF_QUAD8 = NODES_QUAD8 * DOF_NODE  # 16


def initialize():
    """配列を初期化 - VBA: initialize()"""
    # 要素内節点番号 0-indexed (VBA値 - 1)
    conn_vba = [
        (1,2,13,12,56,57,58,59),(2,3,14,13,60,61,62,57),
        (3,4,15,14,63,64,65,61),(4,5,16,15,66,67,68,64),
        (5,6,17,16,69,70,71,67),(6,7,18,17,72,73,74,70),
        (7,8,19,18,75,76,77,73),(8,9,20,19,78,79,80,76),
        (9,10,21,20,81,82,83,79),(10,11,22,21,84,85,86,82),
        (12,13,24,23,58,87,88,89),(13,14,25,24,62,90,91,87),
        (14,15,26,25,65,92,93,90),(15,16,27,26,68,94,95,92),
        (16,17,28,27,71,96,97,94),(17,18,29,28,74,98,99,96),
        (18,19,30,29,77,100,101,98),(19,20,31,30,80,102,103,100),
        (20,21,32,31,83,104,105,102),(21,22,33,32,86,106,107,104),
        (23,24,35,34,88,108,109,110),(24,25,36,35,91,111,112,108),
        (25,26,37,36,93,113,114,111),(26,27,38,37,95,115,116,113),
        (27,28,39,38,97,117,118,115),(28,29,40,39,99,119,120,117),
        (29,30,41,40,101,121,122,119),(30,31,42,41,103,123,124,121),
        (31,32,43,42,105,125,126,123),(32,33,44,43,107,127,128,125),
        (34,35,46,45,109,129,130,131),(35,36,47,46,112,132,133,129),
        (36,37,48,47,114,134,135,132),(37,38,49,48,116,136,137,134),
        (38,39,50,49,118,138,139,136),(39,40,51,50,120,140,141,138),
        (40,41,52,51,122,142,143,140),(41,42,53,52,124,144,145,142),
        (42,43,54,53,126,146,147,144),(43,44,55,54,128,148,149,146),
    ]
    connectivity = np.array(conn_vba, dtype=int) - 1

    # 節点座標 (VBAの x(i), y(i) をリスト化)
    # 節点1-55: 5行×11列グリッド (y=0,0.5,1,1.5,2, x=0..50)
    # 節点56-149: 各要素の辺中点
    coords_vba = {}
    idx = 1
    for yv in [0.0, 0.5, 1.0, 1.5, 2.0]:
        for xv in [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]:
            coords_vba[idx] = (xv, yv)
            idx += 1

    # 辺中点ノード座標 (VBAのx(56)..x(149))
    mid_coords = [
        (2.5,0),(5,0.25),(2.5,0.5),(0,0.25),
        (7.5,0),(10,0.25),(7.5,0.5),
        (12.5,0),(15,0.25),(12.5,0.5),
        (17.5,0),(20,0.25),(17.5,0.5),
        (22.5,0),(25,0.25),(22.5,0.5),
        (27.5,0),(30,0.25),(27.5,0.5),
        (32.5,0),(35,0.25),(32.5,0.5),
        (37.5,0),(40,0.25),(37.5,0.5),
        (42.5,0),(45,0.25),(42.5,0.5),
        (47.5,0),(50,0.25),(47.5,0.5),
        (5,0.75),(2.5,1),(0,0.75),
        (10,0.75),(7.5,1),
        (15,0.75),(12.5,1),
        (20,0.75),(17.5,1),
        (25,0.75),(22.5,1),
        (30,0.75),(27.5,1),
        (35,0.75),(32.5,1),
        (40,0.75),(37.5,1),
        (45,0.75),(42.5,1),
        (50,0.75),(47.5,1),
        (5,1.25),(2.5,1.5),(0,1.25),
        (10,1.25),(7.5,1.5),
        (15,1.25),(12.5,1.5),
        (20,1.25),(17.5,1.5),
        (25,1.25),(22.5,1.5),
        (30,1.25),(27.5,1.5),
        (35,1.25),(32.5,1.5),
        (40,1.25),(37.5,1.5),
        (45,1.25),(42.5,1.5),
        (50,1.25),(47.5,1.5),
        (5,1.75),(2.5,2),(0,1.75),
        (10,1.75),(7.5,2),
        (15,1.75),(12.5,2),
        (20,1.75),(17.5,2),
        (25,1.75),(22.5,2),
        (30,1.75),(27.5,2),
        (35,1.75),(32.5,2),
        (40,1.75),(37.5,2),
        (45,1.75),(42.5,2),
        (50,1.75),(47.5,2),
    ]
    for i, (xv, yv) in enumerate(mid_coords):
        coords_vba[56 + i] = (xv, yv)

    x = np.array([coords_vba[i][0] for i in range(1, NODES + 1)])
    y = np.array([coords_vba[i][1] for i in range(1, NODES + 1)])

    U_presc = np.zeros(DOF_TOTAL)
    F = np.zeros(DOF_TOTAL)
    constrained = np.zeros(DOF_TOTAL, dtype=bool)

    # 変位拘束: VBA FixNode = {1,12,23,34,45,59,89,110,131}
    for nv in [1, 12, 23, 34, 45, 59, 89, 110, 131]:
        n = nv - 1
        constrained[n * DOF_NODE]     = True
        constrained[n * DOF_NODE + 1] = True

    # 荷重ベクトル
    load_data = {
        11: -0.00416666666,
        55: -0.00416666666,
        22: -0.00833333333,
        33: -0.00833333333,
        44: -0.00833333333,
        85: -0.01666666666,
        106: -0.01666666666,
        127: -0.01666666666,
        148: -0.01666666666,
    }
    for nv, fval in load_data.items():
        F[(nv - 1) * DOF_NODE + 1] = fval

    # 3×3 ガウス積分点座標と重み
    ce = np.sqrt(3.0 / 5.0)
    cc = 0.0
    we = 5.0 / 9.0
    wc = 8.0 / 9.0
    xi_vals = [-ce, cc, ce, -ce, cc, ce, -ce, cc, ce]
    et_vals = [-ce, -ce, -ce, cc, cc, cc, ce, ce, ce]
    wi_vals = [we, wc, we, we, wc, we, we, wc, we]
    wj_vals = [we, we, we, wc, wc, wc, we, we, we]
    ip_xi = np.array(xi_vals)
    ip_et = np.array(et_vals)
    ip_wi = np.array(wi_vals)
    ip_wj = np.array(wj_vals)

    return connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj


def _shape_deriv_quad8(xi: float, et: float):
    """四角形2次要素の形状関数偏微分 ∂N/∂ξ, ∂N/∂η

    節点順: コーナー4点 (1-4) + 辺中点4点 (5-8)
    1:(-1,-1), 2:(+1,-1), 3:(+1,+1), 4:(-1,+1)
    5:(0,-1),  6:(+1,0),  7:(0,+1),  8:(-1,0)
    """
    dN_dxi = np.array([
        (-(1-et)*(-1-xi-et) - (1-xi)*(1-et)) / 4,
        ( (1-et)*(-1+xi-et) + (1+xi)*(1-et)) / 4,
        ( (1+et)*(-1+xi+et) + (1+xi)*(1+et)) / 4,
        (-(1+et)*(-1-xi+et) - (1-xi)*(1+et)) / 4,
        (-2*xi*(1-et)) / 2,
        ( (1-et*et)) / 2,
        (-2*xi*(1+et)) / 2,
        (-(1-et*et)) / 2,
    ])
    dN_det = np.array([
        (-(1-xi)*(-1-xi-et) - (1-xi)*(1-et)) / 4,
        (-(1+xi)*(-1+xi-et) - (1+xi)*(1-et)) / 4,
        ( (1+xi)*(-1+xi+et) + (1+xi)*(1+et)) / 4,
        ( (1-xi)*(-1-xi+et) + (1-xi)*(1+et)) / 4,
        (-(1-xi*xi)) / 2,
        (-2*et*(1+xi)) / 2,
        ( (1-xi*xi)) / 2,
        (-2*et*(1-xi)) / 2,
    ])
    return dN_dxi, dN_det


def make_B(connectivity, x, y, ip_xi, ip_et):
    """全要素のBマトリックスとdetJを計算 - VBA: make_B()

    Returns:
        B_mat: (ELEMENTS, 9, 3, 16)
        detJ:  (ELEMENTS, 9)
    """
    B_mat = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS, DOF_QUAD8))
    detJ  = np.zeros((ELEMENTS, INTEGRAL_POINTS))

    for e in range(ELEMENTS):
        xn = x[connectivity[e]]  # (8,)
        yn = y[connectivity[e]]  # (8,)

        for ip in range(INTEGRAL_POINTS):
            xi = ip_xi[ip]
            et = ip_et[ip]

            dN_dxi, dN_det = _shape_deriv_quad8(xi, et)

            dX_dxi = dN_dxi @ xn
            dY_dxi = dN_dxi @ yn
            dX_det = dN_det @ xn
            dY_det = dN_det @ yn

            detJ[e, ip] = dX_dxi * dY_det - dY_dxi * dX_det

            inv_detJ = 1.0 / detJ[e, ip]
            dN_dx = (dN_dxi * dY_det - dN_det * dY_dxi) * inv_detJ
            dN_dy = (-dN_dxi * dX_det + dN_det * dX_dxi) * inv_detJ

            Be = np.zeros((COMPONENTS, DOF_QUAD8))
            for i in range(NODES_QUAD8):
                Be[0, i * 2]     = dN_dx[i]
                Be[1, i * 2 + 1] = dN_dy[i]
                Be[2, i * 2]     = dN_dy[i]
                Be[2, i * 2 + 1] = dN_dx[i]

            B_mat[e, ip] = Be

    return B_mat, detJ


def make_Ke(B_mat, detJ, D, ip_wi, ip_wj):
    """要素剛性マトリックスを計算 - VBA: make_Ke()

    Returns:
        Ke: (ELEMENTS, 16, 16)
    """
    Ke = np.zeros((ELEMENTS, DOF_QUAD8, DOF_QUAD8))
    for e in range(ELEMENTS):
        for ip in range(INTEGRAL_POINTS):
            Be = B_mat[e, ip]  # (3, 16)
            w = detJ[e, ip] * ip_wi[ip] * ip_wj[ip] * THICKNESS
            Ke[e] += Be.T @ D @ Be * w
    return Ke


def cantilever_quad8():
    """メインプロシージャ - VBA: simple_fem_quad8()

    Returns:
        U:         変位ベクトル (298,)
        Fr:        反力ベクトル (298,)
        strain_ip: (40, 9, 3)
        stress_ip: (40, 9, 3)
    """
    connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    B_mat, detJ = make_B(connectivity, x, y, ip_xi, ip_et)
    Ke = make_Ke(B_mat, detJ, D, ip_wi, ip_wj)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_QUAD8)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)

    Fr = K @ U

    strain_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))
    stress_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))

    for e in range(ELEMENTS):
        dof_map = np.array([
            connectivity[e, n] * 2 + d
            for n in range(NODES_QUAD8) for d in range(DOF_NODE)
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

    parser = argparse.ArgumentParser(description="第3.3章 片持ち梁 四角形2次要素")
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス")
    args = parser.parse_args()

    U, Fr, strain_ip, stress_ip = cantilever_quad8()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
