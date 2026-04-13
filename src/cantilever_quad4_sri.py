"""
cantilever_quad4_sri.py - 四角形1次要素 選択的低減積分 (Selective Reduced Integration)
==========================================================================================
B-bar (B̄) 法とも呼ばれる。
  - 体積変化 (εxx + εyy) → 低減積分 (1×1)
  - せん断 γxy → 低減積分 (1×1)
  - 偏差成分 → 通常積分 (2×2)

Hughes の選択的低減積分法 (SRI):
    K = K_dilatational(1pt) + K_deviatoric(2×2)

または「B̄ 法」として B を修正する実装:
    B̄[vol] = (B̄_vol averaged over element)
    B̄[dev] = B[dev] evaluated at each Gauss point

本実装: 各ガウス点で D マトリクスを体積部・偏差部に分割して
異なる積分点数で積分する方法。

参考: Hughes (1980), "Generalization of selective integration"
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

# 通常積分 (2×2)
g = 1.0 / np.sqrt(3.0)
IP_FULL_XI = np.array([-g,  g, -g,  g])
IP_FULL_ET = np.array([-g, -g,  g,  g])
IP_FULL_W  = np.array([ 1,  1,  1,  1])

# 低減積分 (1×1)
IP_RED_XI = np.array([0.0])
IP_RED_ET = np.array([0.0])
IP_RED_W  = np.array([4.0])


def _B_at(e_nodes_x, e_nodes_y, xi, et):
    """B マトリックスと det_J を返す"""
    dN_dxi, dN_det = _shape_deriv_quad4(xi, et)
    dX_dxi = dN_dxi @ e_nodes_x; dY_dxi = dN_dxi @ e_nodes_y
    dX_det = dN_det @ e_nodes_x; dY_det = dN_det @ e_nodes_y
    det_J  = dX_dxi * dY_det - dY_dxi * dX_det
    inv_J  = 1.0 / det_J
    dN_dx  = ( dN_dxi * dY_det - dN_det * dY_dxi) * inv_J
    dN_dy  = (-dN_dxi * dX_det + dN_det * dX_dxi) * inv_J
    B = np.zeros((COMPONENTS, DOF_QUAD4))
    for k in range(NODES_QUAD4):
        B[0, k*2]   = dN_dx[k]
        B[1, k*2+1] = dN_dy[k]
        B[2, k*2]   = dN_dy[k]
        B[2, k*2+1] = dN_dx[k]
    return B, det_J


def make_Ke_sri(connectivity, x, y, D):
    """選択的低減積分要素剛性

    D_bulk: 体積膨張成分 (低減積分)
    D_dev:  偏差成分 (通常積分)

    平面ひずみで ν=0 の場合: D_bulk ≈ 0 (ほぼ影響なし)
    ν ≠ 0 では体積ロッキング対策に有効
    """
    Ke_out = np.zeros((ELEMENTS, DOF_QUAD4, DOF_QUAD4))

    # D をせん断部と曲げ・膜部に分解 (Hughes 1980 SRI)
    # D_shear: γxy 成分のみ (低減積分 1×1 で積分)
    # D_bend : εxx/εyy 成分 (通常積分 2×2 で積分)
    # → せん断ロッキングが除去される
    D_shear = np.zeros((3, 3))
    D_shear[2, 2] = D[2, 2]
    D_bend  = D.copy()
    D_bend[2, 2] = 0.0

    for e in range(ELEMENTS):
        xn = x[connectivity[e]]
        yn = y[connectivity[e]]

        Ke = np.zeros((DOF_QUAD4, DOF_QUAD4))

        # せん断部: 低減積分 (1×1)
        for ip in range(len(IP_RED_XI)):
            B, det_J = _B_at(xn, yn, IP_RED_XI[ip], IP_RED_ET[ip])
            w = det_J * IP_RED_W[ip] * THICKNESS
            Ke += B.T @ D_shear @ B * w

        # 曲げ・膜部: 通常積分 (2×2)
        for ip in range(len(IP_FULL_XI)):
            B, det_J = _B_at(xn, yn, IP_FULL_XI[ip], IP_FULL_ET[ip])
            w = det_J * IP_FULL_W[ip] * THICKNESS
            Ke += B.T @ D_bend @ B * w

        Ke_out[e] = Ke

    return Ke_out


def cantilever_quad4_sri():
    connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    Ke = make_Ke_sri(connectivity, x, y, D)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_QUAD4)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)
    Fr = K @ U

    from cantilever_quad4 import make_B as make_B_std
    B_mat, detJ = make_B_std(connectivity, x, y, ip_xi, ip_et)
    strain_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))
    stress_ip = np.zeros((ELEMENTS, INTEGRAL_POINTS, COMPONENTS))
    for e in range(ELEMENTS):
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
    out = open(output_file, "w") if output_file else None
    try:
        target = out if out else sys.stdout
        print_result_nodes(U, Fr, file=target)
        print_result_ip(strain_ip, stress_ip, file=target)
    finally:
        if out: out.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="quad4 選択的低減積分 (SRI/B-bar)")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    U, Fr, strain_ip, stress_ip = cantilever_quad4_sri()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
