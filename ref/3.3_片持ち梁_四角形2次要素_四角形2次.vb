Attribute VB_Name = "四角形2次"
' *********************************************************************
'
' 　第3章　高度な2次元プログラミング
'          四角形2次要素／平面ひずみ
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

Private Const NODES As Integer = 149                                    ' 全節点数
Private Const ELEMENTS As Integer = 40                                  ' 全要素数

Private Const INTEGRAL_POINTS9 As Integer = 9                           ' 要素の積分点数
Private Const NODES_QUAD8 As Integer = 8                                ' 要素の節点数

Private Const COMPONENTS As Integer = 3                                 ' 要素の成分数
Private Const DOF_NODE As Integer = 2                                   ' 節点の自由度
Private Const DOF_TOTAL As Integer = NODES * DOF_NODE                   ' モデル全体の自由度
Private Const DOF_QUAD8 As Integer = NODES_QUAD8 * DOF_NODE             ' 要素の自由度

Private Const RESULT_FILE_TITLE As String = "result-quad8"              ' 結果ファイルのファイルタイトル
Private Const RESULT_FORMAT As String = "0.000000000000000E+00"         ' 結果ファイルへの書き出しフォーマット


' =====================================================================
' モジュール変数
' =====================================================================
Private x(NODES) As Double                                              ' 節点のx座標配列
Private y(NODES) As Double                                              ' 節点のy座標配列
Private connectivity(ELEMENTS, NODES_QUAD8) As Integer                  ' 要素内節点番号の配列

Private ip_xi(INTEGRAL_POINTS9) As Double                               ' 積分点座標ξ
Private ip_et(INTEGRAL_POINTS9) As Double                               ' 積分点座標η
Private ip_wi(INTEGRAL_POINTS9) As Double                               ' 積分点重みξ方向
Private ip_wj(INTEGRAL_POINTS9) As Double                               ' 積分点座標η方向

Private D(COMPONENTS, COMPONENTS) As Double                             ' Dマトリックス
Private B(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS, DOF_QUAD8) As Double  ' Bマトリックス
Private detJ(ELEMENTS, INTEGRAL_POINTS9) As Double                      ' |J|
Private Ke(ELEMENTS, DOF_QUAD8, DOF_QUAD8) As Double                    ' 要素剛性マトリックス
Private strain_ip(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS) As Double     ' 積分点 ひずみベクトル
Private stress_ip(ELEMENTS, INTEGRAL_POINTS9, COMPONENTS) As Double     ' 積分点 応力ベクトル

Private K(DOF_TOTAL, DOF_TOTAL) As Double                               ' 全体剛性マトリックス
Private U(DOF_TOTAL) As Double                                          ' 変位ベクトル
Private F(DOF_TOTAL) As Double                                          ' 荷重ベクトル
Private Um(DOF_TOTAL) As Boolean                                        ' 拘束目印
Private Kc(DOF_TOTAL, DOF_TOTAL) As Double                              ' 求解用全体剛性マトリックス
Private Fr(DOF_TOTAL) As Double                                         ' 反力ベクトル


' =====================================================================
' メインプロシージャ
' =====================================================================
Sub simple_fem_quad8()
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
    connectivity(1, 1) = 1: connectivity(1, 2) = 2: connectivity(1, 3) = 13: connectivity(1, 4) = 12: connectivity(1, 5) = 56: connectivity(1, 6) = 57: connectivity(1, 7) = 58: connectivity(1, 8) = 59:
    connectivity(2, 1) = 2: connectivity(2, 2) = 3: connectivity(2, 3) = 14: connectivity(2, 4) = 13: connectivity(2, 5) = 60: connectivity(2, 6) = 61: connectivity(2, 7) = 62: connectivity(2, 8) = 57:
    connectivity(3, 1) = 3: connectivity(3, 2) = 4: connectivity(3, 3) = 15: connectivity(3, 4) = 14: connectivity(3, 5) = 63: connectivity(3, 6) = 64: connectivity(3, 7) = 65: connectivity(3, 8) = 61:
    connectivity(4, 1) = 4: connectivity(4, 2) = 5: connectivity(4, 3) = 16: connectivity(4, 4) = 15: connectivity(4, 5) = 66: connectivity(4, 6) = 67: connectivity(4, 7) = 68: connectivity(4, 8) = 64:
    connectivity(5, 1) = 5: connectivity(5, 2) = 6: connectivity(5, 3) = 17: connectivity(5, 4) = 16: connectivity(5, 5) = 69: connectivity(5, 6) = 70: connectivity(5, 7) = 71: connectivity(5, 8) = 67:
    connectivity(6, 1) = 6: connectivity(6, 2) = 7: connectivity(6, 3) = 18: connectivity(6, 4) = 17: connectivity(6, 5) = 72: connectivity(6, 6) = 73: connectivity(6, 7) = 74: connectivity(6, 8) = 70:
    connectivity(7, 1) = 7: connectivity(7, 2) = 8: connectivity(7, 3) = 19: connectivity(7, 4) = 18: connectivity(7, 5) = 75: connectivity(7, 6) = 76: connectivity(7, 7) = 77: connectivity(7, 8) = 73:
    connectivity(8, 1) = 8: connectivity(8, 2) = 9: connectivity(8, 3) = 20: connectivity(8, 4) = 19: connectivity(8, 5) = 78: connectivity(8, 6) = 79: connectivity(8, 7) = 80: connectivity(8, 8) = 76:
    connectivity(9, 1) = 9: connectivity(9, 2) = 10: connectivity(9, 3) = 21: connectivity(9, 4) = 20: connectivity(9, 5) = 81: connectivity(9, 6) = 82: connectivity(9, 7) = 83: connectivity(9, 8) = 79:
    connectivity(10, 1) = 10: connectivity(10, 2) = 11: connectivity(10, 3) = 22: connectivity(10, 4) = 21: connectivity(10, 5) = 84: connectivity(10, 6) = 85: connectivity(10, 7) = 86: connectivity(10, 8) = 82:
    connectivity(11, 1) = 12: connectivity(11, 2) = 13: connectivity(11, 3) = 24: connectivity(11, 4) = 23: connectivity(11, 5) = 58: connectivity(11, 6) = 87: connectivity(11, 7) = 88: connectivity(11, 8) = 89:
    connectivity(12, 1) = 13: connectivity(12, 2) = 14: connectivity(12, 3) = 25: connectivity(12, 4) = 24: connectivity(12, 5) = 62: connectivity(12, 6) = 90: connectivity(12, 7) = 91: connectivity(12, 8) = 87:
    connectivity(13, 1) = 14: connectivity(13, 2) = 15: connectivity(13, 3) = 26: connectivity(13, 4) = 25: connectivity(13, 5) = 65: connectivity(13, 6) = 92: connectivity(13, 7) = 93: connectivity(13, 8) = 90:
    connectivity(14, 1) = 15: connectivity(14, 2) = 16: connectivity(14, 3) = 27: connectivity(14, 4) = 26: connectivity(14, 5) = 68: connectivity(14, 6) = 94: connectivity(14, 7) = 95: connectivity(14, 8) = 92:
    connectivity(15, 1) = 16: connectivity(15, 2) = 17: connectivity(15, 3) = 28: connectivity(15, 4) = 27: connectivity(15, 5) = 71: connectivity(15, 6) = 96: connectivity(15, 7) = 97: connectivity(15, 8) = 94:
    connectivity(16, 1) = 17: connectivity(16, 2) = 18: connectivity(16, 3) = 29: connectivity(16, 4) = 28: connectivity(16, 5) = 74: connectivity(16, 6) = 98: connectivity(16, 7) = 99: connectivity(16, 8) = 96:
    connectivity(17, 1) = 18: connectivity(17, 2) = 19: connectivity(17, 3) = 30: connectivity(17, 4) = 29: connectivity(17, 5) = 77: connectivity(17, 6) = 100: connectivity(17, 7) = 101: connectivity(17, 8) = 98:
    connectivity(18, 1) = 19: connectivity(18, 2) = 20: connectivity(18, 3) = 31: connectivity(18, 4) = 30: connectivity(18, 5) = 80: connectivity(18, 6) = 102: connectivity(18, 7) = 103: connectivity(18, 8) = 100:
    connectivity(19, 1) = 20: connectivity(19, 2) = 21: connectivity(19, 3) = 32: connectivity(19, 4) = 31: connectivity(19, 5) = 83: connectivity(19, 6) = 104: connectivity(19, 7) = 105: connectivity(19, 8) = 102:
    connectivity(20, 1) = 21: connectivity(20, 2) = 22: connectivity(20, 3) = 33: connectivity(20, 4) = 32: connectivity(20, 5) = 86: connectivity(20, 6) = 106: connectivity(20, 7) = 107: connectivity(20, 8) = 104:
    connectivity(21, 1) = 23: connectivity(21, 2) = 24: connectivity(21, 3) = 35: connectivity(21, 4) = 34: connectivity(21, 5) = 88: connectivity(21, 6) = 108: connectivity(21, 7) = 109: connectivity(21, 8) = 110:
    connectivity(22, 1) = 24: connectivity(22, 2) = 25: connectivity(22, 3) = 36: connectivity(22, 4) = 35: connectivity(22, 5) = 91: connectivity(22, 6) = 111: connectivity(22, 7) = 112: connectivity(22, 8) = 108:
    connectivity(23, 1) = 25: connectivity(23, 2) = 26: connectivity(23, 3) = 37: connectivity(23, 4) = 36: connectivity(23, 5) = 93: connectivity(23, 6) = 113: connectivity(23, 7) = 114: connectivity(23, 8) = 111:
    connectivity(24, 1) = 26: connectivity(24, 2) = 27: connectivity(24, 3) = 38: connectivity(24, 4) = 37: connectivity(24, 5) = 95: connectivity(24, 6) = 115: connectivity(24, 7) = 116: connectivity(24, 8) = 113:
    connectivity(25, 1) = 27: connectivity(25, 2) = 28: connectivity(25, 3) = 39: connectivity(25, 4) = 38: connectivity(25, 5) = 97: connectivity(25, 6) = 117: connectivity(25, 7) = 118: connectivity(25, 8) = 115:
    connectivity(26, 1) = 28: connectivity(26, 2) = 29: connectivity(26, 3) = 40: connectivity(26, 4) = 39: connectivity(26, 5) = 99: connectivity(26, 6) = 119: connectivity(26, 7) = 120: connectivity(26, 8) = 117:
    connectivity(27, 1) = 29: connectivity(27, 2) = 30: connectivity(27, 3) = 41: connectivity(27, 4) = 40: connectivity(27, 5) = 101: connectivity(27, 6) = 121: connectivity(27, 7) = 122: connectivity(27, 8) = 119:
    connectivity(28, 1) = 30: connectivity(28, 2) = 31: connectivity(28, 3) = 42: connectivity(28, 4) = 41: connectivity(28, 5) = 103: connectivity(28, 6) = 123: connectivity(28, 7) = 124: connectivity(28, 8) = 121:
    connectivity(29, 1) = 31: connectivity(29, 2) = 32: connectivity(29, 3) = 43: connectivity(29, 4) = 42: connectivity(29, 5) = 105: connectivity(29, 6) = 125: connectivity(29, 7) = 126: connectivity(29, 8) = 123:
    connectivity(30, 1) = 32: connectivity(30, 2) = 33: connectivity(30, 3) = 44: connectivity(30, 4) = 43: connectivity(30, 5) = 107: connectivity(30, 6) = 127: connectivity(30, 7) = 128: connectivity(30, 8) = 125:
    connectivity(31, 1) = 34: connectivity(31, 2) = 35: connectivity(31, 3) = 46: connectivity(31, 4) = 45: connectivity(31, 5) = 109: connectivity(31, 6) = 129: connectivity(31, 7) = 130: connectivity(31, 8) = 131:
    connectivity(32, 1) = 35: connectivity(32, 2) = 36: connectivity(32, 3) = 47: connectivity(32, 4) = 46: connectivity(32, 5) = 112: connectivity(32, 6) = 132: connectivity(32, 7) = 133: connectivity(32, 8) = 129:
    connectivity(33, 1) = 36: connectivity(33, 2) = 37: connectivity(33, 3) = 48: connectivity(33, 4) = 47: connectivity(33, 5) = 114: connectivity(33, 6) = 134: connectivity(33, 7) = 135: connectivity(33, 8) = 132:
    connectivity(34, 1) = 37: connectivity(34, 2) = 38: connectivity(34, 3) = 49: connectivity(34, 4) = 48: connectivity(34, 5) = 116: connectivity(34, 6) = 136: connectivity(34, 7) = 137: connectivity(34, 8) = 134:
    connectivity(35, 1) = 38: connectivity(35, 2) = 39: connectivity(35, 3) = 50: connectivity(35, 4) = 49: connectivity(35, 5) = 118: connectivity(35, 6) = 138: connectivity(35, 7) = 139: connectivity(35, 8) = 136:
    connectivity(36, 1) = 39: connectivity(36, 2) = 40: connectivity(36, 3) = 51: connectivity(36, 4) = 50: connectivity(36, 5) = 120: connectivity(36, 6) = 140: connectivity(36, 7) = 141: connectivity(36, 8) = 138:
    connectivity(37, 1) = 40: connectivity(37, 2) = 41: connectivity(37, 3) = 52: connectivity(37, 4) = 51: connectivity(37, 5) = 122: connectivity(37, 6) = 142: connectivity(37, 7) = 143: connectivity(37, 8) = 140:
    connectivity(38, 1) = 41: connectivity(38, 2) = 42: connectivity(38, 3) = 53: connectivity(38, 4) = 52: connectivity(38, 5) = 124: connectivity(38, 6) = 144: connectivity(38, 7) = 145: connectivity(38, 8) = 142:
    connectivity(39, 1) = 42: connectivity(39, 2) = 43: connectivity(39, 3) = 54: connectivity(39, 4) = 53: connectivity(39, 5) = 126: connectivity(39, 6) = 146: connectivity(39, 7) = 147: connectivity(39, 8) = 144:
    connectivity(40, 1) = 43: connectivity(40, 2) = 44: connectivity(40, 3) = 55: connectivity(40, 4) = 54: connectivity(40, 5) = 128: connectivity(40, 6) = 148: connectivity(40, 7) = 149: connectivity(40, 8) = 146:

    
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
    x(56) = 2.5: y(56) = 0
    x(57) = 5: y(57) = 0.25
    x(58) = 2.5: y(58) = 0.5
    x(59) = 0: y(59) = 0.25
    x(60) = 7.5: y(60) = 0
    x(61) = 10: y(61) = 0.25
    x(62) = 7.5: y(62) = 0.5
    x(63) = 12.5: y(63) = 0
    x(64) = 15: y(64) = 0.25
    x(65) = 12.5: y(65) = 0.5
    x(66) = 17.5: y(66) = 0
    x(67) = 20: y(67) = 0.25
    x(68) = 17.5: y(68) = 0.5
    x(69) = 22.5: y(69) = 0
    x(70) = 25: y(70) = 0.25
    x(71) = 22.5: y(71) = 0.5
    x(72) = 27.5: y(72) = 0
    x(73) = 30: y(73) = 0.25
    x(74) = 27.5: y(74) = 0.5
    x(75) = 32.5: y(75) = 0
    x(76) = 35: y(76) = 0.25
    x(77) = 32.5: y(77) = 0.5
    x(78) = 37.5: y(78) = 0
    x(79) = 40: y(79) = 0.25
    x(80) = 37.5: y(80) = 0.5
    x(81) = 42.5: y(81) = 0
    x(82) = 45: y(82) = 0.25
    x(83) = 42.5: y(83) = 0.5
    x(84) = 47.5: y(84) = 0
    x(85) = 50: y(85) = 0.25
    x(86) = 47.5: y(86) = 0.5
    x(87) = 5: y(87) = 0.75
    x(88) = 2.5: y(88) = 1
    x(89) = 0: y(89) = 0.75
    x(90) = 10: y(90) = 0.75
    x(91) = 7.5: y(91) = 1
    x(92) = 15: y(92) = 0.75
    x(93) = 12.5: y(93) = 1
    x(94) = 20: y(94) = 0.75
    x(95) = 17.5: y(95) = 1
    x(96) = 25: y(96) = 0.75
    x(97) = 22.5: y(97) = 1
    x(98) = 30: y(98) = 0.75
    x(99) = 27.5: y(99) = 1
    x(100) = 35: y(100) = 0.75
    x(101) = 32.5: y(101) = 1
    x(102) = 40: y(102) = 0.75
    x(103) = 37.5: y(103) = 1
    x(104) = 45: y(104) = 0.75
    x(105) = 42.5: y(105) = 1
    x(106) = 50: y(106) = 0.75
    x(107) = 47.5: y(107) = 1
    x(108) = 5: y(108) = 1.25
    x(109) = 2.5: y(109) = 1.5
    x(110) = 0: y(110) = 1.25
    x(111) = 10: y(111) = 1.25
    x(112) = 7.5: y(112) = 1.5
    x(113) = 15: y(113) = 1.25
    x(114) = 12.5: y(114) = 1.5
    x(115) = 20: y(115) = 1.25
    x(116) = 17.5: y(116) = 1.5
    x(117) = 25: y(117) = 1.25
    x(118) = 22.5: y(118) = 1.5
    x(119) = 30: y(119) = 1.25
    x(120) = 27.5: y(120) = 1.5
    x(121) = 35: y(121) = 1.25
    x(122) = 32.5: y(122) = 1.5
    x(123) = 40: y(123) = 1.25
    x(124) = 37.5: y(124) = 1.5
    x(125) = 45: y(125) = 1.25
    x(126) = 42.5: y(126) = 1.5
    x(127) = 50: y(127) = 1.25
    x(128) = 47.5: y(128) = 1.5
    x(129) = 5: y(129) = 1.75
    x(130) = 2.5: y(130) = 2
    x(131) = 0: y(131) = 1.75
    x(132) = 10: y(132) = 1.75
    x(133) = 7.5: y(133) = 2
    x(134) = 15: y(134) = 1.75
    x(135) = 12.5: y(135) = 2
    x(136) = 20: y(136) = 1.75
    x(137) = 17.5: y(137) = 2
    x(138) = 25: y(138) = 1.75
    x(139) = 22.5: y(139) = 2
    x(140) = 30: y(140) = 1.75
    x(141) = 27.5: y(141) = 2
    x(142) = 35: y(142) = 1.75
    x(143) = 32.5: y(143) = 2
    x(144) = 40: y(144) = 1.75
    x(145) = 37.5: y(145) = 2
    x(146) = 45: y(146) = 1.75
    x(147) = 42.5: y(147) = 2
    x(148) = 50: y(148) = 1.75
    x(149) = 47.5: y(149) = 2


    ' 変位拘束
    Dim FixNode(9) As Integer
    FixNode(1) = 1
    FixNode(2) = 12
    FixNode(3) = 23
    FixNode(4) = 34
    FixNode(5) = 45
    FixNode(6) = 59
    FixNode(7) = 89
    FixNode(8) = 110
    FixNode(9) = 131
   
    
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
    F((11 - 1) * DOF_NODE + 2) = -0.00416666666
    F((55 - 1) * DOF_NODE + 2) = -0.00416666666
    F((22 - 1) * DOF_NODE + 2) = -0.00833333333
    F((33 - 1) * DOF_NODE + 2) = -0.00833333333
    F((44 - 1) * DOF_NODE + 2) = -0.00833333333
    
    F((85 - 1) * DOF_NODE + 2) = -0.01666666666
    F((106 - 1) * DOF_NODE + 2) = -0.01666666666
    F((127 - 1) * DOF_NODE + 2) = -0.01666666666
    F((148 - 1) * DOF_NODE + 2) = -0.01666666666


    ' 積分点座標
    Dim ce As Double, cc As Double
    ce = Sqr(3 / 5)
    cc = 0
    ip_xi(1) = -ce: ip_et(1) = -ce
    ip_xi(2) = cc: ip_et(2) = -ce
    ip_xi(3) = ce: ip_et(3) = -ce
    ip_xi(4) = -ce: ip_et(4) = cc
    ip_xi(5) = cc: ip_et(5) = cc
    ip_xi(6) = ce: ip_et(6) = cc
    ip_xi(7) = -ce: ip_et(7) = ce
    ip_xi(8) = cc: ip_et(8) = ce
    ip_xi(9) = ce: ip_et(9) = ce
    
    ' 積分点重み
    Dim we As Double, wc As Double
    we = 5 / 9
    wc = 8 / 9
    ip_wi(1) = we: ip_wj(1) = we
    ip_wi(2) = wc: ip_wj(2) = we
    ip_wi(3) = we: ip_wj(3) = we
    ip_wi(4) = we: ip_wj(4) = wc
    ip_wi(5) = wc: ip_wj(5) = wc
    ip_wi(6) = we: ip_wj(6) = wc
    ip_wi(7) = we: ip_wj(7) = we
    ip_wi(8) = wc: ip_wj(8) = we
    ip_wi(9) = we: ip_wj(9) = we
    
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
            
            ' ① ∂Ｎi/∂ξ，∂Ｎi/∂η
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
            
    
            ' ② ∂ｘ/∂ξ，∂ｘ/∂η，∂ｙ/∂ξ，∂ｙ/∂η
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
        
            ' ③ |J|
            detJ(e, ip) = dXdXi * dYdEt - dYdXi * dXdEt
            
            ' ④ ∂Ｎi/∂x, ∂Ｎi/∂y
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
    
    
            ' ⑤ [B]
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
Private Sub make_Ke()
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
' 全体Kマトリクス作成プロシージャ
' =====================================================================
Private Sub make_K()
    Dim e As Integer
    Dim r As Integer
    Dim c As Integer
    Dim nr As Integer
    Dim nc As Double
    
    For e = 1 To ELEMENTS
        For r = 1 To NODES_QUAD8
            nr = connectivity(e, r)
            For c = 1 To NODES_QUAD8
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
    Dim Ue(DOF_QUAD8) As Double
    
    For e = 1 To ELEMENTS
        For ip = 1 To INTEGRAL_POINTS9
            ' 要素内節点変位を計算
            For n = 1 To NODES_QUAD8
                Ue(n * 2 - 1) = U(connectivity(e, n) * 2 - 1)   ' x成分
                Ue(n * 2) = U(connectivity(e, n) * 2)           ' y成分
            Next n
            
            ' 積分点のひずみを計算
            For r = 1 To COMPONENTS
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
Private Sub make_stress()
    Dim e As Integer
    Dim ip As Integer
    Dim r As Integer
    Dim c As Integer
    Dim n As Integer
    
    For e = 1 To ELEMENTS
    
        ' 積分点の応力を計算
        For ip = 1 To INTEGRAL_POINTS9
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
        For ip = 1 To INTEGRAL_POINTS9
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
        For ip = 1 To INTEGRAL_POINTS9
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

