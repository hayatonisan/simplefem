Attribute VB_Name = "Module1"
' *********************************************************************
'
' 　第4章 前処理・後処理
'       4.2.3　ヤコビ法テスト
'
'
'   作者：日比　学（第4章担当）
'   更新：2014/06/22 Version 1.0 初版
'
' *********************************************************************

Option Base 1                           ' 配列のインデックスを1から始める
Option Explicit                         ' 変数の定義を強制する

' =====================================================================
' ヤコビ法プログラム(プログラム4.11)
' =====================================================================
Function Jacobi(Aorg() As Variant, V() As Variant)
    Dim WF As WorksheetFunction
    Set WF = Application.WorksheetFunction

    Dim tolerance As Double, Apq As Double
    Dim a As Variant, g As Variant
    Dim n As Integer, p As Integer, q As Integer
    Dim i As Integer, j As Integer
    Dim theta As Double
    
    tolerance = 0.00001
    a = Aorg
    n = UBound(a)
    V = eye(n)
    Do
        '①絶対値最大の非対角項の探索：　Apq, p行p列目
        p = 1
        q = 2
        Apq = Abs(a(p, q))
        For i = 1 To n
            For j = i + 1 To n
                If (Abs(a(i, j)) > Apq) Then
                    Apq = Abs(a(i, j)): p = i: q = j
                End If
            Next j
        Next i
        '②収束判断
        If (Apq < tolerance) Then Exit Do
        
        '③回転角の計算
        theta = WF.Atan2(a(q, q) - a(p, p), 2 * Apq) / 2

        '④回転行列Ｇ
        g = eye(n)
        g(p, p) = Cos(theta): g(p, q) = Sin(theta)
        g(q, p) = -Sin(theta): g(q, q) = Cos(theta)
        
        '⑤ A=G'*A*G　（実対称行列の更新）
        '   V=   V*G　（固有ベクトルの更新）
        a = WF.MMult(WF.MMult(WF.Transpose(g), a), g)
        V = WF.MMult(V, g)
    Loop
    
    '固有値（主応力）の配列を関数値として返す。
    Jacobi = Array(a(1, 1), a(2, 2), a(3, 3))
End Function

' =====================================================================
' 単位行列関数(プログラム4.12)
' =====================================================================
Function eye(n As Integer)
    Dim e() As Variant
    ReDim e(n, n)
    Dim i As Integer, j As Integer
    
    For i = 1 To n
        For j = 1 To n
            If (i = j) Then e(i, j) = 1 Else e(i, j) = 0
        Next j
    Next i
    
    eye = e
End Function


' =====================================================================
' ヤコビ法のテストプログラム(プログラム4.13)
' =====================================================================
Sub jacobi_test()
    Dim a() As Variant, V() As Variant
    Dim lambda As Variant
    
    a = Range("A")
    lambda = Jacobi(a, V)
    Range("lambda") = lambda
    Range("V") = V
End Sub

' =====================================================================
' 「計算」ボタンクリック動作：    jacobi_testを実行
' =====================================================================
Sub CalcButton_Click()
    Call jacobi_test
End Sub

' =====================================================================
' 「結果消去」ボタンクリック動作:   固有値と固有ベクトルをクリア
' =====================================================================
Sub ClearButton_Click()
    Range("V").ClearContents
    Range("lambda").ClearContents
End Sub

