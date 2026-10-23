param(
    [string]$DocxPath = "docs\Challenge_4_RAG_und_Dokument_Upload_V1.docx",
    [string]$PdfPath = "docs\Challenge_4_RAG_und_Dokument_Upload_V1.pdf"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$docx = [System.IO.Path]::GetFullPath((Join-Path $root $DocxPath))
$pdf = [System.IO.Path]::GetFullPath((Join-Path $root $PdfPath))
$headings = @("Auf einen Blick", "Ihre Aufgabe", "Der Gesamtprozess", "Vorgehen", "Artefakte", "Evidenz und Bestehen", "Optionale Erweiterung: RAG-Genauigkeit verbessern")
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($docx)
    foreach ($paragraph in $document.Paragraphs) {
        $text = $paragraph.Range.Text.Trim([char]13, [char]7, [char]32)
        if ($text -eq "Unit 4: Challenge") {
            $paragraph.Range.Font.Name = "Aptos Display"
            $paragraph.Range.Font.Size = 24
            $paragraph.Range.Font.Bold = -1
            $paragraph.Range.Font.Color = 10027008
            $paragraph.Range.ParagraphFormat.SpaceAfter = 12
            $paragraph.Range.ParagraphFormat.KeepWithNext = -1
        }
        elseif ($headings -contains $text) {
            $paragraph.Range.Font.Size = 14
            $paragraph.Range.Font.Bold = -1
            $paragraph.Range.Font.Color = 10027008
            $paragraph.Range.ParagraphFormat.SpaceBefore = 12
            $paragraph.Range.ParagraphFormat.SpaceAfter = 6
            $paragraph.Range.ParagraphFormat.KeepWithNext = -1
        }
        elseif ($text -match '^[1-6]\. (Dokument ausw.hlen|Referenzdatensatz|Beide Bedingungen|R0 und V|Antworten pr.fen|Schlussfolgerung)') {
            $paragraph.Range.Font.Size = 12
            $paragraph.Range.Font.Bold = -1
            $paragraph.Range.Font.Color = 10027008
            $paragraph.Range.ParagraphFormat.SpaceBefore = 8
            $paragraph.Range.ParagraphFormat.KeepWithNext = -1
        }
    }
    foreach ($table in $document.Tables) {
        $table.Rows.AllowBreakAcrossPages = 0
        $table.Rows.Item(1).HeadingFormat = -1
        # Small reference/category tables should stay together.
        if ($table.Rows.Count -le 6) {
            $table.Range.ParagraphFormat.KeepWithNext = -1
            $table.Rows.Last.Range.ParagraphFormat.KeepWithNext = 0
        }
    }
    $document.Save()
    $document.ExportAsFixedFormat($pdf, 17)
    Write-Output "Styled challenge handout and matching PDF. Pages: $($document.ComputeStatistics(2))"
}
finally {
    if ($document) { $document.Close($false); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($word) { $word.Quit(); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
