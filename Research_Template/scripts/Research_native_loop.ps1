param(
  [string]$TemplatePath = ".\RESEARCH_NATIVE_LOOP_TEMPLATE.json",
  [Alias("UltimateGoals")][string]$Task = "",
  [string]$DoneCriteria = "",
  [string]$RepoRoot = ".",
  [string]$RiskTier,
  [int]$MaxIterations = 0,
  [Alias("GoalsPath")][string]$PrdPath = ".\Research_Template\RESEARCH_GOALS.md",
  [Alias("PlanPath")][string]$DevDocPath = ".\Research_Template\RESEARCH_PLAN.md",
  [string]$FindingsPath = ".\Research_Template\FINDINGS.md",
  [string]$ProblemLink = "",
  [ValidateSet("full","researcher_only")][string]$RoleMode = "researcher_only",
  [ValidateSet("mark_continue","stop","force_pivot")][string]$NoProgressPolicy = "mark_continue",
  [switch]$RequireEvidenceDelta,
  [switch]$ContinueAfterApproval,
  [switch]$StopOnApproval,
  [switch]$DryRun,
  [switch]$NoLiveOutput
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-PathSafe {
  param([string]$Base, [string]$PathSpec)
  if ([System.IO.Path]::IsPathRooted($PathSpec)) { return [System.IO.Path]::GetFullPath($PathSpec) }
  $normalized = $PathSpec -replace '^[.][/\\]', ''
  return [System.IO.Path]::GetFullPath((Join-Path $Base $normalized))
}

function Resolve-DocPath {
  param(
    [string]$RepoRoot,
    [string]$TemplateDir,
    [string]$PathSpec,
    [string]$FallbackLeaf
  )

  $candidates = New-Object System.Collections.ArrayList

  if (-not [string]::IsNullOrWhiteSpace($PathSpec)) {
    if ([System.IO.Path]::IsPathRooted($PathSpec)) {
      [void]$candidates.Add([System.IO.Path]::GetFullPath($PathSpec))
    } else {
      $normalized = $PathSpec -replace '^[.][/\\]', ''
      [void]$candidates.Add([System.IO.Path]::GetFullPath((Join-Path $RepoRoot $normalized)))
      [void]$candidates.Add([System.IO.Path]::GetFullPath((Join-Path $TemplateDir $normalized)))
    }
  }

  if (-not [string]::IsNullOrWhiteSpace($FallbackLeaf)) {
    [void]$candidates.Add([System.IO.Path]::GetFullPath((Join-Path $TemplateDir $FallbackLeaf)))
  }

  $seen = @{}
  foreach ($candidate in @($candidates.ToArray())) {
    if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
    if ($seen.ContainsKey($candidate)) { continue }
    $seen[$candidate] = $true
    if (Test-Path $candidate) { return $candidate }
  }

  if ($candidates.Count -gt 0) {
    return [string]$candidates[0]
  }
  return ""
}

function Save-Json {
  param([object]$Obj, [string]$Path)
  $Obj | ConvertTo-Json -Depth 12 | Set-Content -Path $Path -Encoding UTF8
}

function Write-Heartbeat {
  param([string]$HeartbeatFile, [string]$Message)
  $line = "{0} | {1}" -f (Get-Date -Format "s"), $Message
  Add-Content -Path $HeartbeatFile -Value $line
}

function Write-TraceEvent {
  param(
    [string]$TraceFile,
    [string]$RunId,
    [string]$Step,
    [string]$Status,
    [int]$Iteration = -1,
    [int]$Attempt = -1,
    [string]$Message = ""
  )
  if ([string]::IsNullOrWhiteSpace($TraceFile)) { return }
  $record = [ordered]@{
    ts = (Get-Date).ToString("o")
    run_id = $RunId
    step = $Step
    status = $Status
    iteration = if ($Iteration -ge 0) { $Iteration } else { $null }
    attempt = if ($Attempt -ge 0) { $Attempt } else { $null }
    message = $Message
  }
  ($record | ConvertTo-Json -Compress) | Add-Content -Path $TraceFile -Encoding UTF8
}

function Add-RollingItem {
  param(
    [System.Collections.ArrayList]$List,
    [string]$Item,
    [int]$MaxItems = 12
  )
  if ($null -eq $List) { return }
  if ([string]::IsNullOrWhiteSpace($Item)) { return }
  [void]$List.Add($Item.Trim())
  while ($List.Count -gt $MaxItems) {
    $List.RemoveAt(0)
  }
}

function Get-TailArray {
  param(
    [System.Collections.ArrayList]$List,
    [int]$MaxItems = 4
  )
  if ($null -eq $List -or $List.Count -le 0) { return @() }
  if ($List.Count -le $MaxItems) { return @($List.ToArray()) }
  $start = $List.Count - $MaxItems
  return @($List.ToArray()[$start..($List.Count - 1)])
}

function Clamp-ContextText {
  param(
    [string]$Text,
    [int]$MaxChars = 1200
  )
  if ($null -eq $Text) { return "" }
  $value = [string]$Text
  if ($value.Length -le $MaxChars) { return $value }
  return ($value.Substring(0, $MaxChars) + " ...[truncated]")
}

function Get-TailArrayClamped {
  param(
    [System.Collections.ArrayList]$List,
    [int]$MaxItems = 4,
    [int]$MaxCharsPerItem = 1200
  )
  $tail = Get-TailArray -List $List -MaxItems $MaxItems
  $out = @()
  foreach ($item in $tail) {
    $out += (Clamp-ContextText -Text ([string]$item) -MaxChars $MaxCharsPerItem)
  }
  return @($out)
}

function Read-NewStreamChunk {
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

function Parse-FirstJsonObject {
  param([string]$Text)
  $raw = [string]$Text
  if ([string]::IsNullOrWhiteSpace($raw)) {
    throw "Model output is empty; cannot parse JSON."
  }

  # Prefer fenced ```json blocks to avoid accidentally matching later braces in markdown.
  $fenceIdx = $raw.IndexOf("```json", [System.StringComparison]::OrdinalIgnoreCase)
  if ($fenceIdx -ge 0) {
    $lineEnd = $raw.IndexOf("`n", $fenceIdx)
    if ($lineEnd -ge 0) {
      $jsonStart = $lineEnd + 1
      $fenceEnd = $raw.IndexOf("```", $jsonStart, [System.StringComparison]::Ordinal)
      if ($fenceEnd -gt $jsonStart) {
        $jsonText = $raw.Substring($jsonStart, $fenceEnd - $jsonStart).Trim()
        if (-not [string]::IsNullOrWhiteSpace($jsonText)) {
          return ($jsonText | ConvertFrom-Json)
        }
      }
    }
  }

  # Fallback: extract the first balanced JSON object by brace counting, ignoring braces inside strings.
  $start = $raw.IndexOf("{")
  if ($start -lt 0) {
    throw "Could not find JSON object in model output."
  }

  $depth = 0
  $inString = $false
  $escaped = $false
  $end = -1

  for ($i = $start; $i -lt $raw.Length; $i++) {
    $ch = $raw[$i]

    if ($escaped) {
      $escaped = $false
      continue
    }
    if ($inString -and $ch -eq '\') {
      $escaped = $true
      continue
    }
    if ($ch -eq '"') {
      $inString = -not $inString
      continue
    }
    if ($inString) { continue }

    if ($ch -eq '{') {
      $depth++
      continue
    }
    if ($ch -eq '}') {
      $depth--
      if ($depth -eq 0) {
        $end = $i
        break
      }
    }
  }

  if ($end -lt 0) {
    throw "Could not find a balanced JSON object in model output."
  }

  $jsonCandidate = $raw.Substring($start, $end - $start + 1)
  return ($jsonCandidate | ConvertFrom-Json)
}

function Convert-ToRepoRelativePath {
  param(
    [string]$RepoRoot,
    [string]$Path
  )
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  $fullRepo = [System.IO.Path]::GetFullPath($RepoRoot)
  $fullPath = [System.IO.Path]::GetFullPath($Path)
  if ($fullPath.StartsWith($fullRepo, [System.StringComparison]::OrdinalIgnoreCase)) {
    $relative = $fullPath.Substring($fullRepo.Length).TrimStart('\','/')
    if ([string]::IsNullOrWhiteSpace($relative)) { return "." }
    return $relative -replace '\\','/'
  }
  return $fullPath -replace '\\','/'
}

function Get-EvidenceSnapshot {
  param(
    [string]$RepoRoot,
    [string[]]$PathSpecs
  )
  $snapshot = @{}
  foreach ($spec in $PathSpecs) {
    if ([string]::IsNullOrWhiteSpace($spec)) { continue }
    $fullPath = Resolve-PathSafe -Base $RepoRoot -PathSpec $spec
    if (-not (Test-Path $fullPath)) { continue }
    $item = Get-Item -Path $fullPath -ErrorAction SilentlyContinue
    if ($null -eq $item) { continue }
    if ($item.PSIsContainer) {
      Get-ChildItem -Path $fullPath -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        $snapshot[[System.IO.Path]::GetFullPath($_.FullName)] = [int64]$_.LastWriteTimeUtc.Ticks
      }
    } else {
      $snapshot[[System.IO.Path]::GetFullPath($item.FullName)] = [int64]$item.LastWriteTimeUtc.Ticks
    }
  }
  return $snapshot
}

function Get-EvidenceDeltaPaths {
  param(
    [hashtable]$Before,
    [hashtable]$After
  )
  if ($null -eq $Before) { $Before = @{} }
  if ($null -eq $After) { $After = @{} }
  $delta = New-Object System.Collections.ArrayList
  foreach ($path in $After.Keys) {
    if (-not $Before.ContainsKey($path)) {
      [void]$delta.Add($path)
      continue
    }
    if ([int64]$After[$path] -gt [int64]$Before[$path]) {
      [void]$delta.Add($path)
    }
  }
  return @($delta.ToArray() | Sort-Object -Unique)
}

function Get-GitStatusMap {
  param([string]$RepoRoot)
  $map = @{}
  try {
    $lines = @(& git -C $RepoRoot status --porcelain=v1 --untracked-files=all 2>$null)
  } catch {
    return $map
  }
  foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    if ($line.Length -lt 4) { continue }
    $status = $line.Substring(0, 2)
    $path = $line.Substring(3).Trim()
    if ($path -match ' -> ') {
      $parts = $path -split ' -> '
      $path = $parts[$parts.Length - 1].Trim()
    }
    if ([string]::IsNullOrWhiteSpace($path)) { continue }
    $normalized = ($path -replace '\\', '/')
    $map[$normalized] = $status
  }
  return $map
}

function Get-GitDeltaPaths {
  param(
    [hashtable]$Before,
    [hashtable]$After
  )
  if ($null -eq $Before) { $Before = @{} }
  if ($null -eq $After) { $After = @{} }
  $delta = New-Object System.Collections.ArrayList
  foreach ($path in $After.Keys) {
    if (-not $Before.ContainsKey($path)) {
      [void]$delta.Add($path)
      continue
    }
    if ([string]$Before[$path] -ne [string]$After[$path]) {
      [void]$delta.Add($path)
    }
  }
  return @($delta.ToArray() | Sort-Object -Unique)
}

function Test-PathExcludedByPrefix {
  param(
    [string]$RelativePath,
    [string[]]$ExcludePrefixes
  )
  if ([string]::IsNullOrWhiteSpace($RelativePath)) { return $true }
  $normalizedPath = ($RelativePath -replace '\\', '/').TrimStart('/')
  foreach ($prefix in $ExcludePrefixes) {
    if ([string]::IsNullOrWhiteSpace($prefix)) { continue }
    $normalizedPrefix = ($prefix -replace '\\', '/').TrimStart('/')
    if ($normalizedPath.StartsWith($normalizedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
      return $true
    }
  }
  return $false
}

function Resolve-CommitCandidatePaths {
  param(
    [string]$RepoRoot,
    [string[]]$CandidatePaths
  )
  $resolved = New-Object System.Collections.ArrayList
  foreach ($candidate in $CandidatePaths) {
    $raw = [string]$candidate
    if ([string]::IsNullOrWhiteSpace($raw)) { continue }
    $fullPath = Resolve-PathSafe -Base $RepoRoot -PathSpec $raw
    if (-not (Test-Path $fullPath)) { continue }
    $relative = Convert-ToRepoRelativePath -RepoRoot $RepoRoot -Path $fullPath
    if ([string]::IsNullOrWhiteSpace($relative) -or $relative -eq ".") { continue }
    [void]$resolved.Add(($relative -replace '\\', '/'))
  }
  return @($resolved.ToArray() | Sort-Object -Unique)
}

function Invoke-IterationAutoCommit {
  param(
    [string]$RepoRoot,
    [int]$Iteration,
    [string]$Summary,
    [string]$NextDirection,
    [string[]]$FilesTouched,
    [string]$CommitMessageHint,
    [hashtable]$GitStatusBefore,
    [string[]]$ExcludePrefixes,
    [switch]$AutoPush
  )

  $result = [ordered]@{
    attempted = $true
    committed = $false
    pushed = $false
    reason = ""
    commit_hash = ""
    staged_paths = @()
  }

  if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $result.reason = "git_not_found"
    return $result
  }

  $afterMap = Get-GitStatusMap -RepoRoot $RepoRoot
  $deltaPaths = Get-GitDeltaPaths -Before $GitStatusBefore -After $afterMap
  $resolvedTouched = Resolve-CommitCandidatePaths -RepoRoot $RepoRoot -CandidatePaths $FilesTouched

  $candidatePaths = New-Object System.Collections.ArrayList
  foreach ($path in $resolvedTouched) {
    # Commit explicitly touched files if they are currently dirty, even if the repo started dirty.
    if ($afterMap.ContainsKey($path)) {
      [void]$candidatePaths.Add($path)
    }
  }
  if ($candidatePaths.Count -eq 0) {
    foreach ($path in $deltaPaths) {
      [void]$candidatePaths.Add($path)
    }
  }

  $filtered = New-Object System.Collections.ArrayList
  foreach ($path in @($candidatePaths.ToArray() | Sort-Object -Unique)) {
    if (Test-PathExcludedByPrefix -RelativePath $path -ExcludePrefixes $ExcludePrefixes) { continue }
    [void]$filtered.Add($path)
  }
  if ($filtered.Count -eq 0) {
    $result.reason = "no_commit_candidates"
    return $result
  }

  $pathArgs = @($filtered.ToArray())
  try {
    & git -C $RepoRoot add -- @pathArgs
    $staged = @(& git -C $RepoRoot diff --cached --name-only -- @pathArgs 2>$null)
    if ($staged.Count -eq 0) {
      $result.reason = "no_staged_changes"
      return $result
    }
    $commitMessage = $CommitMessageHint
    if ([string]::IsNullOrWhiteSpace($commitMessage)) {
      $summaryCompact = if ([string]::IsNullOrWhiteSpace($Summary)) { "update" } else { $Summary.Trim() }
      if ($summaryCompact.Length -gt 90) { $summaryCompact = $summaryCompact.Substring(0, 90) }
      $commitMessage = ("research(loop): iter {0} - {1}" -f $Iteration, $summaryCompact)
    }
    & git -C $RepoRoot commit -m $commitMessage -- @pathArgs | Out-Null
    $hash = (& git -C $RepoRoot rev-parse --short HEAD 2>$null)
    $result.committed = $true
    $result.commit_hash = [string]$hash
    $result.staged_paths = @($staged)

    if ($AutoPush) {
      & git -C $RepoRoot push | Out-Null
      $result.pushed = $true
    }
  } catch {
    $result.reason = $_.Exception.Message
    return $result
  }

  $result.reason = "ok"
  return $result
}

function Is-TemplatePlaceholder {
  param([string]$Value)
  if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
  $trim = $Value.Trim()
  if ($trim -match '^<\s*required\b') { return $true }
  return $false
}

function Is-ProcessAlive {
  param([int]$PidValue)
  if ($PidValue -le 0) { return $false }
  try {
    $null = Get-Process -Id $PidValue -ErrorAction Stop
    return $true
  } catch {
    return $false
  }
}

function Get-ProcessCommandLine {
  param([int]$PidValue)
  if ($PidValue -le 0) { return "" }
  try {
    $proc = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $PidValue) -ErrorAction Stop
    if ($null -eq $proc) { return "" }
    return [string]$proc.CommandLine
  } catch {
    return ""
  }
}

function Is-ResearchLoopProcess {
  param([int]$PidValue)
  $cmd = Get-ProcessCommandLine -PidValue $PidValue
  if ([string]::IsNullOrWhiteSpace($cmd)) { return $false }
  return ($cmd -match "Research_native_loop\.ps1")
}

function Acquire-RunLock {
  param(
    [string]$LockFile,
    [string]$RunId
  )
  if (Test-Path $LockFile) {
    $existing = $null
    $removeStaleLock = $false
    try {
      $existing = Get-Content -Path $LockFile -Raw | ConvertFrom-Json
    } catch {
      $existing = $null
      $removeStaleLock = $true
    }

    if ($null -ne $existing) {
      $existingPid = if ($existing.PSObject.Properties.Name -contains "pid") { [int]$existing.pid } else { -1 }
      if (Is-ProcessAlive -PidValue $existingPid) {
        $existingRunId = if ($existing.PSObject.Properties.Name -contains "run_id") { [string]$existing.run_id } else { "unknown" }
        if (Is-ResearchLoopProcess -PidValue $existingPid) {
          throw "Another loop run is active (run_id=$existingRunId, pid=$existingPid). Wait for it to finish or remove stale lock: $LockFile"
        }
        $removeStaleLock = $true
        Write-Host ("[lock] Cleared stale lock with reused pid={0} (not Research_native_loop.ps1)." -f $existingPid) -ForegroundColor DarkYellow
      } else {
        $removeStaleLock = $true
      }
    } else {
      Write-Host "[lock] Cleared unreadable stale lock file before acquiring new lock." -ForegroundColor DarkYellow
    }

    if ($removeStaleLock) {
      Remove-Item -Path $LockFile -Force -ErrorAction SilentlyContinue
    }
  }

  $lock = [ordered]@{
    run_id = $RunId
    pid = $PID
    started_at = (Get-Date).ToString("s")
    command_line = (Get-ProcessCommandLine -PidValue $PID)
  }
  $lock | ConvertTo-Json -Depth 4 | Set-Content -Path $LockFile -Encoding UTF8
}

function Release-RunLock {
  param(
    [string]$LockFile,
    [string]$RunId
  )
  if (-not (Test-Path $LockFile)) { return }
  try {
    $existing = Get-Content -Path $LockFile -Raw | ConvertFrom-Json
    $existingRunId = if ($existing.PSObject.Properties.Name -contains "run_id") { [string]$existing.run_id } else { "" }
    if ($existingRunId -eq $RunId) {
      Remove-Item -Path $LockFile -Force -ErrorAction SilentlyContinue
    }
  } catch {
    Remove-Item -Path $LockFile -Force -ErrorAction SilentlyContinue
  }
}

function Test-BlockedOutput {
  param(
    [string]$Text,
    [string[]]$Patterns
  )
  if ([string]::IsNullOrWhiteSpace($Text)) {
    return [pscustomobject]@{ blocked = $false; pattern = "" }
  }

  foreach ($pattern in $Patterns) {
    if ([string]::IsNullOrWhiteSpace($pattern)) { continue }
    if ($Text -match [regex]::Escape($pattern)) {
      return [pscustomobject]@{ blocked = $true; pattern = $pattern }
    }
  }

  return [pscustomobject]@{ blocked = $false; pattern = "" }
}

function Write-BlockerReport {
  param(
    [string]$BlockerFile,
    [string]$Reason,
    [string]$LastStep,
    [string]$NextActionCommand
  )
  $report = @"
# Blocker Report

- blocker_reason: $Reason
- last_successful_step: $LastStep
- next_action_command: $NextActionCommand
- resume_command: codex resume --last
"@
  Set-Content -Path $BlockerFile -Value $report -Encoding UTF8
}

function Get-CodexLaunchSpec {
  $isWindowsHost = [System.Environment]::OSVersion.Platform -eq [System.PlatformID]::Win32NT
  $allCodexCommands = @(Get-Command codex -All -ErrorAction Stop)

  if ($isWindowsHost) {
    $winAppCommand = $allCodexCommands |
      Where-Object { $_.CommandType -eq "Application" } |
      Where-Object { (($_ | Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue) -like "*.cmd") } |
      Select-Object -First 1

    if (-not $winAppCommand) {
      $winAppCommand = $allCodexCommands |
        Where-Object { $_.CommandType -eq "Application" } |
        Select-Object -First 1
    }

    if ($winAppCommand) {
      $winPath = $winAppCommand | Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue
      if (-not [string]::IsNullOrWhiteSpace($winPath)) {
        return [pscustomobject]@{
          FilePath = $winPath
          ArgPrefix = @()
        }
      }
    }

    $winScriptCommand = $allCodexCommands |
      Where-Object { $_.CommandType -eq "ExternalScript" } |
      Select-Object -First 1
    if ($winScriptCommand) {
      $winScriptPath = $winScriptCommand | Select-Object -ExpandProperty Path -ErrorAction SilentlyContinue
      if (-not [string]::IsNullOrWhiteSpace($winScriptPath)) {
        return [pscustomobject]@{
          FilePath = "powershell"
          ArgPrefix = @("-ExecutionPolicy", "Bypass", "-File", $winScriptPath)
        }
      }
    }

    return [pscustomobject]@{
      FilePath = "codex"
      ArgPrefix = @()
    }
  }
  return [pscustomobject]@{
    FilePath = "codex"
    ArgPrefix = @()
  }
}

function Invoke-CodexExecWithSafety {
  param(
    [string]$Prompt,
    [string]$StepName,
    [int]$Iteration,
    [object]$Template,
    [object]$CodexLaunchSpec,
    [string[]]$ExtraExecArgs,
    [string]$HeartbeatFile,
    [string]$TraceFile,
    [string]$RunId,
    [bool]$ShowLiveOutput,
    [string]$StepArtifactsDir = "",
    [switch]$DryRun
  )

  if ($DryRun) {
    if ($StepName -like "director*") {
      Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "dry_run_output" -Iteration $Iteration -Attempt 0 -Message "Synthetic director output generated."
      return "{`"approved_final`":false,`"note_for_researcher`":`"dry run director note`",`"researcher_direction`":`"dry run researcher direction`",`"mode`":`"light`"}"
    }
    if ($StepName -eq "evaluator") {
      Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "dry_run_output" -Iteration $Iteration -Attempt 0 -Message "Synthetic evaluator output generated."
      $forceCompression = if ($Iteration -ge 2) { "true" } else { "false" }
      $payload = "{`"approved`":false,`"quality_score`":0.75,`"progress_pct`":18,`"summary_for_user`":`"dry run evaluator summary`",`"next_direction`":`"dry run next direction`",`"coverage`":`"dry run coverage`",`"residual_risk`":`"dry run residual risk`",`"risk_level`":`"medium`",`"enforce_compression`":__FORCE__,`"compression_reason`":`"dry run adaptive compression`",`"context_risk_score`":0.35,`"snapshot_priority`":`"normal`"}"
      return $payload.Replace("__FORCE__", $forceCompression)
    }
    if ($StepName -eq "bootstrap_merge") {
      Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "dry_run_output" -Iteration $Iteration -Attempt 0 -Message "Synthetic bootstrap output generated."
      return "{`"baseline_progress_pct`":25,`"reuse_candidates`":[{`"item`":`"prior findings draft`",`"confidence`":0.8}],`"open_gaps`":[`"source triangulation`"],`"next_direction`":`"validate and extend existing findings`"}"
    }
    Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "dry_run_output" -Iteration $Iteration -Attempt 0 -Message "Synthetic researcher output generated."
    return "{`"approved_candidate`":false,`"quality_score_self`":0.7,`"progress_pct_claim`":20,`"summary_for_user`":`"dry run researcher summary`",`"evidence_updates`":[`"none`"],`"limitations`":[`"none`"],`"next_direction`":`"continue`"}"
  }

  $retryCfg = $Template.runtime_safety.auto_retry_on_failure
  $retryEnabled = [bool]$retryCfg.enabled
  $maxRetries = if ($retryEnabled) { [int]$retryCfg.max_retries_per_step } else { 0 }
  $backoff = @($retryCfg.backoff_seconds)
  $maxIdleMinutes = [int]$Template.runtime_safety.max_idle_minutes
  $heartbeatSec = [math]::Max(1, [int]$Template.runtime_safety.heartbeat_interval_sec)
  $liveOutputPollMs = 1000
  if ($Template.runtime_safety.PSObject.Properties.Name -contains "live_output_poll_ms") {
    try { $liveOutputPollMs = [int]$Template.runtime_safety.live_output_poll_ms } catch {}
  }
  if ($liveOutputPollMs -lt 100) { $liveOutputPollMs = 100 }
  $consoleStatusSec = 10
  if ($Template.runtime_safety.PSObject.Properties.Name -contains "console_status_interval_sec") {
    try { $consoleStatusSec = [int]$Template.runtime_safety.console_status_interval_sec } catch {}
  }
  if ($consoleStatusSec -lt 1) { $consoleStatusSec = 1 }

  for ($attempt = 0; $attempt -le $maxRetries; $attempt++) {
    $safeStepName = ($StepName -replace '[^A-Za-z0-9_-]', '_')
    $persistOutFile = ""
    $persistErrFile = ""
    $cleanupOutErrFiles = $true
    if (-not [string]::IsNullOrWhiteSpace($StepArtifactsDir)) {
      $persistOutFile = Join-Path $StepArtifactsDir ("iter_{0}_{1}_attempt_{2}_stdout.log" -f $Iteration, $safeStepName, $attempt)
      $persistErrFile = Join-Path $StepArtifactsDir ("iter_{0}_{1}_attempt_{2}_stderr.log" -f $Iteration, $safeStepName, $attempt)
      Set-Content -Path $persistOutFile -Value "" -Encoding UTF8
      Set-Content -Path $persistErrFile -Value "" -Encoding UTF8
      $outFile = $persistOutFile
      $errFile = $persistErrFile
      $cleanupOutErrFiles = $false
    } else {
      $outFile = Join-Path $env:TEMP ("codex_{0}.out" -f [guid]::NewGuid().ToString("N"))
      $errFile = Join-Path $env:TEMP ("codex_{0}.err" -f [guid]::NewGuid().ToString("N"))
    }
    $promptFile = Join-Path $env:TEMP ("codex_{0}.prompt" -f [guid]::NewGuid().ToString("N"))
    $messageFile = Join-Path $env:TEMP ("codex_{0}.message" -f [guid]::NewGuid().ToString("N"))
    $timedOut = $false
    $stdoutCursor = 0L
    $stderrCursor = 0L

    Write-Heartbeat -HeartbeatFile $HeartbeatFile -Message ("step={0} iter={1} attempt={2} start" -f $StepName, $Iteration, $attempt)
    Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_start" -Iteration $Iteration -Attempt $attempt -Message "Launching codex exec."
    Write-Host ("[{0}] start step={1} iter={2} attempt={3}" -f (Get-Date -Format "HH:mm:ss"), $StepName, $Iteration, $attempt) -ForegroundColor Cyan
    Set-Content -Path $promptFile -Value $Prompt -Encoding UTF8

    $procArgs = @()
    $procArgs += @($CodexLaunchSpec.ArgPrefix)
    $procArgs += "exec"
    $procArgs += @($ExtraExecArgs)
    $procArgs += "--color"
    $procArgs += "never"
    $procArgs += "--output-last-message"
    $procArgs += $messageFile
    $procArgs += "-"
    $proc = Start-Process -FilePath $CodexLaunchSpec.FilePath -ArgumentList $procArgs -PassThru -NoNewWindow -RedirectStandardInput $promptFile -RedirectStandardOutput $outFile -RedirectStandardError $errFile
    $attemptStart = Get-Date
    $lastActivity = $attemptStart
    $lastHeartbeatAt = $attemptStart
    $lastStatusAt = $attemptStart
    $lastOutLen = 0L
    $lastErrLen = 0L

    while (-not $proc.HasExited) {
      Start-Sleep -Milliseconds $liveOutputPollMs
      $now = Get-Date
      $outLen = 0L
      $errLen = 0L
      if (Test-Path $outFile) {
        $outLen = (Get-Item $outFile).Length
      }
      if (Test-Path $errFile) {
        $errLen = (Get-Item $errFile).Length
      }
      if ($outLen -gt $lastOutLen -or $errLen -gt $lastErrLen) {
        $lastActivity = $now
      }
      $lastOutLen = $outLen
      $lastErrLen = $errLen

      if ($ShowLiveOutput) {
        $stdoutChunk = Read-NewStreamChunk -Path $outFile -Cursor $stdoutCursor
        $stdoutCursor = [long]$stdoutChunk.Cursor
        if (-not [string]::IsNullOrWhiteSpace($stdoutChunk.Text)) {
          Write-Host $stdoutChunk.Text -NoNewline
        }

        $stderrChunk = Read-NewStreamChunk -Path $errFile -Cursor $stderrCursor
        $stderrCursor = [long]$stderrChunk.Cursor
        if (-not [string]::IsNullOrWhiteSpace($stderrChunk.Text)) {
          Write-Host $stderrChunk.Text -NoNewline -ForegroundColor DarkYellow
        }
      }

      if (((New-TimeSpan -Start $lastStatusAt -End $now).TotalSeconds) -ge $consoleStatusSec) {
        $elapsedSec = [int](New-TimeSpan -Start $attemptStart -End $now).TotalSeconds
        $idleSec = [int](New-TimeSpan -Start $lastActivity -End $now).TotalSeconds
        $statusMsg = ("step={0} iter={1} attempt={2} elapsed={3}s idle={4}s out={5}B err={6}B" -f $StepName, $Iteration, $attempt, $elapsedSec, $idleSec, $outLen, $errLen)
        Write-Host ("[{0}] status {1}" -f $now.ToString("HH:mm:ss"), $statusMsg) -ForegroundColor DarkCyan
        Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_status" -Iteration $Iteration -Attempt $attempt -Message $statusMsg
        $lastStatusAt = $now
      }

      if (((New-TimeSpan -Start $lastHeartbeatAt -End $now).TotalSeconds) -ge $heartbeatSec) {
        Write-Heartbeat -HeartbeatFile $HeartbeatFile -Message ("step={0} iter={1} attempt={2} alive" -f $StepName, $Iteration, $attempt)
        Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_alive" -Iteration $Iteration -Attempt $attempt -Message "Process still running."
        $lastHeartbeatAt = $now
      }

      if (((New-TimeSpan -Start $lastActivity -End $now).TotalMinutes) -ge $maxIdleMinutes) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        $timedOut = $true
        Write-Heartbeat -HeartbeatFile $HeartbeatFile -Message ("step={0} iter={1} attempt={2} timeout" -f $StepName, $Iteration, $attempt)
        Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_timeout" -Iteration $Iteration -Attempt $attempt -Message "Stopped due to idle timeout."
        break
      }
    }

    try { $proc.WaitForExit() | Out-Null } catch {}
    $exitCode = $null
    try { $exitCode = $proc.ExitCode } catch {}
    $doneNow = Get-Date
    $doneElapsedSec = [int](New-TimeSpan -Start $attemptStart -End $doneNow).TotalSeconds
    $doneExit = if ($null -eq $exitCode) { "NA" } else { [string]$exitCode }
    Write-Host ("[{0}] done step={1} iter={2} attempt={3} exit={4} elapsed={5}s timeout={6}" -f $doneNow.ToString("HH:mm:ss"), $StepName, $Iteration, $attempt, $doneExit, $doneElapsedSec, $timedOut) -ForegroundColor Cyan

    if ($ShowLiveOutput) {
      $stdoutTail = Read-NewStreamChunk -Path $outFile -Cursor $stdoutCursor
      if (-not [string]::IsNullOrWhiteSpace($stdoutTail.Text)) {
        Write-Host $stdoutTail.Text -NoNewline
      }
      $stderrTail = Read-NewStreamChunk -Path $errFile -Cursor $stderrCursor
      if (-not [string]::IsNullOrWhiteSpace($stderrTail.Text)) {
        Write-Host $stderrTail.Text -NoNewline -ForegroundColor DarkYellow
      }
    }

    $stdout = if (Test-Path $outFile) { Get-Content -Path $outFile -Raw } else { "" }
    $stderr = if (Test-Path $errFile) { Get-Content -Path $errFile -Raw } else { "" }
    $lastMessage = if (Test-Path $messageFile) { Get-Content -Path $messageFile -Raw } else { "" }

    if (-not [string]::IsNullOrWhiteSpace($StepArtifactsDir)) {
      $stdoutLogFile = if (-not [string]::IsNullOrWhiteSpace($persistOutFile)) { $persistOutFile } else { $outFile }
      $stderrLogFile = if (-not [string]::IsNullOrWhiteSpace($persistErrFile)) { $persistErrFile } else { $errFile }
      Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_stream_logs_saved" -Iteration $Iteration -Attempt $attempt -Message ("stdout={0}; stderr={1}" -f $stdoutLogFile, $stderrLogFile)
    }

    Remove-Item -Path $promptFile -ErrorAction SilentlyContinue
    Remove-Item -Path $messageFile -ErrorAction SilentlyContinue
    if ($cleanupOutErrFiles) {
      Remove-Item -Path $outFile -ErrorAction SilentlyContinue
      Remove-Item -Path $errFile -ErrorAction SilentlyContinue
    }

    $effectiveOutput = if (-not [string]::IsNullOrWhiteSpace($lastMessage)) { $lastMessage } else { $stdout }
    if (-not $timedOut -and -not [string]::IsNullOrWhiteSpace($effectiveOutput)) {
      Write-Heartbeat -HeartbeatFile $HeartbeatFile -Message ("step={0} iter={1} attempt={2} success" -f $StepName, $Iteration, $attempt)
      Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_success" -Iteration $Iteration -Attempt $attempt -Message "Received non-empty model output."
      return $effectiveOutput.Trim()
    }

    $reason = if ($timedOut) { "timeout-no-output" } else { "nonzero-exit-or-empty-output" }
    $exitDisplay = if ($null -eq $exitCode) { "NA" } else { [string]$exitCode }
    Write-Heartbeat -HeartbeatFile $HeartbeatFile -Message ("step={0} iter={1} attempt={2} fail reason={3} exit={4} stderr={5}" -f $StepName, $Iteration, $attempt, $reason, $exitDisplay, ($stderr -replace '\s+', ' '))
    Write-TraceEvent -TraceFile $TraceFile -RunId $RunId -Step $StepName -Status "attempt_fail" -Iteration $Iteration -Attempt $attempt -Message ("reason={0}; exit={1}" -f $reason, $exitDisplay)

    if ($attempt -lt $maxRetries) {
      $sleepSec = if ($attempt -lt $backoff.Count) { [int]$backoff[$attempt] } else { 30 }
      Start-Sleep -Seconds $sleepSec
      continue
    }

    throw "codex exec failed at step '$StepName' (iteration=$Iteration). reason=$reason"
  }

  throw "Unexpected loop fallthrough."
}

if (-not $DryRun -and -not (Get-Command codex -ErrorAction SilentlyContinue)) {
  throw "codex command not found in PATH."
}
$codexLaunchSpec = if (-not $DryRun) { Get-CodexLaunchSpec } else { $null }

$templateFullPath = [System.IO.Path]::GetFullPath($TemplatePath)
if (-not (Test-Path $templateFullPath)) {
  $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  $fallbackTemplatePath = Join-Path (Split-Path -Parent $scriptDir) "RESEARCH_NATIVE_LOOP_TEMPLATE.json"
  if (Test-Path $fallbackTemplatePath) {
    $templateFullPath = [System.IO.Path]::GetFullPath($fallbackTemplatePath)
  } else {
    throw "Template file not found: $templateFullPath"
  }
}

$template = Get-Content -Path $templateFullPath -Raw | ConvertFrom-Json
if ($template.template_id -ne "codex_native_research_loop_v1") {
  throw "Unexpected template_id: $($template.template_id)"
}
if ([version]$template.version -lt [version]"1.1.0") {
  throw "Template version must be >= 1.1.0. Found: $($template.version)"
}
if (-not [bool]$template.official_commands_only) {
  throw "Template must enforce official_commands_only=true"
}

$templateDir = Split-Path -Parent $templateFullPath
$templateRepoRootCandidate = Split-Path -Parent $templateDir
$requestedRepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

# Portability guard: when launched from another cwd, prefer the repo root that actually contains this template.
$resolvedRepoRoot = $requestedRepoRoot
$expectedTemplateUnderRepo = [System.IO.Path]::GetFullPath((Join-Path $resolvedRepoRoot "Research_Template"))
$sameTemplateLocation = $false
if (Test-Path $expectedTemplateUnderRepo) {
  $sameTemplateLocation = ($expectedTemplateUnderRepo -eq [System.IO.Path]::GetFullPath($templateDir))
}
if (-not $sameTemplateLocation) {
  $resolvedRepoRoot = $templateRepoRootCandidate
}
if (-not (Test-Path $resolvedRepoRoot)) {
  throw "RepoRoot does not exist: $resolvedRepoRoot"
}

$resolvedGoalsPath = Resolve-DocPath -RepoRoot $resolvedRepoRoot -TemplateDir $templateDir -PathSpec $PrdPath -FallbackLeaf "RESEARCH_GOALS.md"
$resolvedPlanPath = Resolve-DocPath -RepoRoot $resolvedRepoRoot -TemplateDir $templateDir -PathSpec $DevDocPath -FallbackLeaf "RESEARCH_PLAN.md"
$resolvedFindingsPath = Resolve-DocPath -RepoRoot $resolvedRepoRoot -TemplateDir $templateDir -PathSpec $FindingsPath -FallbackLeaf "FINDINGS.md"
$resolvedMemoryPath = Resolve-DocPath -RepoRoot $resolvedRepoRoot -TemplateDir $templateDir -PathSpec "./MEMORY.md" -FallbackLeaf "../MEMORY.md"

if (-not (Test-Path $resolvedGoalsPath)) {
  throw "Goals document not found. Checked path: $resolvedGoalsPath"
}
if (-not (Test-Path $resolvedPlanPath)) {
  throw "Plan document not found. Checked path: $resolvedPlanPath"
}
if (-not (Test-Path $resolvedFindingsPath)) {
  throw "Findings document not found. Checked path: $resolvedFindingsPath"
}

$PrdPath = $resolvedGoalsPath
$DevDocPath = $resolvedPlanPath
$FindingsPath = $resolvedFindingsPath
if (-not (Test-Path $resolvedMemoryPath)) {
  $resolvedMemoryPath = [System.IO.Path]::GetFullPath((Join-Path $resolvedRepoRoot "MEMORY.md"))
}

$templateTaskDefault = [string]$template.inputs.task
$templateDoneCriteriaDefault = [string]$template.inputs.done_criteria
$templateProblemLinkDefault = if ($template.inputs.PSObject.Properties.Name -contains "default_problem_link") { [string]$template.inputs.default_problem_link } else { "" }
$templateLiveOutput = if ($template.runtime_safety.PSObject.Properties.Name -contains "live_console_output") { [bool]$template.runtime_safety.live_console_output } else { $true }
$blockerPatterns = if ($template.runtime_safety.PSObject.Properties.Name -contains "blocker_short_circuit_patterns") { @($template.runtime_safety.blocker_short_circuit_patterns) } else { @("blocked by policy", "read-only", "write operations are blocked") }
$nestedExecCfg = if ($template.runtime_safety.PSObject.Properties.Name -contains "nested_codex_exec") { $template.runtime_safety.nested_codex_exec } else { $null }
$qualityMajorMilestone = if ($template.runtime_safety.PSObject.Properties.Name -contains "major_quality_milestone") { [double]$template.runtime_safety.major_quality_milestone } else { 0.90 }
$qualityFinalGate = if ($template.runtime_safety.PSObject.Properties.Name -contains "final_quality_gate") { [double]$template.runtime_safety.final_quality_gate } else { 0.95 }
$minIterationsBeforeApprovalStop = if ($template.runtime_safety.PSObject.Properties.Name -contains "min_iterations_before_approval_stop") { [int]$template.runtime_safety.min_iterations_before_approval_stop } else { 3 }
$approvalStreakRequired = if ($template.runtime_safety.PSObject.Properties.Name -contains "approval_streak_required") { [int]$template.runtime_safety.approval_streak_required } else { 2 }
$requireEvaluatorApprovedForStop = if ($template.runtime_safety.PSObject.Properties.Name -contains "require_evaluator_approved_for_stop") { [bool]$template.runtime_safety.require_evaluator_approved_for_stop } else { $true }
$stallWindow = if ($template.runtime_safety.PSObject.Properties.Name -contains "stall_non_improving_iterations") { [int]$template.runtime_safety.stall_non_improving_iterations } else { 3 }
$scoreDropTrigger = if ($template.runtime_safety.PSObject.Properties.Name -contains "risk_spike_score_drop_threshold") { [double]$template.runtime_safety.risk_spike_score_drop_threshold } else { 0.05 }
$burstIterations = if ($template.runtime_safety.PSObject.Properties.Name -contains "adaptive_burst_iterations") { [int]$template.runtime_safety.adaptive_burst_iterations } else { 2 }
$reuseConfidenceThreshold = if ($template.runtime_safety.PSObject.Properties.Name -contains "reuse_confidence_threshold") { [double]$template.runtime_safety.reuse_confidence_threshold } else { 0.70 }
$contextMode = if ($template.runtime_safety.PSObject.Properties.Name -contains "context_mode") { [string]$template.runtime_safety.context_mode } else { "rolling_thread" }
$compressionCfg = if ($template.runtime_safety.PSObject.Properties.Name -contains "compression") { $template.runtime_safety.compression } else { $null }
$contextCompressionEnabled = if ($null -ne $compressionCfg -and $compressionCfg.PSObject.Properties.Name -contains "enabled") { [bool]$compressionCfg.enabled } else { $true }
$compressionPromptChars = if ($null -ne $compressionCfg -and $compressionCfg.PSObject.Properties.Name -contains "trigger_prompt_chars") { [int]$compressionCfg.trigger_prompt_chars } else { 30000 }
$compressionStallIterations = if ($null -ne $compressionCfg -and $compressionCfg.PSObject.Properties.Name -contains "trigger_stall_iterations") { [int]$compressionCfg.trigger_stall_iterations } else { 3 }
$compressionDriftSignal = if ($null -ne $compressionCfg -and $compressionCfg.PSObject.Properties.Name -contains "trigger_drift_signal") { [string]$compressionCfg.trigger_drift_signal } else { "direction_mismatch_rework" }
$compressionForcedRefresh = if ($null -ne $compressionCfg -and $compressionCfg.PSObject.Properties.Name -contains "forced_refresh") { [string]$compressionCfg.forced_refresh } else { "never" }
$sourcePolicy = if ($template.inputs.PSObject.Properties.Name -contains "source_policy") { [string]$template.inputs.source_policy } else { "Primary-source-first, flexible for high-signal secondary sources." }
$templateRoleModeDefault = if ($template.runtime_safety.PSObject.Properties.Name -contains "role_mode_default") { [string]$template.runtime_safety.role_mode_default } else { "researcher_only" }
$researcherOnlyCfg = if ($template.runtime_safety.PSObject.Properties.Name -contains "researcher_only") { $template.runtime_safety.researcher_only } else { $null }
$templateNoProgressPolicy = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "no_progress_policy") { [string]$researcherOnlyCfg.no_progress_policy } else { "mark_continue" }
$templateRequireEvidenceDelta = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "require_evidence_delta") { [bool]$researcherOnlyCfg.require_evidence_delta } else { $true }
$templateWriteResearcherIterationMd = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "write_researcher_iteration_md") { [bool]$researcherOnlyCfg.write_researcher_iteration_md } else { $true }
$templateEvidencePaths = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "evidence_paths") { @($researcherOnlyCfg.evidence_paths) } else { @("./report", "./results", "./experiments", "./training") }
$templateRecoverMemoryEachIteration = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "recover_memory_each_iteration") { [bool]$researcherOnlyCfg.recover_memory_each_iteration } else { $true }
$templateReviewPreviousIteration = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "review_previous_iteration") { [bool]$researcherOnlyCfg.review_previous_iteration } else { $true }
$templateStrictJsonContract = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "strict_json_contract") { [bool]$researcherOnlyCfg.strict_json_contract } else { $false }
$autoCommitCfg = if ($null -ne $researcherOnlyCfg -and $researcherOnlyCfg.PSObject.Properties.Name -contains "auto_commit_each_iteration") { $researcherOnlyCfg.auto_commit_each_iteration } else { $null }
$templateAutoCommitEnabled = if ($null -ne $autoCommitCfg -and $autoCommitCfg.PSObject.Properties.Name -contains "enabled") { [bool]$autoCommitCfg.enabled } else { $false }
$templateAutoCommitPush = if ($null -ne $autoCommitCfg -and $autoCommitCfg.PSObject.Properties.Name -contains "auto_push") { [bool]$autoCommitCfg.auto_push } else { $false }
if ($null -ne $autoCommitCfg -and $autoCommitCfg.PSObject.Properties.Name -contains "exclude_paths") {
  $templateAutoCommitExcludePaths = [string[]]@($autoCommitCfg.exclude_paths)
} else {
  $templateAutoCommitExcludePaths = [string[]]@("Research_Template/runtime/")
}
$effectiveRoleMode = if ($PSBoundParameters.ContainsKey("RoleMode")) { [string]$RoleMode } else { $templateRoleModeDefault }
if ([string]::IsNullOrWhiteSpace($effectiveRoleMode)) { $effectiveRoleMode = "researcher_only" }
$effectiveRoleMode = $effectiveRoleMode.ToLowerInvariant()
if ($effectiveRoleMode -notin @("full","researcher_only")) {
  throw "Unsupported role mode '$effectiveRoleMode'. Allowed: full, researcher_only."
}
$effectiveNoProgressPolicy = if ($PSBoundParameters.ContainsKey("NoProgressPolicy")) { [string]$NoProgressPolicy } else { $templateNoProgressPolicy }
if ([string]::IsNullOrWhiteSpace($effectiveNoProgressPolicy)) { $effectiveNoProgressPolicy = "mark_continue" }
$effectiveNoProgressPolicy = $effectiveNoProgressPolicy.ToLowerInvariant()
if ($effectiveNoProgressPolicy -notin @("mark_continue","stop","force_pivot")) {
  throw "Unsupported no_progress policy '$effectiveNoProgressPolicy'. Allowed: mark_continue, stop, force_pivot."
}
$effectiveRequireEvidenceDelta = if ($RequireEvidenceDelta) { $true } else { $templateRequireEvidenceDelta }
$effectiveWriteResearcherIterationMd = $templateWriteResearcherIterationMd
$effectiveAutoCommitEnabled = ($effectiveRoleMode -eq "researcher_only" -and $templateAutoCommitEnabled -and -not $DryRun)
$effectiveAutoCommitPush = ($effectiveAutoCommitEnabled -and $templateAutoCommitPush)
$templateContinueAfterApproval = if ($template.runtime_safety.PSObject.Properties.Name -contains "continue_after_approval") { [bool]$template.runtime_safety.continue_after_approval } else { $false }
$effectiveContinueAfterApproval = $templateContinueAfterApproval
if ($ContinueAfterApproval) { $effectiveContinueAfterApproval = $true }
if ($StopOnApproval) { $effectiveContinueAfterApproval = $false }
if ($minIterationsBeforeApprovalStop -lt 1) { $minIterationsBeforeApprovalStop = 1 }
if ($approvalStreakRequired -lt 1) { $approvalStreakRequired = 1 }

$effectiveTask = if (-not [string]::IsNullOrWhiteSpace($Task)) { $Task } elseif (-not (Is-TemplatePlaceholder -Value $templateTaskDefault)) { $templateTaskDefault } else { "Complete research goals with validated evidence, synthesis, and actionable next steps." }
$effectiveDoneCriteria = if (-not [string]::IsNullOrWhiteSpace($DoneCriteria)) { $DoneCriteria } elseif (-not (Is-TemplatePlaceholder -Value $templateDoneCriteriaDefault)) { $templateDoneCriteriaDefault } else { "Director final signoff with quality >= 0.95, and complete executive plus technical findings." }
$effectiveProblemLink = if (-not [string]::IsNullOrWhiteSpace($ProblemLink)) { $ProblemLink } elseif (-not [string]::IsNullOrWhiteSpace($templateProblemLinkDefault)) { $templateProblemLinkDefault } else { "" }
$effectiveLiveOutput = (-not $NoLiveOutput) -and $templateLiveOutput

$effectiveRiskTier = if ($RiskTier) { $RiskTier } else { [string]$template.inputs.risk_tier }
$templateMaxIterations = [int]$template.inputs.max_iterations
$hasExplicitMaxIterations = $PSBoundParameters.ContainsKey("MaxIterations")
$effectiveMaxIterations = if ($hasExplicitMaxIterations) { [int]$MaxIterations } elseif ($templateMaxIterations -gt 0) { $templateMaxIterations } else { 0 }
# Dry-run uses synthetic evaluator/director outputs and cannot satisfy final gate,
# so auto-cap to one iteration unless caller explicitly sets a positive max.
if ($DryRun -and $effectiveMaxIterations -le 0) {
  $effectiveMaxIterations = 1
}
$maxIterationsLabel = if ($effectiveMaxIterations -gt 0) { [string]$effectiveMaxIterations } else { "unlimited" }
$nestedExecArgs = @()
if ($null -ne $nestedExecCfg) {
  $dangerMode = if ($nestedExecCfg.PSObject.Properties.Name -contains "dangerously_bypass_approvals_and_sandbox") { [bool]$nestedExecCfg.dangerously_bypass_approvals_and_sandbox } else { $false }
  $skipRepoCheck = if ($nestedExecCfg.PSObject.Properties.Name -contains "skip_git_repo_check") { [bool]$nestedExecCfg.skip_git_repo_check } else { $false }
  if ($dangerMode) { $nestedExecArgs += "--dangerously-bypass-approvals-and-sandbox" }
  if ($skipRepoCheck) { $nestedExecArgs += "--skip-git-repo-check" }
}

$runRootDir = Resolve-PathSafe -Base $resolvedRepoRoot -PathSpec ([string]$template.artifacts.run_dir)
$stateLeaf = Split-Path -Leaf ([string]$template.artifacts.state_file)
$finalLeaf = Split-Path -Leaf ([string]$template.artifacts.final_report_file)
$heartbeatLeaf = Split-Path -Leaf ([string]$template.artifacts.heartbeat_log_file)
$blockerLeaf = Split-Path -Leaf ([string]$template.artifacts.blocker_report_file)
$traceSpec = if ($template.artifacts.PSObject.Properties.Name -contains "trace_log_file") { [string]$template.artifacts.trace_log_file } else { "./.codex-loop/execution_trace.jsonl" }
$traceLeaf = Split-Path -Leaf $traceSpec

$runId = "research_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss")
New-Item -ItemType Directory -Path $runRootDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $runRootDir "runs") -Force | Out-Null
$lockFile = Join-Path $runRootDir "active.lock"
Acquire-RunLock -LockFile $lockFile -RunId $runId
$runDir = Join-Path (Join-Path $runRootDir "runs") $runId
New-Item -ItemType Directory -Path $runDir -Force | Out-Null
$stateFile = Join-Path $runDir $stateLeaf
$finalReportFile = Join-Path $runDir $finalLeaf
$heartbeatFile = Join-Path $runDir $heartbeatLeaf
$blockerFile = Join-Path $runDir $blockerLeaf
$traceFile = Join-Path $runDir $traceLeaf
$contextSnapshotJsonFile = Join-Path $runDir "context_snapshot.json"
$contextSnapshotMdFile = Join-Path $runDir "context_snapshot.md"
$contextPressureFile = Join-Path $runDir "context_pressure.json"
Set-Content -Path $heartbeatFile -Value "" -Encoding UTF8
Set-Content -Path $traceFile -Value "" -Encoding UTF8
if (Test-Path $blockerFile) {
  Remove-Item -Path $blockerFile -Force -ErrorAction SilentlyContinue
}

$state = [ordered]@{
  run_id = $runId
  status = "running"
  started_at = (Get-Date).ToString("s")
  repo_root = $resolvedRepoRoot
  run_root_dir = $runRootDir
  run_dir = $runDir
  risk_tier = $effectiveRiskTier
  task = $effectiveTask
  done_criteria = $effectiveDoneCriteria
  trace_file = $traceFile
  lock_file = $lockFile
  nested_exec_args = $nestedExecArgs
  role_mode = $effectiveRoleMode
  no_progress_policy = $effectiveNoProgressPolicy
  require_evidence_delta = $effectiveRequireEvidenceDelta
  write_researcher_iteration_md = $effectiveWriteResearcherIterationMd
  strict_json_contract = $templateStrictJsonContract
  recover_memory_each_iteration = $templateRecoverMemoryEachIteration
  review_previous_iteration = $templateReviewPreviousIteration
  memory_doc_path = $resolvedMemoryPath
  auto_commit_each_iteration = $effectiveAutoCommitEnabled
  auto_push_each_commit = $effectiveAutoCommitPush
  auto_commit_exclude_paths = $templateAutoCommitExcludePaths
  evidence_paths = $templateEvidencePaths
  no_progress_count = 0
  max_iterations = $effectiveMaxIterations
  continue_after_approval = $effectiveContinueAfterApproval
  min_iterations_before_approval_stop = $minIterationsBeforeApprovalStop
  approval_streak_required = $approvalStreakRequired
  require_evaluator_approved_for_stop = $requireEvaluatorApprovedForStop
  current_iteration = 0
  milestones = @("25", "50", "75", "100")
  milestone_hits = @()
  context_mode = $contextMode
  rolling_context_bytes_est = 0
  context_risk_score = 0.0
  last_compression_iteration = 0
  compression_count = 0
  active_snapshot_file = ""
  active_snapshot_markdown_file = ""
  context_pressure_file = $contextPressureFile
  next_direction = "none"
  history = @()
}
Save-Json -Obj $state -Path $stateFile
Set-Content -Path (Join-Path $runRootDir "latest_run.txt") -Value $runDir -Encoding UTF8 -NoNewline

$milestones = @(25, 50, 75, 100)
$milestoneHit = @{}
$rollingValidatedEvidence = New-Object System.Collections.ArrayList
$rollingRejectedPaths = New-Object System.Collections.ArrayList
$rollingOpenQuestions = New-Object System.Collections.ArrayList
$rollingRecentSummaries = New-Object System.Collections.ArrayList
$rollingRecentDirections = New-Object System.Collections.ArrayList
$contextPressureHistory = New-Object System.Collections.ArrayList
$lastSuccessfulStep = "template_loaded"
$approved = $false
$directorApprovedFinal = $false
$blocked = $false
$blockedReason = ""
$qualityScore = 0.0
$progressPct = 0
$approvalStreak = 0
$processApprovalSatisfied = $false
$noProgressCount = 0
$bestQualityScore = 0.0
$lastQualityScore = -1.0
$nonImprovingCount = 0
$burstRemaining = 0
$majorQualityMilestoneHit = $false
$directorNote = "No director note yet."
$summaryForUser = ""
$residualRisk = "Loop has not reached approval yet."
$coverage = ""
$validationResult = "PARTIAL"

$state.major_quality_milestone = $qualityMajorMilestone
$state.final_quality_gate = $qualityFinalGate
$state.stall_window = $stallWindow
$state.burst_iterations = $burstIterations
$state.reuse_confidence_threshold = $reuseConfidenceThreshold
$state.context_compression_enabled = $contextCompressionEnabled
$state.context_compression_prompt_chars = $compressionPromptChars
$state.context_compression_stall_iterations = $compressionStallIterations
$state.context_compression_drift_signal = $compressionDriftSignal
$state.context_compression_forced_refresh = $compressionForcedRefresh
Save-Json -Obj $state -Path $stateFile

Push-Location $resolvedRepoRoot
try {
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "run" -Status "start" -Message ("risk_tier={0}; role_mode={1}; max_iterations={2}; auto_commit={3}; auto_push={4}; nested_exec_args={5}" -f $effectiveRiskTier, $effectiveRoleMode, $maxIterationsLabel, $effectiveAutoCommitEnabled, $effectiveAutoCommitPush, ($nestedExecArgs -join " "))
  Write-Heartbeat -HeartbeatFile $heartbeatFile -Message "run_id=$runId start"

  $bootstrapPrompt = @"
You are a startup analyst for a research loop.
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Source policy: $sourcePolicy
Goals doc: $PrdPath
Plan doc: $DevDocPath
Findings doc: $FindingsPath
Problem link: $effectiveProblemLink

Perform a repo-wide smart scan and return strict JSON:
{
  "baseline_progress_pct": 0-100,
  "reuse_candidates": [{"item":"...","confidence":0.0-1.0}],
  "open_gaps": ["..."],
  "next_direction": "...",
  "summary_for_user": "..."
}
"@
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "bootstrap_merge" -Status "dispatch" -Iteration 0 -Message "Dispatching bootstrap merge prompt."
  $bootstrapRaw = Invoke-CodexExecWithSafety -Prompt $bootstrapPrompt -StepName "bootstrap_merge" -Iteration 0 -Template $template -CodexLaunchSpec $codexLaunchSpec -ExtraExecArgs $nestedExecArgs -HeartbeatFile $heartbeatFile -TraceFile $traceFile -RunId $runId -ShowLiveOutput:$effectiveLiveOutput -StepArtifactsDir $runDir -DryRun:$DryRun
  $bootstrapFile = Join-Path $runDir "iter_0_bootstrap_merge.txt"
  Set-Content -Path $bootstrapFile -Value $bootstrapRaw -Encoding UTF8
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "bootstrap_merge" -Status "artifact_written" -Iteration 0 -Message ("Saved output to {0}" -f $bootstrapFile)
  $lastSuccessfulStep = "bootstrap_merge"
  $bootstrapBlock = Test-BlockedOutput -Text $bootstrapRaw -Patterns $blockerPatterns
  if ($bootstrapBlock.blocked) {
    $blocked = $true
    $blockedReason = "Blocked marker detected in bootstrap output (pattern='$($bootstrapBlock.pattern)')."
    $residualRisk = $blockedReason
    $state.status = "blocked"
    Save-Json -Obj $state -Path $stateFile
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "bootstrap_merge" -Status "blocked_short_circuit" -Iteration 0 -Message $blockedReason
    throw $blockedReason
  }

  $bootstrapSummary = ""
  $reuseCandidates = @()
  $bootstrapOpenGaps = @()
  try {
    $bootstrapJson = Parse-FirstJsonObject -Text $bootstrapRaw
    $progressPct = if ($bootstrapJson.PSObject.Properties.Name -contains "baseline_progress_pct") { [math]::Max(0, [math]::Min(100, [int]$bootstrapJson.baseline_progress_pct)) } else { 0 }
    $reuseCandidates = if ($bootstrapJson.PSObject.Properties.Name -contains "reuse_candidates") { @($bootstrapJson.reuse_candidates) } else { @() }
    $bootstrapOpenGaps = if ($bootstrapJson.PSObject.Properties.Name -contains "open_gaps") { @($bootstrapJson.open_gaps) } else { @() }
    if ($bootstrapJson.PSObject.Properties.Name -contains "next_direction") {
      $state.next_direction = [string]$bootstrapJson.next_direction
    }
    $bootstrapSummary = if ($bootstrapJson.PSObject.Properties.Name -contains "summary_for_user") { [string]$bootstrapJson.summary_for_user } else { "Bootstrap completed." }
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "bootstrap_merge" -Status "parsed" -Iteration 0 -Message ("baseline_progress={0}" -f $progressPct)
  } catch {
    $state.next_direction = "Start with highest-priority unresolved research gap."
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "bootstrap_merge" -Status "parse_fallback" -Iteration 0 -Message "Bootstrap parse fallback."
  }
  $bootstrapSnapshotFile = Join-Path $runDir "bootstrap_snapshot.json"
  $mergeBaselineFile = Join-Path $runDir "merge_baseline.json"
  $reusedItemsFile = Join-Path $runDir "reused_items_verified.md"
  Save-Json -Obj ([ordered]@{ baseline_progress_pct = $progressPct; summary = $bootstrapSummary; open_gaps = $bootstrapOpenGaps; raw_file = $bootstrapFile }) -Path $bootstrapSnapshotFile
  Save-Json -Obj ([ordered]@{ reuse_confidence_threshold = $reuseConfidenceThreshold; reuse_candidates = $reuseCandidates }) -Path $mergeBaselineFile
  $reuseLines = @("# Reused Items (Auto Merge Verification)", "", ("- threshold: {0}" -f $reuseConfidenceThreshold))
  foreach ($candidate in $reuseCandidates) {
    $itemName = if ($candidate.PSObject.Properties.Name -contains "item") { [string]$candidate.item } else { "unnamed-item" }
    $confidence = if ($candidate.PSObject.Properties.Name -contains "confidence") { [double]$candidate.confidence } else { 0.0 }
    $decision = if ($confidence -ge $reuseConfidenceThreshold) { "reused_and_verified" } else { "revalidate_in_loop" }
    $reuseLines += ("- item: {0} | confidence: {1} | decision: {2}" -f $itemName, $confidence, $decision)
  }
  Set-Content -Path $reusedItemsFile -Value ($reuseLines -join [Environment]::NewLine) -Encoding UTF8
  Add-RollingItem -List $rollingRecentSummaries -Item ("Bootstrap: {0}" -f $bootstrapSummary) -MaxItems 10
  Add-RollingItem -List $rollingRecentDirections -Item $state.next_direction -MaxItems 10
  foreach ($gap in $bootstrapOpenGaps) {
    Add-RollingItem -List $rollingOpenQuestions -Item ([string]$gap) -MaxItems 16
  }
  $state.bootstrap_snapshot_file = $bootstrapSnapshotFile
  $state.merge_baseline_file = $mergeBaselineFile
  $state.reused_items_file = $reusedItemsFile
  Save-Json -Obj $state -Path $stateFile

  if ($effectiveRoleMode -eq "full") {
    $commanderPrompt = @"
You are DIRECTOR for a research loop.
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Source policy: $sourcePolicy
Baseline progress: $progressPct
Bootstrap summary: $bootstrapSummary
Goals doc: $PrdPath
Plan doc: $DevDocPath
Findings doc: $FindingsPath

You may adjust planning docs if needed.
Return strict JSON only:
{
  "plan_health": "good|needs_adjustment|critical",
  "summary_for_user": "...",
  "researcher_direction": "...",
  "approved_final": true|false
}
"@
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "dispatch" -Iteration 0 -Message "Dispatching director preflight prompt."
    $commanderRaw = Invoke-CodexExecWithSafety -Prompt $commanderPrompt -StepName "director_preflight" -Iteration 0 -Template $template -CodexLaunchSpec $codexLaunchSpec -ExtraExecArgs $nestedExecArgs -HeartbeatFile $heartbeatFile -TraceFile $traceFile -RunId $runId -ShowLiveOutput:$effectiveLiveOutput -StepArtifactsDir $runDir -DryRun:$DryRun
    $commanderFile = Join-Path $runDir "iter_0_director_preflight.txt"
    Set-Content -Path $commanderFile -Value $commanderRaw -Encoding UTF8
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "artifact_written" -Iteration 0 -Message ("Saved output to {0}" -f $commanderFile)
    $lastSuccessfulStep = "director_preflight"
    $commanderBlock = Test-BlockedOutput -Text $commanderRaw -Patterns $blockerPatterns
    if ($commanderBlock.blocked) {
      $blocked = $true
      $blockedReason = "Blocked marker detected in director preflight output (pattern='$($commanderBlock.pattern)')."
      $residualRisk = $blockedReason
      $state.status = "blocked"
      Save-Json -Obj $state -Path $stateFile
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "blocked_short_circuit" -Iteration 0 -Message $blockedReason
      throw $blockedReason
    }
    try {
      $commanderJson = Parse-FirstJsonObject -Text $commanderRaw
      if ($commanderJson.PSObject.Properties.Name -contains "researcher_direction") {
        $state.next_direction = [string]$commanderJson.researcher_direction
      }
      if ($commanderJson.PSObject.Properties.Name -contains "summary_for_user") {
        $directorNote = [string]$commanderJson.summary_for_user
      }
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "parsed" -Iteration 0 -Message "Parsed director preflight JSON and updated next direction."
    } catch {
      $state.next_direction = "Start with highest-priority unresolved research question and update findings."
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "parse_fallback" -Iteration 0 -Message "Director preflight JSON parse failed, using fallback direction."
    }
  } else {
    $directorNote = "Researcher-only mode: director preflight disabled."
    if ([string]::IsNullOrWhiteSpace($state.next_direction) -or $state.next_direction -eq "none") {
      $state.next_direction = "Execute the next best concrete experiment or analysis toward the ultimate goals."
    }
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_preflight" -Status "skipped_researcher_only" -Iteration 0 -Message "Director preflight skipped due to researcher_only role mode."
  }
  Add-RollingItem -List $rollingRecentSummaries -Item ("Director preflight: {0}" -f $directorNote) -MaxItems 10
  Add-RollingItem -List $rollingRecentDirections -Item $state.next_direction -MaxItems 10

  $i = 1
  while ($true) {
    if ($effectiveMaxIterations -gt 0 -and $i -gt $effectiveMaxIterations) {
      break
    }
    $iterationLabel = if ($effectiveMaxIterations -gt 0) { "{0}/{1}" -f $i, $effectiveMaxIterations } else { "{0}/unlimited" -f $i }
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "start" -Iteration $i -Message ("Starting iteration {0}" -f $iterationLabel)
    $state.current_iteration = $i
    Save-Json -Obj $state -Path $stateFile
    $previousDirection = [string]$state.next_direction
    $gitStatusBeforeIteration = @{}
    if ($effectiveAutoCommitEnabled) {
      $gitStatusBeforeIteration = Get-GitStatusMap -RepoRoot $resolvedRepoRoot
    }
    $previousIterationHistory = $null
    if ($state.history.Count -gt 0) {
      $previousIterationHistory = $state.history[$state.history.Count - 1]
    }
    $previousResearcherFile = ""
    $previousResearcherMdFile = ""
    if ($null -ne $previousIterationHistory) {
      if ($previousIterationHistory -is [System.Collections.IDictionary]) {
        if ($previousIterationHistory.Contains("worker_file")) {
          $previousResearcherFile = [string]$previousIterationHistory["worker_file"]
        }
        if ($previousIterationHistory.Contains("worker_markdown_file")) {
          $previousResearcherMdFile = [string]$previousIterationHistory["worker_markdown_file"]
        }
      } else {
        if ($previousIterationHistory.PSObject.Properties.Name -contains "worker_file") {
          $previousResearcherFile = [string]$previousIterationHistory.worker_file
        }
        if ($previousIterationHistory.PSObject.Properties.Name -contains "worker_markdown_file") {
          $previousResearcherMdFile = [string]$previousIterationHistory.worker_markdown_file
        }
      }
    }
    if ([string]::IsNullOrWhiteSpace($previousResearcherFile) -and $i -gt 1) {
      $fallbackPrevWorker = Join-Path $runDir ("iter_{0}_researcher.txt" -f ($i - 1))
      if (Test-Path $fallbackPrevWorker) { $previousResearcherFile = $fallbackPrevWorker }
    }
    if ([string]::IsNullOrWhiteSpace($previousResearcherMdFile) -and $i -gt 1) {
      $fallbackPrevMd = Join-Path $runDir ("iter_{0}_researcher.md" -f ($i - 1))
      if (Test-Path $fallbackPrevMd) { $previousResearcherMdFile = $fallbackPrevMd }
    }
    $previousResearcherExcerpt = ""
    if (-not [string]::IsNullOrWhiteSpace($previousResearcherFile) -and (Test-Path $previousResearcherFile)) {
      $prevRaw = Get-Content -Path $previousResearcherFile -Raw
      $previousResearcherExcerpt = if ($prevRaw.Length -gt 3500) { $prevRaw.Substring(0, 3500) } else { $prevRaw }
    }
    $memoryExcerpt = ""
    if (Test-Path $resolvedMemoryPath) {
      $memoryRaw = Get-Content -Path $resolvedMemoryPath -Raw
      if ($memoryRaw.Length -gt 5000) {
        $memoryExcerpt = $memoryRaw.Substring($memoryRaw.Length - 5000)
      } else {
        $memoryExcerpt = $memoryRaw
      }
    }

    $activeSnapshotExcerpt = ""
    if (-not [string]::IsNullOrWhiteSpace($state.active_snapshot_file) -and (Test-Path $state.active_snapshot_file)) {
      $rawSnapshot = Get-Content -Path $state.active_snapshot_file -Raw
      $activeSnapshotExcerpt = if ($rawSnapshot.Length -gt 4000) { $rawSnapshot.Substring(0, 4000) } else { $rawSnapshot }
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "context_snapshot" -Status "applied" -Iteration $i -Message ("Using active snapshot {0}" -f $state.active_snapshot_file)
    }

    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "context_packet" -Status "build_start" -Iteration $i -Message "Building rolling context packet."
    $rollingContextPacket = [ordered]@{
      mode = $contextMode
      previous_direction = (Clamp-ContextText -Text $previousDirection -MaxChars 1600)
      director_note = (Clamp-ContextText -Text $directorNote -MaxChars 1600)
      recent_summaries = (Get-TailArrayClamped -List $rollingRecentSummaries -MaxItems 4 -MaxCharsPerItem 1000)
      recent_directions = (Get-TailArrayClamped -List $rollingRecentDirections -MaxItems 4 -MaxCharsPerItem 1000)
      validated_evidence = (Get-TailArrayClamped -List $rollingValidatedEvidence -MaxItems 8 -MaxCharsPerItem 1000)
      rejected_paths = (Get-TailArrayClamped -List $rollingRejectedPaths -MaxItems 8 -MaxCharsPerItem 1000)
      open_questions = (Get-TailArrayClamped -List $rollingOpenQuestions -MaxItems 10 -MaxCharsPerItem 1000)
      memory_doc_path = $resolvedMemoryPath
      memory_excerpt = (Clamp-ContextText -Text $memoryExcerpt -MaxChars 2000)
      previous_researcher_file = $previousResearcherFile
      previous_researcher_md_file = $previousResearcherMdFile
      previous_researcher_excerpt = (Clamp-ContextText -Text $previousResearcherExcerpt -MaxChars 1500)
      active_snapshot_file = $state.active_snapshot_file
      active_snapshot_excerpt = (Clamp-ContextText -Text $activeSnapshotExcerpt -MaxChars 2000)
      last_quality_score = $qualityScore
      progress_pct = $progressPct
    }
    $rollingContextJson = $rollingContextPacket | ConvertTo-Json -Depth 10
    if ($rollingContextJson.Length -gt 20000) {
      $rollingContextPacket.recent_summaries = @((Get-TailArrayClamped -List $rollingRecentSummaries -MaxItems 2 -MaxCharsPerItem 600))
      $rollingContextPacket.recent_directions = @((Get-TailArrayClamped -List $rollingRecentDirections -MaxItems 2 -MaxCharsPerItem 600))
      $rollingContextPacket.validated_evidence = @((Get-TailArrayClamped -List $rollingValidatedEvidence -MaxItems 4 -MaxCharsPerItem 600))
      $rollingContextPacket.rejected_paths = @((Get-TailArrayClamped -List $rollingRejectedPaths -MaxItems 4 -MaxCharsPerItem 600))
      $rollingContextPacket.open_questions = @((Get-TailArrayClamped -List $rollingOpenQuestions -MaxItems 6 -MaxCharsPerItem 600))
      $rollingContextPacket.memory_excerpt = (Clamp-ContextText -Text $memoryExcerpt -MaxChars 1200)
      $rollingContextPacket.previous_researcher_excerpt = (Clamp-ContextText -Text $previousResearcherExcerpt -MaxChars 900)
      $rollingContextPacket.active_snapshot_excerpt = (Clamp-ContextText -Text $activeSnapshotExcerpt -MaxChars 1000)
      $rollingContextJson = $rollingContextPacket | ConvertTo-Json -Depth 10
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "context_packet" -Status "trimmed" -Iteration $i -Message ("Rolling context JSON exceeded cap; trimmed to {0} chars." -f $rollingContextJson.Length)
    }
    $state.rolling_context_bytes_est = $rollingContextJson.Length
    Save-Json -Obj $state -Path $stateFile
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "context_packet" -Status "build_done" -Iteration $i -Message ("Rolling context packet size={0} chars." -f $rollingContextJson.Length)

    $evidenceSnapshotBefore = @{}
    if ($effectiveRoleMode -eq "researcher_only" -and $effectiveRequireEvidenceDelta) {
      $evidenceSnapshotBefore = Get-EvidenceSnapshot -RepoRoot $resolvedRepoRoot -PathSpecs $templateEvidencePaths
    }

    if ($effectiveRoleMode -eq "researcher_only") {
      $shouldRecoverMemory = ($i -eq 1 -or $templateRecoverMemoryEachIteration)
      $shouldReviewPrevious = ($i -gt 1 -and $templateReviewPreviousIteration)
      $protocolLines = New-Object System.Collections.ArrayList
      if ($i -eq 1) {
        [void]$protocolLines.Add("Recover memory/context from MEMORY.md + goals/plan/findings, then immediately execute one next-best research step.")
      } else {
        if ($shouldRecoverMemory) {
          [void]$protocolLines.Add("Recover memory/context from MEMORY.md + goals/plan/findings (optional by config).")
        } else {
          [void]$protocolLines.Add("Do not re-read the full MEMORY.md; use the rolling context packet + excerpts.")
        }
        if ($shouldReviewPrevious) {
          [void]$protocolLines.Add("Review the previous researcher artifact/markdown and continue from it.")
        }
      }
      [void]$protocolLines.Add("Execute one concrete next-best step now (run commands and/or edit files).")
      [void]$protocolLines.Add("Update repo artifacts (FINDINGS/PLAN/GOALS/etc) and set a precise next_direction for the next iteration.")
      $iterationProtocolText = (@($protocolLines.ToArray()) | ForEach-Object { "- $_" }) -join [Environment]::NewLine
      $jsonStrictRule = if ($templateStrictJsonContract) {
        "JSON contract is strict for this run."
      } else {
        "If JSON is not perfect, continue with best effort; do not stop the task."
      }
      $iterationGoal = if ($i -eq 1) {
        "Recover memory/context + execute one concrete step."
      } else {
        "Execute the next best step."
      }
      $workerPrompt = @"
You are RESEARCHER in a research CLI loop (researcher-only mode).
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Iteration: $iterationLabel
Iteration goal: $iterationGoal
Goals doc: $PrdPath
Plan doc: $DevDocPath
Findings doc: $FindingsPath
Source policy: $sourcePolicy
Current direction: $($state.next_direction)
Memory doc: $resolvedMemoryPath
Previous researcher artifact: $previousResearcherFile
Previous researcher markdown: $previousResearcherMdFile
Rolling context packet (JSON):
$rollingContextJson

Act like a normal Codex coding session in this repo: inspect files, run commands, edit code/docs, and validate where possible.
Iteration protocol:
$iterationProtocolText
- Do not run nested orchestration loops (`Research_native_loop.ps1` / `start_research.bat`).
- Do not edit files under `Research_Template/runtime/` (loop-managed logs/locks/artifacts).
- Kaggle is optional; use it only when it materially helps the current step.

Output format:
- Prefer JSON first and then short markdown.
- $jsonStrictRule
Preferred JSON fields:
{
  "summary_for_user": "...",
  "actions": ["..."],
  "files_touched": ["relative/path"],
  "commit_message": "...",
  "evidence_updates": ["..."],
  "limitations": ["..."],
  "progress_pct_claim": 0-100,
  "quality_score_self": 0.0-1.0,
  "approved_candidate": true|false,
  "next_direction": "..."
}
"@
    } else {
      $workerPrompt = @"
You are RESEARCHER in a research CLI loop.
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Iteration: $iterationLabel
Goals doc: $PrdPath
Plan doc: $DevDocPath
Findings doc: $FindingsPath
Source policy: $sourcePolicy
Direction from evaluator: $($state.next_direction)
Director post-note from last iteration: $directorNote
Rolling context packet (JSON):
$rollingContextJson

Execute the next best research step now.
Important constraints:
- Do NOT invoke `Research_native_loop.ps1`, `start_research.bat`, or any nested "run research loop/template" command from inside this loop.
- Do NOT start another orchestration loop recursively.
- Perform one concrete next-best research action, then return results.
Return JSON first, then short markdown.
Required JSON:
{
  "approved_candidate": true|false,
  "quality_score_self": 0.0-1.0,
  "progress_pct_claim": 0-100,
  "summary_for_user": "...",
  "evidence_updates": ["..."],
  "limitations": ["..."],
  "next_direction": "..."
}
"@
    }
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "researcher" -Status "dispatch" -Iteration $i -Message "Dispatching researcher prompt."
    $workerRaw = Invoke-CodexExecWithSafety -Prompt $workerPrompt -StepName "researcher" -Iteration $i -Template $template -CodexLaunchSpec $codexLaunchSpec -ExtraExecArgs $nestedExecArgs -HeartbeatFile $heartbeatFile -TraceFile $traceFile -RunId $runId -ShowLiveOutput:$effectiveLiveOutput -StepArtifactsDir $runDir -DryRun:$DryRun
    $workerFile = Join-Path $runDir ("iter_{0}_researcher.txt" -f $i)
    Set-Content -Path $workerFile -Value $workerRaw -Encoding UTF8
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "researcher" -Status "artifact_written" -Iteration $i -Message ("Saved output to {0}" -f $workerFile)
    $lastSuccessfulStep = "researcher_iter_$i"
    $workerBlock = Test-BlockedOutput -Text $workerRaw -Patterns $blockerPatterns
    if ($workerBlock.blocked) {
      $blocked = $true
      $blockedReason = "Blocked marker detected in researcher output (pattern='$($workerBlock.pattern)')."
      $residualRisk = $blockedReason
      $state.status = "blocked"
      $state.history += [ordered]@{
        iteration = $i
        worker_file = $workerFile
        reviewer_file = ""
        approved = $false
        quality_score = 0.0
        progress_pct = $progressPct
        next_direction = $state.next_direction
        blocked_reason = $blockedReason
      }
      Save-Json -Obj $state -Path $stateFile
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "researcher" -Status "blocked_short_circuit" -Iteration $i -Message $blockedReason
      throw $blockedReason
    }

    try {
      $workerJson = Parse-FirstJsonObject -Text $workerRaw
      if ($workerJson.PSObject.Properties.Name -contains "summary_for_user") {
        Add-RollingItem -List $rollingRecentSummaries -Item ("Researcher iter_{0}: {1}" -f $i, [string]$workerJson.summary_for_user) -MaxItems 10
      }
      if ($workerJson.PSObject.Properties.Name -contains "next_direction") {
        Add-RollingItem -List $rollingRecentDirections -Item ([string]$workerJson.next_direction) -MaxItems 10
      }
      if ($workerJson.PSObject.Properties.Name -contains "limitations") {
        foreach ($lim in @($workerJson.limitations)) {
          Add-RollingItem -List $rollingOpenQuestions -Item ([string]$lim) -MaxItems 16
        }
      }
      if ($workerJson.PSObject.Properties.Name -contains "evidence_updates") {
        foreach ($ev in @($workerJson.evidence_updates)) {
          Add-RollingItem -List $rollingValidatedEvidence -Item ("candidate: {0}" -f [string]$ev) -MaxItems 20
        }
      }
    } catch {
      Add-RollingItem -List $rollingRecentSummaries -Item ("Researcher iter_{0}: parse fallback summary" -f $i) -MaxItems 10
    }

    if ($effectiveRoleMode -eq "researcher_only") {
      $workerJsonForMode = $null
      $workerJsonParsed = $false
      try {
        $workerJsonForMode = Parse-FirstJsonObject -Text $workerRaw
        $workerJsonParsed = $true
      } catch {
        $workerJsonParsed = $false
      }

      $approvedCandidate = $false
      $qualitySelf = $qualityScore
      $progressClaim = $progressPct
      $summaryForUser = "Researcher-only iteration completed."
      $researcherDirection = $state.next_direction
      $actionType = ""
      $goalLink = ""
      $actionsList = @()
      $commandsExecuted = @()
      $artifactsExpected = @()
      $artifactsObserved = @()
      $evidenceDeltaText = ""
      $limitationsList = @()
      $evidenceUpdatesList = @()
      $filesTouchedList = @()
      $commitMessageHint = ""
      $jsonContractIssues = @()

      if ($workerJsonParsed) {
        if ($workerJsonForMode.PSObject.Properties.Name -contains "approved_candidate") { $approvedCandidate = [bool]$workerJsonForMode.approved_candidate }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "quality_score_self") { $qualitySelf = [double]$workerJsonForMode.quality_score_self }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "progress_pct_claim") { $progressClaim = [math]::Max(0, [math]::Min(100, [int]$workerJsonForMode.progress_pct_claim)) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "summary_for_user") { $summaryForUser = [string]$workerJsonForMode.summary_for_user }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "next_direction") { $researcherDirection = [string]$workerJsonForMode.next_direction }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "action_type") { $actionType = [string]$workerJsonForMode.action_type }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "goal_link") { $goalLink = [string]$workerJsonForMode.goal_link }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "actions") { $actionsList = @($workerJsonForMode.actions) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "commands_executed") { $commandsExecuted = @($workerJsonForMode.commands_executed) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "artifacts_expected") { $artifactsExpected = @($workerJsonForMode.artifacts_expected) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "artifacts_observed") { $artifactsObserved = @($workerJsonForMode.artifacts_observed) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "evidence_delta") { $evidenceDeltaText = [string]$workerJsonForMode.evidence_delta }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "limitations") { $limitationsList = @($workerJsonForMode.limitations) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "evidence_updates") { $evidenceUpdatesList = @($workerJsonForMode.evidence_updates) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "files_touched") { $filesTouchedList = @($workerJsonForMode.files_touched) }
        if ($workerJsonForMode.PSObject.Properties.Name -contains "commit_message") { $commitMessageHint = [string]$workerJsonForMode.commit_message }
        if ($templateStrictJsonContract) {
          $requiredFields = @("summary_for_user","next_direction")
          foreach ($field in $requiredFields) {
            if (-not ($workerJsonForMode.PSObject.Properties.Name -contains $field)) {
              $jsonContractIssues += $field
            }
          }
        }
      } else {
        if ($templateStrictJsonContract) {
          $jsonContractIssues += "json_parse_failed"
        }
      }

      if ($actionsList.Count -gt 0 -and $commandsExecuted.Count -eq 0) {
        $commandsExecuted = @($actionsList)
      }

      $evidenceSnapshotAfter = @{}
      $evidenceDeltaPaths = @()
      if ($effectiveRequireEvidenceDelta) {
        $evidenceSnapshotAfter = Get-EvidenceSnapshot -RepoRoot $resolvedRepoRoot -PathSpecs $templateEvidencePaths
        $evidenceDeltaPaths = Get-EvidenceDeltaPaths -Before $evidenceSnapshotBefore -After $evidenceSnapshotAfter
      }
      $hasEvidenceDelta = ($evidenceDeltaPaths.Count -gt 0)
      if ([string]::IsNullOrWhiteSpace($evidenceDeltaText) -and $hasEvidenceDelta) {
        $evidenceDeltaText = ("Detected {0} changed evidence path(s)." -f $evidenceDeltaPaths.Count)
      }

      $noProgressIteration = $false
      $noProgressReasons = @()
      if ($templateStrictJsonContract -and $jsonContractIssues.Count -gt 0) {
        $noProgressIteration = $true
        $noProgressReasons += ("json_contract_issues={0}" -f ($jsonContractIssues -join ","))
      }
      if ($effectiveRequireEvidenceDelta -and -not $hasEvidenceDelta) {
        $noProgressIteration = $true
        $noProgressReasons += "no_evidence_delta_detected"
      }

      if ($progressClaim -gt $progressPct) { $progressPct = $progressClaim }
      $qualityScore = [math]::Max(0.0, [math]::Min(1.0, $qualitySelf))
      $approved = $approvedCandidate
      $directorApprovedFinal = $false
      $coverage = if ($effectiveRequireEvidenceDelta) { "Researcher-only mode with evidence-delta validation." } else { "Researcher-only mode without evidence-delta requirement." }
      if ($noProgressIteration) {
        $noProgressCount += 1
        $residualRisk = "Researcher-only iteration had no acceptable progress: $($noProgressReasons -join '; ')."
      } else {
        $noProgressCount = 0
        $residualRisk = if ($limitationsList.Count -gt 0) { ($limitationsList -join "; ") } else { "No major residual risk reported by researcher." }
      }
      $state.no_progress_count = $noProgressCount

      if (-not [string]::IsNullOrWhiteSpace($researcherDirection)) {
        $state.next_direction = $researcherDirection
      }
      if ($noProgressIteration -and $effectiveNoProgressPolicy -eq "force_pivot") {
        $state.next_direction = "Pivot strategy: choose a different experiment or analysis path that yields measurable evidence delta toward the ultimate goals."
      }

      foreach ($deltaPath in $evidenceDeltaPaths) {
        $rel = Convert-ToRepoRelativePath -RepoRoot $resolvedRepoRoot -Path $deltaPath
        Add-RollingItem -List $rollingValidatedEvidence -Item ("delta: {0}" -f $rel) -MaxItems 20
      }
      if ($noProgressIteration) {
        Add-RollingItem -List $rollingOpenQuestions -Item ("iter_{0}: no_progress reasons={1}" -f $i, ($noProgressReasons -join "; ")) -MaxItems 16
      }

      $autoCommitResult = $null
      if ($effectiveAutoCommitEnabled) {
        $autoCommitResult = Invoke-IterationAutoCommit `
          -RepoRoot $resolvedRepoRoot `
          -Iteration $i `
          -Summary $summaryForUser `
          -NextDirection $state.next_direction `
          -FilesTouched $filesTouchedList `
          -CommitMessageHint $commitMessageHint `
          -GitStatusBefore $gitStatusBeforeIteration `
          -ExcludePrefixes $templateAutoCommitExcludePaths `
          -AutoPush:$effectiveAutoCommitPush
        if ($autoCommitResult.committed) {
          Add-RollingItem -List $rollingValidatedEvidence -Item ("git_commit: {0}" -f $autoCommitResult.commit_hash) -MaxItems 20
          Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "git_commit" -Status "committed" -Iteration $i -Message ("hash={0}; pushed={1}; paths={2}" -f $autoCommitResult.commit_hash, $autoCommitResult.pushed, (($autoCommitResult.staged_paths -join ", ")))
        } else {
          Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "git_commit" -Status "skipped" -Iteration $i -Message ("reason={0}" -f $autoCommitResult.reason)
        }
      }

      $workerMarkdownFile = Join-Path $runDir ("iter_{0}_researcher.md" -f $i)
      if ($effectiveWriteResearcherIterationMd) {
        $evidenceDeltaLines = if ($evidenceDeltaPaths.Count -gt 0) {
          ($evidenceDeltaPaths | ForEach-Object { "- " + (Convert-ToRepoRelativePath -RepoRoot $resolvedRepoRoot -Path $_) }) -join [Environment]::NewLine
        } else {
          "- (none)"
        }
        $summaryText = if ([string]::IsNullOrWhiteSpace($summaryForUser)) { "(none)" } else { $summaryForUser.Trim() }
        $actionsLines = if ($actionsList.Count -gt 0) { ($actionsList | ForEach-Object { "- " + [string]$_ }) -join [Environment]::NewLine } else { "- (none)" }
        $evidenceUpdatesLines = if ($evidenceUpdatesList.Count -gt 0) { ($evidenceUpdatesList | ForEach-Object { "- " + [string]$_ }) -join [Environment]::NewLine } else { "- (none)" }
        $filesTouchedLines = if ($filesTouchedList.Count -gt 0) { ($filesTouchedList | ForEach-Object { "- " + [string]$_ }) -join [Environment]::NewLine } else { "- (none)" }
        $commandsLines = if ($commandsExecuted.Count -gt 0) { ($commandsExecuted | ForEach-Object { "- $_" }) -join [Environment]::NewLine } else { "- (none)" }
        $limitationsLines = if ($limitationsList.Count -gt 0) { ($limitationsList | ForEach-Object { "- $_" }) -join [Environment]::NewLine } else { "- (none)" }
        $md = @"
# Researcher Iteration $i

- role_mode: researcher_only
- iteration: $iterationLabel
- outcome: $(if ($noProgressIteration) { "no_progress" } else { "progress" })
- action_type: $actionType
- goal_link: $goalLink
- progress_pct_claim: $progressClaim
- quality_score_self: $qualitySelf
- approved_candidate: $approvedCandidate
- evidence_delta_text: $evidenceDeltaText
- evidence_delta_count: $($evidenceDeltaPaths.Count)
- next_direction: $($state.next_direction)
- previous_researcher_file: $previousResearcherFile
- previous_researcher_md_file: $previousResearcherMdFile
- memory_doc_path: $resolvedMemoryPath
- auto_commit_enabled: $effectiveAutoCommitEnabled
- auto_commit_result: $(if ($null -ne $autoCommitResult) { $autoCommitResult.reason } else { "disabled" })
- auto_commit_hash: $(if ($null -ne $autoCommitResult -and $autoCommitResult.committed) { $autoCommitResult.commit_hash } else { "" })

## Summary
$summaryText

## Actions
$actionsLines

## Evidence Updates
$evidenceUpdatesLines

## Files Touched
$filesTouchedLines

## Commands Executed
$commandsLines

## Evidence Delta Files
$evidenceDeltaLines

## Limitations
$limitationsLines

## Raw Output File
- $workerFile
"@
        Set-Content -Path $workerMarkdownFile -Value $md -Encoding UTF8
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "researcher" -Status "markdown_written" -Iteration $i -Message ("Saved markdown summary to {0}" -f $workerMarkdownFile)
      }

      $state.history += [ordered]@{
        iteration = $i
        worker_file = $workerFile
        worker_markdown_file = if ($effectiveWriteResearcherIterationMd) { $workerMarkdownFile } else { "" }
        reviewer_file = ""
        director_file = ""
        approved = $approved
        director_approved_final = $false
        quality_score = $qualityScore
        progress_pct = $progressPct
        context_risk_score = 0.0
        enforce_compression = $false
        next_direction = $state.next_direction
        role_mode = "researcher_only"
        no_progress = $noProgressIteration
        evidence_delta_count = $evidenceDeltaPaths.Count
        files_touched = $filesTouchedList
        commit_hash = if ($null -ne $autoCommitResult -and $autoCommitResult.committed) { [string]$autoCommitResult.commit_hash } else { "" }
        commit_pushed = if ($null -ne $autoCommitResult -and $autoCommitResult.committed) { [bool]$autoCommitResult.pushed } else { $false }
        commit_reason = if ($null -ne $autoCommitResult) { [string]$autoCommitResult.reason } else { "disabled" }
      }
      Save-Json -Obj $state -Path $stateFile

      if ($noProgressIteration) {
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "researcher_only_no_progress" -Iteration $i -Message ("policy={0}; reasons={1}" -f $effectiveNoProgressPolicy, ($noProgressReasons -join "; "))
        if ($effectiveNoProgressPolicy -eq "stop") {
          $state.status = "paused_no_progress"
          Save-Json -Obj $state -Path $stateFile
          $blocked = $true
          $blockedReason = "Researcher-only iteration produced no progress and policy=stop."
          break
        }
      } else {
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "researcher_only_progress" -Iteration $i -Message ("evidence_delta_count={0}" -f $evidenceDeltaPaths.Count)
      }

      $i++
      continue
    }

    $reviewerPrompt = @"
You are EVALUATOR in a research CLI loop.
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Iteration: $iterationLabel
Previous direction: $previousDirection
Rolling context packet (JSON):
$rollingContextJson
Researcher output:
$workerRaw

Return strict JSON only:
{
  "approved": true|false,
  "quality_score": 0.0-1.0,
  "progress_pct": 0-100,
  "summary_for_user": "...",
  "next_direction": "...",
  "coverage": "...",
  "residual_risk": "...",
  "risk_level": "low|medium|high",
  "enforce_compression": true|false,
  "compression_reason": "...",
  "context_risk_score": 0.0-1.0,
  "snapshot_priority": "high|normal"
}
"@
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "evaluator" -Status "dispatch" -Iteration $i -Message "Dispatching evaluator prompt."
    $reviewerRaw = Invoke-CodexExecWithSafety -Prompt $reviewerPrompt -StepName "evaluator" -Iteration $i -Template $template -CodexLaunchSpec $codexLaunchSpec -ExtraExecArgs $nestedExecArgs -HeartbeatFile $heartbeatFile -TraceFile $traceFile -RunId $runId -ShowLiveOutput:$effectiveLiveOutput -StepArtifactsDir $runDir -DryRun:$DryRun
    $reviewerFile = Join-Path $runDir ("iter_{0}_evaluator.txt" -f $i)
    Set-Content -Path $reviewerFile -Value $reviewerRaw -Encoding UTF8
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "evaluator" -Status "artifact_written" -Iteration $i -Message ("Saved output to {0}" -f $reviewerFile)
    $lastSuccessfulStep = "evaluator_iter_$i"
    $reviewerBlock = Test-BlockedOutput -Text $reviewerRaw -Patterns $blockerPatterns
    if ($reviewerBlock.blocked) {
      $blocked = $true
      $blockedReason = "Blocked marker detected in evaluator output (pattern='$($reviewerBlock.pattern)')."
      $residualRisk = $blockedReason
      $state.status = "blocked"
      $state.history += [ordered]@{
        iteration = $i
        worker_file = $workerFile
        reviewer_file = $reviewerFile
        approved = $false
        quality_score = 0.0
        next_direction = $state.next_direction
        blocked_reason = $blockedReason
      }
      Save-Json -Obj $state -Path $stateFile
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "evaluator" -Status "blocked_short_circuit" -Iteration $i -Message $blockedReason
      throw $blockedReason
    }

    $reviewerJson = Parse-FirstJsonObject -Text $reviewerRaw
    $approved = if ($reviewerJson.PSObject.Properties.Name -contains "approved") { [bool]$reviewerJson.approved } else { $false }
    $qualityScore = if ($reviewerJson.PSObject.Properties.Name -contains "quality_score") { [double]$reviewerJson.quality_score } else { 0.0 }
    $summaryForUser = if ($reviewerJson.PSObject.Properties.Name -contains "summary_for_user") { [string]$reviewerJson.summary_for_user } else { "Evaluator summary missing." }
    $evaluatorDirection = if ($reviewerJson.PSObject.Properties.Name -contains "next_direction") { [string]$reviewerJson.next_direction } else { $state.next_direction }
    $coverage = if ($reviewerJson.PSObject.Properties.Name -contains "coverage") { [string]$reviewerJson.coverage } else { $coverage }
    $riskLevel = if ($reviewerJson.PSObject.Properties.Name -contains "risk_level") { [string]$reviewerJson.risk_level } else { "medium" }
    $evaluatorEnforceCompression = if ($reviewerJson.PSObject.Properties.Name -contains "enforce_compression") { [bool]$reviewerJson.enforce_compression } else { $false }
    $evaluatorCompressionReason = if ($reviewerJson.PSObject.Properties.Name -contains "compression_reason") { [string]$reviewerJson.compression_reason } else { "" }
    $evaluatorContextRiskScore = if ($reviewerJson.PSObject.Properties.Name -contains "context_risk_score") { [double]$reviewerJson.context_risk_score } else { -1.0 }
    $snapshotPriority = if ($reviewerJson.PSObject.Properties.Name -contains "snapshot_priority") { [string]$reviewerJson.snapshot_priority } else { "normal" }
    $reportedProgressPct = if ($reviewerJson.PSObject.Properties.Name -contains "progress_pct") { [math]::Max(0, [math]::Min(100, [int]$reviewerJson.progress_pct)) } else { $progressPct }
    if ($reportedProgressPct -gt $progressPct) { $progressPct = $reportedProgressPct }
    if ($reviewerJson.PSObject.Properties.Name -contains "residual_risk") {
      $residualRisk = [string]$reviewerJson.residual_risk
    }
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "evaluator" -Status "parsed" -Iteration $i -Message ("approved={0}; quality_score={1}; progress_pct={2}" -f $approved, $qualityScore, $progressPct)
    $reviewerSummaryBlock = Test-BlockedOutput -Text ($summaryForUser + "`n" + $residualRisk) -Patterns $blockerPatterns
    if ($reviewerSummaryBlock.blocked) {
      $blocked = $true
      $blockedReason = "Blocked marker detected in evaluator summary/risk (pattern='$($reviewerSummaryBlock.pattern)')."
      $residualRisk = $blockedReason
      $state.status = "blocked"
      Save-Json -Obj $state -Path $stateFile
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "evaluator" -Status "blocked_short_circuit" -Iteration $i -Message $blockedReason
      throw $blockedReason
    }
    Add-RollingItem -List $rollingRecentSummaries -Item ("Evaluator iter_{0}: {1}" -f $i, $summaryForUser) -MaxItems 10
    Add-RollingItem -List $rollingRecentDirections -Item $evaluatorDirection -MaxItems 10
    if ($riskLevel -match "(?i)high") {
      Add-RollingItem -List $rollingOpenQuestions -Item ("High risk flagged at iter_{0}: {1}" -f $i, $residualRisk) -MaxItems 16
    }

    if ($qualityScore -gt $bestQualityScore) {
      $bestQualityScore = $qualityScore
      $nonImprovingCount = 0
    } else {
      $nonImprovingCount += 1
    }
    $scoreDropTriggered = $false
    if ($lastQualityScore -ge 0.0) {
      $scoreDropTriggered = (($lastQualityScore - $qualityScore) -ge $scoreDropTrigger)
    }
    $lastQualityScore = $qualityScore

    $rollingContextSizeEstimate = ($rollingContextJson.Length + $workerRaw.Length + $reviewerRaw.Length + $directorNote.Length + $summaryForUser.Length + $residualRisk.Length)
    $sizeTriggered = $contextCompressionEnabled -and ($rollingContextSizeEstimate -ge $compressionPromptChars)
    $compressionStallTriggered = $contextCompressionEnabled -and ($nonImprovingCount -ge $compressionStallIterations)
    $reworkSignal = (($summaryForUser + "`n" + $residualRisk + "`n" + $workerRaw) -match "(?i)\brework\b|\bredo\b|\bre-open\b|\breopen\b|\brevisit\b|\brollback\b|\bundo\b")
    $directionMismatch = (-not [string]::IsNullOrWhiteSpace($previousDirection)) -and (-not [string]::IsNullOrWhiteSpace($evaluatorDirection)) -and ($previousDirection -ne $evaluatorDirection)
    $driftTriggered = $false
    if ($compressionDriftSignal -eq "direction_mismatch_rework") {
      $driftTriggered = ($directionMismatch -and $reworkSignal)
    }
    $compositeCompressionTrigger = $sizeTriggered -or $compressionStallTriggered -or $driftTriggered

    $computedContextRiskScore = 0.0
    if ($sizeTriggered) { $computedContextRiskScore += 0.4 }
    if ($compressionStallTriggered) { $computedContextRiskScore += 0.25 }
    if ($driftTriggered) { $computedContextRiskScore += 0.35 }
    if ($riskLevel -match "(?i)high") { $computedContextRiskScore += 0.2 }
    if ($computedContextRiskScore -gt 1.0) { $computedContextRiskScore = 1.0 }
    $contextRiskScore = if ($evaluatorContextRiskScore -ge 0.0) { [math]::Max(0.0, [math]::Min(1.0, $evaluatorContextRiskScore)) } else { $computedContextRiskScore }
    $enforceCompression = $contextCompressionEnabled -and ($evaluatorEnforceCompression -or $compositeCompressionTrigger)
    $compressionReasonParts = @()
    if ($sizeTriggered) { $compressionReasonParts += ("size>={0}" -f $compressionPromptChars) }
    if ($compressionStallTriggered) { $compressionReasonParts += ("stall>={0}" -f $compressionStallIterations) }
    if ($driftTriggered) { $compressionReasonParts += "drift_signal" }
    if ($evaluatorEnforceCompression) { $compressionReasonParts += "evaluator_enforced" }
    if (-not [string]::IsNullOrWhiteSpace($evaluatorCompressionReason)) { $compressionReasonParts += ("evaluator_reason:{0}" -f $evaluatorCompressionReason) }
    if ($compressionReasonParts.Count -eq 0) { $compressionReasonParts += "none" }
    $compressionReasonText = ($compressionReasonParts -join "; ")

    $pressureRecord = [ordered]@{
      iteration = $i
      context_mode = $contextMode
      prompt_chars_est = $rollingContextSizeEstimate
      prompt_chars_threshold = $compressionPromptChars
      size_triggered = $sizeTriggered
      stall_triggered = $compressionStallTriggered
      drift_triggered = $driftTriggered
      evaluator_enforce_compression = $evaluatorEnforceCompression
      composite_triggered = $compositeCompressionTrigger
      enforce_compression = $enforceCompression
      context_risk_score = $contextRiskScore
      snapshot_priority = $snapshotPriority
      reason = $compressionReasonText
      ts = (Get-Date).ToString("o")
    }
    [void]$contextPressureHistory.Add($pressureRecord)
    while ($contextPressureHistory.Count -gt 40) { $contextPressureHistory.RemoveAt(0) }
    Save-Json -Obj ([ordered]@{ latest = $pressureRecord; history = @($contextPressureHistory.ToArray()) }) -Path $contextPressureFile
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "context_pressure_eval" -Status "computed" -Iteration $i -Message ("chars={0}; score={1}; enforce={2}; reason={3}" -f $rollingContextSizeEstimate, $contextRiskScore, $enforceCompression, $compressionReasonText)

    if ($enforceCompression) {
      $checkpointJson = Join-Path $runDir ("iter_{0}_context_checkpoint.json" -f $i)
      $checkpointMd = Join-Path $runDir ("iter_{0}_context_checkpoint.md" -f $i)
      $snapshotObj = [ordered]@{
        run_id = $runId
        iteration = $i
        goals_state = [ordered]@{
          task = $effectiveTask
          done_criteria = $effectiveDoneCriteria
          progress_pct = $progressPct
          quality_score = $qualityScore
        }
        validated_evidence = @((Get-TailArray -List $rollingValidatedEvidence -MaxItems 10))
        rejected_paths = @((Get-TailArray -List $rollingRejectedPaths -MaxItems 10))
        open_questions = @((Get-TailArray -List $rollingOpenQuestions -MaxItems 12))
        next_direction = $evaluatorDirection
        confidence = [math]::Round([math]::Max(0.0, (1.0 - $contextRiskScore)), 2)
        why_compressed = $compressionReasonText
      }
      Save-Json -Obj $snapshotObj -Path $checkpointJson
      Save-Json -Obj $snapshotObj -Path $contextSnapshotJsonFile
      $snapshotMd = @"
# Context Snapshot (Iteration $i)

- reason: $compressionReasonText
- context_risk_score: $contextRiskScore
- next_direction: $evaluatorDirection
- progress_pct: $progressPct
- quality_score: $qualityScore

## Validated Evidence
$(($snapshotObj.validated_evidence | ForEach-Object { "- $_" }) -join [Environment]::NewLine)

## Rejected Paths
$(($snapshotObj.rejected_paths | ForEach-Object { "- $_" }) -join [Environment]::NewLine)

## Open Questions
$(($snapshotObj.open_questions | ForEach-Object { "- $_" }) -join [Environment]::NewLine)
"@
      Set-Content -Path $checkpointMd -Value $snapshotMd -Encoding UTF8
      Set-Content -Path $contextSnapshotMdFile -Value $snapshotMd -Encoding UTF8

      $state.last_compression_iteration = $i
      $state.compression_count = [int]$state.compression_count + 1
      $state.active_snapshot_file = $contextSnapshotJsonFile
      $state.active_snapshot_markdown_file = $contextSnapshotMdFile
      $state.latest_context_checkpoint_json = $checkpointJson
      $state.latest_context_checkpoint_markdown = $checkpointMd
      $state.rolling_context_bytes_est = $rollingContextSizeEstimate
      $state.context_risk_score = $contextRiskScore
      Save-Json -Obj $state -Path $stateFile
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "compression_enforced" -Status "snapshot_written" -Iteration $i -Message ("json={0}; md={1}" -f $checkpointJson, $checkpointMd)

      $rollingRecentSummaries.Clear()
      $rollingRecentDirections.Clear()
      Add-RollingItem -List $rollingRecentSummaries -Item ("Compression checkpoint iter_{0}: {1}" -f $i, $compressionReasonText) -MaxItems 10
      Add-RollingItem -List $rollingRecentDirections -Item $evaluatorDirection -MaxItems 10
    } else {
      $state.rolling_context_bytes_est = $rollingContextSizeEstimate
      $state.context_risk_score = $contextRiskScore
      Save-Json -Obj $state -Path $stateFile
    }

    $milestonesCrossedNow = @()
    foreach ($m in $milestones) {
      if ($progressPct -ge $m -and -not $milestoneHit.ContainsKey($m)) {
        $milestoneHit[$m] = $true
        $state.milestone_hits += [string]$m
        $milestonesCrossedNow += [string]$m
      }
    }
    $quality090Triggered = $false
    if (-not $majorQualityMilestoneHit -and $qualityScore -ge $qualityMajorMilestone) {
      $majorQualityMilestoneHit = $true
      $quality090Triggered = $true
      $state.milestone_hits += "quality_090"
    }
    $riskHighTriggered = ($riskLevel -match "(?i)high")
    $sourceConflictTriggered = (($summaryForUser + "`n" + $residualRisk) -match "(?i)source conflict|conflicting evidence|contradictory sources")
    $stallTriggered = ($nonImprovingCount -ge $stallWindow)
    if ($sourceConflictTriggered) {
      Add-RollingItem -List $rollingRejectedPaths -Item ("iter_{0}: source conflict path rejected" -f $i) -MaxItems 12
    }
    if ($directionMismatch -and $reworkSignal) {
      Add-RollingItem -List $rollingRejectedPaths -Item ("iter_{0}: direction mismatch and rework signal" -f $i) -MaxItems 12
    }
    $spikeTriggered = ($scoreDropTriggered -or $riskHighTriggered -or $sourceConflictTriggered)
    if ($spikeTriggered -and $burstRemaining -le 0) {
      $burstRemaining = $burstIterations
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_burst" -Status "start" -Iteration $i -Message "Adaptive burst started due to risk spike."
    }
    $directorMode = if (($milestonesCrossedNow.Count -gt 0) -or $quality090Triggered -or $stallTriggered -or ($burstRemaining -gt 0)) { "full" } else { "light" }

    $directorPrompt = @"
You are DIRECTOR in a research CLI loop.
Mode: $directorMode
Ultimate goals: $effectiveTask
Done criteria: $effectiveDoneCriteria
Iteration: $iterationLabel
Quality score: $qualityScore
Progress pct: $progressPct
Evaluator risk level: $riskLevel
Evaluator summary: $summaryForUser
Evaluator direction: $evaluatorDirection
Residual risk: $residualRisk
Rolling context packet (JSON):
$rollingContextJson
Context pressure:
- estimated_chars: $rollingContextSizeEstimate
- context_risk_score: $contextRiskScore
- compression_enabled: $contextCompressionEnabled
- compression_decision_this_iteration: $enforceCompression
- compression_reason: $compressionReasonText
Goals doc: $PrdPath
Plan doc: $DevDocPath
Findings doc: $FindingsPath

Post-iteration note only. Keep compact and actionable.
Return strict JSON only:
{
  "mode": "light|full",
  "note_for_researcher": "...",
  "researcher_direction": "...",
  "approved_final": true|false,
  "plan_change_summary": "..."
}
"@
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_post" -Status "dispatch" -Iteration $i -Message ("Dispatching director post note mode={0}" -f $directorMode)
    $directorRaw = Invoke-CodexExecWithSafety -Prompt $directorPrompt -StepName ("director_post_" + $directorMode) -Iteration $i -Template $template -CodexLaunchSpec $codexLaunchSpec -ExtraExecArgs $nestedExecArgs -HeartbeatFile $heartbeatFile -TraceFile $traceFile -RunId $runId -ShowLiveOutput:$effectiveLiveOutput -StepArtifactsDir $runDir -DryRun:$DryRun
    $directorFile = Join-Path $runDir ("iter_{0}_director_{1}.txt" -f $i, $directorMode)
    Set-Content -Path $directorFile -Value $directorRaw -Encoding UTF8
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "director_post" -Status "artifact_written" -Iteration $i -Message ("Saved output to {0}" -f $directorFile)
    $lastSuccessfulStep = "director_post_iter_$i"

    $directorDirection = ""
    try {
      $directorJson = Parse-FirstJsonObject -Text $directorRaw
      if ($directorJson.PSObject.Properties.Name -contains "note_for_researcher") { $directorNote = [string]$directorJson.note_for_researcher }
      if ($directorJson.PSObject.Properties.Name -contains "researcher_direction") { $directorDirection = [string]$directorJson.researcher_direction }
      if ($directorJson.PSObject.Properties.Name -contains "approved_final") { $directorApprovedFinal = [bool]$directorJson.approved_final }
    } catch {
      $directorNote = "Director parse fallback: keep evaluator direction and close evidence gaps."
    }

    if (-not [string]::IsNullOrWhiteSpace($evaluatorDirection)) {
      if (-not [string]::IsNullOrWhiteSpace($directorDirection) -and $directorDirection -ne $evaluatorDirection) {
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "direction_resolution" -Status "evaluator_tie_break" -Iteration $i -Message "Evaluator direction selected over director direction."
      }
      $state.next_direction = $evaluatorDirection
    } elseif (-not [string]::IsNullOrWhiteSpace($directorDirection)) {
      $state.next_direction = $directorDirection
    }

    if (($directorMode -eq "full") -and $burstRemaining -gt 0) {
      $burstRemaining -= 1
    }

    $state.history += [ordered]@{
      iteration = $i
      worker_file = $workerFile
      reviewer_file = $reviewerFile
      director_file = $directorFile
      approved = $approved
      director_approved_final = $directorApprovedFinal
      quality_score = $qualityScore
      progress_pct = $progressPct
      context_risk_score = $contextRiskScore
      enforce_compression = $enforceCompression
      next_direction = $state.next_direction
    }
    Save-Json -Obj $state -Path $stateFile

    $iterationGatePass = ($directorApprovedFinal -and $qualityScore -ge $qualityFinalGate)
    if ($requireEvaluatorApprovedForStop) {
      $iterationGatePass = ($iterationGatePass -and $approved)
    }
    if ($iterationGatePass) {
      $approvalStreak += 1
    } else {
      $approvalStreak = 0
    }

    $stopGateMet = ($iterationGatePass -and $i -ge $minIterationsBeforeApprovalStop -and $approvalStreak -ge $approvalStreakRequired)
    $state.approval_streak = $approvalStreak
    $state.process_approval_satisfied = $stopGateMet
    Save-Json -Obj $state -Path $stateFile

    if ($stopGateMet) {
      $processApprovalSatisfied = $true
      if ($effectiveContinueAfterApproval) {
        $state.status = "approved_continuing"
        Save-Json -Obj $state -Path $stateFile
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "approval_reached_continue_mode" -Iteration $i -Message ("Process gate satisfied (q>={0}, streak>={1}, min_iter>={2}); continuing due to continue_after_approval mode." -f $qualityFinalGate, $approvalStreakRequired, $minIterationsBeforeApprovalStop)
      } else {
        $state.status = "approved"
        Save-Json -Obj $state -Path $stateFile
        Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "early_stop_approved_process_gate" -Iteration $i -Message ("Process gate satisfied (q>={0}, streak>={1}, min_iter>={2})." -f $qualityFinalGate, $approvalStreakRequired, $minIterationsBeforeApprovalStop)
        break
      }
    } elseif ($iterationGatePass) {
      Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "iteration" -Status "approval_round_not_enough_process_evidence" -Iteration $i -Message ("Current round met quality gate, but process gate not met yet (streak={0}/{1}, iter={2}/{3})." -f $approvalStreak, $approvalStreakRequired, $i, $minIterationsBeforeApprovalStop)
    }
    $i++
  }

  if ($blocked) {
    $state.status = "blocked"
  } elseif ($processApprovalSatisfied) {
    if ($effectiveContinueAfterApproval) {
      $state.status = "approved_continuing"
    } else {
      $state.status = "approved"
    }
  } elseif (-not $processApprovalSatisfied -and $effectiveMaxIterations -gt 0) {
    $state.status = "max_iterations_reached"
    $residualRisk = "Iteration cap reached before approval."
  } elseif (-not $processApprovalSatisfied) {
    $state.status = "in_progress_not_approved"
  }

  $state.ended_at = (Get-Date).ToString("s")
  Save-Json -Obj $state -Path $stateFile

  $validationResult = if ($processApprovalSatisfied) {
    "PASS"
  } elseif ($blocked) {
    "FAIL_BLOCKED"
  } elseif ($effectiveRoleMode -eq "researcher_only" -and $effectiveMaxIterations -gt 0 -and $state.current_iteration -ge $effectiveMaxIterations) {
    "PASS"
  } else {
    "PARTIAL"
  }
  $executionModeSummary = if ($effectiveRoleMode -eq "researcher_only") { "Researcher-only" } else { "Director + Researcher + Evaluator" }
  $iterationFlowCoverage = if ($effectiveRoleMode -eq "researcher_only") {
    "bootstrap merge, per-iteration memory/context recovery, previous-iteration review handoff, researcher execution, researcher-only progress/no-progress decisions, per-iteration JSON artifacts, and per-iteration researcher markdown summaries."
  } else {
    "bootstrap merge, director preflight, researcher execution, evaluator scoring, evaluator-driven context pressure checks, adaptive compression checkpoints (JSON+Markdown), director post notes, adaptive burst, 25/50/75/100 progress milestones, 0.90 quality milestone, and step-level execution tracing."
  }
  $report = @"
# Research Native Loop Final Report

- run_id: $runId
- status: $($state.status)
- risk_tier: $effectiveRiskTier
- role_mode: $effectiveRoleMode
- execution_flow: $executionModeSummary
- auto_commit_each_iteration: $effectiveAutoCommitEnabled
- auto_push_each_commit: $effectiveAutoCommitPush
- max_iterations: $maxIterationsLabel
- completed_iterations: $($state.current_iteration)
- approved: $approved
- director_approved_final: $directorApprovedFinal
- quality_score: $qualityScore
- progress_pct: $progressPct
- process_approval_satisfied: $processApprovalSatisfied
- approval_streak: $approvalStreak / required $approvalStreakRequired
- min_iterations_before_approval_stop: $minIterationsBeforeApprovalStop
- no_progress_count: $($state.no_progress_count)

## Executive Summary
$summaryForUser

## Technical Summary
- Source policy: $sourcePolicy
- Goals doc: $PrdPath
- Plan doc: $DevDocPath
- Findings doc: $FindingsPath
- Coverage: $coverage
- Context mode: $contextMode
- Compression enabled: $contextCompressionEnabled
- Compression count: $($state.compression_count)
- Last compression iteration: $($state.last_compression_iteration)

## Validation Actions and Results
- Loaded and validated template v$($template.version): PASS
- Enforced runtime safety (heartbeat/retry/no_silent_stop/lock): PASS
- Wrote step-level trace stream to ${traceFile}: PASS
- Auto merge bootstrap with baseline artifacts: PASS
- Iterative execution (`$effectiveRoleMode`): $validationResult

## Coverage
- Covered: $iterationFlowCoverage
- Not covered: external domain-expert verification beyond repository/runtime evidence.

## Residual Risk
$residualRisk
"@
  Set-Content -Path $finalReportFile -Value $report -Encoding UTF8
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "run" -Status "final_report_written" -Message ("Saved final report to {0}" -f $finalReportFile)
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "run" -Status "end" -Message ("status={0}; approved={1}; quality_score={2}" -f $state.status, $approved, $qualityScore)
  Write-Host "Run completed. Final report: $finalReportFile"
}
catch {
  $err = $_.Exception.Message
  Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "run" -Status "error" -Iteration $state.current_iteration -Message $err
  if ([bool]$template.runtime_safety.pause_requires_blocker) {
    Write-BlockerReport -BlockerFile $blockerFile -Reason $err -LastStep $lastSuccessfulStep -NextActionCommand ("powershell -ExecutionPolicy Bypass -File .\Research_Template\scripts\Research_native_loop.ps1 -TemplatePath ""{0}"" -Task ""{1}"" -DoneCriteria ""{2}""" -f $TemplatePath, $effectiveTask, $effectiveDoneCriteria)
    Write-TraceEvent -TraceFile $traceFile -RunId $runId -Step "run" -Status "blocker_report_written" -Iteration $state.current_iteration -Message ("Saved blocker report to {0}" -f $blockerFile)
  }
  throw
}
finally {
  Release-RunLock -LockFile $lockFile -RunId $runId
  Pop-Location
}
