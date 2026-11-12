Attribute VB_Name = "LabelPrinter"
Option Explicit

' ============================================================================
'  Print labels on the LW650XL PRO via the iMac
'  ---------------------------------------------------------------------------
'  Installation in Word:
'    1. Tools > Macro > Visual Basic (Alt+F11)
'    2. File > Import file... > pick this .bas file
'    3. Close the editor. The macros now live under Tools > Macro > Macros.
'    4. Put "Label_NaarPrinter" on the Quick Access toolbar.
'
'  Works on Word for Windows and Word for Mac. The macro exports the
'  document as PDF into the shared folder on the iMac; the watcher there
'  prints it automatically. No printer driver is needed on the client.
' ============================================================================

Private Const INBOX_WIN As String = "\\iMac2020\Labelprinter\inbox"
Private Const INBOX_MAC As String = "/Users/Shared/Labelprinter/inbox"

' ----------------------------------------------------------------------------
'  Main macro: current document (or all pages of the mail merge) -> PDF
' ----------------------------------------------------------------------------
Public Sub Label_NaarPrinter()
    Dim doel As String, naam As String, pad As String

    doel = InboxPad()
    If doel = "" Then Exit Sub

    naam = "Label_" & Format(Now, "yyyymmdd_hhnnss") & ".pdf"
    pad = doel & Application.PathSeparator & naam

    On Error GoTo fout
    ActiveDocument.ExportAsFixedFormat _
        OutputFileName:=pad, _
        ExportFormat:=wdExportFormatPDF, _
        OpenAfterExport:=False, _
        OptimizeFor:=wdExportOptimizeForPrint, _
        Range:=wdExportAllDocument, _
        Item:=wdExportDocumentContent, _
        IncludeDocProps:=False, _
        CreateBookmarks:=wdExportCreateNoBookmarks, _
        DocStructureTags:=False, _
        BitmapMissingFonts:=True, _
        UseISO19005_1:=False

    MsgBox "Label(s) sent to the label printer." & vbCrLf & naam, _
           vbInformation, "Label printer"
    Exit Sub
fout:
    MsgBox "Export failed:" & vbCrLf & Err.Description, _
           vbExclamation, "Label printer"
End Sub

' ----------------------------------------------------------------------------
'  Set the page size (once per document)
' ----------------------------------------------------------------------------
' Default roll in the printer: AM11354, 57 x 32 mm (landscape)
Public Sub Label_Pagina_57x32()
    Label_Pagina 5.7, 3.2
End Sub

Public Sub Label_Pagina_102x59()
    Label_Pagina 10.2, 5.9
End Sub

Public Sub Label_Pagina_104x159()
    Label_Pagina 10.4, 15.9
End Sub

Private Sub Label_Pagina(wCm As Single, hCm As Single)
    On Error GoTo fout
    With ActiveDocument.PageSetup
        .PaperSize = wdPaperCustom
        If wCm >= hCm Then
            .Orientation = wdOrientLandscape
        Else
            .Orientation = wdOrientPortrait
        End If
        .PageWidth = CentimetersToPoints(wCm)
        .PageHeight = CentimetersToPoints(hCm)
        .TopMargin = CentimetersToPoints(0.2)
        .BottomMargin = CentimetersToPoints(0.2)
        .LeftMargin = CentimetersToPoints(0.2)
        .RightMargin = CentimetersToPoints(0.2)
        .HeaderDistance = CentimetersToPoints(0)
        .FooterDistance = CentimetersToPoints(0)
    End With
    MsgBox "Page set to " & wCm & " x " & hCm & " cm.", _
           vbInformation, "Label printer"
    Exit Sub
fout:
    MsgBox "Setting the page failed: " & Err.Description, _
           vbExclamation, "Label printer"
End Sub

' ----------------------------------------------------------------------------
'  Helper: does the shared folder exist?
' ----------------------------------------------------------------------------
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
