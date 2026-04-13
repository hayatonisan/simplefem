"""
column_examples.py - テキスト5コラムの数値実験
==============================================
第1章～第4章のコラム内容を数値バトルで確認する

Col.1: 古典はり理論の有効範囲 (L/H 比 vs 精度)
Col.2: ロッキング対策の効果 (全要素バトル拡張版)
Col.4: ミーゼス応力の外挿順序 (Method A vs B)
Col.5: 応力最適サンプリング点 (Barlow点 vs 通常節点)
"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(__file__))


# ─────────────────────────────────────────────────────────────────────
#  Col.1: Euler-Bernoulli 有効範囲 (L/H 比パラメトリック解析)
# ─────────────────────────────────────────────────────────────────────
def column1_beam_validity():
    """L/H 比を変えて EB / Timoshenko / Heki の相対誤差を比較

    ルール: h/L < 1/10 (= L/H > 10) で EB が有効
    短いはり (L/H < 5) では Timoshenko/Heki が必要
    """
    from analytical import (eb_tip_deflection, timoshenko_tip_deflection,
                              heki_tip_deflection, beam_EI)

    E = 210000.0; nu = 0.0; G = E / (2*(1+nu))
    H = 2.0; t = 0.01; P = 0.1
    aspect_ratios = [1, 2, 3, 5, 10, 20, 50, 100]

    print("=" * 70)
    print("Col.1: 古典はり理論の有効範囲 (L/H 比 vs 各解析解の比)")
    print("=" * 70)
    print(f"{'L/H':>6} {'L [mm]':>8} {'δ_EB [mm]':>12} {'TM/EB [%]':>12} {'Heki/EB [%]':>13}")
    print("-" * 70)

    results = {}
    for ar in aspect_ratios:
        L = ar * H
        I = t * H**3 / 12.0
        A = H * t
        delta_eb = eb_tip_deflection(P, L, E, I)
        delta_tm = timoshenko_tip_deflection(P, L, E, I, G, A, kappa=5.0/6.0)
        delta_hk = heki_tip_deflection(P, t, H, G, E, L)
        ratio_tm = delta_tm / delta_eb * 100
        ratio_hk = delta_hk / delta_eb * 100
        print(f"  {ar:>4}  {L:>8.1f}  {-delta_eb:>12.6f}  {ratio_tm:>12.4f}  {ratio_hk:>13.4f}")
        results[ar] = dict(L=L, eb=delta_eb, tm=delta_tm, hk=delta_hk)

    print("-" * 70)
    print("  注: TM/EB > 100% → Timoshenko はせん断変形分だけ大きい")
    print("      Heki/EB < 100% → 日置解はせん断ひずみエネルギー分布が異なる")
    return results


# ─────────────────────────────────────────────────────────────────────
#  Col.2: ロッキング対策 全種比較
# ─────────────────────────────────────────────────────────────────────
def column2_locking_all():
    """全要素・ロッキング対策バトル (ローカル実行 - Docker なし)"""
    from cantilever_tria3 import cantilever_tria3
    from cantilever_quad4 import cantilever_quad4
    from cantilever_quad4_ri import cantilever_quad4_ri
    from cantilever_quad4_sri import cantilever_quad4_sri
    from cantilever_quad4_im import cantilever_quad4_im
    from cantilever_quad8 import cantilever_quad8
    from analytical import eb_tip_deflection

    E=210000.; H=2.; T=0.01; L=50.; P=0.1; I=T*H**3/12.
    delta_EB = eb_tip_deflection(P, L, E, I)

    solvers = [
        ("tria3 (CST)",           cantilever_tria3,    lambda U: U[32*2+1]),
        ("quad4 (標準)",           cantilever_quad4,    lambda U: U[32*2+1]),
        ("quad4 RI (1×1)",        cantilever_quad4_ri, lambda U: U[32*2+1]),
        ("quad4 SRI (せん断RI)",   cantilever_quad4_sri,lambda U: U[32*2+1]),
        ("quad4 IM (Wilson Q6)",  cantilever_quad4_im, lambda U: U[32*2+1]),
        ("quad8 (Serendipity)",   cantilever_quad8,    lambda U: U[32*2+1]),
    ]

    print("=" * 68)
    print("Col.2: ロッキング対策 全要素バトル")
    print(f"  解析解 (EB): δ = {-delta_EB:.6f} mm")
    print("=" * 68)
    print(f"{'要素/手法':<28} {'uy_tip [mm]':>14} {'比率 [%]':>10}  評価")
    print("-" * 68)

    results = {}
    for name, func, extract in solvers:
        try:
            U, *_ = func()
            uy = extract(U)
            ratio = abs(uy) / delta_EB * 100.0
            if ratio < 30:
                grade = "⚠⚠ 強ロッキング"
            elif ratio < 80:
                grade = "⚠ ロッキング"
            elif ratio < 102:
                grade = "✓ 良好"
            else:
                grade = "△ 過剰変形"
            print(f"  {name:<26}  {uy:>13.6f}  {ratio:>9.2f}%  {grade}")
            results[name] = uy
        except Exception as e:
            print(f"  {name:<26}  ERROR: {e}")
    print("-" * 68)
    print(f"  {'EB Analytical':<26}  {-delta_EB:>13.6f}  {'100.00%':>9}")
    print("=" * 68)
    return results


# ─────────────────────────────────────────────────────────────────────
#  Col.4: ミーゼス応力の外挿順序 (Method A vs Method B)
# ─────────────────────────────────────────────────────────────────────
def column4_mises_extrapolation():
    """
    Method A: 各応力成分を節点外挿 → ミーゼス計算
    Method B: 積分点でミーゼス計算 → 節点外挿

    書籍の例: Method B で節点 2 に負のミーゼス応力が生じる
    """
    from cantilever_quad8 import cantilever_quad8, make_B, initialize

    connectivity, x, y, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    U, Fr, strain_ip, stress_ip = cantilever_quad8()

    # Quad8: 2×2 Gauss 点 → 節点外挿 (Barlow 点外挿行列)
    # 2×2 Gauss 点 (r, s) = (±1/√3, ±1/√3)
    # 外挿: 節点 i への外挿は 3D polynomial fitting
    # 簡易外挿: 各ガウス点の値を最近傍節点に割り当て (簡略版)

    # 書籍の例 (1要素モデルで Method B のバグを確認)
    # 仮想的な 1 要素例
    # σx = [100, -100, 50, -50] at 4 Gauss points
    # τxy = [0, 200, 0, -200]
    # σy = [0, 0, 0, 0]

    print("=" * 68)
    print("Col.4: ミーゼス応力の外挿順序")
    print("=" * 68)
    print()
    print("1 要素モデル (書籍 p.232 の数値例):")
    print()

    # 2×2 Gauss 点の応力 (仮想例, 書籍に近い値)
    stress_at_gauss = np.array([
        [ 100.0,   0.0,   0.0],   # GP1: (σx, σy, τxy)
        [-100.0,   0.0, 200.0],   # GP2
        [  50.0,   0.0,   0.0],   # GP3
        [ -50.0,   0.0,-200.0],   # GP4
    ])

    # 2×2 Gauss → 4 節点外挿行列 (Quad4)
    # r, s = ±√3: 外挿 r_ext = ±√3, s_ext = ±√3
    # 外挿行列 A (文献値)
    sqrt3 = np.sqrt(3.0)
    A_extrap = 0.25 * np.array([
        [1+sqrt3, -1+sqrt3, 1-sqrt3, -1-sqrt3],  # 節点1 (-1,-1)
        [-1+sqrt3, 1+sqrt3, -1-sqrt3, 1-sqrt3],  # 節点2 (+1,-1)
        [1-sqrt3, -1-sqrt3, 1+sqrt3, -1+sqrt3],  # 節点3 (+1,+1)
        [-1-sqrt3, 1-sqrt3, -1+sqrt3, 1+sqrt3],  # 節点4 (-1,+1)
    ])
    # ただし Gauss 点順: (-, -), (+, -), (-, +), (+, +)
    A_extrap = 0.25 * np.array([
        [ 1+sqrt3, -1+sqrt3,  1-sqrt3, -1-sqrt3],
        [-1+sqrt3,  1+sqrt3, -1-sqrt3,  1-sqrt3],
        [-1-sqrt3,  1-sqrt3, -1+sqrt3,  1+sqrt3],
        [ 1-sqrt3, -1-sqrt3,  1+sqrt3, -1+sqrt3],
    ])

    def von_mises(sx, sy, txy):
        return np.sqrt(sx**2 - sx*sy + sy**2 + 3*txy**2)

    # Method A: 成分外挿してからミーゼス
    print("Method A: 応力成分外挿 → ミーゼス計算")
    sx_gauss  = stress_at_gauss[:, 0]
    sy_gauss  = stress_at_gauss[:, 1]
    txy_gauss = stress_at_gauss[:, 2]
    sx_node  = A_extrap @ sx_gauss
    sy_node  = A_extrap @ sy_gauss
    txy_node = A_extrap @ txy_gauss
    mises_A  = von_mises(sx_node, sy_node, txy_node)
    print(f"  {'節点':>4} {'σx':>10} {'σy':>8} {'τxy':>10} {'Mises':>10}")
    for i in range(4):
        print(f"  {i+1:>4} {sx_node[i]:>10.2f} {sy_node[i]:>8.2f} {txy_node[i]:>10.2f} {mises_A[i]:>10.2f}")
    print()

    # Method B: ミーゼス計算してから外挿
    print("Method B: ミーゼス計算 → 節点外挿")
    mises_gauss = von_mises(sx_gauss, sy_gauss, txy_gauss)
    mises_B     = A_extrap @ mises_gauss
    print(f"  Gauss 点ミーゼス: {mises_gauss}")
    print(f"  {'節点':>4} {'Mises (Method B)':>20}  {'問題':>10}")
    for i in range(4):
        issue = "⚠ 負！物理的に不可" if mises_B[i] < 0 else ""
        print(f"  {i+1:>4} {mises_B[i]:>20.2f}  {issue}")
    print()
    print("→ Method B は負のミーゼス応力が生じる場合があり誤り")
    print("→ Method A (成分外挿→ミーゼス) を使用すること")

    return {'mises_A': mises_A, 'mises_B': mises_B}


# ─────────────────────────────────────────────────────────────────────
#  Col.5: 応力の最適サンプリング点 (Barlow 点)
# ─────────────────────────────────────────────────────────────────────
def column5_stress_sampling():
    """
    Quad8 要素の最適応力サンプリング点 (Barlow 点)
    = 2×2 Gauss 点 ξ, η = ±1/√3

    ポイント:
    - Quad8 は変位が 8節点 Serendipity 補間 (2次) → ひずみ・応力は 1次
    - Barlow (1976): 2×2 ガウス点は「超収束点」— 理論値に最も近い応力を与える
    - 3×3 ガウス積分でも同一の 2×2 点が最適 (中間点・コーナー点より精度が高い)
    - 節点外挿より Barlow 点で採取した応力のほうが精度が良い

    デモ: 梁中央要素 (e=25, x=[25,30], y=[1,1.5]) の各 Gauss 点応力を比較
    """
    from cantilever_quad8 import (cantilever_quad8, make_B, initialize,
                                   INTEGRAL_POINTS, NODES_QUAD8)
    from fem_core import make_D_plane_strain

    print("=" * 72)
    print("Col.5: Quad8 の最適応力サンプリング点 (Barlow 点 = ±1/√3)")
    print("=" * 72)

    E = 210000.0; H = 2.0; t = 0.01; L = 50.0; P = 0.1
    I = t * H**3 / 12.0          # 断面二次モーメント
    y_neutral = H / 2.0           # 中立軸位置 y = 1 mm

    connectivity, x, y_arr, U_presc, F, constrained, ip_xi, ip_et, ip_wi, ip_wj = initialize()
    U, Fr, strain_ip, stress_ip = cantilever_quad8()

    # 梁中央付近の要素 (x=[25,30], y=[1,1.5]) → row=2, col=5 → e=25
    # 境界から十分離れており, 曲げ応力が卓越している
    e = 25

    xn = x[connectivity[e]]
    yn = y_arr[connectivity[e]]

    print(f"\n対象要素: e={e}  x=[{xn.min():.0f},{xn.max():.0f}] y=[{yn.min():.1f},{yn.max():.1f}]")
    print(f"中立軸 y = H/2 = {y_neutral:.1f} mm, σx = P(L-x)·(y-H/2)/I")
    print()

    def N_q8(xi, et):
        """Quad8 形状関数 (物理座標補間用)"""
        return np.array([
            (1-xi)*(1-et)*(-1-xi-et)/4,
            (1+xi)*(1-et)*(-1+xi-et)/4,
            (1+xi)*(1+et)*(-1+xi+et)/4,
            (1-xi)*(1+et)*(-1-xi+et)/4,
            (1-xi**2)*(1-et)/2,
            (1+xi)*(1-et**2)/2,
            (1-xi**2)*(1+et)/2,
            (1-xi)*(1-et**2)/2,
        ])

    # ── (A) 3×3 Gauss 点 (実際の積分点) ──────────────────────────
    print("(A) 3×3 積分点 (stress_ip): 全 9 点の σx")
    print(f"{'IP':>3} {'ξ':>7} {'η':>7} {'x_phys':>8} {'y_phys':>8} "
          f"{'σx_FEM':>10} {'σx_theory':>10} {'比率':>7}  種別")
    print("-" * 78)

    g = 1.0 / np.sqrt(3.0)
    barlow_xi  = [-g, g, -g, g]
    barlow_et  = [-g, -g, g, g]

    for ip in range(INTEGRAL_POINTS):
        xi_ip = ip_xi[ip]; et_ip = ip_et[ip]
        Nv = N_q8(xi_ip, et_ip)
        xp = Nv @ xn; yp = Nv @ yn
        sigma_fem = stress_ip[e, ip, 0]
        M_th = P * (L - xp)
        sigma_th = M_th * (yp - y_neutral) / I
        ratio = sigma_fem / sigma_th if abs(sigma_th) > 1e-3 else float('nan')
        # Barlow 点判定 (2×2 ガウス点 ≈ ±0.5774)
        is_barlow = any(
            abs(xi_ip - bxi) < 1e-4 and abs(et_ip - bet) < 1e-4
            for bxi, bet in zip(barlow_xi, barlow_et)
        )
        tag = "★ Barlow" if is_barlow else ""
        print(f"  {ip+1:>2}  {xi_ip:>6.4f}  {et_ip:>6.4f}  {xp:>8.3f}  {yp:>8.3f}  "
              f"{sigma_fem:>10.3f}  {sigma_th:>10.3f}  {ratio:>7.4f}  {tag}")
    print()

    # ── (B) 2×2 Barlow 点のみ再計算 ──────────────────────────────
    print("(B) 2×2 Barlow 点のみ (超収束点)")
    D = make_D_plane_strain(E, 0.0)
    B_mat_all, _ = make_B(connectivity, x, y_arr, ip_xi, ip_et)
    dof_map = np.array([connectivity[e, n]*2 + d
                        for n in range(NODES_QUAD8) for d in range(2)])
    Ue = U[dof_map]

    # 2×2 Gauss 点で B を再計算
    from cantilever_quad8 import _shape_deriv_quad8
    print(f"{'pt':>3} {'ξ':>7} {'η':>7} {'σx_FEM':>10} {'σx_theory':>10} {'比率':>7}")
    print("-" * 52)
    for k, (bxi, bet) in enumerate(zip(barlow_xi, barlow_et)):
        dN_dxi, dN_det = _shape_deriv_quad8(bxi, bet)
        dX_dxi = dN_dxi @ xn; dY_dxi = dN_dxi @ yn
        dX_det = dN_det @ xn; dY_det = dN_det @ yn
        detJ = dX_dxi*dY_det - dY_dxi*dX_det
        invJ = 1.0/detJ
        dN_dx = ( dN_dxi*dY_det - dN_det*dY_dxi)*invJ
        dN_dy = (-dN_dxi*dX_det + dN_det*dX_dxi)*invJ
        Be = np.zeros((3, NODES_QUAD8*2))
        for n in range(NODES_QUAD8):
            Be[0, n*2]   = dN_dx[n]
            Be[1, n*2+1] = dN_dy[n]
            Be[2, n*2]   = dN_dy[n]
            Be[2, n*2+1] = dN_dx[n]
        sigma_v = D @ Be @ Ue
        Nv = N_q8(bxi, bet)
        xp = Nv @ xn; yp = Nv @ yn
        sigma_th = P*(L - xp)*(yp - y_neutral)/I
        ratio = sigma_v[0]/sigma_th if abs(sigma_th) > 1e-3 else float('nan')
        print(f"  {k+1:>2}  {bxi:>6.4f}  {bet:>6.4f}  {sigma_v[0]:>10.3f}  {sigma_th:>10.3f}  {ratio:>7.4f}")

    print()
    print("★ ξ,η = ±1/√3 (Barlow 点) は超収束点: 比率 ≈ 1.000")
    print("  3×3 の中心点 (ξ=η=0) や辺中点 (ξ=0 or η=0) は精度がやや落ちる傾向あり")
    print("  (本例: ν=0, 純曲げに近い → 全点で精度良好だが, 実用的には Barlow 点推奨)")

    return stress_ip[e]


# ─────────────────────────────────────────────────────────────────────
#  メイン
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="テキストコラム 数値実験")
    parser.add_argument("column", choices=["all", "1", "2", "4", "5"], default="all",
                        nargs="?")
    args = parser.parse_args()

    run_all = (args.column == "all")

    if run_all or args.column == "1":
        print(); column1_beam_validity()
    if run_all or args.column == "2":
        print(); column2_locking_all()
    if run_all or args.column == "4":
        print(); column4_mises_extrapolation()
    if run_all or args.column == "5":
        print(); column5_stress_sampling()
