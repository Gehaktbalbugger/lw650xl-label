Attribute VB_Name = "LabelPrinter"
Option Explicit

' ============================================================================
'  Excel -> etiketten op de LW650XL PRO (via de iMac)
'  ---------------------------------------------------------------------------
'  Zet in rij 1 deze kolomkoppen (alleen 'text' is verplicht):
'      text | qr | barcode | copies | size
'
'  Voorbeeld:
'      text                          qr                        barcode
'      Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam   https://x/1   CODE128:ABC123
'
'  - Gebruik in 'text' de tekens \n voor een nieuwe regel.
'  - 'size' is optioneel (bv. 57x32); leeg = de standaardmaat.
'  - 'copies' is optioneel; leeg = 1.
'
'  Installatie: Extra > Macro > Visual Basic > Bestand importeren...
'  Daarna: Extra > Macro > Macro's > Label_ExportCSV.
'
'  De macro schrijft een UTF-8 CSV naar de gedeelde inbox; de iMac print
'  één etiket per rij. Geen printerdriver nodig.
' ============================================================================

Private Const INBOX_WIN As String = "\\iMac2020\Labelprinter\inbox"
Private Const INBOX_MAC As String = "/Users/Shared/Labelprinter/inbox"

Public Sub Label_ExportCSV()
    Dim doel As String, pad As String
    doel = InboxPad()
    If doel = "" Then Exit Sub

    pad = doel & Application.PathSeparator & _
          "Label_" & Format(Now, "yyyymmdd_hhnnss") & ".csv"

    Dim rng As Range
    On Error Resume Next
    Set rng = ActiveSheet.Range("Etiketten")
    On Error GoTo 0
    If rng Is Nothing Then Set rng = ActiveSheet.UsedRange

    Dim s As String, r As Long, c As Long
    Dim line As String, cell As String

    For r = 1 To rng.Rows.Count
        line = ""
        For c = 1 To rng.Columns.Count
            cell = CStr(rng.Cells(r, c).Text)
            cell = Replace(cell, """", """""")
            If InStr(cell, ";") > 0 Or InStr(cell, """") > 0 Or InStr(cell, vbLf) > 0 Then
                cell = """" & cell & """"
            End If
            If c > 1 Then line = line & ";"
            line = line & cell
        Next c
        s = s & line & vbCrLf
    Next r

    On Error GoTo fout
    WriteUtf8 pad, s
    MsgBox "CSV naar de labelprinter gestuurd." & vbCrLf & pad, _
           vbInformation, "Labelprinter"
    Exit Sub
fout:
    MsgBox "Schrijven mislukt: " & Err.Description, vbExclamation, "Labelprinter"
End Sub

' ----------------------------------------------------------------------------
'  UTF-8 wegschrijven. Op Windows via ADODB; op Mac Excel als fallback
'  de systeemcodering (csv2labels.py leest ook cp1252/mac_roman).
' ----------------------------------------------------------------------------
Private Sub WriteUtf8(path As String, tekst As String)
    Dim st As Object
    On Error Resume Next
    Set st = CreateObject("ADODB.Stream")
    On Error GoTo 0

    If Not st Is Nothing Then
        On Error GoTo fout
        st.Type = 2
        st.Charset = "utf-8"
        st.Open
        st.WriteText tekst
        st.SaveToFile path, 2
        st.Close
        Exit Sub
    End If

    Dim fn As Integer
    fn = FreeFile
    Open path For Output As #fn
    Print #fn, tekst;
    Close #fn
    Exit Sub
fout:
    MsgBox "UTF-8 wegschrijven mislukt: " & Err.Description, vbExclamation, "Labelprinter"
End Sub

Private Function InboxPad() As String
    Dim p As String
    If InStr(1, Application.OperatingSystem, "Mac", vbTextCompare) > 0 Then
        p = INBOX_MAC
    Else
        p = INBOX_WIN
    End If

    If Dir(p, vbDirectory) = "" Then
        MsgBox "De etikettenmap is niet bereikbaar:" & vbCrLf & p & vbCrLf & vbCrLf & _
               "Staat de iMac aan en is de share 'Labelprinter' gedeeld?" & vbCrLf & _
               "Op Windows kun je ook \\172.16.1.101\Labelprinter\inbox proberen.", _
               vbExclamation, "Labelprinter"
        InboxPad = ""
        Exit Function
    End If
    InboxPad = p
End Function
