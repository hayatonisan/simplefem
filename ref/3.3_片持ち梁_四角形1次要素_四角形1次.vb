Attribute VB_Name = "四角形1次"
' *********************************************************************
'
' 　第3章　高度な2次元プログラミング
'          四角形1次要素／平面ひずみ
'         （片持ち梁モデル）
'
'   作者：青木 伸輔（第3章担当）
'   更新：2014/06/22 Version 1.0 初版
'
' *********************************************************************
' 【書籍との差異】
'　- - - - - - - -
'　①Privateキーワードの追加
'　 エクセルからマクロ一覧を表示したときに，メインプロシージャ以外のプロシージャを表示させないために使用しています
'　 これに合わせ，変数・定数にもPrivateキーワードを付与しています。
'   なお，このプログラムでは，Privateの有無によって計算結果が影響を受けることはありません。
'
'　②結果ファイルの出力処理の追加
'    計算結果ファイルを，エクセルと同一フォルダに書き出す処理(print_resultプロシージャ)を追加しています
' *********************************************************************


Option Base 1
Option Explicit

' =====================================================================
' モジュール定数
' =====================================================================
Private Const THICKNESS As Double = 0.01                                ' 要素の厚さ
Private Const YOUNG   As Double = 210000                                ' ヤング率
Private Const POISSON As Double = 0#                                    ' ポアソン比

Private Const NODES As Integer = 55                                     ' 全節点数
Private Const ELEMENTS As Integer = 40                                  ' 全要素数

Private Const INTEGRAL_POINTS4 As Integer = 4                           ' 要素の積分点数
Private Const NODES_QUAD4 As Integer = 4                                ' 要素の節点数

Private Const COMPONENTS As Integer = 3                                 ' 要素の成分数
Private Const DOF_NODE As Integer = 2                                   ' 節点の自由度
Private Const DOF_TOTAL As Integer = NODES * DOF_NODE                   ' モデル全体の自由度
Private Const DOF_QUAD4 As Integer = NODES_QUAD4 * DOF_NODE             ' 要素の自由度

Private Const RESULT_FILE_TITLE As String = "result-quad4"              ' 結果ファイルのファイルタイトル
Private Const RESULT_FORMAT As String = "0.000000000000000E+00"         ' 結果ファイルへの書き出しフォーマット


' =====================================================================
' モジュール変数
' =====================================================================
Private x(NODES) As Double                                              ' 節点のx座標
Private y(NODES) As Double                                              ' 節点のy座標
Private connectivity(ELEMENTS, NODES_QUAD4) As Integer                  ' 要素内節点番号

Private ip_xi(INTEGRAL_POINTS4) As Double                               ' 積分点座標ξ
Private ip_et(INTEGRAL_POINTS4) As Double                               ' 積分点座標η
Private ip_wi(INTEGRAL_POINTS4) As Double                               ' 積分点重みξ方向
Private ip_wj(INTEGRAL_POINTS4) As Double                               ' 積分点座標η方向

Private D(COMPONENTS, COMPONENTS) As Double                             ' Dマトリックス
Private B(ELEMENTS, INTEGRAL_POINTS4, COMPONENTS, DOF_QUAD4) As Double  ' Bマトリックス
Private detJ(ELEMENTS, INTEGRAL_POINTS4) As Double                      ' |J|
Private Ke(ELEMENTS, DOF_QUAD4, DOF_QUAD4) As Double                    ' 要素剛性マトリックス
Private strain_ip(ELEMENTS, INTEGRAL_POINTS4, COMPONENTS) As Double     ' 積分点 ひずみベクトル
Private stress_ip(ELEMENTS, INTEGRAL_POINTS4, COMPONENTS) As Double     ' 積分点 応力ベクトル

Private K(DOF_TOTAL, DOF_TOTAL) As Double                               ' 全体剛性マトリックス
Private U(DOF_TOTAL) As Double                                          ' 変位ベクトル
Private F(DOF_TOTAL) As Double                                          ' 荷重ベクトル
Private Um(DOF_TOTAL) As Boolean                                        ' 拘束目印
Private Kc(DOF_TOTAL, DOF_TOTAL) As Double                              ' 求解用全体剛性マトリックス
Private Fr(DOF_TOTAL) As Double                                         ' 反力ベクトル


' =====================================================================
' メインプロシージャ
' =====================================================================
Sub simple_fem_quad4()
    Call initialize             ' データを初期化
    Call make_D                 ' Dマトリックスを作成
    Call make_B                 ' Bマトリックスを作成
    Call make_Ke                ' 要素剛性マトリックスを作成
    Call make_K                 ' 全体剛性マトリックスを作成
    Call set_bondary_condition  ' 境界条件処理
    Call solve                  ' 連立方程式を解く
    Call make_reaction          ' 節点反力の計算
    Call make_strain            ' 積分点ひずみの計算
    Call make_stress            ' 積分点応力の計算
    Call print_result           ' 結果の印字
End Sub


' =====================================================================
' データ初期化プロシージャ
' =====================================================================
Private Sub initialize()

    ' 配列消去
     Erase D()
     Erase B()
     Erase detJ()
     Erase Ke()
     Erase K()
     Erase U()
     Erase F()
     Erase Um()
     Erase Kc()
     Erase Fr()
     Erase strain_ip()
     Erase stress_ip()
     
    ' 要素内節点番号の配列
    connectivity(1, 1) = 1: connectivity(1, 2) = 2: connectivity(1, 3) = 13: connectivity(1, 4) = 12:
    connectivity(2, 1) = 2: connectivity(2, 2) = 3: connectivity(2, 3) = 14: connectivity(2, 4) = 13:
    connectivity(3, 1) = 3: connectivity(3, 2) = 4: connectivity(3, 3) = 15: connectivity(3, 4) = 14:
    connectivity(4, 1) = 4: connectivity(4, 2) = 5: connectivity(4, 3) = 16: connectivity(4, 4) = 15:
    connectivity(5, 1) = 5: connectivity(5, 2) = 6: connectivity(5, 3) = 17: connectivity(5, 4) = 16:
    connectivity(6, 1) = 6: connectivity(6, 2) = 7: connectivity(6, 3) = 18: connectivity(6, 4) = 17:
    connectivity(7, 1) = 7: connectivity(7, 2) = 8: connectivity(7, 3) = 19: connectivity(7, 4) = 18:
    connectivity(8, 1) = 8: connectivity(8, 2) = 9: connectivity(8, 3) = 20: connectivity(8, 4) = 19:
    connectivity(9, 1) = 9: connectivity(9, 2) = 10: connectivity(9, 3) = 21: connectivity(9, 4) = 20:
    connectivity(10, 1) = 10: connectivity(10, 2) = 11: connectivity(10, 3) = 22: connectivity(10, 4) = 21:
    connectivity(11, 1) = 12: connectivity(11, 2) = 13: connectivity(11, 3) = 24: connectivity(11, 4) = 23:
    connectivity(12, 1) = 13: connectivity(12, 2) = 14: connectivity(12, 3) = 25: connectivity(12, 4) = 24:
    connectivity(13, 1) = 14: connectivity(13, 2) = 15: connectivity(13, 3) = 26: connectivity(13, 4) = 25:
    connectivity(14, 1) = 15: connectivity(14, 2) = 16: connectivity(14, 3) = 27: connectivity(14, 4) = 26:
    connectivity(15, 1) = 16: connectivity(15, 2) = 17: connectivity(15, 3) = 28: connectivity(15, 4) = 27:
    connectivity(16, 1) = 17: connectivity(16, 2) = 18: connectivity(16, 3) = 29: connectivity(16, 4) = 28:
    connectivity(17, 1) = 18: connectivity(17, 2) = 19: connectivity(17, 3) = 30: connectivity(17, 4) = 29:
    connectivity(18, 1) = 19: connectivity(18, 2) = 20: connectivity(18, 3) = 31: connectivity(18, 4) = 30:
    connectivity(19, 1) = 20: connectivity(19, 2) = 21: connectivity(19, 3) = 32: connectivity(19, 4) = 31:
    connectivity(20, 1) = 21: connectivity(20, 2) = 22: connectivity(20, 3) = 33: connectivity(20, 4) = 32:
    connectivity(21, 1) = 23: connectivity(21, 2) = 24: connectivity(21, 3) = 35: connectivity(21, 4) = 34:
    connectivity(22, 1) = 24: connectivity(22, 2) = 25: connectivity(22, 3) = 36: connectivity(22, 4) = 35:
    connectivity(23, 1) = 25: connectivity(23, 2) = 26: connectivity(23, 3) = 37: connectivity(23, 4) = 36:
    connectivity(24, 1) = 26: connectivity(24, 2) = 27: connectivity(24, 3) = 38: connectivity(24, 4) = 37:
    connectivity(25, 1) = 27: connectivity(25, 2) = 28: connectivity(25, 3) = 39: connectivity(25, 4) = 38:
    connectivity(26, 1) = 28: connectivity(26, 2) = 29: connectivity(26, 3) = 40: connectivity(26, 4) = 39:
    connectivity(27, 1) = 29: connectivity(27, 2) = 30: connectivity(27, 3) = 41: connectivity(27, 4) = 40:
    connectivity(28, 1) = 30: connectivity(28, 2) = 31: connectivity(28, 3) = 42: connectivity(28, 4) = 41:
    connectivity(29, 1) = 31: connectivity(29, 2) = 32: connectivity(29, 3) = 43: connectivity(29, 4) = 42:
    connectivity(30, 1) = 32: connectivity(30, 2) = 33: connectivity(30, 3) = 44: connectivity(30, 4) = 43:
    connectivity(31, 1) = 34: connectivity(31, 2) = 35: connectivity(31, 3) = 46: connectivity(31, 4) = 45:
    connectivity(32, 1) = 35: connectivity(32, 2) = 36: connectivity(32, 3) = 47: connectivity(32, 4) = 46:
    connectivity(33, 1) = 36: connectivity(33, 2) = 37: connectivity(33, 3) = 48: connectivity(33, 4) = 47:
    connectivity(34, 1) = 37: connectivity(34, 2) = 38: connectivity(34, 3) = 49: connectivity(34, 4) = 48:
    connectivity(35, 1) = 38: connectivity(35, 2) = 39: connectivity(35, 3) = 50: connectivity(35, 4) = 49:
    connectivity(36, 1) = 39: connectivity(36, 2) = 40: connectivity(36, 3) = 51: connectivity(36, 4) = 50:
    connectivity(37, 1) = 40: connectivity(37, 2) = 41: connectivity(37, 3) = 52: connectivity(37, 4) = 51:
    connectivity(38, 1) = 41: connectivity(38, 2) = 42: connectivity(38, 3) = 53: connectivity(38, 4) = 52:
    connectivity(39, 1) = 42: connectivity(39, 2) = 43: connectivity(39, 3) = 54: connectivity(39, 4) = 53:
    connectivity(40, 1) = 43: connectivity(40, 2) = 44: connectivity(40, 3) = 55: connectivity(40, 4) = 54:
    
    ' 節点座標配列
    x(1) = 0: y(1) = 0
    x(2) = 5: y(2) = 0
    x(3) = 10: y(3) = 0
    x(4) = 15: y(4) = 0
    x(5) = 20: y(5) = 0
    x(6) = 25: y(6) = 0
    x(7) = 30: y(7) = 0
    x(8) = 35: y(8) = 0
    x(9) = 40: y(9) = 0
    x(10) = 45: y(10) = 0
    x(11) = 50: y(11) = 0
    x(12) = 0: y(12) = 0.5
    x(13) = 5: y(13) = 0.5
    x(14) = 10: y(14) = 0.5
    x(15) = 15: y(15) = 0.5
    x(16) = 20: y(16) = 0.5
    x(17) = 25: y(17) = 0.5
    x(18) = 30: y(18) = 0.5
    x(19) = 35: y(19) = 0.5
    x(20) = 40: y(20) = 0.5
    x(21) = 45: y(21) = 0.5
    x(22) = 50: y(22) = 0.5
    x(23) = 0: y(23) = 1
    x(24) = 5: y(24) = 1
    x(25) = 10: y(25) = 1
    x(26) = 15: y(26) = 1
    x(27) = 20: y(27) = 1
    x(28) = 25: y(28) = 1
    x(29) = 30: y(29) = 1
    x(30) = 35: y(30) = 1
    x(31) = 40: y(31) = 1
    x(32) = 45: y(32) = 1
    x(33) = 50: y(33) = 1
    x(34) = 0: y(34) = 1.5
    x(35) = 5: y(35) = 1.5
    x(36) = 10: y(36) = 1.5
    x(37) = 15: y(37) = 1.5
    x(38) = 20: y(38) = 1.5
    x(39) = 25: y(39) = 1.5
    x(40) = 30: y(40) = 1.5
    x(41) = 35: y(41) = 1.5
    x(42) = 40: y(42) = 1.5
    x(43) = 45: y(43) = 1.5
    x(44) = 50: y(44) = 1.5
    x(45) = 0: y(45) = 2
    x(46) = 5: y(46) = 2
    x(47) = 10: y(47) = 2
    x(48) = 15: y(48) = 2
    x(49) = 20: y(49) = 2
    x(50) = 25: y(50) = 2
    x(51) = 30: y(51) = 2
    x(52) = 35: y(52) = 2
    x(53) = 40: y(53) = 2
    x(54) = 45: y(54) = 2
    x(55) = 50: y(55) = 2


    ' 変位拘束
    Dim FixNode(5) As Integer
    FixNode(1) = 1
    FixNode(2) = 12
    FixNode(3) = 23
    FixNode(4) = 34
    FixNode(5) = 45
    
    Dim i As Integer
    Dim dof As Integer
    For i = 1 To UBound(FixNode)
        Dim node As Integer
        node = FixNode(i)
        
        For dof = 1 To DOF_NODE
            Dim index As Integer
            index = (node - 1) * DOF_NODE + dof
            U(index) = 0
            Um(index) = True
        Next dof
    Next i
    

    ' 荷重ベクトル
    F((11 - 1) * DOF_NODE + 2) = -0.0125
    F((22 - 1) * DOF_NODE + 2) = -0.025
    F((33 - 1) * DOF_NODE + 2) = -0.025
    F((44 - 1) * DOF_NODE + 2) = -0.025
    F((55 - 1) * DOF_NODE + 2) = -0.0125

    ' 積分点座標
    ip_xi(1) = -1 / Sqr(3): ip_et(1) = -1 / Sqr(3)
    ip_xi(2) = 1 / Sqr(3): ip_et(2) = -1 / Sqr(3)
    ip_xi(3) = -1 / Sqr(3): ip_et(3) = 1 / Sqr(3)
    ip_xi(4) = 1 / Sqr(3): ip_et(4) = 1 / Sqr(3)
    
    ' 積分点重み
    ip_wi(1) = 1#: ip_wj(1) = 1#
    ip_wi(2) = 1#: ip_wj(2) = 1#
    ip_wi(3) = 1#: ip_wj(3) = 1#
    ip_wi(4) = 1#: ip_wj(4) = 1#
    
End Sub


' =====================================================================
' Dマトリックス作成プロシージャ (平面ひずみ)
' =====================================================================
Private Sub make_D()
    Dim coef As Double
    
    coef = YOUNG / (1# - 2# * POISSON) / (1# + POISSON) ' マトリックスの成分に共通な係数
    D(1, 1) = coef * (1# - POISSON)
    D(1, 2) = coef * POISSON
    D(1, 3) = 0#
    D(2, 1) = D(1, 2)
    D(2, 2) = coef * (1# - POISSON)
    D(2, 3) = 0#
    D(3, 1) = D(1, 3)
    D(3, 2) = D(2, 3)
    D(3, 3) = coef * (1# - 2# * POISSON) / 2#
End Sub


' =====================================================================
' 全要素のBマトリックス[B]の計算
' =====================================================================
Private Sub make_B()
        
    ' 要素ループ
    Dim e As Integer
    For e = 1 To ELEMENTS
    
        ' 節点座標の取得（既知パラメータ）
        Dim x1 As Double, y1 As Double
        Dim x2 As Double, y2 As Double
        Dim x3 As Double, y3 As Double
        Dim x4 As Double, y4 As Double
        x1 = x(connectivity(e, 1)): y1 = y(connectivity(e, 1))
        x2 = x(connectivity(e, 2)): y2 = y(connectivity(e, 2))
        x3 = x(connectivity(e, 3)): y3 = y(connectivity(e, 3))
        x4 = x(connectivity(e, 4)): y4 = y(connectivity(e, 4))
    
        ' 積分点ループ
        Dim ip As Integer
        For ip = 1 To INTEGRAL_POINTS4
            
            ' 積分点座標の取得（既知パラメータ）
            Dim xi As Double, et As Double
            xi = ip_xi(ip)
            et = ip_et(ip)
            
            ' ① ∂Ｎi/∂ξ，∂Ｎi/∂η
            Dim dN1dXi As Double, dN1dEt As Double
            Dim dN2dXi As Double, dN2dEt As Double
            Dim dN3dXi As Double, dN3dEt As Double
            Dim dN4dXi As Double, dN4dEt As Double
            dN1dXi = -(1 - et) / 4
            dN2dXi = (1 - et) / 4
            dN3dXi = (1 + et) / 4
            dN4dXi = -(1 + et) / 4
            
            dN1dEt = -(1 - xi) / 4
            dN2dEt = -(1 + xi) / 4
            dN3dEt = (1 + xi) / 4
            dN4dEt = (1 - xi) / 4
            
            ' ② ∂ｘ/∂ξ，∂ｘ/∂η，∂ｙ/∂ξ，∂ｙ/∂η
            Dim dXdXi As Double, dXdEt As Double
            Dim dYdXi As Double, dYdEt As Double
            dXdXi = dN1dXi * x1 + dN2dXi * x2 + dN3dXi * x3 + dN4dXi * x4
            dYdXi = dN1dXi * y1 + dN2dXi * y2 + dN3dXi * y3 + dN4dXi * y4
            dXdEt = dN1dEt * x1 + dN2dEt * x2 + dN3dEt * x3 + dN4dEt * x4
            dYdEt = dN1dEt * y1 + dN2dEt * y2 + dN3dEt * y3 + dN4dEt * y4
        
            ' ③ |J|
            detJ(e, ip) = dXdXi * dYdEt - dYdXi * dXdEt
            
            ' ④ ∂Ｎi/∂x, ∂Ｎi/∂y
            Dim dN1dX As Double, dN1dY As Double
            Dim dN2dX As Double, dN2dY As Double
            Dim dN3dX As Double, dN3dY As Double
            Dim dN4dX As Double, dN4dY As Double
            dN1dX = (dN1dXi * dYdEt - dN1dEt * dYdXi) / detJ(e, ip)
            dN2dX = (dN2dXi * dYdEt - dN2dEt * dYdXi) / detJ(e, ip)
            dN3dX = (dN3dXi * dYdEt - dN3dEt * dYdXi) / detJ(e, ip)
            dN4dX = (dN4dXi * dYdEt - dN4dEt * dYdXi) / detJ(e, ip)
            dN1dY = (-dN1dXi * dXdEt + dN1dEt * dXdXi) / detJ(e, ip)
            dN2dY = (-dN2dXi * dXdEt + dN2dEt * dXdXi) / detJ(e, ip)
            dN3dY = (-dN3dXi * dXdEt + dN3dEt * dXdXi) / detJ(e, ip)
            dN4dY = (-dN4dXi * dXdEt + dN4dEt * dXdXi) / detJ(e, ip)

            ' ⑤ [B]
            B(e, ip, 1, 1) = dN1dX
            B(e, ip, 1, 2) = 0
            B(e, ip, 1, 3) = dN2dX
            B(e, ip, 1, 4) = 0
            B(e, ip, 1, 5) = dN3dX
            B(e, ip, 1, 6) = 0
            B(e, ip, 1, 7) = dN4dX
            B(e, ip, 1, 8) = 0
            B(e, ip, 2, 1) = 0
            B(e, ip, 2, 2) = dN1dY
            B(e, ip, 2, 3) = 0
            B(e, ip, 2, 4) = dN2dY
            B(e, ip, 2, 5) = 0
            B(e, ip, 2, 6) = dN3dY
            B(e, ip, 2, 7) = 0
            B(e, ip, 2, 8) = dN4dY
            B(e, ip, 3, 1) = dN1dY
            B(e, ip, 3, 2) = dN1dX
            B(e, ip, 3, 3) = dN2dY
            B(e, ip, 3, 4) = dN2dX
            B(e, ip, 3, 5) = dN3dY
            B(e, ip, 3, 6) = dN3dX
            B(e, ip, 3, 7) = dN4dY
            B(e, ip, 3, 8) = dN4dX
                      
          Next ip
          
    Next e
    
End Sub


' =====================================================================
' 全要素の要素剛性マトリックス[Ke]の計算
' =====================================================================
Private Sub make_Ke()
    Dim r As Integer
    Dim c As Integer
    Dim i As Integer

    ' 全要素の[Ke]ループ
    Dim e As Integer
    For e = 1 To ELEMENTS

        ' 積分点[Ke]マトリクスと要素Kマトリクスの計算
        Dim ip As Integer
        For ip = 1 To INTEGRAL_POINTS4
    
            ' [B]tの計算
            Dim Bt(DOF_QUAD4, COMPONENTS) As Double
            For r = 1 To COMPONENTS
                For c = 1 To DOF_QUAD4
                    Bt(c, r) = B(e, ip, r, c)
                Next c
            Next r
            
            ' [D]tの計算
            Dim Dt(COMPONENTS, COMPONENTS) As Double
            For r = 1 To COMPONENTS
                For c = 1 To COMPONENTS
                    Dt(c, r) = D(r, c)
                Next c
            Next r
            
            ' [B]t*[D]tの計算
            Dim BtDt(DOF_QUAD4, COMPONENTS) As Double
            For r = 1 To DOF_QUAD4
               For c = 1 To COMPONENTS
                    BtDt(r, c) = 0#
                    For i = 1 To COMPONENTS
                        BtDt(r, c) = BtDt(r, c) + Bt(r, i) * Dt(i, c)
                    Next i
                Next c
            Next r
    
            ' 積分点[Ke]マトリクスの計算 Kep=((Bt*Dt)*B)*J*Wi*Wj*t
            Dim Kep(DOF_QUAD4, DOF_QUAD4) As Double
            For r = 1 To DOF_QUAD4
                For c = 1 To DOF_QUAD4
                    Kep(r, c) = 0#
                    For i = 1 To COMPONENTS
                        Kep(r, c) = Kep(r, c) + BtDt(r, i) * B(e, ip, i, c)
                    Next i
                    Dim wi As Double, wj As Double
                    wi = ip_wi(ip)
                    wj = ip_wj(ip)
                    Kep(r, c) = Kep(r, c) * detJ(e, ip) * wi * wj * THICKNESS
                Next c
            Next r
    
            ' 要素[Ke]マトリクスの計算 K=ΣKep
            For r = 1 To DOF_QUAD4
                For c = 1 To DOF_QUAD4
                    Ke(e, r, c) = Ke(e, r, c) + Kep(r, c)
                Next c
            Next r
            
        Next ip
        
    Next e
    
End Sub


' =====================================================================
' 全体Kマトリクス作成プロシージャ
' =====================================================================
Private Sub make_K()
    Dim e As Integer
    Dim r As Integer
    Dim c As Integer
    Dim nr As Integer
    Dim nc As Double
    
    For e = 1 To ELEMENTS
        For r = 1 To NODES_QUAD4
            nr = connectivity(e, r)
            For c = 1 To NODES_QUAD4
                nc = connectivity(e, c)
                K(nr * 2 - 1, nc * 2 - 1) _
                    = K(nr * 2 - 1, nc * 2 - 1) + Ke(e, r * 2 - 1, c * 2 - 1)
                K(nr * 2 - 1, nc * 2) _
                    = K(nr * 2 - 1, nc * 2) + Ke(e, r * 2 - 1, c * 2)
                K(nr * 2, nc * 2 - 1) _
                    = K(nr * 2, nc * 2 - 1) + Ke(e, r * 2, c * 2 - 1)
                K(nr * 2, nc * 2) _
                    = K(nr * 2, nc * 2) + Ke(e, r * 2, c * 2)
            Next c
        Next r
    Next e
End Sub


' =====================================================================
' 境界条件処理プロシージャ
' =====================================================================
Private Sub set_bondary_condition()
    Dim r As Integer
    Dim c As Integer
    Dim rr As Integer
    Dim cc As Integer
   
    ' 全体剛性マトリックスのコピーを作成
    For r = 1 To DOF_TOTAL
        For c = 1 To DOF_TOTAL
            Kc(r, c) = K(r, c)
        Next c
    Next r

    For r = 1 To DOF_TOTAL

        ' 変位が拘束されている自由度に対する処理
        If Um(r) = True Then
            ' 変位拘束自由度以外の荷重ベクトルを修正
            For rr = 1 To DOF_TOTAL
                If rr <> r Then
                    F(rr) = F(rr) - Kc(rr, r) * U(r)
                End If
            Next rr
            
            ' 全体剛性マトリックスの変位拘束がある行と列を0にする(対角成分のみ1)
            For rr = 1 To DOF_TOTAL
                Kc(rr, r) = 0#
            Next rr
            For cc = 1 To DOF_TOTAL
                Kc(r, cc) = 0#
            Next cc
            Kc(r, r) = 1#

            ' 変位拘束自由度の荷重ベクトルを修正
            F(r) = U(r)
        End If
    Next r
End Sub


' =====================================================================
' ガウスの消去法によるソルバプロシージャ
' =====================================================================
Private Sub solve()
    Dim r As Integer
    Dim c As Integer
    Dim rr As Integer
    Dim p As Double
    Dim pp As Double
    Dim cc As Double
   
    ' 前進消去
    For r = 1 To DOF_TOTAL
        p = Kc(r, r)
        For c = r To DOF_TOTAL
            Kc(r, c) = Kc(r, c) / p
        Next c
        F(r) = F(r) / p
        
        For rr = r + 1 To DOF_TOTAL
            pp = Kc(rr, r)
            For cc = r To DOF_TOTAL
                Kc(rr, cc) = Kc(rr, cc) - pp * Kc(r, cc)
            Next cc
            F(rr) = F(rr) - pp * F(r)
       Next rr
    Next r

    ' 後退代入
    For r = DOF_TOTAL To 1 Step -1
        U(r) = F(r)
        For c = r + 1 To DOF_TOTAL
            U(r) = U(r) - Kc(r, c) * U(c)
        Next c
    Next r
End Sub


' =====================================================================
' 反力プロシージャ
' =====================================================================
Private Sub make_reaction()
    Dim r As Integer
    Dim c As Integer
    
    For r = 1 To DOF_TOTAL
        For c = 1 To DOF_TOTAL
            Fr(r) = Fr(r) + K(r, c) * U(c)
        Next c
    Next r
End Sub


' =====================================================================
' ひずみプロシージャ
' =====================================================================
Private Sub make_strain()
    Dim e As Integer
    Dim ip As Integer
    Dim r As Integer
    Dim c As Integer
    Dim n As Integer
    Dim Ue(DOF_QUAD4) As Double
    
    For e = 1 To ELEMENTS
        For ip = 1 To INTEGRAL_POINTS4
            ' 要素内節点変位を計算
            For n = 1 To NODES_QUAD4
                Ue(n * 2 - 1) = U(connectivity(e, n) * 2 - 1)   ' x成分
                Ue(n * 2) = U(connectivity(e, n) * 2)           ' y成分
            Next n
            
            ' 積分点のひずみを計算
            For r = 1 To COMPONENTS
                For c = 1 To DOF_QUAD4
                    strain_ip(e, ip, r) = strain_ip(e, ip, r) + B(e, ip, r, c) * Ue(c)
                Next c
            Next r
        Next ip
    Next e
End Sub


' =====================================================================
' 応力プロシージャ
' =====================================================================
Private Sub make_stress()
    Dim e As Integer
    Dim ip As Integer
    Dim r As Integer
    Dim c As Integer
    Dim n As Integer
    
    For e = 1 To ELEMENTS
    
        ' 積分点の応力を計算
        For ip = 1 To INTEGRAL_POINTS4
            For r = 1 To COMPONENTS
                For c = 1 To COMPONENTS
                    stress_ip(e, ip, r) = stress_ip(e, ip, r) + D(r, c) * strain_ip(e, ip, c)
                Next c
            Next r
        Next ip
        
    Next e
End Sub


' =====================================================================
' 結果の表示
' =====================================================================
Private Sub print_result()
    Dim i As Integer
    Dim e As Integer
    Dim ip As Integer
    Dim n As Integer
    
    ' エクセルファイルパスと同じパスに結果ファイルを出力する
    ChDir ActiveWorkbook.Path
    Dim output_file_name As String
    output_file_name = RESULT_FILE_TITLE + ".txt"
    Open output_file_name For Output As #1

    Print #1, "====={Displacement@Node}================="
    For i = 1 To DOF_TOTAL Step DOF_NODE
        Print #1, (i + 1) / DOF_NODE, Format(U(i), RESULT_FORMAT), Format(U(i + 1), RESULT_FORMAT)
    Next i
    Print #1,
    
    Print #1, "====={ReactionForce@Node}================="
    For i = 1 To DOF_TOTAL Step DOF_NODE
        Print #1, (i + 1) / DOF_NODE, Format(Fr(i), RESULT_FORMAT), Format(Fr(i + 1), RESULT_FORMAT)
    Next i
    Print #1,
    
    Print #1, "====={Strain@IntegralPoint}================="
    For e = 1 To ELEMENTS
        For ip = 1 To INTEGRAL_POINTS4
            Print #1, e, ip,
            For i = 1 To COMPONENTS
                Print #1, Format(strain_ip(e, ip, i), RESULT_FORMAT),
            Next i
            Print #1,
        Next ip
    Next e
    Print #1,
    
    Print #1, "====={Stress@IntegralPoint}================="
    For e = 1 To ELEMENTS
        For ip = 1 To INTEGRAL_POINTS4
            Print #1, e, ip,
            For i = 1 To COMPONENTS
                Print #1, Format(stress_ip(e, ip, i), RESULT_FORMAT),
            Next i
            Print #1,
        Next ip
    Next e
    Print #1,
     
    Close

End Sub
