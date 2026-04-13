"""
main.py - SIMPLEFEM CLI エントリーポイント

Usage:
  python main.py simple_fem [-o result.txt]
  python main.py tria3      [-o result.txt]
  python main.py quad4      [-o result.txt]
  python main.py quad4_ri   [-o result.txt]
  python main.py quad4_sri  [-o result.txt]
  python main.py quad4_im   [-o result.txt]
  python main.py quad8      [-o result.txt]
  python main.py jacobi
  python main.py column [1|2|4|5|all]
  python main.py plate_hole
  python main.py analytical
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

MODELS = {
    "simple_fem": "第2章: 三角形1次要素 (6節点4要素, 平面ひずみ)",
    "tria3":      "第3.3章: 片持ち梁 三角形1次要素 (CST, ロッキングあり)",
    "quad4":      "第3.3章: 片持ち梁 四角形1次要素 (標準, ロッキングあり)",
    "quad4_ri":   "第3.3章: 四角形1次 低減積分 (1×1, アワーグラス不安定)",
    "quad4_sri":  "第3.3章: 四角形1次 選択的低減積分 (せん断RI, ロッキング解消)",
    "quad4_im":   "第3.3章: 四角形1次 非適合モード (Wilson Q6, ロッキング解消)",
    "quad8":      "第3.3章: 片持ち梁 四角形2次要素 (Serendipity, 高精度)",
    "jacobi":     "第4.2.3章: ヤコビ法固有値解析",
    "column":     "テキストコラム数値実験 (1/2/4/5/all)",
    "plate_hole": "第4.4章: 穴あき平板 応力集中係数 (Quad8)",
    "analytical": "解析解一覧 (EB/Timoshenko/Heki/Oberst)",
}


def main():
    parser = argparse.ArgumentParser(
        description="SIMPLEFEM - 有限要素法プログラム (VBA → Python 変換)\n\n"
                    "＜解析塾秘伝＞有限要素法の作り方! より",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "model",
        choices=list(MODELS.keys()),
        help="\n".join(f"  {k:<12} {v}" for k, v in MODELS.items()),
    )
    parser.add_argument("--output", "-o", default=None, help="出力ファイルパス (省略時は標準出力)")
    parser.add_argument("subcmd", nargs="?", default="all",
                        help="column サブコマンド: 1/2/4/5/all")
    args = parser.parse_args()

    if args.model == "simple_fem":
        from simple_fem import simple_fem, print_result
        U, Fr, strain, stress = simple_fem()
        print_result(U, Fr, strain, stress, args.output)

    elif args.model == "tria3":
        from cantilever_tria3 import cantilever_tria3, print_result
        U, Fr, strain_ip, stress_ip = cantilever_tria3()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "quad4":
        from cantilever_quad4 import cantilever_quad4, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad4()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "quad4_ri":
        from cantilever_quad4_ri import cantilever_quad4_ri, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad4_ri()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "quad4_sri":
        from cantilever_quad4_sri import cantilever_quad4_sri, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad4_sri()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "quad4_im":
        from cantilever_quad4_im import cantilever_quad4_im, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad4_im()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "quad8":
        from cantilever_quad8 import cantilever_quad8, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad8()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "jacobi":
        from jacobi import jacobi_test
        jacobi_test()

    elif args.model == "column":
        from column_examples import (column1_beam_validity, column2_locking_all,
                                     column4_mises_extrapolation, column5_stress_sampling)
        sub = args.subcmd
        if sub in ("1", "all"): column1_beam_validity()
        if sub in ("2", "all"): column2_locking_all()
        if sub in ("4", "all"): column4_mises_extrapolation()
        if sub in ("5", "all"): column5_stress_sampling()

    elif args.model == "plate_hole":
        from plate_hole_quad8 import plate_hole_quad8
        plate_hole_quad8()

    elif args.model == "analytical":
        import analytical


if __name__ == "__main__":
    main()
