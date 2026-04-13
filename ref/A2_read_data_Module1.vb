Attribute VB_Name = "Module1"
Option Base 1
Option Explicit

' *********************************
'  read_data
'
'  ワークシートからデータを読み込む
'
'  Ver 1.00  2014/6/9
' *********************************

Sub read_data()
    Dim nodes As Integer                ' 全節点数
    Dim elements As Integer             ' 全要素数
    Dim x() As Double                   ' 節点のx座標配列
    Dim y() As Double                   ' 節点のy座標配列
    Dim connectivity() As Integer       ' 要素内節点番号配列
    Dim young As Double                 ' ヤング率
    Dim poisson As Double               ' ポアソン比
    Dim thickness As Double             ' 要素の厚さ
    Dim F() As Double                   ' 全体荷重ベクトル
    Dim U() As Double                   ' 全体変位ベクトル
    Dim Um() As Boolean                 ' 拘束目印ベクトル
    Dim n As Integer                    ' 節点番号カウンター
    Dim e As Integer                    ' 要素番号カウンター
    Dim i As Integer                    ' 汎用カウンター
    
    nodes = Range("B1").Value           ' 節点数を読み込む
    elements = Range("B2").Value        ' 要素数を読み込む
    
    young = Range("YOUNG").Value        ' ヤング率を読み込む
    poisson = Range("POISSON").Value    ' ポアソン比を読み込む
    thickness = Range("THICKNESS").Value ' 要素の厚さを読み込む
    
    ReDim x(nodes) As Double            ' ベクトルの大きさを変更
    ReDim y(nodes) As Double
    ReDim connectivity(elements, 3) As Integer
    ReDim F(nodes * 2) As Double
    ReDim U(nodes * 2) As Double
    ReDim Um(nodes * 2) As Boolean
    
    For n = 1 To nodes                  ' 節点座標を読み込む
        x(n) = Cells(n + 9, 7).Value
        y(n) = Cells(n + 9, 8).Value
    Next n
    
    For e = 1 To elements               ' 要素内節点順を読み込む
        For n = 1 To 3
            connectivity(e, n) = Cells(e + 9, n + 1).Value
        Next n
    Next e
    
    For i = 1 To nodes                  ' 節点荷重を読み込む
        F(2 * i - 1) = Cells(i + 9, 9).Value
        F(2 * i) = Cells(i + 9, 10).Value
    Next i

    For n = 1 To nodes                  ' 拘束条件と拘束目印を読み込む
        For i = 1 To 2
            If Cells(n + 9, i + 10).Value <> "" Then
                U((n - 1) * 2 + i) = Cells(n + 9, i + 10).Value
                Um((n - 1) * 2 + i) = True
            Else
                Um((n - 1) * 2 + i) = False
            End If
        Next i
    Next n
End Sub


