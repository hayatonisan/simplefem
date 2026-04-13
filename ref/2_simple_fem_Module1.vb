Attribute VB_Name = "Module1"
' ************************
'  simple_fem
'
'  シンプルなFEMプログラム
'       三角形1次要素
'       平面ひずみ
'
'  Ver 1.00  2014/4/28
' ************************

Option Base 1                               ' 配列のインデックスを1から始める
Option Explicit                             ' 変数の定義を強制する

' ----
' 定数
' ----
Const NODES As Integer = 6                   ' 全節点数
Const ELEMENTS As Integer = 4                ' 全要素数
Const COMPONENTS As Integer = 3              ' ひずみと応力の成分数
Const NODES_TRIA3 As Integer = 3             ' 三角形1次要素の節点数
Const DOF_NODE As Integer = 2                ' 節点自由度
Const DOF_TOTAL As Integer = DOF_NODE * NODES ' 全体自由度
Const DOF_TRIA3 As Integer = DOF_NODE * NODES_TRIA3 ' 要素自由度
Const THICKNESS As Double = 1#               ' 要素の厚さ
Const YOUNG As Double = 210000#              ' ヤング率
Const POISSON As Double = 0.3                ' ポアソン比

' --------------------
' モジュールレベル変数
' --------------------
Dim x(NODES) As Double                       ' 節点のx座標配列
Dim y(NODES) As Double                       ' 節点のy座標配列
Dim connectivity(ELEMENTS, NODES_TRIA3) As Integer ' 要素内節点順配列
Dim D(COMPONENTS, COMPONENTS) As Double      ' Dマトリックス
Dim B(ELEMENTS, COMPONENTS, DOF_TRIA3) As Double ' Bマトリックス
Dim area_element(ELEMENTS) As Double         ' 要素面積の配列
Dim Ke(ELEMENTS, DOF_TRIA3, DOF_TRIA3) As Double ' 要素剛性マトリックス
Dim K(DOF_TOTAL, DOF_TOTAL) As Double        ' 全体剛性マトリックス
Dim U(DOF_TOTAL) As Double                   ' 全体変位ベクトル
Dim F(DOF_TOTAL) As Double                   ' 全体荷重ベクトル
Dim Um(DOF_TOTAL) As Boolean                 ' 拘束目印ベクトル
Dim Kc(DOF_TOTAL, DOF_TOTAL) As Double       ' 計算用全体剛性マトリックス
Dim Fr(DOF_TOTAL) As Double                  ' 節点反力ベクトル
Dim strain_element(ELEMENTS, COMPONENTS) As Double ' 要素ひずみベクトル
Dim stress_element(ELEMENTS, COMPONENTS) As Double ' 要素応力ベクトル

' ------------------
' メインプロシージャ
' ------------------
Sub simple_fem()            ' メインプロシージャ
    Call initialize              ' 配列を初期化
    Call make_D                  ' Dマトリックスを作成
    Call make_B                  ' Bマトリックスを作成
    Call make_Ke                 ' 要素剛性マトリックスを作成
    Call make_K                  ' 全体剛性マトリックスを作成
    Call set_boundary_condition  ' 境界条件処理
    Call solve                   ' 連立方程式を解く
    Call make_reaction           ' 節点反力を計算
    Call make_strain_element     ' 要素ひずみを計算
    Call make_stress_element     ' 要素応力を計算
End Sub

' ----------------------
' 配列初期化プロシージャ
' ----------------------
Sub initialize()
    ' 要素内節点順を設定
    connectivity(1, 1) = 1: connectivity(1, 2) = 2: connectivity(1, 3) = 5
    connectivity(2, 1) = 2: connectivity(2, 2) = 3: connectivity(2, 3) = 4
    connectivity(3, 1) = 2: connectivity(3, 2) = 4: connectivity(3, 3) = 5
    connectivity(4, 1) = 1: connectivity(4, 2) = 5: connectivity(4, 3) = 6
    
    ' 節点座標配列の設定
    x(1) = 0#: y(1) = 0#
    x(2) = 1#: y(2) = 0#
    x(3) = 2#: y(3) = 0#
    x(4) = 2#: y(4) = 1#
    x(5) = 1#: y(5) = 1#
    x(6) = 0#: y(6) = 1#

    ' 全体変位ベクトル
    U(1) = 0#: U(2) = 0#: U(3) = 0#: U(4) = 0#: U(5) = 0#: U(6) = 0#
    U(7) = 0#: U(8) = 0#: U(9) = 0#: U(10) = 0#: U(11) = 0#: U(12) = 0#

    ' 全体荷重ベクトル
    F(1) = 0#: F(2) = 0#: F(3) = 0#: F(4) = 0#: F(5) = 0#: F(6) = 0#
    F(7) = 0#: F(8) = -100#: F(9) = 0#: F(10) = 0#: F(11) = 0#: F(12) = 0#

    ' 拘束目印ベクトル
    Um(1) = True: Um(2) = True: Um(3) = False: Um(4) = False
    Um(5) = False: Um(6) = False: Um(7) = False: Um(8) = False
    Um(9) = False: Um(10) = False: Um(11) = True: Um(12) = False

End Sub

' -----------------------------
' Dマトリックス作成プロシージャ
' -----------------------------
Sub make_D()
    Dim coef As Double                  ' マトリックス成分に共通な係数
    coef = YOUNG / (1# - 2# * POISSON) / (1# + POISSON)
    
    D(1, 1) = coef * (1# - POISSON)     ' Dマトリックスを作成
    D(1, 2) = coef * POISSON
    D(1, 3) = 0#
    D(2, 1) = D(1, 2)
    D(2, 2) = coef * (1# - POISSON)
    D(2, 3) = 0#
    D(3, 1) = D(1, 3)
    D(3, 2) = D(2, 3)
    D(3, 3) = coef * (1# - 2# * POISSON) / 2#
End Sub

' -----------------------------
' Bマトリックス作成プロシージャ
' -----------------------------
Sub make_B()
    Dim e As Integer                    ' 要素番号カウンター
    
    For e = 1 To ELEMENTS               ' 要素ごとに処理
        ' 節点座標をローカル変数に代入
        Dim x1 As Double, y1 As Double
        Dim x2 As Double, y2 As Double
        Dim x3 As Double, y3 As Double
        x1 = x(connectivity(e, 1)): y1 = y(connectivity(e, 1))
        x2 = x(connectivity(e, 2)): y2 = y(connectivity(e, 2))
        x3 = x(connectivity(e, 3)): y3 = y(connectivity(e, 3))
    
        ' 要素面積を計算
        area_element(e) = (x1 * y2 - x1 * y3 + x2 * y3 - x2 * y1 + x3 * y1 - x3 * y2) / 2
        
        Dim coef As Double              ' マトリックス成分に共通な係数
        coef = 1# / area_element(e) / 2#
        
        B(e, 1, 1) = coef * (y2 - y3)   ' Bマトリックスを作成
        B(e, 1, 2) = 0#
        B(e, 1, 3) = coef * (y3 - y1)
        B(e, 1, 4) = 0#
        B(e, 1, 5) = coef * (y1 - y2)
        B(e, 1, 6) = 0#
        B(e, 2, 1) = 0#
        B(e, 2, 2) = coef * (x3 - x2)
        B(e, 2, 3) = 0#
        B(e, 2, 4) = coef * (x1 - x3)
        B(e, 2, 5) = 0#
        B(e, 2, 6) = coef * (x2 - x1)
        B(e, 3, 1) = B(e, 2, 2)
        B(e, 3, 2) = B(e, 1, 1)
        B(e, 3, 3) = B(e, 2, 4)
        B(e, 3, 4) = B(e, 1, 3)
        B(e, 3, 5) = B(e, 2, 6)
        B(e, 3, 6) = B(e, 1, 5)
    Next e
End Sub

' ------------------------------------
' 要素剛性マトリックス作成プロシージャ
' ------------------------------------
Sub make_Ke()
    Dim Dt(COMPONENTS, COMPONENTS) As Double   ' Dの転置マトリックス
    Dim Bt(DOF_TRIA3, COMPONENTS) As Double    ' Bの転置マトリックス
    Dim BtDt(DOF_TRIA3, COMPONENTS) As Double  ' Bt×Dtのマトリックス
    Dim e As Integer                    ' 要素番号カウンター
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    Dim m As Integer                    ' マトリックス掛け算用カウンター
    
    For r = 1 To COMPONENTS             ' Dの転置マトリックスDtを作成
        For c = 1 To COMPONENTS
            Dt(c, r) = D(r, c)
        Next c
    Next r
    
    For e = 1 To ELEMENTS               ' 要素ごとに処理
    
        For r = 1 To COMPONENTS         ' Bの転置マトリックスBtを作成
            For c = 1 To DOF_TRIA3
                Bt(c, r) = B(e, r, c)
            Next c
        Next r
    
        For r = 1 To DOF_TRIA3          ' Bt×Dt
            For c = 1 To COMPONENTS
                BtDt(r, c) = 0#
                For m = 1 To COMPONENTS
                    BtDt(r, c) = BtDt(r, c) + Bt(r, m) * Dt(m, c)
                Next m
            Next c
        Next r
    
        For r = 1 To DOF_TRIA3          ' Keの計算
            For c = 1 To DOF_TRIA3
                Ke(e, r, c) = 0#
                For m = 1 To COMPONENTS
                    Ke(e, r, c) = Ke(e, r, c) + BtDt(r, m) * B(e, m, c)
                Next m
                Ke(e, r, c) = Ke(e, r, c) * area_element(e) * THICKNESS
            Next c
        Next r
    Next e
End Sub

' ------------------------------------
' 全体剛性マトリックス作成プロシージャ
' ------------------------------------
Sub make_K()
    Dim e As Integer                    ' 要素番号カウンター
    Dim r As Integer, c As Integer      ' 要素剛性マトリックスの行と列のカウンター
    Dim rt As Integer, ct As Integer    ' 全体剛性マトリックスの行と列のカウンター
    
    For rt = 1 To DOF_TOTAL             ' 全体剛性マトリックスの成分を初期化
        For ct = 1 To DOF_TOTAL
            K(rt, ct) = 0#
        Next ct
    Next rt
    
    For e = 1 To ELEMENTS               ' 要素ごとにKeの成分をKに足し込む
        For r = 1 To DOF_TRIA3
            rt = connectivity(e, (r + 1) \ DOF_NODE) * DOF_NODE - (r Mod DOF_NODE)
            For c = 1 To DOF_TRIA3
                ct = connectivity(e, (c + 1) \ DOF_NODE) * DOF_NODE - (c Mod DOF_NODE)
                K(rt, ct) = K(rt, ct) + Ke(e, r, c)
            Next c
        Next r
    Next e
End Sub

' ------------------------
' 境界条件処理プロシージャ
' ------------------------
Sub set_boundary_condition()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    Dim rr As Integer, cc As Integer    ' マトリックスの行と列のカウンター
    
    For r = 1 To DOF_TOTAL              ' 全体剛性マトリックスのコピーを作成
        For c = 1 To DOF_TOTAL
            Kc(r, c) = K(r, c)
        Next c
    Next r

    For r = 1 To DOF_TOTAL              ' 行方向に順に処理
        If Um(r) = True Then            ' 変位が拘束されている成分に対する処理
            For rr = 1 To DOF_TOTAL     ' 変位拘束成分以外の荷重ベクトルを修正
                If rr <> r Then
                    F(rr) = F(rr) - Kc(rr, r) * U(r)
                End If
            Next rr
            
            For rr = 1 To DOF_TOTAL     ' 変位拘束が存在する行の成分を0にする
                Kc(rr, r) = 0#
            Next rr
            
            For cc = 1 To DOF_TOTAL     ' 変位拘束が存在する列の成分を0にする
                Kc(r, cc) = 0#
            Next cc
            
            Kc(r, r) = 1#               ' 対角成分を1にする
            F(r) = U(r)                 ' 変位拘束成分に対応する荷重ベクトルを修正
        End If
    Next r
End Sub

' --------------------------------------
' ガウスの消去法によるソルバプロシージャ
' --------------------------------------
Sub solve()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    Dim rr As Integer, cc As Integer    ' マトリックスの行と列のカウンター
    Dim pivot As Double                 ' マトリックスの対角成分
    Dim p As Double                     ' 計算に使用するマトリックスの成分
    
    For r = 1 To DOF_TOTAL              ' 前進消去
        pivot = Kc(r, r)                ' 対角成分をpivotに代入
        
        For c = r To DOF_TOTAL          ' r行目の処理
            Kc(r, c) = Kc(r, c) / pivot
        Next c
        F(r) = F(r) / pivot
        
        For rr = r + 1 To DOF_TOTAL     ' r+1行目以下の処理
            p = Kc(rr, r)
            For cc = r To DOF_TOTAL
                Kc(rr, cc) = Kc(rr, cc) - p * Kc(r, cc)
            Next cc
            F(rr) = F(rr) - p * F(r)
       Next rr
    Next r

    For r = DOF_TOTAL To 1 Step -1      ' 後退代入
        U(r) = F(r)
        For c = r + 1 To DOF_TOTAL
            U(r) = U(r) - Kc(r, c) * U(c)
        Next c
    Next r
End Sub

' --------------------
' 節点反力プロシージャ
' --------------------
Sub make_reaction()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    
    For r = 1 To DOF_TOTAL              ' 節点反力の計算 (K×U)
        Fr(r) = 0#
        For c = 1 To DOF_TOTAL
            Fr(r) = Fr(r) + K(r, c) * U(c)
        Next c
    Next r
End Sub

' ----------------------
' 要素ひずみプロシージャ
' ----------------------
Sub make_strain_element()
    Dim Ue(DOF_TRIA3) As Double         ' 要素内節点変位ベクトル
    Dim e As Integer                    ' 要素番号カウンター
    Dim n As Integer                    ' 節点番号カウンター
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    
    For e = 1 To ELEMENTS               ' 要素ごとに要素ひずみを計算
    
        For n = 1 To NODES_TRIA3        ' 要素内節点変位を計算
            Ue(n * 2 - 1) = U(connectivity(e, n) * 2 - 1)  ' x成分
            Ue(n * 2) = U(connectivity(e, n) * 2)          ' y成分
        Next n
    
        For r = 1 To COMPONENTS         ' 要素のひずみを計算 (B×Ue)
            strain_element(e, r) = 0#
            For c = 1 To DOF_TRIA3
                strain_element(e, r) = strain_element(e, r) + B(e, r, c) * Ue(c)
            Next c
        Next r
    Next e
End Sub

' --------------------
' 要素応力プロシージャ
' --------------------
Sub make_stress_element()
    Dim e As Integer                    ' 要素番号カウンター
    Dim r As Integer, c As Integer      ' マトリックスの行と列のカウンター
    
    For e = 1 To ELEMENTS               ' 要素ごとに要素応力を計算 (D×strain_element)
        For r = 1 To COMPONENTS
            stress_element(e, r) = 0#
            For c = 1 To COMPONENTS
                stress_element(e, r) = stress_element(e, r) _
                                     + D(r, c) * strain_element(e, c)
            Next c
        Next r
    Next e
End Sub


