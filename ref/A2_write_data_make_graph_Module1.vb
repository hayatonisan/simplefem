Attribute VB_Name = "Module1"
Option Base 1
Option Explicit

' *********************************
'  write_data
'
'  ワークシートへデータを書き込む
'
'  Ver 1.00  2014/6/9
' *********************************

Sub write_data()
    Dim elements As Integer             ' 全要素数
    Dim magnify As Double               ' 変形拡大倍率
    Dim n As Integer                    ' 節点番号カウンター
    Dim e As Integer                    ' 要素番号カウンター
    Dim r As Integer                    ' 行番号カウンター
    Dim er As Integer                   ' 要素内節点順カウンター
    Dim connectivity(4, 3) As Integer   ' 要素内節点順
    Dim x(6) As Double                  ' 節点のx座標
    Dim y(6) As Double                  ' 節点のy座標
    Dim U(12) As Double                 ' 節点変位ベクトル

    ' ----------------------------------
    ' 変数にデータを設定
    ' ----------------------------------
    elements = 4
    x(1) = 0#: x(2) = 1#: x(3) = 2#: x(4) = 2#: x(5) = 1#: x(6) = 0#
    y(1) = 0#: y(2) = 0#: y(3) = 0#: y(4) = 1#: y(5) = 1#: y(6) = 1#
    U(1) = 0#: U(2) = 0#
    U(3) = -0.0001045: U(4) = -0.0003229
    U(5) = -0.0001229: U(6) = -0.0007001
    U(7) = 0.0001619: U(8) = -0.0007185
    U(9) = 0.0001447: U(10) = -0.0003016
    U(11) = 0#: U(12) = -0.0001153
    connectivity(1, 1) = 1: connectivity(1, 2) = 2: connectivity(1, 3) = 5
    connectivity(2, 1) = 2: connectivity(2, 2) = 3: connectivity(2, 3) = 4
    connectivity(3, 1) = 2: connectivity(3, 2) = 4: connectivity(3, 3) = 5
    connectivity(4, 1) = 1: connectivity(4, 2) = 5: connectivity(4, 3) = 6
    
    magnify = 100#                      ' 変形拡大倍率を設定
    
    ' ----------------------------------
    ' 座標、変位データをシートへ記入
    ' ----------------------------------
    For e = 1 To elements
        r = e * 5 + 15                  ' 記入する行番号を設定
        Cells(r, 1).Value = e           ' 要素番号を記入

        For er = 1 To 3
            n = connectivity(e, er)
            Cells(r + er, 2).Value = n     ' 節点番号を記入
            Cells(r + er, 3).Value = x(n)  ' x座標を記入
            Cells(r + er, 4).Value = y(n)  ' y座標を記入
            Cells(r + er, 5).Value = x(n) + U(n * 2 - 1) * magnify ' x変位後のx座標を記入
            Cells(r + er, 6).Value = y(n) + U(n * 2) * magnify ' 変位後のy座標を記入
        Next er
    Next e
End Sub

' ************************
'  make_graph
'
'  変位グラフを作成する
'
'  Ver 1.00  2014/6/9
' ************************

Sub make_graph()
    Dim elements As Integer             ' 全要素数
    Dim e As Integer                    ' 要素番号カウンター
    Dim g As Range                      ' グラフを作成するセル範囲
    
    elements = 4
    
    ' ----------------------------------
    ' グラフの作成
    ' ----------------------------------
    Set g = Range("H20:P40")
    ActiveSheet.ChartObjects.Add(g.Left, g.Top, g.Width, g.Height).Activate
    ActiveChart.ChartType = xlXYScatterLines    ' 散布図グラフ

    ' ----------------------------------
    ' 変形前の要素を描画
    ' ----------------------------------
    For e = 1 To elements
                                        ' データ系列を追加
        ActiveChart.SeriesCollection.NewSeries

                                        ' データ系列の設定
        ActiveChart.SeriesCollection(e).Select
        With Selection
            .XValues = Range(Cells(e * 5 + 16, 3), Cells(e * 5 + 18, 3))
            .Values = Range(Cells(e * 5 + 16, 4), Cells(e * 5 + 18, 4))
            .MarkerBackgroundColorIndex = 8
            .MarkerForegroundColorIndex = 8
            .MarkerStyle = xlCircle
            .Smooth = False
            .MarkerSize = 10
        End With
        With Selection.Border           ' 要素形状線の設定
            .ColorIndex = 8
        End With
    Next e

    ' ----------------------------------
    ' 変形後の要素を描画
    ' ----------------------------------
    For e = 1 To elements
                                        ' データ系列を追加
        ActiveChart.SeriesCollection.NewSeries

                                        ' データ系列の設定
        ActiveChart.SeriesCollection(e + elements).Select
        With Selection
            .XValues = Range(Cells(e * 5 + 16, 5), Cells(e * 5 + 18, 5))
            .Values = Range(Cells(e * 5 + 16, 6), Cells(e * 5 + 18, 6))
            .MarkerBackgroundColorIndex = 5
            .MarkerForegroundColorIndex = 5
            .MarkerStyle = xlCircle
            .Smooth = False
            .MarkerSize = 10
        End With
        With Selection.Border           ' 要素形状線の設定
            .ColorIndex = 5
        End With
    Next e
    
    ActiveChart.HasLegend = False       ' 凡例は表示しない

End Sub


