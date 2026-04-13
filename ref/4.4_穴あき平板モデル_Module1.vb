Attribute VB_Name = "Module1"
' *********************************************************************
'
' 　第4章 前処理・後処理
'       4.4 例題　穴あき平板
'
'   作者：日比　学（第4章担当）
'   更新：2014/06/22 Version 1.0 初版
'
' *********************************************************************

Option Base 1                           ' 配列のインデックスを1から始める
Option Explicit                         ' 変数の定義を強制する

' =====================================================================
' モジュール定数
' =====================================================================
Const NODES As Integer = 266                                            ' 全節点数
Const ELEMENTS As Integer = 75                                          ' 全要素数
Const THICKNESS As Double = 0.1                                         ' 要素の厚さ
Const YOUNG   As Double = 210000                                        ' ヤング率
Const POISSON As Double = 0.3                                           ' ポアソン比

Const INTEGRAL_POINTS9 As Integer = 9                                   ' 要素の積分点数
Const NODES_QUAD8 As Integer = 8                                        ' 要素の節点数
Const COMPONENTS As Integer = 3                                         ' 要素の成分数
Const DOF_NODE As Integer = 2                                           ' 節点の自由度
Const DOF_TOTAL As Integer = NODES * DOF_NODE                           ' モデル全体の自由度
Const DOF_QUAD8 As Integer = NODES_QUAD8 * DOF_NODE                     ' 要素の自由度

Const NFIXED As Integer = 32                                            ' 拘束条件の数
Const FACES As Integer = 5                                              ' 分布荷重条件の数

Const BX As Double = 0                                                  ' 物体力(x方向成分)
Const BY As Double = 0                                                  ' 物体力(y方向成分)

Const PLANE_STRESS As Integer = 1                                       ' 平面応力問題識別子
Const PLANE_STRAIN As Integer = 2                                       ' 平面ひずみ問題識別子

Const PLANE_TYPE As Integer = PLANE_STRESS                              ' 本問題は平面応力を選択

' =====================================================================
' モジュール変数
' =====================================================================
Dim x(NODES) As Double                                                  ' 節点のx座標配列
Dim y(NODES) As Double                                                  ' 節点のy座標配列
Dim connectivity(ELEMENTS, NODES_QUAD8) As Integer                      ' 要素内節点番号の配列

Dim ip_xi(INTEGRAL_POINTS9) As Double                                   ' 積分点座標ξ
Dim ip_et(INTEGRAL_POINTS9) As Double                                   ' 積分点座標η
Dim ip_wi(INTEGRAL_POINTS9) As Double                                   ' 積分点重みξ方向
Dim ip_wj(INTEGRAL_POINTS9) As Double                                   ' 積分点座標η方向


Dim D(COMPONENTS, COMPONENTS) As Double                                 ' Dマトリックス
Dim B(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS, DOF_QUAD8) As Double      ' Bマトリックス
Dim detJ(ELEMENTS, INTEGRAL_POINTS9) As Double                          ' |J|
Dim Ke(ELEMENTS, DOF_QUAD8, DOF_QUAD8) As Double                        ' 要素剛性マトリックス
Dim strain_ip(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS) As Double         ' 積分点 ひずみベクトル
Dim stress_ip(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS) As Double         ' 積分点 応力ベクトル

Dim K(DOF_TOTAL, DOF_TOTAL) As Double                                   ' 全体剛性マトリックス
Dim U(DOF_TOTAL) As Double                                              ' 変位ベクトル
Dim F(DOF_TOTAL) As Double                                              ' 荷重ベクトル
Dim Um(DOF_TOTAL) As Boolean                                            ' 拘束目印
Dim Kc(DOF_TOTAL, DOF_TOTAL) As Double                                  ' 求解用全体剛性マトリックス
Dim Fr(DOF_TOTAL) As Double                                             ' 反力ベクトル
 
Dim fixed(NFIXED, 2) As Integer                                         ' 拘束節点および自由度設定配列
Dim fixed_disp(NFIXED) As Double                                        ' 拘束変位設定配列

Dim face_element(FACES) As Integer                                      ' 分布荷重条件設定要素配列
Dim face_edge(FACES) As Integer                                         ' 分布荷重条件設定エッジ配列
Dim face_px(FACES) As Double                                            ' 分布荷重x方向成分
Dim face_py(FACES) As Double                                            ' 分布荷重y方向成分

Dim Feb(ELEMENTS, DOF_QUAD8) As Double                                  ' 等価節点力保持変数

Dim count_node(NODES) As Integer                                        ' 節点の要素接合数の配列
Dim stress_node(NODES, COMPONENTS) As Double                            ' 節点応力配列

Dim node_to_gauss_quad8(NODES_QUAD8) As Integer                         ' 節点近傍積分点配列
Dim stress_element(ELEMENTS, COMPONENTS) As Double                      ' 要素応力配列

' =====================================================================
' メインプロシージャ
' =====================================================================
Sub simple_fem_quad8()
    Call initialize                             ' データを初期化
    Call make_D                                 ' Dマトリックスを作成
    Call make_B                                 ' Bマトリックスを作成
    Call make_Ke                                ' 要素剛性マトリックスを作成
    Call make_K                                 ' 全体剛性マトリックスを作成
    Call calc_body_force_quad8                  ' 物体力の等価節点力計算
    Call add_body_force_quad8                   ' 物体力の等価節点力を足しこみ
    Call calc_surface_force_quad8               ' 表面力の等価節点力計算
    Call set_boundary_condition                 ' 境界条件処理
    Call solve                                  ' 連立方程式を解く
    Call make_reaction                          ' 節点反力の計算
    Call make_strain                            ' 積分点ひずみの計算
    Call make_stress                            ' 積分点応力の計算
    Call make_stress_node_quad8                 ' 節点応力の計算

    Call outputsheet2("節点応力", stress_node)  ' シート「節点応力」の節点応力を出力
End Sub

' =====================================================================
' データ初期化プロシージャ
' =====================================================================
Sub initialize()
   
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
   
    Call readmodel                              ' ワークシートより、節点・要素・拘束・荷重条件を読み取る。


   ' 積分点座標　※参照：図 3.7
    Dim ce As Double, cc As Double
    ce = Sqr(3 / 5): cc = 0
    ip_xi(1) = -ce:     ip_et(1) = -ce
    ip_xi(2) = cc:      ip_et(2) = -ce
    ip_xi(3) = ce:      ip_et(3) = -ce
    ip_xi(4) = -ce:     ip_et(4) = cc
    ip_xi(5) = cc:      ip_et(5) = cc
    ip_xi(6) = ce:      ip_et(6) = cc
    ip_xi(7) = -ce:     ip_et(7) = ce
    ip_xi(8) = cc:      ip_et(8) = ce
    ip_xi(9) = ce:      ip_et(9) = ce
    
    ' 積分点重み　※参照：図 3.7
    Dim we As Double, wc As Double
    we = 5 / 9:    wc = 8 / 9
    ip_wi(1) = we:      ip_wj(1) = we
    ip_wi(2) = wc:      ip_wj(2) = we
    ip_wi(3) = we:      ip_wj(3) = we
    ip_wi(4) = we:      ip_wj(4) = wc
    ip_wi(5) = wc:      ip_wj(5) = wc
    ip_wi(6) = we:      ip_wj(6) = wc
    ip_wi(7) = we:      ip_wj(7) = we
    ip_wi(8) = wc:      ip_wj(8) = we
    ip_wi(9) = we:      ip_wj(9) = we
End Sub

' =====================================================================
' Dマトリックス作成プロシージャ
' =====================================================================
Sub make_D()
    Dim coef As Double          ' マトリックス成分に共通な係数
    
    Select Case PLANE_TYPE
        Case PLANE_STRESS       ' 平面応力問題のDマトリックス
            coef = YOUNG / (1 - POISSON) / (1 + POISSON)
        
            D(1, 1) = coef * 1
            D(1, 2) = coef * POISSON
            D(1, 3) = 0#
            D(2, 1) = D(1, 2)
            D(2, 2) = coef * 1
            D(2, 3) = 0#
            D(3, 1) = D(1, 3)
            D(3, 2) = D(2, 3)
            D(3, 3) = coef * (1# - POISSON) / 2#
    
        Case PLANE_STRAIN       ' 平面ひずみ問題のDマトリックス
            coef = YOUNG / (1# - 2# * POISSON) / (1# + POISSON)
        
            D(1, 1) = coef * (1# - POISSON)
            D(1, 2) = coef * POISSON
            D(1, 3) = 0#
            D(2, 1) = D(1, 2)
            D(2, 2) = coef * (1# - POISSON)
            D(2, 3) = 0#
            D(3, 1) = D(1, 3)
            D(3, 2) = D(2, 3)
            D(3, 3) = coef * (1# - 2# * POISSON) / 2#
        End Select
End Sub

' =====================================================================
' 全要素のBマトリックス[B]の計算
' =====================================================================
Sub make_B()
    ' 要素ループ
    Dim e As Integer
    For e = 1 To ELEMENTS
        ' 節点座標の取得（既知パラメータ）
        Dim x1 As Double, y1 As Double
        Dim x2 As Double, y2 As Double
        Dim x3 As Double, y3 As Double
        Dim x4 As Double, y4 As Double
        Dim x5 As Double, y5 As Double
        Dim x6 As Double, y6 As Double
        Dim x7 As Double, y7 As Double
        Dim x8 As Double, y8 As Double
        x1 = x(connectivity(e, 1)): y1 = y(connectivity(e, 1))
        x2 = x(connectivity(e, 2)): y2 = y(connectivity(e, 2))
        x3 = x(connectivity(e, 3)): y3 = y(connectivity(e, 3))
        x4 = x(connectivity(e, 4)): y4 = y(connectivity(e, 4))
        x5 = x(connectivity(e, 5)): y5 = y(connectivity(e, 5))
        x6 = x(connectivity(e, 6)): y6 = y(connectivity(e, 6))
        x7 = x(connectivity(e, 7)): y7 = y(connectivity(e, 7))
        x8 = x(connectivity(e, 8)): y8 = y(connectivity(e, 8))
    
        ' 積分点ループ
        Dim ip As Integer
        For ip = 1 To INTEGRAL_POINTS9
            ' 積分点座標の取得（既知パラメータ）
            Dim xi As Double, et As Double
            xi = ip_xi(ip)
            et = ip_et(ip)
            
            ' ① ∂Ｎi/∂ξ、∂Ｎi/∂η　※参照： 式(3.37)、式(3.38)
            Dim dN1dXi As Double, dN1dEt As Double
            Dim dN2dXi As Double, dN2dEt As Double
            Dim dN3dXi As Double, dN3dEt As Double
            Dim dN4dXi As Double, dN4dEt As Double
            Dim dN5dXi As Double, dN5dEt As Double
            Dim dN6dXi As Double, dN6dEt As Double
            Dim dN7dXi As Double, dN7dEt As Double
            Dim dN8dXi As Double, dN8dEt As Double
            dN1dXi = (-(1 - et) * (-1 - xi - et) - (1 - xi) * (1 - et)) / 4
            dN2dXi = ((1 - et) * (-1 + xi - et) + (1 + xi) * (1 - et)) / 4
            dN3dXi = ((1 + et) * (-1 + xi + et) + (1 + xi) * (1 + et)) / 4
            dN4dXi = (-(1 + et) * (-1 - xi + et) - (1 - xi) * (1 + et)) / 4
            dN5dXi = (-2 * xi * (1 - et)) / 2
            dN6dXi = ((1 - et * et)) / 2
            dN7dXi = (-2 * xi * (1 + et)) / 2
            dN8dXi = (-(1 - et * et)) / 2
        
            dN1dEt = (-(1 - xi) * (-1 - xi - et) - (1 - xi) * (1 - et)) / 4
            dN2dEt = (-(1 + xi) * (-1 + xi - et) - (1 + xi) * (1 - et)) / 4
            dN3dEt = ((1 + xi) * (-1 + xi + et) + (1 + xi) * (1 + et)) / 4
            dN4dEt = ((1 - xi) * (-1 - xi + et) + (1 - xi) * (1 + et)) / 4
            dN5dEt = (-(1 - xi * xi)) / 2
            dN6dEt = (-2 * et * (1 + xi)) / 2
            dN7dEt = ((1 - xi * xi)) / 2
            dN8dEt = (-2 * et * (1 - xi)) / 2
            
            ' ② ∂ｘ/∂ξ、∂ｘ/∂η、∂ｙ/∂ξ、∂ｙ/∂η　※参照：式(3.36)
            Dim dXdXi As Double, dXdEt As Double
            Dim dYdXi As Double, dYdEt As Double
            dXdXi = dN1dXi * x1 + dN2dXi * x2 _
                   + dN3dXi * x3 + dN4dXi * x4 _
                   + dN5dXi * x5 + dN6dXi * x6 _
                   + dN7dXi * x7 + dN8dXi * x8
                  
            dYdXi = dN1dXi * y1 + dN2dXi * y2 _
                   + dN3dXi * y3 + dN4dXi * y4 _
                   + dN5dXi * y5 + dN6dXi * y6 _
                   + dN7dXi * y7 + dN8dXi * y8
             dXdEt = dN1dEt * x1 + dN2dEt * x2 _
                   + dN3dEt * x3 + dN4dEt * x4 _
                   + dN5dEt * x5 + dN6dEt * x6 _
                   + dN7dEt * x7 + dN8dEt * x8
                  
            dYdEt = dN1dEt * y1 + dN2dEt * y2 _
                   + dN3dEt * y3 + dN4dEt * y4 _
                   + dN5dEt * y5 + dN6dEt * y6 _
                   + dN7dEt * y7 + dN8dEt * y8
        
            ' ③ |J|　※参照：式(3.34)
            detJ(e, ip) = dXdXi * dYdEt - dYdXi * dXdEt
            
            ' ④ ∂Ｎi/∂x, ∂Ｎi/∂y　※参照：式(3.34)
            Dim dN1dX As Double, dN1dY As Double
            Dim dN2dX As Double, dN2dY As Double
            Dim dN3dX As Double, dN3dY As Double
            Dim dN4dX As Double, dN4dY As Double
            Dim dN5dX As Double, dN5dY As Double
            Dim dN6dX As Double, dN6dY As Double
            Dim dN7dX As Double, dN7dY As Double
            Dim dN8dX As Double, dN8dY As Double
            dN1dX = (dN1dXi * dYdEt - dN1dEt * dYdXi) / detJ(e, ip)
            dN2dX = (dN2dXi * dYdEt - dN2dEt * dYdXi) / detJ(e, ip)
            dN3dX = (dN3dXi * dYdEt - dN3dEt * dYdXi) / detJ(e, ip)
            dN4dX = (dN4dXi * dYdEt - dN4dEt * dYdXi) / detJ(e, ip)
            dN5dX = (dN5dXi * dYdEt - dN5dEt * dYdXi) / detJ(e, ip)
            dN6dX = (dN6dXi * dYdEt - dN6dEt * dYdXi) / detJ(e, ip)
            dN7dX = (dN7dXi * dYdEt - dN7dEt * dYdXi) / detJ(e, ip)
            dN8dX = (dN8dXi * dYdEt - dN8dEt * dYdXi) / detJ(e, ip)
            
            dN1dY = (-dN1dXi * dXdEt + dN1dEt * dXdXi) / detJ(e, ip)
            dN2dY = (-dN2dXi * dXdEt + dN2dEt * dXdXi) / detJ(e, ip)
            dN3dY = (-dN3dXi * dXdEt + dN3dEt * dXdXi) / detJ(e, ip)
            dN4dY = (-dN4dXi * dXdEt + dN4dEt * dXdXi) / detJ(e, ip)
            dN5dY = (-dN5dXi * dXdEt + dN5dEt * dXdXi) / detJ(e, ip)
            dN6dY = (-dN6dXi * dXdEt + dN6dEt * dXdXi) / detJ(e, ip)
            dN7dY = (-dN7dXi * dXdEt + dN7dEt * dXdXi) / detJ(e, ip)
            dN8dY = (-dN8dXi * dXdEt + dN8dEt * dXdXi) / detJ(e, ip)
    
    
            ' ⑤ [B] 　※参照：式(3.33)
            B(e, ip, 1, 1) = dN1dX
            B(e, ip, 1, 2) = 0
            B(e, ip, 1, 3) = dN2dX
            B(e, ip, 1, 4) = 0
            B(e, ip, 1, 5) = dN3dX
            B(e, ip, 1, 6) = 0
            B(e, ip, 1, 7) = dN4dX
            B(e, ip, 1, 8) = 0
            B(e, ip, 1, 9) = dN5dX
            B(e, ip, 1, 10) = 0
            B(e, ip, 1, 11) = dN6dX
            B(e, ip, 1, 12) = 0
            B(e, ip, 1, 13) = dN7dX
            B(e, ip, 1, 14) = 0
            B(e, ip, 1, 15) = dN8dX
            B(e, ip, 1, 16) = 0
            
            B(e, ip, 2, 1) = 0
            B(e, ip, 2, 2) = dN1dY
            B(e, ip, 2, 3) = 0
            B(e, ip, 2, 4) = dN2dY
            B(e, ip, 2, 5) = 0
            B(e, ip, 2, 6) = dN3dY
            B(e, ip, 2, 7) = 0
            B(e, ip, 2, 8) = dN4dY
            B(e, ip, 2, 9) = 0
            B(e, ip, 2, 10) = dN5dY
            B(e, ip, 2, 11) = 0
            B(e, ip, 2, 12) = dN6dY
            B(e, ip, 2, 13) = 0
            B(e, ip, 2, 14) = dN7dY
            B(e, ip, 2, 15) = 0
            B(e, ip, 2, 16) = dN8dY
           
            B(e, ip, 3, 1) = dN1dY
            B(e, ip, 3, 2) = dN1dX
            B(e, ip, 3, 3) = dN2dY
            B(e, ip, 3, 4) = dN2dX
            B(e, ip, 3, 5) = dN3dY
            B(e, ip, 3, 6) = dN3dX
            B(e, ip, 3, 7) = dN4dY
            B(e, ip, 3, 8) = dN4dX
            B(e, ip, 3, 9) = dN5dY
            B(e, ip, 3, 10) = dN5dX
            B(e, ip, 3, 11) = dN6dY
            B(e, ip, 3, 12) = dN6dX
            B(e, ip, 3, 13) = dN7dY
            B(e, ip, 3, 14) = dN7dX
            B(e, ip, 3, 15) = dN8dY
            B(e, ip, 3, 16) = dN8dX
          Next ip
    Next e
End Sub

' =====================================================================
' 全要素の要素剛性マトリックス[Ke]の計算
' =====================================================================
Sub make_Ke()
    Dim r As Integer
    Dim c As Integer
    Dim i As Integer

    ' 全要素の[Ke]ループ
    Dim e As Integer
    For e = 1 To ELEMENTS
        ' 積分点[Ke]マトリクスと要素Kマトリクスの計算
        Dim ip As Integer
        For ip = 1 To INTEGRAL_POINTS9
            ' [B]tの計算
            Dim Bt(DOF_QUAD8, COMPONENTS) As Double
            For r = 1 To COMPONENTS
                For c = 1 To DOF_QUAD8
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
            Dim BtDt(DOF_QUAD8, COMPONENTS) As Double
            For r = 1 To DOF_QUAD8
               For c = 1 To COMPONENTS
                    BtDt(r, c) = 0#
                    For i = 1 To COMPONENTS
                        BtDt(r, c) = BtDt(r, c) + Bt(r, i) * Dt(i, c)
                    Next i
                Next c
            Next r
    
            ' 積分点[Ke]マトリクスの計算 Kep=((Bt*Dt)*B)*J*Wi*Wj*t
            Dim Kep(DOF_QUAD8, DOF_QUAD8) As Double
            For r = 1 To DOF_QUAD8
                For c = 1 To DOF_QUAD8
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
            For r = 1 To DOF_QUAD8
                For c = 1 To DOF_QUAD8
                    Ke(e, r, c) = Ke(e, r, c) + Kep(r, c)
                Next c
            Next r
        Next ip
    Next e
End Sub

' =====================================================================
' 全体剛性マトリックス作成プロシージャ
' =====================================================================
Sub make_K()
    Dim e As Integer                    ' 要素番号インデックス
    Dim r As Integer, c As Integer      ' 要素剛性マトリックスの行と列のインデックス
    Dim rt As Integer, ct As Integer    ' 全体剛性マトリックスの行と列のインデックス
    
    For rt = 1 To DOF_TOTAL             ' 全体剛性マトリックスの成分を初期化
        For ct = 1 To DOF_TOTAL
            K(rt, ct) = 0#
        Next ct
    Next rt
    
    For e = 1 To ELEMENTS               ' 要素ごとにKeの成分をKに足し込む
        For r = 1 To DOF_QUAD8
            rt = connectivity(e, (r + 1) \ DOF_NODE) * DOF_NODE - (r Mod DOF_NODE)
            For c = 1 To DOF_QUAD8
                ct = connectivity(e, (c + 1) \ DOF_NODE) * DOF_NODE - (c Mod DOF_NODE)
                K(rt, ct) = K(rt, ct) + Ke(e, r, c)
            Next c
        Next r
    Next e
End Sub


' =====================================================================
' 境界条件処理プロシージャ
' =====================================================================
Sub set_boundary_condition()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のインデックス
    Dim rr As Integer, cc As Integer    ' マトリックスの行と列のインデックス
    
    For r = 1 To DOF_TOTAL              ' 全体剛性マトリックスのコピーを作成
        For c = 1 To DOF_TOTAL
            Kc(r, c) = K(r, c)
        Next c
    Next r

    For r = 1 To DOF_TOTAL              ' 行方向に順に処理
        If Um(r) = True Then            ' 変位が拘束されている自由度に対する処理
            For rr = 1 To DOF_TOTAL     ' 変位拘束自由度以外の荷重ベクトルを修正
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
            F(r) = U(r)                 ' 変位拘束が存在する成分の荷重ベクトルを修正
        End If
    Next r
End Sub

' =====================================================================
' ガウスの消去法によるソルバプロシージャ
' =====================================================================
Sub solve()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のインデックス
    Dim rr As Integer, cc As Integer    ' マトリックスの行と列のインデックス
    Dim pivot As Double                 ' マトリックスの対角成分
    Dim p As Double                     ' 計算に使用するマトリックスの成分
    
    ' 前進消去 -----
    For r = 1 To DOF_TOTAL
        
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

    ' 後退代入 -----
    For r = DOF_TOTAL To 1 Step -1
        U(r) = F(r)
        For c = r + 1 To DOF_TOTAL
            U(r) = U(r) - Kc(r, c) * U(c)
        Next c
    Next r
End Sub

' =====================================================================
' 節点反力プロシージャ
' =====================================================================
Sub make_reaction()
    Dim r As Integer, c As Integer      ' マトリックスの行と列のインデックス
    
    For r = 1 To DOF_TOTAL              ' 節点反力の計算 (K×U)
        Fr(r) = 0#
        For c = 1 To DOF_TOTAL
            Fr(r) = Fr(r) + K(r, c) * U(c)
        Next c
    Next r
End Sub

' =====================================================================
' ひずみプロシージャ
' =====================================================================
Sub make_strain()
    Dim e As Integer
    Dim ip As Integer
    Dim r As Integer
    Dim c As Integer
    Dim n As Integer
    Dim Ue(DOF_QUAD8) As Double
    
    For e = 1 To ELEMENTS
        For ip = 1 To INTEGRAL_POINTS9
            ' 要素内節点変位を計算
            For n = 1 To NODES_QUAD8
                Ue(n * 2 - 1) = U(connectivity(e, n) * 2 - 1)   ' x成分
                Ue(n * 2) = U(connectivity(e, n) * 2)           ' y成分
            Next n
            
            '積分点のひずみを計算
            For r = 1 To COMPONENTS
                strain_ip(e, ip, r) = 0
                For c = 1 To DOF_QUAD8
                    strain_ip(e, ip, r) = strain_ip(e, ip, r) + B(e, ip, r, c) * Ue(c)
                Next c
            Next r
        Next ip
    Next e
End Sub

' =====================================================================
' 応力プロシージャ
' =====================================================================
Sub make_stress()
    Dim e As Integer
    Dim ip As Integer
    Dim r As Integer
    Dim c As Integer
    Dim n As Integer
    
    For e = 1 To ELEMENTS
        ' 積分点の応力を計算
        For ip = 1 To INTEGRAL_POINTS9
            For r = 1 To COMPONENTS
                stress_ip(e, ip, r) = 0
                For c = 1 To COMPONENTS
                    stress_ip(e, ip, r) = stress_ip(e, ip, r) + _
                                        D(r, c) * strain_ip(e, ip, c)
                Next c
            Next r
        Next ip
    Next e
End Sub

' =====================================================================
' 四角形２次要素の物体力の計算（プログラム4.8）
' =====================================================================
Sub calc_body_force_quad8()
    Dim N1(INTEGRAL_POINTS9) As Double  ' 形状関数N1の積分点での値
    Dim N2(INTEGRAL_POINTS9) As Double  ' 形状関数N2の積分点での値
    Dim N3(INTEGRAL_POINTS9) As Double  ' 形状関数N3の積分点での値
    Dim N4(INTEGRAL_POINTS9) As Double  ' 形状関数N4の積分点での値
    Dim N5(INTEGRAL_POINTS9) As Double  ' 形状関数N5の積分点での値
    Dim N6(INTEGRAL_POINTS9) As Double  ' 形状関数N6の積分点での値
    Dim N7(INTEGRAL_POINTS9) As Double  ' 形状関数N7の積分点での値
    Dim N8(INTEGRAL_POINTS9) As Double  ' 形状関数N8の積分点での値

    Dim ip As Integer                   ' 積分点カウンター
    Dim e As Integer                    ' 要素カウンター
    Dim xi As Double, et As Double      ' 積分点位置(ξ位置、η位置)
    Dim i As Integer                    ' 要素自由度カウンター
    Dim coef As Double                  ' 各成分に共通な係数

    '   各積分点での形状関数の値を計算
    For ip = 1 To INTEGRAL_POINTS9      ' 積分点数ループ
        xi = ip_xi(ip)                  ' 積分点座標（９点）ip_xi, ip_et
        et = ip_et(ip)                  '　プログラム3.10参照

        ' 積分点位置での形状関数の値　式(4.32)参照
        N1(ip) = (1 - xi) * (1 - et) * (-1 - xi - et) / 4
        N2(ip) = (1 + xi) * (1 - et) * (-1 + xi - et) / 4
        N3(ip) = (1 + xi) * (1 + et) * (-1 + xi + et) / 4
        N4(ip) = (1 - xi) * (1 + et) * (-1 - xi + et) / 4
        N5(ip) = (1 - xi * xi) * (1 - et) / 2
        N6(ip) = (1 + xi) * (1 - et * et) / 2
        N7(ip) = (1 - xi * xi) * (1 + et) / 2
        N8(ip) = (1 - xi) * (1 - et * et) / 2
    Next ip

    ' 物体力の等価節点力を計算
    For e = 1 To ELEMENTS               ' 要素ループ
        For i = 1 To DOF_QUAD8          '　要素あたりの節点数×節点自由度
            Feb(e, i) = 0
        Next i

        ' 物体力の等価節点力：　式(4.31)参照
        For ip = 1 To INTEGRAL_POINTS9  ' 積分点数
            '共通係数計算:積分点重み(9点）ip_wi, ip_wjプログラム3.10参照
            coef = THICKNESS * ip_wi(ip) * ip_wj(ip) * detJ(e, ip)

            Feb(e, 1) = Feb(e, 1) + coef * N1(ip) * BX      ' 第１節点x
            Feb(e, 2) = Feb(e, 2) + coef * N1(ip) * BY      ' 第１節点y

            Feb(e, 3) = Feb(e, 3) + coef * N2(ip) * BX      ' 第2節点x
            Feb(e, 4) = Feb(e, 4) + coef * N2(ip) * BY      ' 第2節点y

            Feb(e, 5) = Feb(e, 5) + coef * N3(ip) * BX      ' 第3節点x
            Feb(e, 6) = Feb(e, 6) + coef * N3(ip) * BY      ' 第3節点y

            Feb(e, 7) = Feb(e, 7) + coef * N4(ip) * BX      ' 第4節点x
            Feb(e, 8) = Feb(e, 8) + coef * N4(ip) * BY      ' 第4節点y

            Feb(e, 9) = Feb(e, 9) + coef * N5(ip) * BX      ' 第5節点x
            Feb(e, 10) = Feb(e, 10) + coef * N5(ip) * BY    ' 第5節点y

            Feb(e, 11) = Feb(e, 11) + coef * N6(ip) * BX    ' 第6節点x
            Feb(e, 12) = Feb(e, 12) + coef * N6(ip) * BY    ' 第6節点y

            Feb(e, 13) = Feb(e, 13) + coef * N7(ip) * BX    ' 第7節点x
            Feb(e, 14) = Feb(e, 14) + coef * N7(ip) * BY    ' 第7節点y

            Feb(e, 15) = Feb(e, 15) + coef * N8(ip) * BX    ' 第8節点x
            Feb(e, 16) = Feb(e, 16) + coef * N8(ip) * BY    ' 第8節点y
        Next ip
    Next e
End Sub

' =====================================================================
' 要素毎の物体力の等価節点力の全体荷重ベクトルへの足しこみ
'                                   （プログラム4.7の四角形２次要素版）
' =====================================================================
Sub add_body_force_quad8()
    Dim e As Integer                            ' 要素カウンター
    Dim m As Integer                            ' 要素内節点カウンター
    Dim n As Integer                            ' 節点番号
    Dim i As Integer                            ' 自由度カウンター
    Dim idx As Integer                          ' 荷重ベクトルインデックス

    For e = 1 To ELEMENTS
        For m = 1 To NODES_QUAD8                ' 要素あたりの節点数
            n = connectivity(e, m)              ' 要素e　第m節点の節点番号取得
            For i = 1 To DOF_NODE               ' 節点自由度
                idx = (n - 1) * DOF_NODE + i    ' 荷重ベクトル指標計算
            ' 要素ごとの等価節点力の全体荷重ベクトルへの足しこみ
                F(idx) = F(idx) + Feb(e, (m - 1) * DOF_NODE + i)
            Next i
        Next m
    Next e
End Sub

' =====================================================================
' 表面力の等価節点力計算と全体荷重ベクトルへの足しこみ
'                                   (プログラム4.4の四角形２次要素版）
' =====================================================================
Sub calc_surface_force_quad8()
    Dim iface As Integer                        ' 辺荷重カウンター
    Dim e As Integer                            ' 要素番号
    Dim na As Integer                           ' 辺始点節点番号
    Dim nb As Integer                           ' 辺終点節点番号
    Dim nc As Integer                           ' 辺中間節点番号
    Dim xa As Double, ya As Double              ' 辺始点節点座標
    Dim xb As Double, yb As Double              ' 辺終点節点座標
    Dim edge_length As Double                   ' 辺の長さ
    Dim fx As Double, fy As Double              ' 等価節点力

    For iface = 1 To FACES                      ' 表面力ループ
        e = face_element(iface)                 ' 表面力作用要素番号取得
        Select Case face_edge(iface)            ' 表面力作用辺による処理分岐
        ' 辺の構成節点取得（始点: na、終点: nb ）
            Case 1                              ' 表面力定義が辺1の場合、
                na = connectivity(e, 1): nb = connectivity(e, 2)
                nc = connectivity(e, 5)
            Case 2                              ' 表面力定義が辺2の場合、
                na = connectivity(e, 2): nb = connectivity(e, 3)
                nc = connectivity(e, 6)
            Case 3                              ' 表面力定義が辺 3の場合、
                na = connectivity(e, 3): nb = connectivity(e, 4)
                nc = connectivity(e, 7)
            Case 4                              ' 表面力定義が辺 3の場合、
                na = connectivity(e, 4): nb = connectivity(e, 1)
                nc = connectivity(e, 8)
        
        End Select

        ' 表面力が作用する辺の長さを計算
        xa = x(na): ya = y(na)                  ' 始点の座標
        xb = x(nb): yb = y(nb)                  ' 終点の座標
        edge_length = Sqr((xa - xb) * (xa - xb) + _
                                (ya - yb) * (ya - yb))
        
        ' 表面力の等価節点力の算出　式(4.37)参照
        fx = THICKNESS * face_px(iface) * edge_length / 6
        fy = THICKNESS * face_py(iface) * edge_length / 6
    
        ' 等価節点力を辺を構成する節点の荷重ベクトルに足しこみ
        F((na - 1) * 2 + 1) = F((na - 1) * 2 + 1) + fx
        F((na - 1) * 2 + 2) = F((na - 1) * 2 + 2) + fy
        F((nb - 1) * 2 + 1) = F((nb - 1) * 2 + 1) + fx
        F((nb - 1) * 2 + 2) = F((nb - 1) * 2 + 2) + fy
        F((nc - 1) * 2 + 1) = F((nc - 1) * 2 + 1) + fx * 4
        F((nc - 1) * 2 + 2) = F((nc - 1) * 2 + 2) + fy * 4
    Next iface
End Sub

' =====================================================================
' 四角形２次要素の節点応力計算（プログラム4.16）
' =====================================================================
Sub make_stress_node_quad8()                    ' 節点応力計算(四角形２次要素)
    Call initialize_node_to_gauss_quad8         ' 節点近傍積分点配列設定

    Call make_stress_element_quad8              ' 要素応力計算
    Call sum_stress_node_quad8_linearmethod     ' 方法①線形外挿法
    Call average_stress_node                    ' 節点応力平均プロシージャ
End Sub

' =====================================================================
' 節点近傍の積分点番号設定初期化（図3.7参照）
' =====================================================================
Sub initialize_node_to_gauss_quad8()
    node_to_gauss_quad8(1) = 1                  ' 第１節点近傍積分点:第１積分点
    node_to_gauss_quad8(2) = 3                  ' 第２節点近傍積分点:第３積分点
    node_to_gauss_quad8(3) = 9                  ' 第３節点近傍積分点:第９積分点
    node_to_gauss_quad8(4) = 7                  ' 第４節点近傍積分点:第７積分点
    node_to_gauss_quad8(5) = 2                  ' 第５節点近傍積分点:第２積分点
    node_to_gauss_quad8(6) = 6                  ' 第６節点近傍積分点:第６積分点
    node_to_gauss_quad8(7) = 8                  ' 第７節点近傍積分点:第８積分点
    node_to_gauss_quad8(8) = 4                  ' 第８節点近傍積分点:第４積分点
End Sub

' =====================================================================
' 四角形２次要素の要素応力の計算（プログラム4.16）
' =====================================================================
Sub make_stress_element_quad8()
    Dim e As Integer                            ' 要素カウンター
    Dim K As Integer                            ' 成分カウンター
    Dim ip As Integer                           ' 積分点カウンター
    Dim sum_stress As Double                    ' 応力合計算出用一時変数
    
    For e = 1 To ELEMENTS
        ' 要素応力を計算（積分点応力の平均）
        ' 積分点位置での応力は、プログラム3.14にて計算済(stress_ip)
        For K = 1 To COMPONENTS                 ' 成分数ループ
            sum_stress = 0
            For ip = 1 To INTEGRAL_POINTS9      ' 積分点ループ
                sum_stress = sum_stress + stress_ip(e, ip, K)
            Next ip
            stress_element(e, K) = sum_stress / INTEGRAL_POINTS9
        Next K
    Next e
End Sub

' =====================================================================
' 要素毎の節点応力外挿（方法①線形外挿法）  （プログラム4.16）
' =====================================================================
Sub sum_stress_node_quad8_linearmethod()        ' 方法①線形外挿法
    Const SCALE_QUAD8 As Double = 1.29004448    ' 1/sqrt(3/5)

    Dim n As Integer                            ' 節点カウンター
    Dim K As Integer                            ' 成分カウンター
    Dim e As Integer                            ' 要素カウンター
    Dim m As Integer                            ' 要素内節点カウンター
    Dim ip As Integer                           ' 積分点インデックス

    ' 配列の初期化処理
    For n = 1 To NODES                          ' 全節点数
        count_node(n) = 0
        For K = 1 To COMPONENTS                 ' 応力の成分数　(σx, σy,τxy)
            stress_node(n, K) = 0
        Next K
    Next n
  
    For e = 1 To ELEMENTS                       ' 要素ループ
        For m = 1 To NODES_QUAD8                ' 要素構成節点の数：　8
            ip = node_to_gauss_quad8(m)         ' 節点近傍積分点番号取得
            n = connectivity(e, m)              ' 要素e　第m節点の節点番号取得

            count_node(n) = count_node(n) + 1   ' 節点の要素接合数
            For K = 1 To COMPONENTS
                stress_node(n, K) = stress_node(n, K) + _
                    stress_element(e, K) + _
                    SCALE_QUAD8 * (stress_ip(e, ip, K) _
                                    - stress_element(e, K))
            Next K
        Next m
    Next e
End Sub

' =====================================================================
' 要素毎の節点応力の平均化処理  （プログラム4.15）
' =====================================================================
Sub average_stress_node()                       ' 平均化処理
    Dim n As Integer                            ' 節点カウンター
    Dim K As Integer                            ' 成分カウンター

    For n = 1 To NODES                          ' 節点ループ
        For K = 1 To COMPONENTS                 ' 成分数ループ
            stress_node(n, K) = stress_node(n, K) / count_node(n)
        Next K
    Next n
End Sub

' =====================================================================
' ワークシートから解析入力データを読み取る。
' =====================================================================
Sub readmodel()
    Dim i As Integer
    Dim idx As Integer
    
    Call readrange(x, "x")                              ' 節点x座標読み取り
    Call readrange(y, "y")                              ' 節点y座標読み取り
    Call readrange(connectivity, "connectivity")        ' 要素構成節点読み取り
    
    Call readrange(fixed, "fixed")                      ' 拘束条件読み取り（節点番号、拘束自由度）
    Call readrange(fixed_disp, "fixed_disp")            ' 拘束変位読み取り
    
    Dim fixed_node As Integer, fixed_dof As Integer
    For i = 1 To NFIXED
        fixed_node = fixed(i, 1)                        ' 拘束節点番号
        fixed_dof = fixed(i, 2)                         ' 拘束節点自由度
        idx = (fixed_node - 1) * DOF_NODE + fixed_dof   ' 配列指標計算
        
        Um(idx) = True
        U(idx) = fixed_disp(i)
    Next i
    
    Call readrange(face_element, "face_element")        ' 分布荷重設定要素読み取り
    Call readrange(face_edge, "face_edge")              ' 分布荷重設定要素辺番号読み取り
    Call readrange(face_px, "face_px")                  ' 分布荷重x方向成分読み取り
    Call readrange(face_py, "face_py")                  ' 分布荷重y方向成分読み取り
    
End Sub

' =====================================================================
' ワークシートから解析データを読み取る。
'       名前rangenameの範囲のデータを変数varに読み取り
' =====================================================================
Sub readrange(var, rangename As String)
    Dim i As Integer, j As Integer
    Dim a As Variant                                    ' 一時読み取り変数
    
    a = Range(rangename)                ' 名前rangenameの範囲データを一時的に変数aに読み取り
    
    If (UBound(a, 2) > 1) Then
        ' 読み取った範囲の列が２列以上の場合、２次元配列として変数varに設定。
        For i = 1 To UBound(a, 1)
            For j = 1 To UBound(a, 2)
                var(i, j) = a(i, j)
            Next j
        Next i
    Else
        ' 読み取った範囲の列が１列の場合、変数varを１次元配列として代入。
        For i = 1 To UBound(a, 1)
            var(i) = a(i, 1)
        Next i
    End If

End Sub

' =====================================================================
' 指定シート(sheetname)に１次元配列varの値を出力(書き出しはセルA1)
'   ※本プログラムでは使用していない。
' =====================================================================
Sub outputsheet1(sheetname As String, var As Variant)
    Dim i As Integer
    Worksheets(sheetname).Cells.Clear
    For i = 1 To UBound(var)
            Worksheets(sheetname).Cells(i, 1) = var(i)
    Next i
    
End Sub

' =====================================================================
' 指定シート(sheetname)に２次元配列varの値を出力(書き出しはセルA1)
' =====================================================================
Sub outputsheet2(sheetname As String, var As Variant)
    Worksheets(sheetname).Cells.Clear
    With Sheets(sheetname)
        .Range(.Cells(1, 1), .Cells(UBound(var), UBound(var, 2))) = var
    End With
    
End Sub

' =====================================================================
' 節点応力ファイル出力プログラム（ParaView用Vtkフォーマット）
'       Mac版EXCEL 2004では、GetSaveFilenameのfileFilterの動作が不明
' =====================================================================
Sub outputVtk()
    Dim myFile As Variant
    
    ' 出力ファイル名の取得
    myFile = Application.GetSaveAsFilename(fileFilter:="Vtkファイル(*.vtk),*.vtk")
'    myFile = Application.GetSaveAsFilename(fileFilter:="TEXT")     ' MacではfileFilterの動作が不明

    ' 出力ファイル名が指定されていない場合はプログラム終了
    If VarType(myFile) = vbBoolean Then
        Exit Sub
    End If
    
    ' 出力ファイルのファイルオープン
    Open myFile For Output As #1
    
    ' Header 出力
    Print #1, "# vtk DataFile Version 2.0"
    Print #1, "Header"
    Print #1, "ASCII"
    Print #1, "DATASET UNSTRUCTURED_GRID"
    Print #1,
    
    ' 節点座業出力
    Print #1, "POINTS "; NODES; " double"
    Dim i As Integer, j As Integer
    For i = 1 To NODES
        Print #1, x(i); y(i); 0#
    Next i
    Print #1,
    
    ' 要素構成節点番号出力
    Print #1, "CELLS "; ELEMENTS; ELEMENTS * 9
    For i = 1 To ELEMENTS
        Print #1, 8;
        For j = 1 To NODES_QUAD8
            Print #1, connectivity(i, j) - 1;
        Next j
        Print #1,
    Next i
    Print #1,
    
    ' 要素タイプ出力
    Print #1, "CELL_TYPES "; ELEMENTS
    For i = 1 To ELEMENTS
        Print #1, 23
    Next i
    Print #1,
    
    ' 節点応力出力
    Print #1, "POINT_DATA "; NODES
    Print #1, "SCALARS Sx float 1"
    Print #1, "LOOKUP_TABLE default"
    For i = 1 To NODES
        Print #1, stress_node(i, 1)
    Next i
    Print #1,
    
    ' 節点変位出力
    Print #1, "VECTORS Displacement float"
    For i = 1 To NODES
        Print #1, U((i - 1) * 2 + 1); U((i - 1) * 2 + 2); 0#
    Next i
    Print #1,
    
    ' ファイルクローズ
    Close #1

End Sub

' =====================================================================
' 「計算」ボタンクリック動作：    simple_fem_quad8を実行
' =====================================================================
Sub CalcButton_Click()
    Call simple_fem_quad8
End Sub

' =====================================================================
' 「結果消去」ボタンクリック動作:   シート「節点応力」の全クリア
' =====================================================================
Sub ClearButton_Click()
    Worksheets("節点応力").Cells.Clear
End Sub

' =====================================================================
' 「結果出力」ボタンクリック動作：  節点応力のファイル出力
' =====================================================================
Sub OutputButton_Click()
    Call outputVtk
End Sub

