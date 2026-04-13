"""
main.py - SIMPLEFEM CLI エントリーポイント

Usage:
  python main.py simple_fem [-o result.txt]
  python main.py tria3      [-o result.txt]
  python main.py quad4      [-o result.txt]
  python main.py quad8      [-o result.txt]
  python main.py jacobi
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

MODELS = {
    "simple_fem": "第2章: 三角形1次要素 (6節点4要素, 平面ひずみ)",
    "tria3":      "第3.3章: 片持ち梁 三角形1次要素 (55節点80要素)",
    "quad4":      "第3.3章: 片持ち梁 四角形1次要素 (55節点40要素)",
    "quad8":      "第3.3章: 片持ち梁 四角形2次要素 (149節点40要素)",
    "jacobi":     "第4.2.3章: ヤコビ法固有値解析",
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

    elif args.model == "quad8":
        from cantilever_quad8 import cantilever_quad8, print_result
        U, Fr, strain_ip, stress_ip = cantilever_quad8()
        print_result(U, Fr, strain_ip, stress_ip, args.output)

    elif args.model == "jacobi":
        from jacobi import jacobi_test
        jacobi_test()


if __name__ == "__main__":
    main()
