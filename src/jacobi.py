"""
jacobi.py - 第4.2.3章: ヤコビ法固有値解析
実対称行列の固有値・固有ベクトルを計算

VBA原本: 4.2.3_ヤコビ法テスト_Module1.vb
"""
import numpy as np
import sys


def jacobi_method(A_in: np.ndarray, tolerance: float = 1e-5):
    """ヤコビ法で実対称行列の固有値と固有ベクトルを計算

    VBA: Jacobi() 関数

    Args:
        A_in:      実対称行列 (n, n)
        tolerance: 収束判定 (デフォルト 1e-5)

    Returns:
        eigenvalues:  固有値 配列 (n,)
        eigenvectors: 固有ベクトル行列 (n, n) - 列が固有ベクトル
    """
    A = A_in.astype(float).copy()
    n = A.shape[0]
    V = np.eye(n)  # VBA: V = eye(n)

    max_iter = 10000
    for _ in range(max_iter):
        # ①絶対値最大の非対角項を探索 - VBA: Step①
        p, q = 0, 1
        Apq = abs(A[p, q])
        for i in range(n):
            for j in range(i + 1, n):
                if abs(A[i, j]) > Apq:
                    Apq = abs(A[i, j])
                    p, q = i, j

        # ②収束判断 - VBA: Step②
        if Apq < tolerance:
            break

        # ③回転角の計算 - VBA: Step③
        # VBA: WF.Atan2(x=a(q,q)-a(p,p), y=2*Apq) / 2
        # VBA Atan2(x,y) = Python arctan2(y,x) → 引数順が逆
        theta = np.arctan2(2 * Apq, A[q, q] - A[p, p]) / 2.0

        # ④回転行列G - VBA: Step④
        G = np.eye(n)
        G[p, p] =  np.cos(theta)
        G[p, q] =  np.sin(theta)
        G[q, p] = -np.sin(theta)
        G[q, q] =  np.cos(theta)

        # ⑤ A = G^T * A * G, V = V * G - VBA: Step⑤
        A = G.T @ A @ G
        V = V @ G

    eigenvalues = np.diag(A)
    return eigenvalues, V


def jacobi_test():
    """ヤコビ法のテスト - VBA: jacobi_test()

    デモ用入力行列 (書籍例題に近い3×3対称行列)
    """
    # テスト行列
    A = np.array([
        [4.0, 2.0, 1.0],
        [2.0, 3.0, 0.5],
        [1.0, 0.5, 2.0],
    ])

    print("入力行列 A:")
    print(A)
    print()

    lambdas, V = jacobi_method(A)

    print("固有値 (lambda):")
    for i, lam in enumerate(lambdas):
        print(f"  lambda[{i+1}] = {lam:.10f}")
    print()

    print("固有ベクトル行列 V (列が固有ベクトル):")
    for i in range(V.shape[0]):
        vals = "  ".join(f"{V[i, j]:12.9f}" for j in range(V.shape[1]))
        print(f"  {vals}")
    print()

    # numpy の固有値と比較
    np_lam, np_vec = np.linalg.eigh(A)
    print("numpy.linalg.eigh による固有値 (参考):")
    for i, lam in enumerate(np_lam):
        print(f"  lambda[{i+1}] = {lam:.10f}")

    return lambdas, V


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="第4.2.3章 ヤコビ法固有値解析")
    parser.add_argument(
        "--matrix", "-m",
        nargs="+",
        type=float,
        default=None,
        help="行列成分をスペース区切りで指定 (n*n 個, 行優先)",
    )
    parser.add_argument("--size", "-n", type=int, default=3, help="行列サイズ (デフォルト=3)")
    parser.add_argument("--tolerance", "-t", type=float, default=1e-5, help="収束判定値")
    args = parser.parse_args()

    if args.matrix:
        n = args.size
        A = np.array(args.matrix).reshape(n, n)
        lams, V = jacobi_method(A, args.tolerance)
        print("固有値:", lams)
        print("固有ベクトル行列 V:\n", V)
    else:
        jacobi_test()
