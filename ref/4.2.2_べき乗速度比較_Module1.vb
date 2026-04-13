Attribute VB_Name = "Module1"
' *********************************************************************
'
' 　第4章 前処理・後処理
'       4.2 Column　べき乗の計算方法
'
'   作者：日比　学（第4章担当）
'   更新：2014/06/22 Version 1.0 初版
'
' *********************************************************************

' =====================================================================
' メインプロシージャ
' =====================================================================
Sub TestPowerSpeed()
    x = Range("B2")                             ' べき乗する値を設定
    NLOOP = Range("B3")                         ' 繰り返し回数
    
    For howto = 1 To 3                          ' べき乗の方法変更
    Select Case howto
        Case 1 ' べき乗演算子
            For y = 2 To 6
                Call PowerSpeed(NLOOP, x, y, aTime)
                Range("A4").Offset(y, howto) = aTime
            Next y
        Case 2 ' 掛け算
            For y = 2 To 6
                Select Case y
                    Case 2  ' 2乗
                        Call Time2Speed(NLOOP, x, y, aTime)
                    Case 3  ' 3乗
                        Call Time3Speed(NLOOP, x, y, aTime)
                    Case 4  ' 4乗
                        Call Time4Speed(NLOOP, x, y, aTime)
                    Case 5  ' 5乗
                        Call Time5Speed(NLOOP, x, y, aTime)
                    Case 6  ' 6乗
                        Call Time6Speed(NLOOP, x, y, aTime)
                End Select
                Range("A4").Offset(y, howto) = aTime
            Next y
            
        Case 3 ' 対数指数表現
            For y = 2 To 6
                Call LogExpSpeed(NLOOP, x, y, aTime)
                Range("A4").Offset(y, howto) = aTime
            Next y
    End Select
        
    Next howto
    
End Sub

' =====================================================================
' EXCEL VBAのべき乗演算子
' =====================================================================
Private Sub PowerSpeed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x ^ y
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

' =====================================================================
' 掛け算によるべき乗処理
' =====================================================================
Private Sub Time2Speed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x * x
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

Private Sub Time3Speed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x * x * x
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

Private Sub Time4Speed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x * x * x * x
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

Private Sub Time5Speed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x * x * x * x * x
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

Private Sub Time6Speed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = x * x * x * x * x * x
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

' =====================================================================
' Exp(y*Log(x))によるべき乗処理
' =====================================================================
Private Sub LogExpSpeed(NLOOP, x, y, aTime)
    aStart = Timer
    For i = 1 To NLOOP
        z = Exp(y * Log(x))
    Next i
    aEnd = Timer
    aTime = aEnd - aStart

End Sub

' =====================================================================
' 「計算」ボタンクリック動作：  TestPowerSpeedを実行
' =====================================================================
Sub CalcButton_Click()
    Call TestPowerSpeed
End Sub

' =====================================================================
' 「結果消去」ボタンクリック動作:
' =====================================================================
Sub ClearButton_Click()
    Range("B6:D10").ClearContents
End Sub
