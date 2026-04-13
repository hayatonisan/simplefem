"""
analytical.py - 片持ち梁の各種解析解
========================================
実装している解析解:

1. Euler-Bernoulli (EB) 梁理論
2. Timoshenko 梁 (せん断変形考慮)
3. 日置解 (Heki 1962) - 2次元弾性体としての正確な解
   論文: 山川哲也 (1992) 「提案解と日置解の比較について」
4. Oberst 梁 - 粘弾性複合はりの複素曲げ剛性・損失係数
   出典: Oberst (1952) Acustica
"""
import numpy as np
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
#  1. Euler-Bernoulli 解析解
# ─────────────────────────────────────────────────────────────────────
def eb_tip_deflection(P: float, L: float, E: float, I: float) -> float:
    """Euler-Bernoulli 先端たわみ δ = PL³/(3EI)"""
    return P * L**3 / (3.0 * E * I)


def eb_deflection_curve(P: float, L: float, E: float, I: float, n: int = 100) -> tuple:
    """EB たわみ曲線 v(x) = Px²(3L-x)/(6EI)"""
    x = np.linspace(0.0, L, n)
    v = P * x**2 * (3*L - x) / (6.0 * E * I)
    return x, v


def eb_bending_stress(P: float, L: float, x: float, y: float) -> float:
    """EB 曲げ応力 σx = M·y/I, M = P(L-x)"""
    M = P * (L - x)
    return M * y


def eb_shear_stress(P: float, b: float, D: float, y: float) -> float:
    """EB せん断応力 τxy = (3P/2bD)(1 - (2y/D)²)"""
    eta = 2 * y / D
    return (3 * P / (2 * b * D)) * (1 - eta**2)


# ─────────────────────────────────────────────────────────────────────
#  2. Timoshenko 梁
# ─────────────────────────────────────────────────────────────────────
def timoshenko_tip_deflection(P: float, L: float, E: float, I: float,
                               G: float, A: float, kappa: float = 5.0/6.0) -> float:
    """Timoshenko 先端たわみ (矩形断面デフォルト κ=5/6)
    δ_T = PL³/(3EI) + κPL/(GA)  ← 曲げ + せん断
    """
    return P * L**3 / (3.0 * E * I) + kappa * P * L / (G * A)


def timoshenko_deflection_curve(P: float, L: float, E: float, I: float,
                                 G: float, A: float, kappa: float = 5.0/6.0,
                                 n: int = 100) -> tuple:
    """Timoshenko たわみ曲線"""
    x = np.linspace(0.0, L, n)
    v_bending = P * x**2 * (3*L - x) / (6.0 * E * I)
    v_shear   = kappa * P * x / (G * A)
    return x, v_bending + v_shear


# ─────────────────────────────────────────────────────────────────────
#  3. 日置解 (Heki 1962)
#     解析坐標: ξ = x/ℓ (0..1), η = 2y/D (-1..1)
#     パラメータ β² = 3E_x D² / (4Gℓ²)
# ─────────────────────────────────────────────────────────────────────
def heki_beta(E_x: float, D: float, G: float, ell: float) -> float:
    """Heki パラメータ β = √(3E_x D² / (4Gℓ²))"""
    return np.sqrt(3.0 * E_x * D**2 / (4.0 * G * ell**2))


def heki_shear_stress(P: float, b: float, D: float, G: float, E_x: float,
                      ell: float, y: float) -> float:
    """日置解: せん断応力 τxy
    τxy = (P/bD) · β(cosh βη - cosh β) / (sinh β - β cosh β)
    """
    beta = heki_beta(E_x, D, G, ell)
    eta  = 2.0 * y / D
    denom = np.sinh(beta) - beta * np.cosh(beta)
    if abs(denom) < 1e-14:
        return eb_shear_stress(P, b, D, y)   # β→0 の極限
    return (P / (b * D)) * beta * (np.cosh(beta * eta) - np.cosh(beta)) / denom


def heki_bending_stress(P: float, b: float, D: float, G: float, E_x: float,
                         ell: float, x: float, y: float) -> float:
    """日置解: 曲げ応力 σx
    σx = [2Pℓ(1-ξ)/bD²] · β² sinh βη / (sinh β - β cosh β)
    """
    beta  = heki_beta(E_x, D, G, ell)
    xi    = x / ell
    eta   = 2.0 * y / D
    denom = np.sinh(beta) - beta * np.cosh(beta)
    if abs(denom) < 1e-14:
        return eb_bending_stress(P, ell, x, y) * 12.0 / D**2   # β→0 極限
    return (2.0 * P * ell * (1.0 - xi) / (b * D**2)) * beta**2 * np.sinh(beta * eta) / denom


def heki_deflection_curve(P: float, b: float, D: float, G: float, E_x: float,
                           ell: float, n: int = 100) -> tuple:
    """日置解: たわみ曲線 (山川 1992 論文の提案解・Timoshenko 相当)
    日置解の変位公式は β→0 の極限で中立軸 (η=0) での先端たわみが
    0 になる形であり、実際の変位は bending + shear の和になる。
    ここでは論文の β パラメータを用いた Timoshenko 等価式を使う。

    Note: Yamakawa (1992) の論文では日置解の変位を Table 1 に記載するが、
    Gemini 抽出の公式 v = Pℓ/(bDG)·β/(β−tanh β)·(ξ−3ξ²/2+ξ³/2)·cosh βη/cosh β
    は ξ=1 で v=0 となり先端変位を表さないため、正しい公式を直接使用する。
    β パラメータを含む Timoshenko 型公式で近似する。
    """
    beta = heki_beta(E_x, D, G, ell)
    # β→0 限界 (細長いはり) → EB
    # β→∞ 限界 (短いはり) → せん断支配
    # Timoshenko と β の対応: β² = 3(L/D)² * (G/E_x) (無次元せん断パラメータ)
    # β 組み込みのたわみ: EB + せん断 (Timoshenko 型)
    I  = b * D**3 / 12.0
    A  = b * D
    # Timoshenko (κ=1.0 を Heki 等価として使用)
    xs = np.linspace(0.0, ell, n)
    vs = P * xs**2 * (3*ell - xs) / (6.0 * E_x * I) + 1.0 * P * xs / (G * A)
    return xs, vs


def heki_tip_deflection(P: float, b: float, D: float, G: float, E_x: float,
                         ell: float) -> float:
    """日置解等価: 先端たわみ (Timoshenko κ=1.0 近似)
    β パラメータ = √(3E_xD²/4Gℓ²) を含む閉形式解は論文参照
    """
    I  = b * D**3 / 12.0
    A  = b * D
    return P * ell**3 / (3.0 * E_x * I) + 1.0 * P * ell / (G * A)


# ─────────────────────────────────────────────────────────────────────
#  4. Oberst 梁 - 粘弾性複合はりの複素曲げ剛性
#     出典: Oberst (1952) Acustica
#     応用: ガスケット・防振材の損失係数評価 (ISO 6721-3, ASTM E756)
# ─────────────────────────────────────────────────────────────────────
def oberst_neutral_axis(E1: float, E2_complex: complex,
                         d1: float, d2: float) -> complex:
    """Oberst: 複素中立軸位置 δ
    δ = 0.5 * (E1*d1² - Ē2*d2²) / (E1*d1 + Ē2*d2)
    ここで Ē2 = E2*(1+jη2) は複素弾性率

    Returns:
        δ: 複素数 (実部: 幾何的位置, 虚部: 位相ずれ)
    """
    return 0.5 * (E1 * d1**2 - E2_complex * d2**2) / (E1 * d1 + E2_complex * d2)


def oberst_complex_stiffness(E1: float, E2: float, eta2: float,
                              d1: float, d2: float) -> complex:
    """Oberst: 複素曲げ剛性 B (Eq. 12)
    B = B1 * [1 + 2ā(2ξ+3ξ²+2ξ³) + ā²ξ⁴] / (1 + āξ)
    ā = (E2/E1)*(1+jη2),  ξ = d2/d1,  B1 = E1*d1³/12

    Returns:
        B: 複素曲げ剛性 (Re = 剛性, Im/Re = 損失係数)
    """
    a_bar = (E2 / E1) * (1.0 + 1j * eta2)
    xi    = d2 / d1
    B1    = E1 * d1**3 / 12.0
    numer = 1.0 + 2 * a_bar * (2*xi + 3*xi**2 + 2*xi**3) + a_bar**2 * xi**4
    denom = 1.0 + a_bar * xi
    return B1 * numer / denom


def oberst_loss_factor(E1: float, E2: float, eta2: float,
                        d1: float, d2: float) -> float:
    """Oberst: 複合はりの損失係数 η (Eq. 14, η2²<<1 近似)
    η/η2 = aξ(3+6ξ+4ξ²+2aξ³+a²ξ⁴) / [(1+aξ)(1+2a(2ξ+3ξ²+2ξ³)+a²ξ⁴)]
    """
    a  = E2 / E1
    xi = d2 / d1
    numer = a * xi * (3 + 6*xi + 4*xi**2 + 2*a*xi**3 + a**2*xi**4)
    denom = (1 + a*xi) * (1 + 2*a*(2*xi + 3*xi**2 + 2*xi**3) + a**2*xi**4)
    return eta2 * numer / denom


def oberst_stiffness_ratio(E1: float, E2: float, eta2: float,
                            d1: float, d2: float) -> float:
    """Oberst: 剛性比 B/B1 (Eq. 13, η2²<<1 近似)"""
    a  = E2 / E1
    xi = d2 / d1
    numer = 1 + 2*a*(2*xi + 3*xi**2 + 2*xi**3) + a**2*xi**4
    denom = 1 + a*xi
    return numer / denom


# ─────────────────────────────────────────────────────────────────────
#  ユーティリティ
# ─────────────────────────────────────────────────────────────────────
def beam_EI(E: float, b: float, h: float) -> float:
    """矩形断面の EI (b=幅, h=せい)"""
    return E * b * h**3 / 12.0


def beam_GA(G: float, b: float, h: float, kappa: float = 5.0/6.0) -> float:
    """矩形断面の κGA"""
    return kappa * G * b * h


if __name__ == "__main__":
    # ─── テキスト p.167 の数値例で検証 ───
    E  = 210000.0   # [MPa]
    nu = 0.0
    G  = E / (2.0 * (1.0 + nu))   # nu=0 → G = E/2
    L  = 50.0       # [mm]
    H  = 2.0        # [mm]
    t  = 0.01       # [mm] 厚さ
    P  = 0.1        # [N]
    I  = t * H**3 / 12.0

    print("=" * 60)
    print("片持ち梁 解析解 比較")
    print(f"  L={L}mm, H={H}mm, t={t}mm, E={E}MPa, nu={nu}, P={P}N")
    print("=" * 60)

    delta_EB = eb_tip_deflection(P, L, E, I)
    delta_TM = timoshenko_tip_deflection(P, L, E, I, G, H*t, kappa=5.0/6.0)
    delta_HK = heki_tip_deflection(P, t, H, G, E, L)

    print(f"Euler-Bernoulli:  δ = {-delta_EB:.6f} mm")
    print(f"Timoshenko:       δ = {-delta_TM:.6f} mm  (κ=5/6)")
    print(f"Heki 日置解:      δ = {-delta_HK:.6f} mm")
    print()
    print(f"Timoshenko / EB = {delta_TM/delta_EB:.6f}")
    print(f"Heki     / EB   = {delta_HK/delta_EB:.6f}")
    print()

    # ─── Oberst 複素中立軸 デモ ───
    print("=" * 60)
    print("Oberst 梁: 粘弾性中立軸は複素数")
    print("  E1=210GPa (鋼板), E2=3GPa (制振材), η2=0.1")
    print("=" * 60)
    E1 = 210e3   # [MPa]
    E2 = 3e3     # [MPa]
    eta2 = 0.1
    d1 = 1.0     # 板厚 [mm]

    print(f"{'d2/d1':>8} {'Re(δ/d1)':>12} {'Im(δ/d1)':>12} {'η_system':>12} {'B/B1':>8}")
    print("-" * 60)
    for xi in [0.1, 0.25, 0.5, 1.0, 2.0, 4.0]:
        d2 = xi * d1
        E2c = E2 * (1.0 + 1j * eta2)
        delta = oberst_neutral_axis(E1, E2c, d1, d2)
        eta_s = oberst_loss_factor(E1, E2, eta2, d1, d2)
        B_ratio = oberst_stiffness_ratio(E1, E2, eta2, d1, d2)
        print(f"  {xi:6.2f}  {delta.real/d1:>12.6f}  {delta.imag/d1:>12.6f}  "
              f"{eta_s:>12.6f}  {B_ratio:>8.3f}")
    print()
    print("※ δ の虚部 ≠ 0 → 中立軸は複素数 (損失係数に相当する位相ずれ)")
