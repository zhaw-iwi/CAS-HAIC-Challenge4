param(
    [string]$SourcePath = "docs\Challenge_4_RAG_und_Dokument_Upload_V1.md",
    [string]$DocxPath = "docs\Challenge_4_RAG_und_Dokument_Upload_V1.docx",
    [string]$PdfPath = "docs\Challenge_4_RAG_und_Dokument_Upload_V1.pdf",
    [string]$DocumentTitle = "Unit 4: Challenge - RAG und Dokument-Upload",
    [string]$FooterLabel = "Challenge 4 - Version 1 - 23.10.2026"
)

$ErrorActionPreference = "Stop"

function Resolve-WorkspacePath {
    param([string]$PathValue, [string]$WorkspaceRoot)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $WorkspaceRoot $PathValue))
}

function Get-PlainText {
    param([string]$Text)
    $value = $Text -replace '\*\*', ''
    $value = $value -replace '`', ''
    return $value
}

function Add-WordParagraph {
    param(
        $Document,
        [string]$Text,
        [int]$StyleId = -1,
        [switch]$Code,
        [switch]$Quote,
        [switch]$Bullet,
        [switch]$Numbered
    )

    $range = $Document.Content
    $range.Collapse(0)
    $paragraph = $Document.Paragraphs.Add($range)
    $paragraph.Range.Text = (Get-PlainText $Text)
    # Word inherits direct formatting from the preceding paragraph when new
    # paragraphs are appended. Reset it before applying the intended style so
    # a quote or code block does not turn all following content grey/italic.
    try { $paragraph.Range.Font.Reset() } catch { }
    try { $paragraph.Range.ParagraphFormat.Reset() } catch { }
    try {
        $paragraph.Range.Shading.Texture = 0
        $paragraph.Range.Shading.BackgroundPatternColor = -16777216
    }
    catch { }
    try { $paragraph.Range.set_Style($StyleId) } catch { }

    if ($Code) {
        $paragraph.Range.Font.Name = "Consolas"
        $paragraph.Range.Font.Size = 8.5
        $paragraph.Range.ParagraphFormat.SpaceBefore = 4
        $paragraph.Range.ParagraphFormat.SpaceAfter = 4
        $paragraph.Range.ParagraphFormat.LeftIndent = 14
        $paragraph.Range.ParagraphFormat.RightIndent = 8
        $paragraph.Range.Shading.BackgroundPatternColor = 15987699
    }
    elseif ($Quote) {
        $paragraph.Range.Font.Italic = 1
        $paragraph.Range.ParagraphFormat.LeftIndent = 18
        $paragraph.Range.ParagraphFormat.RightIndent = 10
        $paragraph.Range.ParagraphFormat.SpaceAfter = 8
        $paragraph.Range.Shading.BackgroundPatternColor = 15592941
    }
    elseif ($Bullet) {
        $paragraph.Range.Text = ([char]0x2022) + " " + (Get-PlainText $Text)
        $paragraph.Range.ParagraphFormat.LeftIndent = 14
        $paragraph.Range.ParagraphFormat.FirstLineIndent = -8
    }
    elseif ($Numbered) {
        $paragraph.Range.ParagraphFormat.LeftIndent = 14
        $paragraph.Range.ParagraphFormat.FirstLineIndent = -8
    }

    $paragraph.Range.InsertParagraphAfter()
    return $paragraph
}

function Add-WordTable {
    param($Document, [object[]]$Rows)

    if ($Rows.Count -eq 0) { return }
    $columnCount = ($Rows | ForEach-Object { $_.Count } | Measure-Object -Maximum).Maximum
    if ($columnCount -lt 1) { return }

    $range = $Document.Content
    $range.Collapse(0)
    $table = $Document.Tables.Add($range, $Rows.Count, $columnCount)
    $table.Borders.Enable = 1
    $table.AllowAutoFit = $true
    $table.AutoFitBehavior(2)
    $table.Range.Font.Name = "Aptos"
    $table.Range.Font.Size = 8.5
    $table.Range.ParagraphFormat.SpaceAfter = 2

    for ($rowIndex = 0; $rowIndex -lt $Rows.Count; $rowIndex++) {
        for ($columnIndex = 0; $columnIndex -lt $columnCount; $columnIndex++) {
            $cellText = ""
            if ($columnIndex -lt $Rows[$rowIndex].Count) {
                $cellText = Get-PlainText ([string]$Rows[$rowIndex][$columnIndex])
            }
            $table.Cell($rowIndex + 1, $columnIndex + 1).Range.Text = $cellText
        }
    }

    $table.Rows.Item(1).Range.Font.Bold = 1
    $table.Rows.Item(1).Range.Font.Color = 16777215
    $table.Rows.Item(1).Shading.BackgroundPatternColor = 10526880
    try { $table.Rows.Item(1).HeadingFormat = 1 } catch { }

    $afterRange = $Document.Range($table.Range.End, $table.Range.End)
    $afterRange.InsertParagraphAfter()
}

function Convert-MarkdownToWord {
    param($Document, [string[]]$Lines)

    $inCode = $false
    $codeLines = New-Object System.Collections.Generic.List[string]
    $lineIndex = 0

    while ($lineIndex -lt $Lines.Count) {
        $line = $Lines[$lineIndex]

        if ($line -match '^```') {
            if ($inCode) {
                Add-WordParagraph -Document $Document -Text ($codeLines -join "`v") -Code | Out-Null
                $codeLines.Clear()
                $inCode = $false
            }
            else {
                $inCode = $true
            }
            $lineIndex++
            continue
        }

        if ($inCode) {
            $codeLines.Add($line)
            $lineIndex++
            continue
        }

        if ($line -eq '<!-- pagebreak -->') {
            $range = $Document.Content
            $range.Collapse(0)
            $range.InsertBreak(7)
            $lineIndex++
            continue
        }

        if ([string]::IsNullOrWhiteSpace($line)) {
            $lineIndex++
            continue
        }

        if ($line -match '^\|.*\|\s*$') {
            $tableLines = New-Object System.Collections.Generic.List[string]
            while ($lineIndex -lt $Lines.Count -and $Lines[$lineIndex] -match '^\|.*\|\s*$') {
                $tableLines.Add($Lines[$lineIndex])
                $lineIndex++
            }

            $rows = New-Object System.Collections.Generic.List[object]
            foreach ($tableLine in $tableLines) {
                $inner = $tableLine.Trim().Trim('|')
                if ($inner -match '^\s*:?-{3,}:?(\s*\|\s*:?-{3,}:?)*\s*$') { continue }
                $cells = @($inner -split '\|' | ForEach-Object { $_.Trim() })
                $rows.Add($cells)
            }
            Add-WordTable -Document $Document -Rows $rows
            continue
        }

        if ($line -match '^# (.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -StyleId -63 | Out-Null
        }
        elseif ($line -match '^## (.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -StyleId -2 | Out-Null
        }
        elseif ($line -match '^### (.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -StyleId -3 | Out-Null
        }
        elseif ($line -match '^#### (.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -StyleId -4 | Out-Null
        }
        elseif ($line -match '^>\s?(.*)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -Quote | Out-Null
        }
        elseif ($line -match '^-\s+(.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -Bullet | Out-Null
        }
        elseif ($line -match '^(\d+\.\s+.+)$') {
            Add-WordParagraph -Document $Document -Text $Matches[1] -Numbered | Out-Null
        }
        else {
            Add-WordParagraph -Document $Document -Text $line | Out-Null
        }

        $lineIndex++
    }

    if ($inCode -and $codeLines.Count -gt 0) {
        Add-WordParagraph -Document $Document -Text ($codeLines -join "`v") -Code | Out-Null
    }
}

$workspaceRoot = Split-Path -Parent $PSScriptRoot
$sourceFullPath = Resolve-WorkspacePath $SourcePath $workspaceRoot
$docxFullPath = Resolve-WorkspacePath $DocxPath $workspaceRoot
$pdfFullPath = Resolve-WorkspacePath $PdfPath $workspaceRoot

if (-not (Test-Path -LiteralPath $sourceFullPath)) {
    throw "Markdown source not found: $sourceFullPath"
}

$outputDirectory = Split-Path -Parent $docxFullPath
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$lines = Get-Content -LiteralPath $sourceFullPath -Encoding UTF8
$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Add()

    $section = $document.Sections.Item(1)
    $section.PageSetup.PaperSize = 7
    $section.PageSetup.TopMargin = $word.CentimetersToPoints(1.8)
    $section.PageSetup.BottomMargin = $word.CentimetersToPoints(1.7)
    $section.PageSetup.LeftMargin = $word.CentimetersToPoints(1.8)
    $section.PageSetup.RightMargin = $word.CentimetersToPoints(1.8)

    $normalStyle = $document.Styles.Item(-1)
    $normalStyle.Font.Name = "Aptos"
    $normalStyle.Font.Size = 10.5
    $normalStyle.ParagraphFormat.SpaceAfter = 6
    $normalStyle.ParagraphFormat.LineSpacingRule = 0

    $titleStyle = $document.Styles.Item(-63)
    $titleStyle.Font.Name = "Aptos Display"
    $titleStyle.Font.Size = 24
    $titleStyle.Font.Bold = 1
    $titleStyle.Font.Color = 10027008
    $titleStyle.ParagraphFormat.SpaceAfter = 16

    foreach ($styleId in @(-2, -3, -4)) {
        $style = $document.Styles.Item($styleId)
        $style.Font.Name = "Aptos Display"
        $style.Font.Color = 10027008
        $style.Font.Bold = 1
    }

    try {
        $document.BuiltInDocumentProperties.Item("Title").Value = $DocumentTitle
        $document.BuiltInDocumentProperties.Item("Subject").Value = "CAS HAIC Unit 4"
        $document.BuiltInDocumentProperties.Item("Author").Value = "CAS HAIC"
    }
    catch {
        # Some Office installations do not expose these properties through COM.
    }

    Convert-MarkdownToWord -Document $document -Lines $lines

    $footer = $section.Footers.Item(1).Range
    $footer.Text = "CAS HAIC - Unit 4 - $FooterLabel     "
    $footer.Font.Name = "Aptos"
    $footer.Font.Size = 8
    $footer.Font.Color = 8421504
    $footer.Collapse(0)
    $footer.Fields.Add($footer, 33) | Out-Null

    $document.SaveAs2($docxFullPath, 16)
    $document.ExportAsFixedFormat($pdfFullPath, 17)
}
finally {
    if ($document -ne $null) {
        $document.Close($false)
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($document) | Out-Null
    }
    if ($word -ne $null) {
        $word.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}

Write-Output "Created: $docxFullPath"
Write-Output "Created: $pdfFullPath"

