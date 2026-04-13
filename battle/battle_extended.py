"""
battle_extended.py - ロッキング対策完全バトル
=============================================
SIMPLEFEM の全バリアントを Python 直接実行で比較する
(Docker なし / 高速版)

問題設定:
  L=50mm, H=2mm, t=0.01mm, E=210000MPa, ν=0, P=0.1N
  解析解: δ_EB = PL³/(3EI) = 2.9762 mm

対象:
  1. SIMPLEFEM tria3       - CST (強ロッキング)
  2. SIMPLEFEM quad4       - 標準 bilinear (強ロッキング)
  3. SIMPLEFEM quad4 RI    - 低減積分 1×1 (アワーグラス不安定)
  4. SIMPLEFEM quad4 SRI   - 選択的低減積分 (ロッキング解消)
  5. SIMPLEFEM quad4 IM    - 非適合モード Wilson Q6 (ロッキング解消)
  6. SIMPLEFEM quad8       - 2次要素 Serendipity (高精度)
  7. OpenSees elasticBeamColumn (梁理論, Docker)
  8. OpenSees quad PlaneStrain  (quad4 等価, Docker)
  9. Kratos SmallDisplacementElement2D4N (quad4 等価, Docker)
 10. f90fem PLS_LIN (bilinear Q4, Python 直接実行)
"""
import sys, os, subprocess, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

# ── 解析解 ─────────────────────────────────────────────────
E  = 210000.0; H = 2.0; T = 0.01; L = 50.0; P = 0.1
I  = T * H**3 / 12.0
DELTA_EB = P * L**3 / (3.0 * E * I)   # 2.9762 mm

BASE  = os.path.dirname(os.path.abspath(__file__))
OPSEE = os.path.join(BASE, 'opensees')
KRAT  = os.path.join(BASE, 'kratos')
RES   = os.path.join(BASE, 'results')
os.makedirs(RES, exist_ok=True)


def tip_uy(U):
    """先端たわみ: node 10 (1-indexed: 11), uy DOF = node*2+1"""
    return U[10 * 2 + 1]   # 0-indexed node 10


def run_docker(cmd, label, timeout=180):
    """Docker コマンド実行"""
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r, time.perf_counter() - t0


# ─────────────────────────────────────────────────────────────
#  SIMPLEFEM ローカル実行
# ─────────────────────────────────────────────────────────────
results = {}

print("=" * 72)
print("  片持ち梁 先端たわみ バトル (全ロッキング対策バリアント)")
print(f"  L={L}mm H={H}mm t={T}mm E={E}MPa ν=0 P={P}N")
print(f"  解析解 (EB): δ = {-DELTA_EB:.6f} mm")
print("=" * 72)

from cantilever_tria3 import cantilever_tria3
from cantilever_quad4 import cantilever_quad4
from cantilever_quad4_ri import cantilever_quad4_ri
from cantilever_quad4_sri import cantilever_quad4_sri
from cantilever_quad4_im import cantilever_quad4_im
from cantilever_quad8 import cantilever_quad8
from analytical import eb_tip_deflection, timoshenko_tip_deflection, heki_tip_deflection

# f90fem (05_f90fem/elements/pls_lin.py)
F90FEM_PATH = os.path.join(BASE, '..', '..', '05_f90fem')
sys.path.insert(0, os.path.abspath(F90FEM_PATH))

# --- 解析解 ---
delta_TM = timoshenko_tip_deflection(P, L, E, I, E/2, H*T, kappa=5.0/6.0)
delta_HK = heki_tip_deflection(P, T, H, E/2, E, L)

_local_solvers = [
    ("tria3 (CST)",           cantilever_tria3,    "⚠⚠ 強ロッキング"),
    ("quad4 標準",             cantilever_quad4,    "⚠⚠ 強ロッキング"),
    ("quad4 RI (1×1)",        cantilever_quad4_ri, "△ 過剰変形"),
    ("quad4 SRI (選択的RI)",   cantilever_quad4_sri,"✓ ロッキング解消"),
    ("quad4 IM (Wilson Q6)",  cantilever_quad4_im, "✓ ロッキング解消"),
    ("quad8 (Serendipity)",   cantilever_quad8,    "✓ 高精度"),
]

for name, func, expect in _local_solvers:
    t0 = time.perf_counter()
    U, *_ = func()
    elapsed = time.perf_counter() - t0
    uy = tip_uy(U)
    ratio = abs(uy) / DELTA_EB * 100.0
    results[name] = dict(uy=uy, ratio=ratio, elapsed=elapsed)

# f90fem PLS_LIN (bilinear Q4, Python 直接実行)
try:
    import importlib.util, subprocess as _sp
    _f90fem_script = os.path.join(BASE, 'f90fem', 'cantilever_f90fem.py')
    _spec = importlib.util.spec_from_file_location("cantilever_f90fem", _f90fem_script)
    _mod  = importlib.util.module_from_spec(_spec)
    # 独立スクリプトとして実行してファイル経由で結果取得
    _t0 = time.perf_counter()
    _proc = _sp.run(['python3', _f90fem_script], capture_output=True, text=True)
    _dt = time.perf_counter() - _t0
    _res_path = os.path.join(BASE, 'f90fem', 'results', 'f90fem_uy.txt')
    _uy_f90 = float(open(_res_path).readline().strip()) if os.path.exists(_res_path) else None
    if _uy_f90 is not None:
        results['f90fem PLS_LIN'] = dict(uy=_uy_f90,
                                         ratio=abs(_uy_f90)/DELTA_EB*100, elapsed=_dt)
except Exception as e:
    print(f"[WARN] f90fem skip: {e}")

# ─────────────────────────────────────────────────────────────
#  Docker 実行 (OpenSees / Kratos)
# ─────────────────────────────────────────────────────────────
def parse_single(path):
    try:
        with open(path) as f: return float(f.readline().strip())
    except Exception: return None

# OpenSees beam
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0', 'beam.py',
], 'OpenSees beam')
uy_os_beam = parse_single(os.path.join(OPSEE, 'results', 'beam_uy.txt'))
if uy_os_beam is not None:
    results['OpenSees beam'] = dict(uy=uy_os_beam,
                                    ratio=abs(uy_os_beam)/DELTA_EB*100, elapsed=dt)

# OpenSees quad
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0', 'quad.py',
], 'OpenSees quad')
uy_os_q = parse_single(os.path.join(OPSEE, 'results', 'quad_uy.txt'))
if uy_os_q is not None:
    results['OpenSees quad'] = dict(uy=uy_os_q,
                                    ratio=abs(uy_os_q)/DELTA_EB*100, elapsed=dt)

# Kratos quad4
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{KRAT}:/work/work',
    'solver-kratos:9.5', 'MainKratos.py',
], 'Kratos quad4', timeout=300)
uy_kr = parse_single(os.path.join(KRAT, 'results', 'kratos_uy.txt'))
if uy_kr is not None:
    results['Kratos quad4'] = dict(uy=uy_kr,
                                   ratio=abs(uy_kr)/DELTA_EB*100, elapsed=dt)

# OpenSees SSPquad (安定化1点積分, ロッキングなし)
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0', 'quad_ssp.py',
], 'OpenSees SSPquad')
uy_os_ssp = parse_single(os.path.join(OPSEE, 'results', 'quad_ssp_uy.txt'))
if uy_os_ssp is not None:
    results['OpenSees SSPquad'] = dict(uy=uy_os_ssp,
                                       ratio=abs(uy_os_ssp)/DELTA_EB*100, elapsed=dt)

# Kratos Q8 (SmallDisplacementElement2D8N, ロッキングなし)
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{KRAT}:/work/work',
    'solver-kratos:9.5', 'MainKratos_q8.py',
], 'Kratos Q8', timeout=300)
uy_kr_q8 = parse_single(os.path.join(KRAT, 'results', 'kratos_q8_uy.txt'))
if uy_kr_q8 is not None:
    results['Kratos Q8'] = dict(uy=uy_kr_q8,
                                ratio=abs(uy_kr_q8)/DELTA_EB*100, elapsed=dt)

# OpenSees enhancedQuad (EAS / Wilson Q6 相当, ロッキングなし)
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0', 'quad_enhanced.py',
], 'OpenSees enhancedQuad')
uy_os_enh = parse_single(os.path.join(OPSEE, 'results', 'quad_enhanced_uy.txt'))
if uy_os_enh is not None:
    results['OpenSees enhancedQuad'] = dict(uy=uy_os_enh,
                                            ratio=abs(uy_os_enh)/DELTA_EB*100, elapsed=dt)

# OpenSees quad9n (9節点 Lagrange, 3×3 Gauss, ロッキングなし)
r, dt = run_docker([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0', 'quad9n.py',
], 'OpenSees quad9n')
uy_os_q9 = parse_single(os.path.join(OPSEE, 'results', 'quad9n_uy.txt'))
if uy_os_q9 is not None:
    results['OpenSees quad9n'] = dict(uy=uy_os_q9,
                                      ratio=abs(uy_os_q9)/DELTA_EB*100, elapsed=dt)


# ─────────────────────────────────────────────────────────────
#  結果表示
# ─────────────────────────────────────────────────────────────
print()
print(f"{'Solver':<28} {'uy_tip [mm]':>14} {'比率 [%]':>10} {'時間':>8}  評価")
print("-" * 72)

grade_map = {
    "tria3 (CST)":          "⚠⚠ 強ロッキング (9.6%)",
    "quad4 標準":            "⚠⚠ 強ロッキング (24.3%)",
    "f90fem PLS_LIN":       "⚠⚠ 強ロッキング (24.3%) ← quad4 相互検証",
    "quad4 RI (1×1)":       "△ 過剰変形 (アワーグラス)",
    "quad4 SRI (選択的RI)":  "✓ ロッキング解消",
    "quad4 IM (Wilson Q6)": "✓ ロッキング解消",
    "quad8 (Serendipity)":  "✓ 高精度",
    "OpenSees beam":        "✓ 梁理論 (基準)",
    "OpenSees quad":        "⚠⚠ ロッキング (quad4=24%)",
    "OpenSees SSPquad":        "✓ 安定化1点積分 (103.1%)",
    "OpenSees enhancedQuad":  "✓ EAS/Wilson Q6 相当 (ロッキングなし)",
    "OpenSees quad9n":        "✓ 9節点 Lagrange 2次 (ロッキングなし)",
    "Kratos quad4":           "⚠⚠ ロッキング (quad4=24%)",
    "Kratos quad":            "⚠⚠ ロッキング (quad4=24%)",
    "Kratos Q8":              "✓ Q8 Serendipity (ロッキングなし)",
}

for name, v in results.items():
    uy = v['uy']; ratio = v['ratio']; t_s = v.get('elapsed', 0)
    grade = grade_map.get(name, "")
    t_str = f"{t_s:.2f}s"
    print(f"  {name:<26}  {uy:>13.6f}  {ratio:>9.2f}%  {t_str:>7}  {grade}")

print("-" * 72)
print(f"  {'EB Analytical':<26}  {-DELTA_EB:>13.6f}  {'100.00%':>9}           理論値")
print(f"  {'Timoshenko (κ=5/6)':<26}  {-delta_TM:>13.6f}  {delta_TM/DELTA_EB*100:>9.2f}%")
print(f"  {'Heki 日置解 (κ=1.0)':<26}  {-delta_HK:>13.6f}  {delta_HK/DELTA_EB*100:>9.2f}%")
print("=" * 72)

# ─────────────────────────────────────────────────────────────
#  サマリー CSV
# ─────────────────────────────────────────────────────────────
csv_path = os.path.join(RES, 'battle_extended.csv')
with open(csv_path, 'w') as f:
    f.write('solver,uy_tip_mm,ratio_pct,elapsed_s\n')
    for name, v in results.items():
        f.write(f'{name},{v["uy"]:.8e},{v["ratio"]:.4f},{v.get("elapsed",0):.3f}\n')
    f.write(f'EB Analytical,{-DELTA_EB:.8e},100.0000,0.000\n')
    f.write(f'Timoshenko,{-delta_TM:.8e},{delta_TM/DELTA_EB*100:.4f},0.000\n')
print(f'\nCSV: {csv_path}')

# ─────────────────────────────────────────────────────────────
#  プロット
# ─────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    color_map = {
        'tria3 (CST)':          '#e05c5c',
        'quad4 標準':            '#e09a5c',
        'quad4 RI (1×1)':       '#e0c85c',
        'quad4 SRI (選択的RI)':  '#5cae5c',
        'quad4 IM (Wilson Q6)': '#5cb05c',
        'quad8 (Serendipity)':  '#2d8a2d',
        'OpenSees beam':        '#5c8ae0',
        'OpenSees quad':        '#a05ce0',
        'Kratos quad':          '#5cc8c8',
        'EB Analytical':        '#444444',
        'Timoshenko':           '#777777',
    }

    plot_data = [(k, v['ratio']) for k, v in results.items()]
    plot_data.append(('EB Analytical', 100.0))
    plot_data.append(('Timoshenko', delta_TM/DELTA_EB*100))

    labels = [d[0] for d in plot_data]
    vals   = [d[1] for d in plot_data]
    colors = [color_map.get(l, '#aaaaaa') for l in labels]

    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(labels, vals, color=colors, edgecolor='white', linewidth=0.5)
    ax.axvline(100.0, color='#333333', linestyle='--', linewidth=1.5, label='EB 100%')
    for bar, val in zip(bars, vals):
        ax.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}%', va='center', fontsize=8.5)
    ax.set_xlabel('先端たわみ比率 [%] (対 EB 解析解)', fontsize=11)
    ax.set_title(
        f'片持ち梁 ロッキング対策バトル\n'
        f'L={L}mm H={H}mm t={T}mm E={E}MPa ν=0 P={P}N  δ_EB={DELTA_EB:.3f}mm',
        fontsize=10
    )
    ax.set_xlim(0, max(max(vals)*1.15, 115))
    ax.legend()
    plt.tight_layout()
    plot_path = os.path.join(RES, 'battle_extended.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'Plot: {plot_path}')
except ImportError:
    print('[INFO] matplotlib unavailable – skipping plot')

if __name__ == "__main__":
    pass
