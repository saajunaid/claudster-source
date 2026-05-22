<#
.SYNOPSIS
    CI-mode golden-nugget capture for release workflows.

.DESCRIPTION
    Collects conventional-commit subjects from the release range and writes
    candidate nugget blocks to `.github\agent-docs\nuggets-inbox.md` only.
    This script must never write live instruction files, runbooks, or the hub.

.PARAMETER Version
    The release version being captured, e.g. v2026.05.21.1.

.PARAMETER RepoRoot
    Project repo root. Defaults to the current location.

.PARAMETER InboxPath
    Optional override for the inbox path. Defaults to
    <RepoRoot>\.github\agent-docs\nuggets-inbox.md.

.PARAMETER MaxPending
    Maximum number of pending candidates allowed in the inbox before capture
    stops. Defaults to 15.
#>
param(
    [Parameter(Mandatory)]
    [string]$Version,

    [string]$RepoRoot = (Get-Location).Path,

    [string]$InboxPath = '',

    [int]$MaxPending = 15
)

$ErrorActionPreference = 'Stop'
Set-Location $RepoRoot

if ([string]::IsNullOrWhiteSpace($InboxPath)) {
    $InboxPath = Join-Path $RepoRoot '.github\agent-docs\nuggets-inbox.md'
}

$CaptureTypes = @('feat', 'fix', 'perf', 'refactor')
$TagPattern = '^v\d{4}\.\d{2}\.\d{2}\.\d+$'

function Get-NormalizedSubject {
    param([string]$Subject)

    $normalized = $Subject.Trim().ToLowerInvariant()
    $normalized = [regex]::Replace($normalized, '\s+', ' ')
    return $normalized
}

function Get-Fingerprint {
    param([string]$Text)

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($bytes)
    }
    finally {
        $sha.Dispose()
    }
    return ([System.BitConverter]::ToString($hash)).Replace('-', '').ToLowerInvariant().Substring(0, 16)
}

function Get-ExistingFingerprints {
    param([string]$Content)

    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    if ([string]::IsNullOrWhiteSpace($Content)) {
        return ,$seen
    }

    foreach ($match in [regex]::Matches($Content, '(?im)^\s*-\s*fingerprint:\s*(.+?)\s*$')) {
        [void]$seen.Add($match.Groups[1].Value.Trim())
    }
    foreach ($match in [regex]::Matches($Content, '(?im)^\s*-\s*raw:\s*(.+?)\s*$')) {
        $raw = $match.Groups[1].Value.Trim()
        if (-not [string]::IsNullOrWhiteSpace($raw)) {
            [void]$seen.Add((Get-Fingerprint (Get-NormalizedSubject $raw)))
        }
    }
    return ,$seen
}

function Get-PendingCount {
    param([string]$Content)

    if ([string]::IsNullOrWhiteSpace($Content)) {
        return 0
    }
    return ([regex]::Matches($Content, '(?im)^\s*-\s*status:\s*pending\s*$')).Count
}

function Get-Header {
    return @"
# Nugget Inbox

> Auto-captured candidates from CI on prod deploy. These are raw candidates,
> not live instruction updates. Run `junai pool nuggets review` to triage
> keep-local, promote-to-pool, or discard decisions.

"@
}

function Split-Inbox {
    param([string]$Content)

    if ([string]::IsNullOrWhiteSpace($Content) -or -not $Content.StartsWith('# Nugget Inbox')) {
        return @{
            Header = (Get-Header)
            Body = $Content
        }
    }

    $marker = "## CANDIDATE "
    $index = $Content.IndexOf($marker, [System.StringComparison]::Ordinal)
    if ($index -lt 0) {
        return @{
            Header = $Content.TrimEnd() + "`r`n`r`n"
            Body = ''
        }
    }

    return @{
        Header = $Content.Substring(0, $index)
        Body = $Content.Substring($index)
    }
}

$prevTag = git tag --sort=-version:refname 2>$null |
    Where-Object { $_ -match $TagPattern -and $_ -ne $Version } |
    Select-Object -First 1

if ($prevTag) {
    Write-Host "  [extract-nuggets] Range $prevTag..HEAD" -ForegroundColor Cyan
    $commitLines = @(git log "$prevTag..HEAD" --no-merges "--pretty=format:%h%x1f%s" 2>$null)
}
else {
    Write-Host "  [extract-nuggets] No previous tag - using full history." -ForegroundColor Cyan
    $commitLines = @(git log HEAD --no-merges "--pretty=format:%h%x1f%s" 2>$null)
}

if (-not $commitLines -or $commitLines.Count -eq 0) {
    Write-Host "  [extract-nuggets] No commits in range. Nothing to capture."
    exit 0
}

$grouped = @{}
foreach ($line in $commitLines) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }

    $separatorIndex = $line.IndexOf([char]0x1f)
    if ($separatorIndex -lt 0) {
        continue
    }

    $sha7 = $line.Substring(0, $separatorIndex).Trim()
    $subject = $line.Substring($separatorIndex + 1).Trim()
    if ($subject -notmatch '^(?<type>\w+)(\([^)]*\))?!?:\s*(?<desc>.+)$') {
        continue
    }

    $type = $Matches['type'].ToLowerInvariant()
    if ($CaptureTypes -notcontains $type) {
        continue
    }

    $normalized = Get-NormalizedSubject $subject
    $fingerprint = Get-Fingerprint $normalized
    if (-not $grouped.ContainsKey($fingerprint)) {
        $shape = if ($type -in @('perf', 'refactor')) { 'rule-shaped' } else { 'project-local' }
        $suggestedRoute = if ($shape -eq 'rule-shaped') { 'promote-to-pool' } else { 'keep-local' }
        $grouped[$fingerprint] = [pscustomobject]@{
            Fingerprint = $fingerprint
            Shape = $shape
            SuggestedRoute = $suggestedRoute
            Raw = $subject
            Type = $type
            Commits = [System.Collections.Generic.List[string]]::new()
        }
    }
    $grouped[$fingerprint].Commits.Add($sha7)
}

if ($grouped.Count -eq 0) {
    Write-Host "  [extract-nuggets] No feat/fix/perf/refactor commits in range. Nothing to capture."
    exit 0
}

$existingContent = ''
if (Test-Path $InboxPath) {
    $existingContent = Get-Content -Path $InboxPath -Raw -Encoding utf8
}

$pendingCount = Get-PendingCount $existingContent
if ($pendingCount -ge $MaxPending) {
    Write-Host "  [extract-nuggets] Inbox full ($pendingCount pending >= $MaxPending). Review pending - appending nothing." -ForegroundColor Yellow
    exit 0
}

$seenFingerprints = Get-ExistingFingerprints $existingContent
$today = (Get-Date).ToString('yyyy-MM-dd')
$builder = [System.Text.StringBuilder]::new()
$appended = 0

foreach ($candidate in @($grouped.Values) | Sort-Object Raw) {
    if (($pendingCount + $appended) -ge $MaxPending) {
        Write-Host "  [extract-nuggets] Hit cap mid-append; stopping." -ForegroundColor Yellow
        break
    }
    if ($seenFingerprints.Contains($candidate.Fingerprint)) {
        continue
    }

    [void]$seenFingerprints.Add($candidate.Fingerprint)
    $commitList = ($candidate.Commits | Sort-Object -Unique) -join ', '
    $rawDescription = $candidate.Raw
    if ($candidate.Raw -match '^\w+(\([^)]*\))?!?:\s*(?<desc>.+)$') {
        $rawDescription = $Matches['desc'].Trim()
    }
    $nugget = "$($candidate.Type): $rawDescription"

    [void]$builder.AppendLine("## CANDIDATE $today - $Version")
    [void]$builder.AppendLine("- fingerprint: $($candidate.Fingerprint)")
    [void]$builder.AppendLine("- source: ci-release-capture")
    [void]$builder.AppendLine("- shape: $($candidate.Shape)")
    [void]$builder.AppendLine("- category: (unrouted - set at review)")
    [void]$builder.AppendLine("- suggested-route: $($candidate.SuggestedRoute)")
    [void]$builder.AppendLine("- proposed-target: (unrouted - set at review)")
    [void]$builder.AppendLine("- from-commits: $commitList")
    [void]$builder.AppendLine("- raw: $($candidate.Raw)")
    [void]$builder.AppendLine("- nugget: $nugget")
    [void]$builder.AppendLine("- status: pending")
    [void]$builder.AppendLine("")
    $appended++
}

if ($appended -eq 0) {
    Write-Host "  [extract-nuggets] All candidates already present (dedup). Nothing appended."
    exit 0
}

$inboxDir = Split-Path -Parent $InboxPath
if (-not (Test-Path $inboxDir)) {
    New-Item -ItemType Directory -Path $inboxDir -Force | Out-Null
}

$split = Split-Inbox $existingContent
$newContent = $split.Header + $builder.ToString() + $split.Body
Set-Content -Path $InboxPath -Value $newContent -Encoding utf8

Write-Host "  [extract-nuggets] Appended $appended candidate(s) to $InboxPath" -ForegroundColor Green
exit 0
