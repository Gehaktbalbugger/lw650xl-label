Attribute VB_Name = "LabelPrinter"
Option Explicit

' ============================================================================
'  Etiketten printen op de LW650XL PRO via de iMac
'  ---------------------------------------------------------------------------
'  Installatie in Word:
'    1. Extra > Macro > Visual Basic (Alt+F11)
'    2. Bestand > Bestand importeren... > kies dit .bas-bestand
'    3. Sluit de editor. De macro's staan nu onder Extra > Macro > Macro's.
'    4. Zet "Label_NaarPrinter" op de werkbalk Snelle toegang.
'
'  Werkt op Word voor Windows en Word voor Mac. De macro exporteert het
'  document als PDF naar de gedeelde map op de iMac; de watcher daar print
'  hem automatisch. Er is geen printerdriver op de client nodig.
' ============================================================================

Private Const INBOX_WIN As String = "\\iMac2020\Labelprinter\inbox"
Private Const INBOX_MAC As String = "/Users/Shared/Labelprinter/inbox"

' ----------------------------------------------------------------------------
'  Hoofdmacro: huidige document (of alle pagina's van de samenvoeging) -> PDF
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

    MsgBox "Etiket(ten) naar de labelprinter gestuurd." & vbCrLf & naam, _
           vbInformation, "Labelprinter"
    Exit Sub
fout:
    MsgBox "Exporteren mislukt:" & vbCrLf & Err.Description, _
           vbExclamation, "Labelprinter"
End Sub

' ----------------------------------------------------------------------------
'  Paginaformaat goed zetten (eenmalig per document)
' ----------------------------------------------------------------------------
' Standaardrol in de printer: AM11354, 57 x 32 mm (liggend)
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
    MsgBox "Pagina ingesteld op " & wCm & " x " & hCm & " cm.", _
           vbInformation, "Labelprinter"
    Exit Sub
fout:
    MsgBox "Pagina instellen mislukt: " & Err.Description, _
           vbExclamation, "Labelprinter"
End Sub

' ----------------------------------------------------------------------------
'  Hulp: bestaat de gedeelde map?
' ----------------------------------------------------------------------------
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
