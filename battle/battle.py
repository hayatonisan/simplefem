"""
battle.py - 片持ち梁 曲げ解析バトル
==============================================
SIMPLEFEM / OpenSees / Kratos を Docker 経由で実行し、
先端たわみを Euler-Bernoulli 解析解と比較する。

問題設定:
  L = 50 mm, H = 2 mm, t = 0.01 mm
  E = 210000 MPa, nu = 0 (平面ひずみ)
  P = 0.1 N (先端集中荷重)
  解析解: delta_EB = PL^3 / (3EI) = 2.976 mm

比較対象:
  1. SIMPLEFEM tria3   (3角形1次, 55節点, 80要素)
  2. SIMPLEFEM quad4   (4角形1次, 55節点, 40要素)
  3. SIMPLEFEM quad8   (4角形2次, 149節点, 40要素)
  4. OpenSees beam     (elasticBeamColumn, 梁理論)
  5. OpenSees quad     (quad PlaneStrain, 55節点)
  6. Kratos quad       (SmallDisplacementElement2D4N, 55節点)
"""
import subprocess
import sys
import os
import re
import time

BASE  = os.path.dirname(os.path.abspath(__file__))
SFEM  = os.path.join(BASE, '..') # SIMPLEFEM root
OPSEE = os.path.join(BASE, 'opensees')
KRAT  = os.path.join(BASE, 'kratos')
RES   = os.path.join(BASE, 'results')
os.makedirs(RES, exist_ok=True)

# ── 解析解 ──────────────────────────────────────────────
E  = 210000.0
H  = 2.0
T  = 0.01
L  = 50.0
P  = 0.1
I  = T * H**3 / 12.0
DELTA_EB = P * L**3 / (3.0 * E * I)   # 2.976 mm (下方向, 正値)


def run(cmd, label, timeout=120):
    """サブプロセス実行 → stdout/stderr 表示 → 経過時間"""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  cmd: {' '.join(cmd)}")
    print('='*60)
    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=False, timeout=timeout)
    elapsed = time.perf_counter() - t0
    if result.returncode != 0:
        print(f"[WARN] returncode={result.returncode}")
    return elapsed


# ── 1~3: SIMPLEFEM ──────────────────────────────────────
for model in ('tria3', 'quad4', 'quad8'):
    outfile = f'/results/simplefem_{model}.txt'
    run([
        'docker', 'run', '--rm',
        '-v', f'{RES}:/results',
        'simplefem:latest',
        model, '-o', outfile,
    ], f'SIMPLEFEM {model}')

# ── 4: OpenSees beam ────────────────────────────────────
run([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0',
    'beam.py',
], 'OpenSees elasticBeamColumn')

# ── 5: OpenSees quad ────────────────────────────────────
run([
    'docker', 'run', '--rm',
    '-v', f'{OPSEE}:/work/work',
    'solver-opensees:3.7.0',
    'quad.py',
], 'OpenSees quad PlaneStrain')

# ── 6: Kratos quad ──────────────────────────────────────
run([
    'docker', 'run', '--rm',
    '-v', f'{KRAT}:/work/work',
    'solver-kratos:9.5',
    'MainKratos.py',
], 'Kratos SmallDisplacementElement2D4N', timeout=180)


# ── 結果収集 ────────────────────────────────────────────

def parse_simplefem(path, node_id=33):
    """SIMPLEFEM 出力から node_id の uy を抽出"""
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        return None
    # ====={Displacement@Node}===
    in_disp = False
    for line in text.splitlines():
        if 'Displacement@Node' in line:
            in_disp = True
            continue
        if in_disp:
            parts = line.split()
            if len(parts) >= 3 and parts[0].isdigit():
                if int(parts[0]) == node_id:
                    return float(parts[2])  # uy
    return None


def parse_single_value(path):
    """最初の行から float を読む"""
    try:
        with open(path) as f:
            return float(f.readline().strip())
    except Exception:
        return None


results = {
    'SIMPLEFEM tria3' : parse_simplefem(os.path.join(RES, 'simplefem_tria3.txt')),
    'SIMPLEFEM quad4' : parse_simplefem(os.path.join(RES, 'simplefem_quad4.txt')),
    'SIMPLEFEM quad8' : parse_simplefem(os.path.join(RES, 'simplefem_quad8.txt')),
    'OpenSees beam'   : parse_single_value(os.path.join(OPSEE, 'results', 'beam_uy.txt')),
    'OpenSees quad'   : parse_single_value(os.path.join(OPSEE, 'results', 'quad_uy.txt')),
    'Kratos quad'     : parse_single_value(os.path.join(KRAT,  'results', 'kratos_uy.txt')),
}

# ── 結果表示 ─────────────────────────────────────────────
print('\n')
print('=' * 68)
print(f'  片持ち梁 先端たわみ バトル結果')
print(f'  問題: L={L}, H={H}, t={T}, E={E}, nu=0, P={P} N')
print(f'  解析解 (EB): delta = {DELTA_EB:.4f} mm  (下向き正)')
print('=' * 68)
print(f"{'Solver':<22} {'uy_tip [mm]':>14} {'比率 [%]':>10}  注記")
print('-' * 68)

for name, uy in results.items():
    if uy is None:
        print(f"  {name:<20} {'---':>14} {'---':>10}  (結果ファイルなし)")
        continue
    tip = abs(uy)
    ratio = tip / DELTA_EB * 100.0
    note = ''
    if 'beam' in name.lower():
        note = '梁理論 (基準)'
    elif 'quad8' in name.lower():
        note = '2次要素 (せん断ロッキングなし)'
    else:
        note = 'ロッキング' if ratio < 80 else ''
    print(f"  {name:<20}  {-tip:>13.6f}  {ratio:>9.2f}%  {note}")

print('-' * 68)
print(f"  {'Euler-Bernoulli 解析解':<20}  {-DELTA_EB:>13.6f}  {'100.00%':>9}  理論値")
print('=' * 68)

# 結果をファイルに保存
summary_path = os.path.join(RES, 'battle_summary.txt')
with open(summary_path, 'w') as f:
    f.write('solver,uy_tip_mm,ratio_pct\n')
    for name, uy in results.items():
        if uy is not None:
            f.write(f'{name},{uy:.8e},{abs(uy)/DELTA_EB*100:.4f}\n')
    f.write(f'Analytical EB,{-DELTA_EB:.8e},100.0000\n')
print(f'\n結果サマリー: {summary_path}')

# ── matplotlib プロット ───────────────────────────────────
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # 日本語フォント候補
    jp_fonts = [f.name for f in fm.fontManager.ttflist
                if 'Noto' in f.name or 'IPAex' in f.name or 'Meiryo' in f.name]
    if jp_fonts:
        plt.rcParams['font.family'] = jp_fonts[0]

    labels = []
    vals   = []
    colors = []
    color_map = {
        'SIMPLEFEM tria3' : '#e05c5c',
        'SIMPLEFEM quad4' : '#e09a5c',
        'SIMPLEFEM quad8' : '#5cae5c',
        'OpenSees beam'   : '#5c8ae0',
        'OpenSees quad'   : '#a05ce0',
        'Kratos quad'     : '#5cc8c8',
    }
    for name, uy in results.items():
        if uy is None:
            continue
        labels.append(name)
        vals.append(abs(uy) / DELTA_EB * 100.0)
        colors.append(color_map.get(name, '#aaaaaa'))

    labels.append('EB Analytical')
    vals.append(100.0)
    colors.append('#444444')

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(labels, vals, color=colors, edgecolor='white', linewidth=0.8)
    ax.axvline(100.0, color='#333333', linestyle='--', linewidth=1.2, label='Euler-Bernoulli 100%')
    for bar, val in zip(bars, vals):
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', ha='left', fontsize=9)
    ax.set_xlabel('先端たわみ比率 [%] (対 EB 解析解)')
    ax.set_title(f'片持ち梁 バトル\n'
                 f'L={L}mm H={H}mm t={T}mm E={E}MPa ν=0 P={P}N  '
                 f'δ_EB={DELTA_EB:.3f}mm', fontsize=10)
    ax.set_xlim(0, max(max(vals) * 1.12, 110))
    ax.legend(fontsize=9)
    plt.tight_layout()
    plot_path = os.path.join(RES, 'battle_plot.png')
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'プロット: {plot_path}')
except ImportError:
    print('[INFO] matplotlib not available – プロットをスキップ')
