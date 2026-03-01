param(
  [string]$RunDir = "",
  [int]$PollMs = 800,
  [int]$DurationSec = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-LatestRunDir {
  param([string]$TemplateDir)
  $latestFile = Join-Path $TemplateDir "runtime\latest_run.txt"
  if (-not (Test-Path $latestFile)) {
    throw "latest_run.txt not found at: $latestFile"
  }
  $raw = (Get-Content -Path $latestFile -Raw).Trim()
  if ([string]::IsNullOrWhiteSpace($raw)) {
    throw "latest_run.txt is empty: $latestFile"
  }
  if ([System.IO.Path]::IsPathRooted($raw)) {
    return [System.IO.Path]::GetFullPath($raw)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $TemplateDir $raw))
}

function Read-NewChunk {
  param(
    [string]$Path,
    [long]$Cursor
  )
  if (-not (Test-Path $Path)) {
    return [pscustomobject]@{ Text = ""; Cursor = $Cursor }
  }
  try {
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
      if ($fs.Length -lt $Cursor) { $Cursor = 0L }
      $fs.Seek($Cursor, [System.IO.SeekOrigin]::Begin) | Out-Null
      $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true, 1024, $true)
      try {
        $text = $reader.ReadToEnd()
      } finally {
        $reader.Dispose()
      }
      return [pscustomobject]@{
        Text = $text
        Cursor = $fs.Position
      }
    } finally {
      $fs.Dispose()
    }
  } catch {
    return [pscustomobject]@{ Text = ""; Cursor = $Cursor }
  }
}

function Write-LabeledLines {
  param(
    [string]$Label,
    [string]$Text,
    [ConsoleColor]$Color
  )
  if ([string]::IsNullOrEmpty($Text)) { return }
  $normalized = $Text -replace "`r", ""
  $lines = $normalized -split "`n"
  foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    Write-Host ("[{0}] {1}" -f $Label, $line) -ForegroundColor $Color
  }
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$templateDir = Split-Path -Parent $scriptDir

$resolvedRunDir = if ([string]::IsNullOrWhiteSpace($RunDir)) {
  Resolve-LatestRunDir -TemplateDir $templateDir
} else {
  if ([System.IO.Path]::IsPathRooted($RunDir)) {
    [System.IO.Path]::GetFullPath($RunDir)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $templateDir $RunDir))
  }
}

if (-not (Test-Path $resolvedRunDir)) {
  throw "Run directory not found: $resolvedRunDir"
}

if ($PollMs -lt 100) { $PollMs = 100 }

$tracePath = Join-Path $resolvedRunDir "execution_trace.jsonl"
$traceCursor = 0L
$researcherErrPath = ""
$researcherErrCursor = 0L
$startedAt = Get-Date

Write-Host ("[monitor] run_dir={0}" -f $resolvedRunDir) -ForegroundColor Cyan
Write-Host ("[monitor] poll_ms={0}, duration_sec={1} (0 means unlimited)" -f $PollMs, $DurationSec) -ForegroundColor Cyan
Write-Host "[monitor] Press Ctrl+C to stop." -ForegroundColor Cyan

while ($true) {
  if ((Test-Path $tracePath)) {
    $traceChunk = Read-NewChunk -Path $tracePath -Cursor $traceCursor
    $traceCursor = [long]$traceChunk.Cursor
    Write-LabeledLines -Label "TRACE" -Text $traceChunk.Text -Color Gray
  }

  $latestResearcherErr = Get-ChildItem -Path $resolvedRunDir -Filter "iter_*_researcher_attempt_*_stderr.log" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

  if ($null -ne $latestResearcherErr) {
    if ($researcherErrPath -ne $latestResearcherErr.FullName) {
      $researcherErrPath = $latestResearcherErr.FullName
      $researcherErrCursor = 0L
      Write-Host ("[monitor] researcher_stderr={0}" -f $researcherErrPath) -ForegroundColor DarkCyan
    }

    $errChunk = Read-NewChunk -Path $researcherErrPath -Cursor $researcherErrCursor
    $researcherErrCursor = [long]$errChunk.Cursor
    Write-LabeledLines -Label "RESEARCHER" -Text $errChunk.Text -Color DarkYellow
  }

  if ($DurationSec -gt 0) {
    $elapsed = (New-TimeSpan -Start $startedAt -End (Get-Date)).TotalSeconds
    if ($elapsed -ge $DurationSec) { break }
  }

  Start-Sleep -Milliseconds $PollMs
}

Write-Host "[monitor] Done." -ForegroundColor Cyan
