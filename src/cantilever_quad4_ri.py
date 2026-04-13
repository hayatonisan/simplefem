"""
cantilever_quad4_ri.py - 四角形1次要素 低減積分 (Reduced Integration)
==========================================================================
quad4 の 2×2 ガウス積分を 1×1 に変更する最も単純なロッキング対策。
寄生せん断 (parasitic shear) が消えて曲げ精度が向上するが、
アワーグラス (hourglass) 不安定モードが生じる。

参考: Hughes, "The Finite Element Method", §4.5
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
from cantilever_quad4 import (
    initialize,
    ELEMENTS, INTEGRAL_POINTS, NODES_QUAD4, COMPONENTS,
    DOF_NODE, DOF_TOTAL, DOF_QUAD4, YOUNG, POISSON, THICKNESS,
    _shape_deriv_quad4,
)

# 低減積分: 1×1 ガウス点 (中心点, 重み=2)
RI_POINTS = 1
RI_XI = np.array([0.0])
RI_ET = np.array([0.0])
RI_W  = np.array([4.0])   # wxi * wet = 2 * 2 = 4


def make_B_ri(connectivity, x, y):
    """低減積分用 B マトリックス (1×1 Gauss)"""
    B_mat = np.zeros((ELEMENTS, RI_POINTS, COMPONENTS, DOF_QUAD4))
    detJ  = np.zeros((ELEMENTS, RI_POINTS))

    for e in range(ELEMENTS):
        xn = x[connectivity[e]]
        yn = y[connectivity[e]]

        for ip in range(RI_POINTS):
            xi = RI_XI[ip]; et = RI_ET[ip]
            dN_dxi, dN_det = _shape_deriv_quad4(xi, et)

            dX_dxi = dN_dxi @ xn; dY_dxi = dN_dxi @ yn
            dX_det = dN_det @ xn; dY_det = dN_det @ yn
            detJ[e, ip] = dX_dxi * dY_det - dY_dxi * dX_det

            inv_J = 1.0 / detJ[e, ip]
            dN_dx = ( dN_dxi * dY_det - dN_det * dY_dxi) * inv_J
            dN_dy = (-dN_dxi * dX_det + dN_det * dX_dxi) * inv_J

            Be = np.zeros((COMPONENTS, DOF_QUAD4))
            for i in range(NODES_QUAD4):
                Be[0, i*2]   = dN_dx[i]
                Be[1, i*2+1] = dN_dy[i]
                Be[2, i*2]   = dN_dy[i]
                Be[2, i*2+1] = dN_dx[i]
            B_mat[e, ip] = Be

    return B_mat, detJ


def make_Ke_ri(B_mat, detJ, D):
    """低減積分要素剛性"""
    Ke = np.zeros((ELEMENTS, DOF_QUAD4, DOF_QUAD4))
    for e in range(ELEMENTS):
        for ip in range(RI_POINTS):
            Be = B_mat[e, ip]
            w  = detJ[e, ip] * RI_W[ip] * THICKNESS
            Ke[e] += Be.T @ D @ Be * w
    return Ke


def cantilever_quad4_ri():
    """低減積分 quad4 メインプロシージャ"""
    connectivity, x, y, U_presc, F, constrained, _, _, _, _ = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    B_mat, detJ = make_B_ri(connectivity, x, y)
    Ke = make_Ke_ri(B_mat, detJ, D)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_QUAD4)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)
    Fr = K @ U

    # ひずみ・応力は低減積分点で計算
    strain_ip = np.zeros((ELEMENTS, RI_POINTS, COMPONENTS))
    stress_ip = np.zeros((ELEMENTS, RI_POINTS, COMPONENTS))
    for e in range(ELEMENTS):
        dof_map = np.array([
            connectivity[e, n] * 2 + d
            for n in range(NODES_QUAD4) for d in range(DOF_NODE)
        ])
        Ue = U[dof_map]
        for ip in range(RI_POINTS):
            strain_ip[e, ip] = B_mat[e, ip] @ Ue
            stress_ip[e, ip] = D @ strain_ip[e, ip]

    return U, Fr, strain_ip, stress_ip


def print_result(U, Fr, strain_ip, stress_ip, output_file=None):
    out = open(output_file, "w") if output_file else None
    try:
        target = out if out else sys.stdout
        print_result_nodes(U, Fr, file=target)
        print_result_ip(strain_ip, stress_ip, file=target)
    finally:
        if out: out.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="quad4 低減積分")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    U, Fr, strain_ip, stress_ip = cantilever_quad4_ri()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
