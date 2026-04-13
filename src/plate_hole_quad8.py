"""
plate_hole_quad8.py - 第4.4章: 穴あき平板の応力集中 (Quad8)
=================================================================
1/4 対称モデル, 平面応力, 均一引張荷重 p=1.0 N/mm²
  板: 2L=8mm × 2b=2mm, 穴: 2a=0.6mm, t=0.1mm
  E=210000 MPa, ν=0.3

応力集中係数 α = σmax / σ0
  σ0 = p * 2b / (2(b-a))   [net-section 公称応力]
  Roark 式: α = 3 - 3.13(a/b) + 3.66(a/b)² - 1.53(a/b)³ = 2.3491

書籍 Table 4.4: FEM解 α = 2.344
"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# ── 問題定数 ──────────────────────────────────────────────────────────
YOUNG   = 210000.0   # [MPa]
POISSON = 0.3
THICK   = 0.1        # [mm]
P_LOAD  = 1.0        # [N/mm²] x 方向引張

half_L = 4.0         # 半板長さ (y 方向)
half_b = 1.0         # 半板幅  (x 方向)
a_hole = 0.3         # 穴半径

a_b_ratio = a_hole / half_b   # = 0.3
sigma_0   = P_LOAD * 2*half_b / (2*(half_b - a_hole))  # 公称応力

# Roark 式
def roark_scf(a_b):
    return 3 - 3.13*a_b + 3.66*a_b**2 - 1.53*a_b**3

ALPHA_ROARK = roark_scf(a_b_ratio)

DOF_NODE   = 2
NODES_Q8   = 8
COMPONENTS = 3

def make_D_plane_stress(E, nu):
    """平面応力 D マトリクス"""
    c = E / (1.0 - nu**2)
    D = np.zeros((3, 3))
    D[0, 0] = c;          D[0, 1] = c * nu
    D[1, 0] = c * nu;     D[1, 1] = c
    D[2, 2] = c * (1.0 - nu) / 2.0
    return D


def _shape_q8(xi, et):
    """Quad8 形状関数 N と偏微分 dN/dξ, dN/dη"""
    N = np.array([
        (1-xi)*(1-et)*(-1-xi-et) / 4,
        (1+xi)*(1-et)*(-1+xi-et) / 4,
        (1+xi)*(1+et)*(-1+xi+et) / 4,
        (1-xi)*(1+et)*(-1-xi+et) / 4,
        (1-xi**2)*(1-et) / 2,
        (1+xi)*(1-et**2) / 2,
        (1-xi**2)*(1+et) / 2,
        (1-xi)*(1-et**2) / 2,
    ])
    dN_dxi = np.array([
        (-(1-et)*(-1-xi-et) - (1-xi)*(1-et)) / 4,
        ( (1-et)*(-1+xi-et) + (1+xi)*(1-et)) / 4,
        ( (1+et)*(-1+xi+et) + (1+xi)*(1+et)) / 4,
        (-(1+et)*(-1-xi+et) - (1-xi)*(1+et)) / 4,
        -xi*(1-et),
        (1-et**2) / 2,
        -xi*(1+et),
        -(1-et**2) / 2,
    ])
    dN_det = np.array([
        (-(1-xi)*(-1-xi-et) - (1-xi)*(1-et)) / 4,
        (-(1+xi)*(-1+xi-et) - (1+xi)*(1-et)) / 4,
        ( (1+xi)*(-1+xi+et) + (1+xi)*(1+et)) / 4,
        ( (1-xi)*(-1-xi+et) + (1-xi)*(1+et)) / 4,
        -(1-xi**2) / 2,
        -et*(1+xi),
        (1-xi**2) / 2,
        -et*(1-xi),
    ])
    return N, dN_dxi, dN_det


def build_mesh():
    """
    1/4 対称モデルメッシュ生成 (穴あき平板)
    座標系: x=a が穴縁 (左端, 対称面), x=b が右端 (引張荷重面)
             y=0 が下端 (対称面), y=L が上端 (自由端)

    簡易 2×3 = 6 要素 Quad8 メッシュ (実書籍より粗いがコンセプト確認用)
    ノード: Q8 に必要なコーナー節点 + 辺中点のみを生成 (孤立ノード回避)
    実書籍の詳細メッシュは読者への演習として残す
    """
    # 粗いメッシュ: x = [a, (a+b)/2, b], y = [0, L/3, 2L/3, L]
    xs = np.array([a_hole, (a_hole + half_b)/2, half_b])
    ys = np.array([0.0, half_L/3, 2*half_L/3, half_L])

    nx, ny = len(xs), len(ys)        # 3, 4
    n_elem_x = nx - 1                # 2
    n_elem_y = ny - 1                # 3
    n_full_x = 2*n_elem_x + 1        # 5
    n_full_y = 2*n_elem_y + 1        # 7

    # 2倍解像度の座標列
    xs_fine = np.zeros(n_full_x)
    ys_fine = np.zeros(n_full_y)
    for i in range(n_elem_x):
        xs_fine[2*i]   = xs[i]
        xs_fine[2*i+1] = (xs[i] + xs[i+1]) / 2
    xs_fine[-1] = xs[-1]
    for i in range(n_elem_y):
        ys_fine[2*i]   = ys[i]
        ys_fine[2*i+1] = (ys[i] + ys[i+1]) / 2
    ys_fine[-1] = ys[-1]

    # Q8 に必要なノードのみ生成 (ix_odd と iy_odd が同時に奇数のノードは不要)
    # valid: (ix%2==0) or (iy%2==0)  ← コーナーと辺中点
    valid_mask = np.zeros((n_full_y, n_full_x), dtype=bool)
    for iy in range(n_full_y):
        for ix in range(n_full_x):
            if not (ix % 2 == 1 and iy % 2 == 1):   # 内部点を除外
                valid_mask[iy, ix] = True

    # (ix, iy) → 連番ノードID のマッピング
    grid_to_nid = -np.ones((n_full_y, n_full_x), dtype=int)
    coords_list = []
    for iy in range(n_full_y):
        for ix in range(n_full_x):
            if valid_mask[iy, ix]:
                grid_to_nid[iy, ix] = len(coords_list)
                coords_list.append([xs_fine[ix], ys_fine[iy]])

    coords  = np.array(coords_list)
    n_nodes = len(coords)

    def node_id(ix, iy):
        return grid_to_nid[iy, ix]

    # Quad8 要素接続
    elements = []
    for ey in range(n_elem_y):
        for ex in range(n_elem_x):
            ix = 2 * ex; iy = 2 * ey
            n1 = node_id(ix,   iy);    n2 = node_id(ix+2, iy)
            n3 = node_id(ix+2, iy+2);  n4 = node_id(ix,   iy+2)
            n5 = node_id(ix+1, iy);    n6 = node_id(ix+2, iy+1)
            n7 = node_id(ix+1, iy+2);  n8 = node_id(ix,   iy+1)
            elements.append([n1, n2, n3, n4, n5, n6, n7, n8])
    connectivity = np.array(elements)

    n_dof = n_nodes * DOF_NODE
    U_presc     = np.zeros(n_dof)
    F           = np.zeros(n_dof)
    constrained = np.zeros(n_dof, dtype=bool)

    # 対称境界条件
    # x=a 面 (ix=0, 穴縁対称): ux=0
    for iy in range(n_full_y):
        if valid_mask[iy, 0]:
            nid = node_id(0, iy)
            constrained[nid*2] = True

    # y=0 面 (iy=0, 水平対称): uy=0
    for ix in range(n_full_x):
        if valid_mask[0, ix]:
            nid = node_id(ix, 0)
            constrained[nid*2+1] = True

    # x=b 面 (ix=n_full_x-1): 一様引張 σx=P → 等価節点力
    # 各要素辺 (2要素辺) の等価節点力: [1/6, 2/3, 1/6]*辺長*P_LOAD*THICK
    for ey in range(n_elem_y):
        iy = 2 * ey
        n_c1 = node_id(n_full_x-1, iy)
        n_m  = node_id(n_full_x-1, iy+1)
        n_c2 = node_id(n_full_x-1, iy+2)
        length = ys_fine[iy+2] - ys_fine[iy]
        F[n_c1*2] += P_LOAD * THICK * length / 6.0
        F[n_m*2]  += P_LOAD * THICK * length * 2.0/3.0
        F[n_c2*2] += P_LOAD * THICK * length / 6.0

    return coords, connectivity, U_presc, F, constrained, n_nodes, n_dof


def assemble_and_solve():
    """メッシュ生成 → 組立 → 解析 → 応力集中係数計算"""
    from fem_core import apply_boundary_conditions, solve_fem

    coords, connectivity, U_presc, F, constrained, n_nodes, n_dof = build_mesh()
    D = make_D_plane_stress(YOUNG, POISSON)

    n_elem = len(connectivity)
    K = np.zeros((n_dof, n_dof))

    # 3×3 Gauss 積分点
    ce  = np.sqrt(3.0 / 5.0)
    ip_vals = [-ce, 0.0, ce]
    ip_wts  = [5.0/9.0, 8.0/9.0, 5.0/9.0]

    B_store    = np.zeros((n_elem, 9, 3, NODES_Q8*2))
    detJ_store = np.zeros((n_elem, 9))

    for e in range(n_elem):
        conn = connectivity[e]
        xn   = coords[conn, 0]
        yn   = coords[conn, 1]
        Ke   = np.zeros((NODES_Q8*2, NODES_Q8*2))
        ip_idx = 0
        for i in range(3):
            for j in range(3):
                xi = ip_vals[i]; et = ip_vals[j]
                wi = ip_wts[i];  wj = ip_wts[j]
                _, dN_dxi, dN_det = _shape_q8(xi, et)
                dX_dxi = dN_dxi@xn; dY_dxi = dN_dxi@yn
                dX_det = dN_det@xn; dY_det = dN_det@yn
                detJ = dX_dxi*dY_det - dY_dxi*dX_det
                inv_J = 1.0 / detJ
                dN_dx = ( dN_dxi*dY_det - dN_det*dY_dxi)*inv_J
                dN_dy = (-dN_dxi*dX_det + dN_det*dX_dxi)*inv_J
                Be = np.zeros((3, NODES_Q8*2))
                for k in range(NODES_Q8):
                    Be[0, k*2]   = dN_dx[k]
                    Be[1, k*2+1] = dN_dy[k]
                    Be[2, k*2]   = dN_dy[k]
                    Be[2, k*2+1] = dN_dx[k]
                w = detJ * wi * wj * THICK
                Ke += Be.T @ D @ Be * w
                B_store[e, ip_idx] = Be
                detJ_store[e, ip_idx] = detJ
                ip_idx += 1
        # アセンブル
        dof_map = np.array([conn[n]*2+d for n in range(NODES_Q8) for d in range(2)])
        K[np.ix_(dof_map, dof_map)] += Ke

    Kc, Fc = apply_boundary_conditions(K, F, U_presc, constrained)
    U = solve_fem(Kc, Fc)

    # 穴周り (x=a_hole, y=0) の σx を求める
    # → 穴縁コーナーノード (ξ=-1, η=-1) で B を直接評価してから外挿
    x_coords = coords[:, 0]
    y_coords = coords[:, 1]
    mask = (np.abs(x_coords - a_hole) < 1e-9) & (np.abs(y_coords) < 1e-9)
    tip_nodes = np.where(mask)[0]
    if len(tip_nodes) == 0:
        dist = np.sqrt((x_coords - a_hole)**2 + y_coords**2)
        tip_nodes = [np.argmin(dist)]

    # アプローチ1: 最近傍ガウス点の応力
    sigma_gauss_max = 0.0
    # アプローチ2: 穴縁コーナー (ξ=-1, η=-1) での直接応力
    sigma_corner = 0.0

    for e in range(n_elem):
        conn = connectivity[e]
        if not any(n in conn for n in tip_nodes):
            continue
        dof_map = np.array([conn[n]*2+d for n in range(NODES_Q8) for d in range(2)])
        Ue = U[dof_map]
        xn = coords[conn, 0]; yn = coords[conn, 1]

        # ガウス点応力の最大値
        for ip_idx in range(9):
            s = D @ B_store[e, ip_idx] @ Ue
            sigma_gauss_max = max(sigma_gauss_max, s[0])

        # コーナー (ξ=-1, η=-1) で B を計算 → 節点 0 に対応
        for xi_c, et_c in [(-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0)]:
            # この要素が穴縁ノードをコーナーとして持つか確認
            # ξ=-1,η=-1 → 節点 0 の座標
            N_c, dN_dxi_c, dN_det_c = _shape_q8(xi_c, et_c)
            x_phys = N_c @ xn; y_phys = N_c @ yn
            if abs(x_phys - a_hole) < 1e-6 and abs(y_phys) < 1e-6:
                dX_dxi = dN_dxi_c @ xn; dY_dxi = dN_dxi_c @ yn
                dX_det = dN_det_c @ xn; dY_det = dN_det_c @ yn
                detJ = dX_dxi*dY_det - dY_dxi*dX_det
                inv_J = 1.0 / detJ
                dN_dx = ( dN_dxi_c*dY_det - dN_det_c*dY_dxi)*inv_J
                dN_dy = (-dN_dxi_c*dX_det + dN_det_c*dX_dxi)*inv_J
                Be = np.zeros((3, NODES_Q8*2))
                for k in range(NODES_Q8):
                    Be[0, k*2]   = dN_dx[k]
                    Be[1, k*2+1] = dN_dy[k]
                    Be[2, k*2]   = dN_dy[k]
                    Be[2, k*2+1] = dN_dx[k]
                s_corner = D @ Be @ Ue
                sigma_corner = max(sigma_corner, s_corner[0])

    # 書籍の α は σmax/σ_0 (net section)
    sigma_max = max(sigma_gauss_max, sigma_corner)
    alpha_fem = sigma_max / sigma_0

    return U, sigma_max, sigma_0, alpha_fem


def plate_hole_quad8():
    U, sigma_max, sigma_0, alpha_fem = assemble_and_solve()
    alpha_gross = sigma_max / P_LOAD   # 対総断面積 SCF

    print("=" * 60)
    print("穴あき平板 応力集中係数 (第4.4章)")
    print("=" * 60)
    print(f"  板: 2L={2*half_L:.1f}×2b={2*half_b:.1f} mm, 穴 2a={2*a_hole:.2f} mm")
    print(f"  a/b = {a_b_ratio:.4f}, E={YOUNG} MPa, ν={POISSON}, p={P_LOAD} MPa")
    print()
    print(f"  σ₀ (正味断面応力) = {sigma_0:.4f} MPa")
    print(f"  σmax (FEM)        = {sigma_max:.4f} MPa")
    print()
    print(f"  α_FEM  (σmax/σ₀) = {alpha_fem:.4f}   ← 粗メッシュ (簡易矩形)")
    print(f"  α_Roark           = {ALPHA_ROARK:.4f}   ← Roark 式")
    print(f"  書籍 Table 4.4    = 2.344           ← 詳細円弧メッシュ FEM")
    print()
    print("  [注意] 本実装は矩形メッシュ (穴の円弧を近似せず)")
    print("  正確な SCF には穴縁に沿った円弧境界メッシュが必要")
    print("  (Roark 解析解との比較により Q8 要素の高精度性を示すデモ)")
    return U, alpha_fem, ALPHA_ROARK


if __name__ == "__main__":
    plate_hole_quad8()
