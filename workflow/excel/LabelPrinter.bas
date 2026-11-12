Attribute VB_Name = "LabelPrinter"
Option Explicit

' ============================================================================
'  Excel -> labels on the LW650XL PRO (via the iMac)
'  ---------------------------------------------------------------------------
'  Put these column headers in row 1 (only 'text' is required):
'      text | qr | barcode | copies | size
'
'  Example:
'      text                          qr                        barcode
'      Anna de Bakker\nKeukenstraat 12\n1011 AB Amsterdam   https://x/1   CODE128:ABC123
'
'  - In 'text' use the characters \n for a new line.
'  - 'size' is optional (e.g. 57x32); empty = the default size.
'  - 'copies' is optional; empty = 1.
'
'  Installation: Tools > Macro > Visual Basic > Import file...
'  Then: Tools > Macro > Macros > Label_ExportCSV.
'
'  The macro writes a UTF-8 CSV into the shared inbox; the iMac prints one
'  label per row. No printer driver needed.
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
    MsgBox "CSV sent to the label printer." & vbCrLf & pad, _
           vbInformation, "Label printer"
    Exit Sub
fout:
    MsgBox "Writing failed: " & Err.Description, vbExclamation, "Label printer"
End Sub

' ----------------------------------------------------------------------------
'  Writing UTF-8. On Windows via ADODB; on Mac Excel fall back to the
'  system encoding (csv2labels.py also reads cp1252/mac_roman).
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
    MsgBox "Writing UTF-8 failed: " & Err.Description, vbExclamation, "Label printer"
End Sub

Private Function InboxPad() As String
    Dim p As String
    If InStr(1, Application.OperatingSystem, "Mac", vbTextCompare) > 0 Then
        p = INBOX_MAC
    Else
        p = INBOX_WIN
    End If

    If Dir(p, vbDirectory) = "" Then
        MsgBox "The label folder is not reachable:" & vbCrLf & p & vbCrLf & vbCrLf & _
               "Is the iMac on and is the 'Labelprinter' share published?" & vbCrLf & _
               "On Windows you can also try \\172.16.1.101\Labelprinter\inbox.", _
               vbExclamation, "Label printer"
        InboxPad = ""
        Exit Function
    End If
    InboxPad = p
End Function
