"""
cantilever_quad4_im.py - 四角形1次要素 非適合モード (Incompatible Modes)
==========================================================================
Wilson-Taylor の非適合変位モード要素 (Q6/QM6)。
内部自由度 (1-ξ²) と (1-η²) を追加し，スタティック凝縮で消去する。

  u_inc = α1*(1-ξ²) + α3*(1-η²)
  v_inc = α2*(1-ξ²) + α4*(1-η²)

パッチテストを厳密には満たさないが, 実用的には非常に精度が高い。
Tayor 修正版 (QM6) はヤコビアンの中心値を使うことでパッチテストを
近似的に満たす。本実装は修正なし Wilson-Q6。

参考: Wilson et al. (1973), Taylor et al. (1976)
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

INTERNAL_DOF = 4   # 非適合内部 DOF 数 (α1..α4)


def _shape_inc_deriv(xi, et):
    """非適合モードの偏微分 (自然座標系)
    φ1 = 1 - ξ²,  φ2 = 1 - η²
    dφ1/dξ = -2ξ,  dφ1/dη = 0
    dφ2/dξ =   0,  dφ2/dη = -2η
    """
    # [dφ1/dξ, dφ2/dξ]
    dphi_dxi = np.array([-2*xi,    0.0  ])
    # [dφ1/dη, dφ2/dη]
    dphi_det = np.array([  0.0,  -2*et  ])
    return dphi_dxi, dphi_det


def make_Ke_im(connectivity, x, y, D, ip_xi, ip_et, ip_wi, ip_wj):
    """非適合モード要素剛性・スタティック凝縮

    拡張剛性 K_ext (8+4) × (8+4) を組み立て、内部 DOF を凝縮：
      [Kuu  Kua] {U}   {F}
      [Kau  Kaa] {α} = {0}
    → Kuu_cond = Kuu - Kua * Kaa^{-1} * Kau

    Returns:
        Ke:    (ELEMENTS, 8, 8) 凝縮後の要素剛性
    """
    Ke_out = np.zeros((ELEMENTS, DOF_QUAD4, DOF_QUAD4))

    for e in range(ELEMENTS):
        xn = x[connectivity[e]]
        yn = y[connectivity[e]]

        Kuu = np.zeros((DOF_QUAD4,   DOF_QUAD4))
        Kua = np.zeros((DOF_QUAD4,   INTERNAL_DOF))
        Kaa = np.zeros((INTERNAL_DOF, INTERNAL_DOF))

        for ip in range(INTEGRAL_POINTS):
            xi = ip_xi[ip]; et = ip_et[ip]
            wi = ip_wi[ip]; wj = ip_wj[ip]

            # ── 適合部分の B 行列 ──
            dN_dxi, dN_det = _shape_deriv_quad4(xi, et)
            dX_dxi = dN_dxi @ xn; dY_dxi = dN_dxi @ yn
            dX_det = dN_det @ xn; dY_det = dN_det @ yn
            det_J = dX_dxi * dY_det - dY_dxi * dX_det
            inv_J = 1.0 / det_J

            dN_dx = ( dN_dxi * dY_det - dN_det * dY_dxi) * inv_J
            dN_dy = (-dN_dxi * dX_det + dN_det * dX_dxi) * inv_J

            Bu = np.zeros((COMPONENTS, DOF_QUAD4))
            for k in range(NODES_QUAD4):
                Bu[0, k*2]   = dN_dx[k]
                Bu[1, k*2+1] = dN_dy[k]
                Bu[2, k*2]   = dN_dy[k]
                Bu[2, k*2+1] = dN_dx[k]

            # ── 非適合モードの B 行列 (4 × 4) ──
            # α = [α1, α2, α3, α4]
            # u_inc = α1*φ1 + α3*φ2,  v_inc = α2*φ1 + α4*φ2
            # εxx = du/dx = (dφ1/dx)*α1 + (dφ2/dx)*α3
            # εyy = dv/dy = (dφ1/dy)*α2 + (dφ2/dy)*α4
            # γxy = du/dy + dv/dx
            dphi_dxi, dphi_det = _shape_inc_deriv(xi, et)
            # dφk/dx, dφk/dy (2 modes k=0,1)
            dphi_dx = ( dphi_dxi * dY_det - dphi_det * dY_dxi) * inv_J
            dphi_dy = (-dphi_dxi * dX_det + dphi_det * dX_dxi) * inv_J

            # Ba (3 × 4): Ba[:, [0,1,2,3]] = [α1,α2,α3,α4]
            Ba = np.array([
                [dphi_dx[0],        0.0, dphi_dx[1],        0.0],  # εxx
                [       0.0, dphi_dy[0],        0.0, dphi_dy[1]],  # εyy
                [dphi_dy[0], dphi_dx[0], dphi_dy[1], dphi_dx[1]],  # γxy
            ])

            w = det_J * wi * wj * THICKNESS

            Kuu += Bu.T @ D @ Bu * w
            Kua += Bu.T @ D @ Ba * w
            Kaa += Ba.T @ D @ Ba * w

        # スタティック凝縮: K_cond = Kuu - Kua * Kaa^{-1} * Kau
        Kaa_inv = np.linalg.inv(Kaa)
        Ke_out[e] = Kuu - Kua @ Kaa_inv @ Kua.T

    return Ke_out


def cantilever_quad4_im():
    """非適合モード quad4 メインプロシージャ"""
    connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    D = make_D_plane_strain(YOUNG, POISSON)
    Ke = make_Ke_im(connectivity, x, y, D, ip_xi, ip_et, ip_wi, ip_wj)
    K = assemble_global_K(Ke, connectivity, DOF_TOTAL, NODES_QUAD4)
    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)
    Fr = K @ U

    # 応力は通常 2×2 積分点で計算 (適合部のみ使用)
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
    parser = argparse.ArgumentParser(description="quad4 非適合モード (Wilson-Taylor Q6)")
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    U, Fr, strain_ip, stress_ip = cantilever_quad4_im()
    print_result(U, Fr, strain_ip, stress_ip, args.output)
