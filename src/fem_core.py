"""
fem_core.py - 共通FEMソルバー関数
VBA original: all xlsm files

平面ひずみDマトリックス、境界条件処理、連立方程式ソルバー
"""
import numpy as np
from scipy import linalg


def make_D_plane_strain(young: float, poisson: float) -> np.ndarray:
    """平面ひずみDマトリックスを作成 (3x3)

    VBA: make_D() / make_D プロシージャ
    """
    coef = young / (1.0 - 2.0 * poisson) / (1.0 + poisson)
    D = np.zeros((3, 3))
    D[0, 0] = coef * (1.0 - poisson)
    D[0, 1] = coef * poisson
    D[1, 0] = D[0, 1]
    D[1, 1] = coef * (1.0 - poisson)
    D[2, 2] = coef * (1.0 - 2.0 * poisson) / 2.0
    return D


def apply_boundary_conditions(
    K: np.ndarray,
    F: np.ndarray,
    U_prescribed: np.ndarray,
    constrained: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """境界条件処理 - Kc と Fc を返す（K, F を破壊しない）

    VBA: set_boundary_condition() / set_bondary_condition()

    Args:
        K:             全体剛性マトリックス (ndof, ndof)
        F:             荷重ベクトル (ndof,)
        U_prescribed:  規定変位ベクトル (ndof,) - 拘束DOFのみ有効
        constrained:   拘束フラグ (ndof,), True=拘束
    Returns:
        Kc: 修正剛性マトリックス
        Fc: 修正荷重ベクトル
    """
    Kc = K.copy()
    Fc = F.copy()
    ndof = len(constrained)

    for r in range(ndof):
        if constrained[r]:
            u_r = U_prescribed[r]
            # 拘束自由度以外の荷重ベクトルを修正
            mask = np.ones(ndof, dtype=bool)
            mask[r] = False
            Fc[mask] -= Kc[mask, r] * u_r
            # 列・行を0にして対角を1
            Kc[:, r] = 0.0
            Kc[r, :] = 0.0
            Kc[r, r] = 1.0
            Fc[r] = u_r

    return Kc, Fc


def solve_fem(Kc: np.ndarray, Fc: np.ndarray) -> np.ndarray:
    """連立方程式を解く (scipy.linalg.solve 使用)

    VBA: solve() - ガウスの消去法に相当
    """
    return linalg.solve(Kc, Fc)


def gauss_solve(Kc_in: np.ndarray, Fc_in: np.ndarray) -> np.ndarray:
    """VBAと同一のガウスの消去法ソルバー（教育用）

    VBA: solve() - 前進消去 + 後退代入
    """
    n = len(Fc_in)
    K = Kc_in.copy()
    F = Fc_in.copy()

    # 前進消去
    for r in range(n):
        pivot = K[r, r]
        K[r, r:] /= pivot
        F[r] /= pivot
        for rr in range(r + 1, n):
            p = K[rr, r]
            K[rr, r:] -= p * K[r, r:]
            F[rr] -= p * F[r]

    # 後退代入
    U = np.zeros(n)
    for r in range(n - 1, -1, -1):
        U[r] = F[r]
        for c in range(r + 1, n):
            U[r] -= K[r, c] * U[c]

    return U


def assemble_global_K(
    Ke: np.ndarray,
    connectivity: np.ndarray,
    n_dof_total: int,
    nodes_per_elem: int,
    dof_per_node: int = 2,
) -> np.ndarray:
    """全体剛性マトリックスを組み立て

    VBA: make_K() プロシージャ

    Args:
        Ke:             要素剛性マトリックス (n_elem, dof_elem, dof_elem)
        connectivity:   要素内節点番号 0-indexed (n_elem, nodes_per_elem)
        n_dof_total:    全体自由度数
        nodes_per_elem: 要素の節点数
        dof_per_node:   節点自由度数 (デフォルト=2)
    Returns:
        K: 全体剛性マトリックス (n_dof_total, n_dof_total)
    """
    K = np.zeros((n_dof_total, n_dof_total))
    n_elem = connectivity.shape[0]
    dof_elem = nodes_per_elem * dof_per_node

    for e in range(n_elem):
        # 要素DOFから全体DOFへのマッピング
        dof_map = np.zeros(dof_elem, dtype=int)
        for a in range(nodes_per_elem):
            n_global = connectivity[e, a]
            for d in range(dof_per_node):
                dof_map[a * dof_per_node + d] = n_global * dof_per_node + d
        # scipy.add.at相当でアセンブリ
        K[np.ix_(dof_map, dof_map)] += Ke[e]

    return K


def print_result_nodes(
    U: np.ndarray,
    Fr: np.ndarray,
    dof_per_node: int = 2,
    file=None,
) -> None:
    """節点変位と反力を出力"""
    import sys
    out = file if file else sys.stdout
    n_nodes = len(U) // dof_per_node

    print("====={Displacement@Node}=================", file=out)
    for i in range(n_nodes):
        vals = "  ".join(f"{U[i*dof_per_node+d]:.15E}" for d in range(dof_per_node))
        print(f"{i+1:6d}  {vals}", file=out)

    print("\n====={ReactionForce@Node}=================", file=out)
    for i in range(n_nodes):
        vals = "  ".join(f"{Fr[i*dof_per_node+d]:.15E}" for d in range(dof_per_node))
        print(f"{i+1:6d}  {vals}", file=out)


def print_result_ip(
    strain_ip: np.ndarray,
    stress_ip: np.ndarray,
    section_label: str = "IntegralPoint",
    file=None,
) -> None:
    """積分点ひずみ・応力を出力

    Args:
        strain_ip: (n_elem, n_ip, 3) または (n_elem, 3)
        stress_ip: (n_elem, n_ip, 3) または (n_elem, 3)
    """
    import sys
    out = file if file else sys.stdout

    # 2次元 (n_elem, 3) の場合は次元追加
    if strain_ip.ndim == 2:
        strain_ip = strain_ip[:, np.newaxis, :]
        stress_ip = stress_ip[:, np.newaxis, :]

    n_elem, n_ip, n_comp = strain_ip.shape

    print(f"\n====={{Strain@{section_label}}}=================", file=out)
    for e in range(n_elem):
        for ip in range(n_ip):
            vals = "  ".join(f"{strain_ip[e, ip, k]:.15E}" for k in range(n_comp))
            print(f"{e+1:6d} {ip+1:3d}  {vals}", file=out)

    print(f"\n====={{Stress@{section_label}}}=================", file=out)
    for e in range(n_elem):
        for ip in range(n_ip):
            vals = "  ".join(f"{stress_ip[e, ip, k]:.15E}" for k in range(n_comp))
            print(f"{e+1:6d} {ip+1:3d}  {vals}", file=out)
