<# Datadog Agent v5 runbook (PowerShell 3+)
   - Auto-detects v5 cert path (handles <=5.11 vs >=5.12, 32/64-bit)
   - Forces TLS 1.2, downloads cert, updates use_curl_http_client: true (deduped)
   - Restarts Agent, checks logs only since this restart
#>

# ------------------------------ Helpers ------------------------------
function Error-Exit {
  param([string]$Message)
  Write-Error $Message
  Write-Host "Please contact support for further help."
  exit 1
}

function Assert-Admin {
  try {
    $p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
      Error-Exit "Error: This script must be run as Administrator."
    }
  } catch {
    Write-Warning "Could not verify elevation; continuing. If steps fail, re-run elevated."
  }
}

# -------------------------- Path discovery --------------------------
function Get-DdV5-CertPath {
  $is64 = [Environment]::Is64BitOperatingSystem
  if ($is64) {
    if (Test-Path "C:\Program Files\Datadog\Datadog Agent\agent") {
      return "C:\Program Files\Datadog\Datadog Agent\agent\datadog-cert.pem"   # >=5.12
    } else {
      return "C:\Program Files (x86)\Datadog\Datadog Agent\files\datadog-cert.pem" # <=5.11
    }
  } else {
    return "C:\Program Files\Datadog\Datadog Agent\files\datadog-cert.pem"        # <=5.11 32-bit
  }
}

function Get-DdV5-ServiceNames { @("DatadogAgent", "datadogagent") }
function Get-DdV5-ConfigFile { "C:\ProgramData\Datadog\datadog.conf" }

function Get-DdV5-LogFiles {
  $base = 'C:\ProgramData\Datadog\logs'
  $candidates = @("$base\forwarder.log", "$base\collector.log", "$base\agent.log")
  $existing = @()
  foreach ($p in $candidates) { if (Test-Path -LiteralPath $p) { $existing += $p } }
  if (@($existing).Count -gt 0) { return $existing } else { return $candidates }
}

# --------------------------- Core actions ---------------------------
function Ensure-Directory {
  param([string]$Dir)
  if (-not (Test-Path -LiteralPath $Dir)) {
    Write-Host "Directory $Dir does not exist. Creating it..."
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null
  }
}

function Enable-Tls12 {
  try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch { }
}

function Download-Certificate {
  param([string]$Url, [string]$TargetFile)
  Write-Host "Downloading the DataDog certificate..."
  Enable-Tls12
  try {
    Invoke-WebRequest -Uri $Url -OutFile $TargetFile -UseBasicParsing -ErrorAction Stop
  } catch {
    Write-Warning "Invoke-WebRequest failed: $($_.Exception.Message). Trying BITS..."
    try { Start-BitsTransfer -Source $Url -Destination $TargetFile -ErrorAction Stop }
    catch { Error-Exit "Error: Failed to download certificate with built-in methods." }
  }
  if (-not (Test-Path -LiteralPath $TargetFile)) { Error-Exit "Error: Download reported success but file not found at $TargetFile." }
  Write-Host "Certificate downloaded successfully to $TargetFile."
}

function Update-DatadogConfig {
  param([string]$ConfFile)
  if (-not (Test-Path -LiteralPath $ConfFile)) { Error-Exit "Error: Configuration file $ConfFile not found." }
  Write-Host "Updating $ConfFile for use_curl_http_client (dedupe & force true)..."

  # Backup
  $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
  $backup = "$ConfFile.bak-$stamp"
  try { Copy-Item -LiteralPath $ConfFile -Destination $backup -Force } catch { Write-Warning "Backup failed: $($_.Exception.Message)" }

  # Read & normalize: remove ALL occurrences (even commented/with '=') then append exactly one true line
  $raw = Get-Content -LiteralPath $ConfFile -Raw
  $lines = $raw -split "`r?`n"
  $filtered = @()
  foreach ($line in $lines) {
    if ($line -match '^\s*#?\s*use_curl_http_client\s*[:=].*$') {
      continue
    }
    $filtered += $line
  }
  $filtered += 'use_curl_http_client: true'
  $updated = (($filtered -join "`r`n") + "`r`n")

  try { $updated | Set-Content -LiteralPath $ConfFile -Encoding ASCII }
  catch { Error-Exit "Error: Failed to update $ConfFile. $($_.Exception.Message)" }

  Write-Host "Configuration file updated successfully. Backup saved to $backup"
}

function Restart-Agent {
  param([string[]]$ServiceNames, [int]$WaitSeconds = 30)
  Write-Host "Restarting the Datadog Agent..."
  $restarted = $false
  foreach ($name in $ServiceNames) {
    try {
      $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
      if ($svc) {
        Restart-Service -Name $name -Force -ErrorAction Stop
        $restarted = $true
        break
      }
    } catch {
      Write-Warning "Failed to restart service '$name': $($_.Exception.Message)"
    }
  }
  if (-not $restarted) { Error-Exit "Error: Failed to restart the Datadog Agent (service not found or restart failed)." }
  Write-Host "Waiting $WaitSeconds seconds for the Datadog Agent to restart..."
  Start-Sleep -Seconds $WaitSeconds
}

# --- Byte-slicing support (safe string interpolation with $($var)) ---
function Read-NewBytesSince {
  param([string]$Path, [long]$PreLen)
  if (-not (Test-Path -LiteralPath $Path)) { return "" }
  try {
    if ($PreLen -lt 0) {
      return (Get-Content -LiteralPath $Path -Tail 500 -ErrorAction Stop) -join "`n"
    } else {
      $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
      try {
        if ($fs.Length -le $PreLen) { return "" }
        $fs.Position = $PreLen
        $remaining = $fs.Length - $PreLen
        $buffer = New-Object byte[] $remaining
        [void]$fs.Read($buffer, 0, $remaining)
        try { return [System.Text.Encoding]::UTF8.GetString($buffer) } catch { return [System.Text.Encoding]::ASCII.GetString($buffer) }
      } finally { $fs.Close(); $fs.Dispose() }
    }
  } catch {
    Write-Warning ("Failed to read new bytes from $($Path): $($_.Exception.Message)")
    return ""
  }
}

function Test-ConnectivitySinceRestart {
  param([hashtable]$Offsets, [regex]$ErrorPattern)
  Write-Host "=== Connectivity test (since this restart) ==="
  foreach ($kvp in $Offsets.GetEnumerator()) {
    $logPath = $kvp.Key
    $preLen  = [long]$kvp.Value
    if (Test-Path -LiteralPath $logPath) {
      $newText = Read-NewBytesSince -Path $logPath -PreLen $preLen
      if ($newText -and $ErrorPattern.IsMatch($newText)) {
        Error-Exit ("Detected SSL/cert verification failure in {0} since restart." -f ([IO.Path]::GetFileName($logPath)))
      }
    }
  }

  # Best-effort agent info check (paths vary on v5; try a couple)
  $agentInfoPaths = @(
    "C:\Program Files\Datadog\Datadog Agent\agent.exe",
    "C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe"
  )
  $infoOk = $false
  foreach ($p in $agentInfoPaths) {
    if (Test-Path -LiteralPath $p) {
      try {
        $out = & $p info 2>&1
        if ($out -match 'API Key is valid') { $infoOk = $true; break }
      } catch { }
    }
  }
  if ($infoOk) { Write-Host "API key validation: OK" } else { Write-Warning "Could not confirm 'API Key is valid' from agent info." }

  Write-Host "Connectivity test passed: no certificate verification errors since restart."
}

# ------------------------------ Main flow ------------------------------
try {
  Assert-Admin

  # Detect paths
  $CertPath     = Get-DdV5-CertPath
  $TargetDir    = Split-Path -Path $CertPath -Parent
  $TargetFile   = $CertPath
  $ConfFile     = Get-DdV5-ConfigFile
  $LogFiles     = Get-DdV5-LogFiles
  $ServiceNames = Get-DdV5-ServiceNames
  $WaitSeconds  = 30
  $Url          = "https://raw.githubusercontent.com/DataDog/dd-agent/master/datadog-cert.pem"

  Write-Host "Using certificate path: $TargetFile"
  Ensure-Directory $TargetDir
  Download-Certificate -Url $Url -TargetFile $TargetFile
  Update-DatadogConfig -ConfFile $ConfFile

  # Record pre-restart offsets
  $Offsets = @{}
  foreach ($f in $LogFiles) {
    if (Test-Path -LiteralPath $f) { $Offsets[$f] = (Get-Item -LiteralPath $f).Length } else { $Offsets[$f] = -1 }
  }
  $PreTs = [DateTime]::UtcNow
  $epoch = [int][double]([DateTimeOffset]$PreTs).ToUnixTimeSeconds()
  Write-Host ("Pre-restart timestamp: {0:yyyy-MM-dd HH:mm:ss} UTC (epoch: {1})" -f $PreTs, $epoch)

  Restart-Agent -ServiceNames $ServiceNames -WaitSeconds $WaitSeconds

  $ErrorPattern = [regex]'(?i)CERTIFICATE_VERIFY_FAILED|certificate verify failed|ssl[\s\p{P}]*error'
  Test-ConnectivitySinceRestart -Offsets $Offsets -ErrorPattern $ErrorPattern

} catch {
  Error-Exit $_.Exception.Message
}
