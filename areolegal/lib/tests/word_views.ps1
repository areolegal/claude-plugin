param([string]$InPath, [string]$OutDir)
$ErrorActionPreference = 'Stop'
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$word = New-Object -ComObject Word.Application
Start-Sleep -Milliseconds 800
$after = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$newPids = @($after | Where-Object { $before -notcontains $_ })
$word.Visible = $false
$word.DisplayAlerts = 0
$info = @()
try {
  foreach ($mode in @('accept','reject')) {
    $doc = $word.Documents.Open($InPath, $false, $false, $false)
    if ($mode -eq 'accept') { $info += "TrackRevisions=" + $doc.TrackRevisions + " Revisions=" + $doc.Revisions.Count + " Comments=" + $doc.Comments.Count }
    if ($mode -eq 'accept') { $doc.Revisions.AcceptAll() } else { $doc.Revisions.RejectAll() }
    $lines = @()
    foreach ($p in $doc.Paragraphs) { $t = $p.Range.Text; $lines += $t.TrimEnd([char]13, [char]7) }
    $lines | Out-File -Encoding utf8 (Join-Path $OutDir ("word_" + $mode + ".txt"))
    $doc.Close(0)
  }
} finally {
  $word.Quit()
  foreach ($p in $newPids) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
}
$info | Out-File -Encoding utf8 (Join-Path $OutDir 'word_info.txt')
