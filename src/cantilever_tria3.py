"""
cantilever_tria3.py - 第3.3章: 片持ち梁 三角形1次要素
平面ひずみ / 55節点 / 80要素 / 積分点1点

VBA原本: 3.3_片持ち梁_三角形1次要素_三角形1次.vb
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
ELEMENTS = 80
INTEGRAL_POINTS = 1
NODES_TRIA3 = 3
COMPONENTS = 3
DOF_NODE = 2
DOF_TOTAL = NODES * DOF_NODE        # 110
DOF_TRIA3 = NODES_TRIA3 * DOF_NODE  # 6


def initialize():
    """配列を初期化 - VBA: initialize()"""
    # 要素内節点番号 (0-indexed: VBA値 - 1)
    conn_vba = [
        (1,2,13),(13,12,1),(2,3,14),(14,13,2),(3,4,15),(15,14,3),
        (4,5,16),(16,15,4),(5,6,17),(17,16,5),(6,7,18),(18,17,6),
        (7,8,19),(19,18,7),(8,9,20),(20,19,8),(9,10,21),(21,20,9),
        (10,11,22),(22,21,10),(12,13,24),(24,23,12),(13,14,25),(25,24,13),
        (14,15,26),(26,25,14),(15,16,27),(27,26,15),(16,17,28),(28,27,16),
        (17,18,29),(29,28,17),(18,19,30),(30,29,18),(19,20,31),(31,30,19),
        (20,21,32),(32,31,20),(21,22,33),(33,32,21),(23,24,35),(35,34,23),
        (24,25,36),(36,35,24),(25,26,37),(37,36,25),(26,27,38),(38,37,26),
        (27,28,39),(39,38,27),(28,29,40),(40,39,28),(29,30,41),(41,40,29),
        (30,31,42),(42,41,30),(31,32,43),(43,42,31),(32,33,44),(44,43,32),
        (34,35,46),(46,45,34),(35,36,47),(47,46,35),(36,37,48),(48,47,36),
        (37,38,49),(49,48,37),(38,39,50),(50,49,38),(39,40,51),(51,50,39),
        (40,41,52),(52,51,40),(41,42,53),(53,52,41),(42,43,54),(54,53,42),
        (43,44,55),(55,54,43),
    ]
    connectivity = np.array(conn_vba, dtype=int) - 1  # 0-indexed

    # 節点座標 (VBAのx(i), y(i) を 0-indexed で設定)
    xs = []
    ys = []
    # 行 y=0,0.5,1,1.5,2 それぞれ x=0,5,...,50 (11点)
    for row, yv in enumerate([0.0, 0.5, 1.0, 1.5, 2.0]):
        for xv in [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0]:
            xs.append(xv)
            ys.append(yv)
    x = np.array(xs)
    y = np.array(ys)

    U_presc = np.zeros(DOF_TOTAL)
    F = np.zeros(DOF_TOTAL)
    constrained = np.zeros(DOF_TOTAL, dtype=bool)

    # 変位拘束: VBA FixNode = {1,12,23,34,45} → 0-indexed {0,11,22,33,44}
    fix_nodes_vba = [1, 12, 23, 34, 45]
    for nv in fix_nodes_vba:
        n = nv - 1
        for d in range(DOF_NODE):
            constrained[n * DOF_NODE + d] = True

    # 荷重ベクトル (VBAインデックス → Python インデックス)
    # VBA: F((node-1)*2+2) = val  → Python: F[(node-1)*2+1]
    loads_vba = {
        11: -0.0125,   # node 11
        22: -0.025,    # node 22
        33: -0.025,
        44: -0.025,
        55: -0.0125,
    }
    for nv, fval in loads_vba.items():
        F[(nv - 1) * DOF_NODE + 1] = fval  # y方向

    return connectivity, x, y, U_presc, F, constrained


def make_B(connectivity, x, y):
    """Bマトリックスと面積を計算 (積分点1点 = 要素全体) - VBA: make_B()

    Returns:
        B_mat:        (ELEMENTS, 1, 3, 6)
        area_element: (ELEMENTS,)
    """
    B_mat = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS, DOF_TRIA3))
    area_element = np.zeros(ELEMENTS)

    for e in range(ELEMENTS):
        n1, n2, n3 = connectivity[e]
        x1, y1 = x[n1], y[n1]
        x2, y2 = x[n2], y[n2]
        x3, y3 = x[n3], y[n3]

        area_element[e] = (
            x1 * y2 - x1 * y3 + x2 * y3 - x2 * y1 + x3 * y1 - x3 * y2
        ) / 2.0

        coef = 1.0 / (2.0 * area_element[e])
        ip = 0

        B_mat[e, ip, 0, 0] = coef * (y2 - y3)
        B_mat[e, ip, 0, 2] = coef * (y3 - y1)
        B_mat[e, ip, 0, 4] = coef * (y1 - y2)
        B_mat[e, ip, 1, 1] = coef * (x3 - x2)
        B_mat[e, ip, 1, 3] = coef * (x1 - x3)
        B_mat[e, ip, 1, 5] = coef * (x2 - x1)
        B_mat[e, ip, 2, 0] = B_mat[e, ip, 1, 1]
        B_mat[e, ip, 2, 1] = B_mat[e, ip, 0, 0]
        B_mat[e, ip, 2, 2] = B_mat[e, ip, 1, 3]
        B_mat[e, ip, 2, 3] = B_mat[e, ip, 0, 2]
        B_mat[e, ip, 2, 4] = B_mat[e, ip, 1, 5]
        B_mat[e, ip, 2, 5] = B_mat[e, ip, 0, 4]

    return B_mat, area_element


def make_Ke(B_mat, area_element, D):
    """要素剛性マトリックスを計算 - VBA: make_Ke()

    Ke = B^T * D * B * area * t
    Returns:
        Ke: (ELEMENTS, 6, 6)
    """
    Ke = np.zeros((ELEMENTS, DOF_TRIA3, DOF_TRIA3))
    for e in range(ELEMENTS):
        Be = B_mat[e, 0]  # (3, 6)
        Ke[e] = Be.T @ D @ Be * area_element[e] * THICKNESS
    return Ke


def cantilever_tria3():
    """メインプロシージャ - VBA: simple_fem_tria3()

    Returns:
        U:          変位ベクトル (110,)
        Fr:         反力ベクトル (110,)
        strain_ip:  積分点ひずみ (80, 1, 3)
        stress_ip:  積分点応力 (80, 1, 3)
    """
    connectivity, x, y, U_presc, F, constrained = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    B_mat, area_element = make_B(connectivity, x, y)
    Ke = make_Ke(B_mat, area_element, D)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_TRIA3)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)

    Fr = K @ U

    # 積分点ひずみ・応力
    strain_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))
    stress_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))

    for e in range(ELEMENTS):
        for ip in range(INTEGRAL_POINTS):
            Ue = np.zeros(DOF_TRIA3)
            for n in range(NODES_TRIA3):
                Ue[n * 2]     = U[connectivity[e, n] * 2]
                Ue[n * 2 + 1] = U[connectivity[e, n] * 2 + 1]
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

    parser = argparse.ArgumentParser(description="第3.3章 片持ち梁 三角形1次要素")
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス")
    args = parser.parse_args()

    U, Fr, strain_ip, stress_ip = cantilever_tria3()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
