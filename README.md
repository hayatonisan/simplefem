# SIMPLEFEM

**＜解析塾秘伝＞有限要素法の作り方！** (2023) の VBA プログラムを  
Python / Docker に変換した教育用 FEM コードです。

---

## 問題設定 (片持ち梁バトル)

```
固定端                     集中荷重 P=0.1 N
  ├─────────────────────────────────────────┤ ↓
  │  L = 50 mm, H = 2 mm, t = 0.01 mm      │
  │  E = 210 000 MPa, ν = 0                 │
  └─────────────────────────────────────────┘
```

Euler-Bernoulli 解析解: δ = PL³/(3EI) = **2.9762 mm**

---

## バトル結果 (ロッキング対策完全比較)

| 手法 | δ_tip [mm] | 比率 [%] | 評価 |
|------|-----------|---------|------|
| tria3 (CST) | −0.2851 | **9.6%** | ⚠⚠ 強せん断ロッキング |
| quad4 標準 | −0.7221 | **24.3%** | ⚠⚠ 強せん断ロッキング |
| quad4 RI (1×1) | −3.1694 | **106.5%** | △ アワーグラス不安定 |
| quad4 SRI (選択的低減積分) | −2.9715 | **99.8%** | ✓ ロッキング解消 |
| quad4 IM (Wilson Q6) | −2.9715 | **99.8%** | ✓ ロッキング解消 |
| quad8 (Serendipity 2次) | −2.9764 | **100.0%** | ✓ 高精度 |
| OpenSees elasticBeamColumn | −2.9762 | **100.0%** | ✓ 梁理論基準 |
| OpenSees quad (PlaneStrain) | −0.7221 | **24.3%** | ⚠⚠ ロッキング (quad4 同等) |
| **OpenSees SSPquad** | **−3.0673** | **103.1%** | ✓ 安定化1点積分 (ロッキング解消) |
| Kratos SmallDisplacement2D4N | −0.7221 | **24.3%** | ⚠⚠ ロッキング (quad4 同等) |
| **Kratos SmallDisplacement2D8N** | **−2.9763** | **100.0%** | ✓ Q8 Serendipity (高精度) |
| Euler-Bernoulli 解析解 | −2.9762 | **100.0%** | 理論値 |
| Timoshenko (κ=5/6) | −2.9782 | 100.1% | せん断変形含む |
| Heki 日置解 (κ=1.0) | −2.9786 | 100.1% | 2D 弾性体厳密解 |

> **相互検証ポイント:**
> - `OpenSees quad` = `Kratos quad4` = `SIMPLEFEM quad4` → 同一値 −0.7221 (24.3%)  
>   → 3 つの全く異なるコードが同じ bilinear quad4 実装を内部検証
> - `OpenSees SSPquad` (103.1%) vs `SIMPLEFEM quad4 SRI` (99.8%):  
>   どちらも 1 点積分系だがホワイトグラス安定化の有無で若干の差
> - `Kratos Q8` = `SIMPLEFEM quad8` → 同一値 100.0% (Serendipity Q8 相互検証)

---

## 実装内容

### 要素タイプ

| ファイル | 要素 | 節点/要素数 |
|--------|------|------------|
| `src/cantilever_tria3.py` | CST 三角形1次 | 55節点 / 80要素 |
| `src/cantilever_quad4.py` | Bilinear Quad4 標準 (2×2 Gauss) | 55節点 / 40要素 |
| `src/cantilever_quad4_ri.py` | Quad4 低減積分 (1×1 Gauss) | 55節点 / 40要素 |
| `src/cantilever_quad4_sri.py` | Quad4 選択的低減積分 (Hughes 1980) | 55節点 / 40要素 |
| `src/cantilever_quad4_im.py` | Quad4 非適合モード (Wilson-Taylor Q6) | 55節点 / 40要素 |
| `src/cantilever_quad8.py` | Serendipity Quad8 (3×3 Gauss) | 149節点 / 40要素 |

### ロッキング対策の理論まとめ

#### せん断ロッキング (Shear Locking)
bilinear Quad4 要素は曲げ場で **寄生せん断ひずみ (parasitic shear)** が生じ、
剛性を過大評価する。対策:

| 方法 | 実装 | 結果 |
|------|------|------|
| **RI** (低減積分) | γxy を 1×1 Gauss で積分 | ✓ ロッキング解消, △ アワーグラス不安定 |
| **SRI** (選択的低減積分) | γxy のみ 1×1, 残りは 2×2 | ✓ ロッキング解消, アワーグラスなし |
| **IM** (非適合モード) | 内部モード (1-ξ²)(1-η²) + 静的縮合 | ✓ ロッキング解消, パッチテスト近似満足 |
| **Quad8** (2次要素) | Serendipity 2次変位場 | ✓ ロッキング根本解消 |

### 解析解モジュール (`src/analytical.py`)

1. **Euler-Bernoulli** — δ = PL³/(3EI)
2. **Timoshenko** — δ = PL³/(3EI) + κPL/(GA)  (κ=5/6 矩形断面)
3. **日置解 (Heki 1962)** — β = √(3E_xD²/4Gℓ²) を含む双曲線型応力分布
   - せん断応力: τ = (P/bD) · β(cosh βη − cosh β)/(sinh β − β cosh β)
   - 曲げ応力: σx = (2Pℓ(1−ξ)/bD²) · β² sinh βη/(sinh β − β cosh β)
4. **Oberst 梁 (1952)** — 粘弾性複合はりの複素曲げ剛性と損失係数
   - 複素中立軸: δ = (E₁d₁² − Ē₂d₂²) / (2(E₁d₁ + Ē₂d₂))
   - 複素曲げ剛性: B = B₁[1 + 2ā(2ξ+3ξ²+2ξ³) + ā²ξ⁴] / (1 + āξ)
   - 損失係数: η = η₂ · aξ(3+6ξ+4ξ²+...) / [...]

### テキストコラム数値実験 (`src/column_examples.py`)

| コラム | 内容 | コマンド |
|-------|------|---------|
| Col.1 | EB 有効範囲 (L/H 比パラメトリック) | `python main.py column 1` |
| Col.2 | 全ロッキング対策バトル | `python main.py column 2` |
| Col.4 | ミーゼス応力外挿順序 (Method A vs B) | `python main.py column 4` |
| Col.5 | 応力最適サンプリング (Barlow 点) | `python main.py column 5` |

**Col.2 結果 (抜粋):**
```
tria3 (CST)            9.58%   ⚠⚠ 強ロッキング
quad4 標準            24.26%   ⚠⚠ 強ロッキング
quad4 RI (1×1)       106.49%   △  過剰変形
quad4 SRI (選択的RI)  99.84%   ✓  良好
quad4 IM (Wilson Q6)  99.84%   ✓  良好
quad8 (Serendipity)  100.01%   ✓  良好
```

---

## クイックスタート

### Docker (推奨)

```bash
docker build -t simplefem:latest .

# 各要素タイプ
docker run --rm simplefem:latest quad4
docker run --rm simplefem:latest quad8
docker run --rm simplefem:latest quad4_sri
docker run --rm simplefem:latest quad4_im

# コラム実験
docker run --rm simplefem:latest column 2   # ロッキング対策バトル
docker run --rm simplefem:latest column all  # 全コラム

# 穴あき平板 SCF
docker run --rm simplefem:latest plate_hole

# 解析解一覧
docker run --rm simplefem:latest analytical
```

### Python 直接実行

```bash
pip install numpy scipy matplotlib
python main.py quad4_sri
python main.py column 2
```

### バトル全比較 (SIMPLEFEM + OpenSees + Kratos)

```bash
python battle/battle_extended.py   # 全11ソルバー比較 + CSV + PNG
python battle/battle.py            # 旧バージョン (Docker 直接)
```

| ファイル | 内容 |
|---------|------|
| `battle/opensees/beam.py` | elasticBeamColumn (梁理論) |
| `battle/opensees/quad.py` | quad PlaneStrain (ロッキングあり) |
| `battle/opensees/quad_ssp.py` | **SSPquad** 安定化1点積分 (ロッキングなし) |
| `battle/kratos/MainKratos.py` | SmallDisplacement2D4N (ロッキングあり) |
| `battle/kratos/MainKratos_q8.py` | **SmallDisplacement2D8N** Q8 (ロッキングなし) |

---

## 解析解の詳細

### 日置解 (Heki 1962) — 2次元弾性体としての片持ち梁

山川哲也 (1992) の定式化に基づく。EB 梁理論との主な違い:

| 量 | EB 理論 | 日置解 |
|----|--------|--------|
| せん断応力 τxy | 放物線分布 | 双曲線分布 (β 依存) |
| 曲げ応力 σx | M·y/I (線形) | β² sinh βη 項を含む |
| δ_tip | PL³/(3EI) | EB + せん断変形 (κ=1.0) |

β = √(3E_xD²/4Gℓ²) は「梁の太さ」の無次元パラメータ:
- β→0 (細長い梁) → EB 理論に収束
- β→∞ (短い梁) → せん断支配

### Oberst 梁 — 粘弾性中立軸は複素数

制振コーティング材 (ISO 6721-3, ASTM E756) の評価に使用:

- 中立軸位置 δ が **複素数** になる → 位相のずれ = エネルギー散逸
- 損失係数 η の最大化: d₂/d₁ ≈ 1.5−2.0 付近でピーク

```
d2/d1  Im(δ/d1)   η_system
  0.25  ~0       0.005
  1.00  0.001    0.015
  2.00  0.002    0.019  ← ピーク付近
  4.00  0.001    0.016
```

---

## ディレクトリ構成

```
SIMPLEFEM/
├── src/
│   ├── fem_core.py              # 共通: D行列, BC処理, ソルバー
│   ├── simple_fem.py            # 第2章: 三角形基本モデル
│   ├── cantilever_tria3.py      # CST 三角形1次
│   ├── cantilever_quad4.py      # Quad4 標準
│   ├── cantilever_quad4_ri.py   # Quad4 低減積分
│   ├── cantilever_quad4_sri.py  # Quad4 選択的低減積分 (Hughes)
│   ├── cantilever_quad4_im.py   # Quad4 非適合モード (Wilson Q6)
│   ├── cantilever_quad8.py      # Quad8 Serendipity
│   ├── plate_hole_quad8.py      # 穴あき平板 SCF (簡易デモ)
│   ├── column_examples.py       # テキストコラム数値実験
│   ├── analytical.py            # 解析解 (EB/Timoshenko/Heki/Oberst)
│   └── jacobi.py                # ヤコビ法固有値解析
├── battle/
│   ├── battle.py                # Docker オーケストレーター
│   ├── battle_extended.py       # 全ソルバー拡張バトル
│   ├── opensees/                # OpenSees モデル
│   └── kratos/                  # Kratos モデル
├── main.py                      # CLI エントリーポイント
├── Dockerfile
└── requirements.txt
```

---

## 参考文献

1. 大坪英臣 *「＜解析塾秘伝＞有限要素法の作り方！」* (2023)
2. Heki, K. (1962) — 梁の2次元弾性解析
3. 山川哲也 (1992) — 「提案解と日置解の比較について」
4. Oberst, H. (1952) — Acustica (粘弾性複合はり)
5. Hughes, T.J.R. (1980) — "Generalization of selective integration" (SRI)
6. Wilson, E.L. et al. (1973) — Incompatible displacement modes (IM)
7. Taylor, R.L. et al. (1976) — Modified incompatible modes (QM6)
8. Barlow, J. (1976) — "Optimal stress locations in finite element models"

---

## ライセンス

MIT
