param(
    [Parameter(Mandatory = $true)][string]$OutputDirectory,
    [string]$ExpectedTailscaleIPv4,
    [string]$ReturnToTailscaleIPv4,
    [string[]]$RepositoryRoots = @('C:\github', 'C:\dev', 'D:\github', 'D:\dev', 'D:\skymiku'),
    [string[]]$DataDirectories = @()
)
$ErrorActionPreference = 'Stop'
$errorsFound = [Collections.Generic.List[string]]::new()
$output = [IO.Path]::GetFullPath($OutputDirectory)
$ancestor = [IO.DirectoryInfo]::new($output)
while ($null -ne $ancestor) {
    if (Test-Path -LiteralPath (Join-Path $ancestor.FullName '.git')) {
        throw 'The private receiver report must be outside every Git checkout.'
    }
    $ancestor = $ancestor.Parent
}
foreach ($address in @($ExpectedTailscaleIPv4, $ReturnToTailscaleIPv4)) {
    if ($address -and $address -notmatch '^100\.(6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])\.(25[0-5]|2[0-4][0-9]|1?[0-9]?[0-9])$') {
        throw 'Use a Tailscale IPv4 address from 100.64.0.0/10.'
    }
}
$tail = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tail) {
    $installedTail = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'
    if (Test-Path -LiteralPath $installedTail -PathType Leaf) {
        $tail = Get-Command $installedTail -ErrorAction SilentlyContinue
    }
}
$tailState = $null
if ($tail) {
    try { $tailState = (& $tail.Source status --json 2>$null | Out-String | ConvertFrom-Json) }
    catch { $errorsFound.Add('Could not read Tailscale state.') }
}
if ($ExpectedTailscaleIPv4 -and ($null -eq $tailState -or $tailState.Self.TailscaleIPs -notcontains $ExpectedTailscaleIPv4)) {
    throw 'This is not the selected receiver. Run this check on the home computer.'
}

$processes = @()
try {
    $processes = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^(python[^.]*|uv)\.exe$' -and $_.CommandLine -match 'ssr_knowledge|ssr-knowledge'
    } | ForEach-Object {
        $data = $null
        $port = $null
        if ($_.CommandLine -match '--data-dir\s+(?:"([^"]+)"|([^\s]+))') {
            $data = if ($Matches[1]) { $Matches[1] } else { $Matches[2] }
        }
        if ($_.CommandLine -match '--port\s+(\d+)') { $port = [int]$Matches[1] }
        [pscustomobject]@{ pid = $_.ProcessId; name = $_.Name; executable = $_.ExecutablePath; data_directory = $data; port = $port }
    })
} catch { $errorsFound.Add('Could not read all knowledge processes: ' + $_.Exception.Message) }

$git = Get-Command git -ErrorAction SilentlyContinue
$repos = @()
foreach ($root in $RepositoryRoots) {
    foreach ($name in @('ssr-knowledge', 'ssr-collector-peak')) {
        $repo = [IO.Path]::Combine($root, $name)
        if (-not (Test-Path -LiteralPath $repo -PathType Container)) { continue }
        $commit = $null
        $branch = $null
        $changes = @()
        if ($git -and (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
            try {
                $commit = & $git.Source --no-optional-locks -C $repo rev-parse HEAD 2>$null
                if ($LASTEXITCODE -ne 0) { throw 'Git revision unavailable.' }
                $branch = & $git.Source --no-optional-locks -C $repo branch --show-current 2>$null
                if ($LASTEXITCODE -ne 0) { throw 'Git branch unavailable.' }
                $changes = @(& $git.Source --no-optional-locks -C $repo status --porcelain 2>$null | Select-Object -First 100)
                if ($LASTEXITCODE -ne 0) { throw 'Git status unavailable.' }
            } catch { $errorsFound.Add('Could not inspect repository: ' + $repo) }
        }
        $repos += [pscustomobject]@{ path = $repo; commit = $commit; branch = $branch; changed_paths = $changes }
    }
}

$candidates = @($DataDirectories)
$candidates += @($processes | Where-Object data_directory | ForEach-Object data_directory)
if ($env:SSR_KNOWLEDGE_DATA_DIR) { $candidates += $env:SSR_KNOWLEDGE_DATA_DIR }
$candidates += @(
    (Join-Path $env:LOCALAPPDATA 'SSRKnowledge\data'),
    (Join-Path $env:USERPROFILE 'Documents\SSRKnowledgeData'),
    'C:\SSRKnowledgeData', 'D:\SSRKnowledgeData', 'C:\data\SSRKnowledge', 'D:\data\SSRKnowledge'
)
$databases = @()
foreach ($candidate in @($candidates | Where-Object { $_ -and [IO.Path]::IsPathRooted($_) } | Select-Object -Unique)) {
    $path = [IO.Path]::Combine($candidate, 'knowledge.sqlite3')
    if (Test-Path -LiteralPath $path -PathType Leaf) {
        $item = Get-Item -LiteralPath $path
        $databases += [pscustomobject]@{ path = $item.FullName; bytes = $item.Length; last_write_utc = $item.LastWriteTimeUtc.ToString('o') }
    }
}

$services = @(Get-Service -Name Tailscale, sshd -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{ name = $_.Name; status = [string]$_.Status; start_type = [string]$_.StartType }
})
$listeners = @()
try {
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {
        $_.LocalPort -in @(22,445,5985,5986,8765,8766,8767) -or $_.OwningProcess -in @($processes.pid)
    } | Select-Object LocalAddress,LocalPort,OwningProcess)
} catch { $errorsFound.Add('Could not read listeners: ' + $_.Exception.Message) }
$reviews = @()
foreach ($port in @($processes | Where-Object port | ForEach-Object port | Select-Object -Unique)) {
    try {
        $state = Invoke-RestMethod -Uri ('http://127.0.0.1:' + $port + '/api/review') -TimeoutSec 3
        if ($state.metadata.database -and $state.metadata.counts) {
            $reviews += [pscustomobject]@{ port = $port; metadata = $state.metadata }
        }
    } catch { $errorsFound.Add('Knowledge review API unavailable on port ' + $port) }
}

New-Item -ItemType Directory -Path $output -Force | Out-Null
$report = Join-Path $output ('PEAK-Receiver-' + $env:COMPUTERNAME + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0,8) + '.json')
$result = [ordered]@{
    format = 'ssr.receiver-inspection.v1'
    captured_at = [DateTimeOffset]::Now.ToString('o')
    computer_name = $env:COMPUTERNAME
    windows_user = $env:USERNAME
    tailscale = @{ backend_state = $tailState.BackendState; addresses = @($tailState.Self.TailscaleIPs) }
    services = $services
    knowledge_processes = $processes
    listeners = $listeners
    repositories = $repos
    database_candidates = $databases
    live_reviews = $reviews
    errors = @($errorsFound.ToArray())
    database_modified = $false
    services_modified = $false
    note = 'Read-only inspection. No DB import, environment install, credentials, raw knowledge text, or service changes.'
}
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $report -Encoding UTF8
Write-Output ('Report: ' + $report)
Write-Output ('Computer: ' + $env:COMPUTERNAME + '; DB candidates: ' + $databases.Count + '; live reviews: ' + $reviews.Count)
if ($ReturnToTailscaleIPv4) {
    if (-not $tail -or $tailState.BackendState -ne 'Running') { throw ('Tailscale is not connected. Report preserved at ' + $report) }
    & $tail.Source file cp --update-interval=0 $report ($ReturnToTailscaleIPv4 + ':')
    if ($LASTEXITCODE -ne 0) { throw ('Report transfer failed. File preserved at ' + $report) }
    Write-Output 'Report sent to the specified manager computer through Tailscale.'
}
