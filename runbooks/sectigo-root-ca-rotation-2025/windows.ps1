<# Datadog Agent v5 runbook — Windows (all supported versions).
   Compatible with PowerShell 2.0+ and .NET 3.5+.
   Automatically handles Windows Server 2008 R2, 2012 R2, 2016, and later.

   Compatibility notes:
     - Primary downloader is System.Net.WebClient (.NET 2.0+), so it works on
       Windows 2008 R2 with PS 2.0 where Invoke-WebRequest is not available.
       Invoke-WebRequest and BITS are kept as fallbacks.
     - [System.IO.File]::ReadAllText() is used instead of Get-Content -Raw
       (the -Raw switch requires PS 3.0).
     - TLS 1.2 is forced via the numeric value 3072 instead of the named enum
       [Net.SecurityProtocolType]::Tls12, added in .NET 4.5.
       On Windows 2008 R2 without KB3140245 + SChannel registry fix, TLS 1.2
       is unsupported at the OS level and the download will still fail — see
       the README for details.
     - [DateTimeOffset]::ToUnixTimeSeconds() (added in .NET 4.6) is replaced
       with a manual epoch subtraction.
     - OS architecture is detected via environment variables rather than
       [Environment]::Is64BitOperatingSystem (.NET 4.0+) or [IntPtr]::Size
       (which reports the PowerShell process bitness, not the OS bitness).

.PARAMETER AgentDirectory
   Custom Datadog Agent installation directory.

.PARAMETER CertFile
   Path to a local copy of datadog-cert.pem.
   Use this when the host cannot reach raw.githubusercontent.com.
   The file is copied in place; no download is attempted.

.PARAMETER DryRunScrub
   With -ScrubBundles, report what the scrub would change and write nothing.
   Does not affect the certificate update, which always applies.

.PARAMETER ScrubBundles
   Also remove the distrusted eMudhra/emSign roots and the Comodo
   "AAA Certificate Services" cross-signer from the CA bundles shipped inside
   the Agent package (IR-62343). Off by default.

.EXAMPLE
   .\windows.ps1

.EXAMPLE
   .\windows.ps1 -AgentDirectory "D:\Custom\Datadog Agent"

.EXAMPLE
   .\windows.ps1 -CertFile "C:\Temp\datadog-cert.pem"

.EXAMPLE
   .\windows.ps1 -ScrubBundles

.EXAMPLE
   .\windows.ps1 -ScrubBundles -DryRunScrub
#>

param(
    [Alias("p")]
    [string]$AgentDirectory = "",

    [Alias("c")]
    [string]$CertFile = "",

    [Alias("s")]
    [switch]$ScrubBundles,

    [Alias("n")]
    [switch]$DryRunScrub
)

# -------------------------- Configuration ---------------------------
$CERT_URL = "https://raw.githubusercontent.com/DataDog/dd-agent/master/datadog-cert.pem"
$RESTART_WAIT_SECONDS = 30
$script:ScrubWarning = $false   # set when -ScrubBundles could not complete

$CUSTOM_DD_AGENT_DIR = if ($AgentDirectory) { $AgentDirectory } else { "" }
$LOCAL_CERT_FILE = if ($CertFile) { $CertFile } else { "" }

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
    }
    catch {
        Write-Warning "Could not verify elevation; continuing. If steps fail, re-run elevated."
    }
}

# -------------------------- Path discovery --------------------------
function Get-DdV5-CertPath {
    if ($CUSTOM_DD_AGENT_DIR) {
        if (Test-Path -LiteralPath "$CUSTOM_DD_AGENT_DIR\agent") {
            return "$CUSTOM_DD_AGENT_DIR\agent\datadog-cert.pem"
        }
        else {
            return "$CUSTOM_DD_AGENT_DIR\files\datadog-cert.pem"
        }
    }

    # Detect OS bitness via environment variables — reliable on all PS versions.
    # On a 64-bit OS running 32-bit PowerShell (WOW64), PROCESSOR_ARCHITECTURE is
    # 'x86' but PROCESSOR_ARCHITEW6432 is set to 'AMD64'.
    # [Environment]::Is64BitOperatingSystem requires .NET 4.0 (absent on the default
    # PS 2.0/.NET 3.5 stack on Windows 2008 R2).
    # [IntPtr]::Size reports the current process bitness, not the OS bitness, so a
    # 32-bit PowerShell host on a 64-bit OS would incorrectly return 4.
    $is64 = ($env:PROCESSOR_ARCHITECTURE -eq 'AMD64') -or
            ($null -ne $env:PROCESSOR_ARCHITEW6432 -and $env:PROCESSOR_ARCHITEW6432 -eq 'AMD64')

    if ($is64) {
        if (Test-Path -LiteralPath "C:\Program Files\Datadog\Datadog Agent\agent") {
            return "C:\Program Files\Datadog\Datadog Agent\agent\datadog-cert.pem"    # >=5.12
        }
        else {
            return "C:\Program Files (x86)\Datadog\Datadog Agent\files\datadog-cert.pem" # <=5.11
        }
    }
    else {
        return "C:\Program Files\Datadog\Datadog Agent\files\datadog-cert.pem"           # <=5.11 32-bit
    }
}

function Get-DdV5-ServiceNames { @("DatadogAgent", "datadogagent") }

function Get-DdV5-ConfigFile {
    return "C:\ProgramData\Datadog\datadog.conf"
}

function Get-DdV5-LogFiles {
    $logDir = "C:\ProgramData\Datadog\logs"
    $candidates = @("$logDir\forwarder.log", "$logDir\collector.log", "$logDir\agent.log")
    $existing = @()
    foreach ($f in $candidates) { if (Test-Path -LiteralPath $f) { $existing += $f } }
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
    # Force TLS 1.2 using the raw integer value (3072) instead of the named enum member
    # [Net.SecurityProtocolType]::Tls12, which was only added in .NET 4.5.
    # On Windows 2008 R2 this only takes effect if KB3140245 and the matching SChannel
    # registry keys are also applied; without them the OS SChannel stack does not support
    # TLS 1.2 regardless of the .NET setting.
    try {
        $tls12 = 3072
        $current = [int][Net.ServicePointManager]::SecurityProtocol
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]($current -bor $tls12)
    }
    catch {
        Write-Warning (("Could not enable TLS 1.2: {0}. On Windows 2008 R2, TLS 1.2 also " +
            "requires KB3140245 and SChannel registry changes.") -f $_.Exception.Message)
    }
}

function Set-CertFilePermissions {
    param([string]$TargetFile)
    try {
        $acl = Get-Acl -LiteralPath $TargetFile
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("BUILTIN\Users", "Read", "Allow")
        $acl.SetAccessRule($rule)
        Set-Acl -LiteralPath $TargetFile -AclObject $acl
        Write-Host "Certificate file permissions set successfully."
    }
    catch {
        Write-Warning "Could not set certificate permissions: $($_.Exception.Message)"
    }
}

function Download-Certificate {
    param([string]$Url, [string]$TargetFile)
    Write-Host "Downloading the Datadog certificate..."
    Enable-Tls12

    # Stage 1: System.Net.WebClient — available from .NET 2.0, works on PS 2.0.
    # Invoke-WebRequest requires PS 3.0 and is absent on 2008 R2 defaults.
    $downloaded = $false
    try {
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($Url, $TargetFile)
        $downloaded = $true
    }
    catch {
        Write-Warning "WebClient download failed: $($_.Exception.Message). Trying Invoke-WebRequest..."
    }

    # Stage 2: Invoke-WebRequest (PS 3.0+, available on 2012 R2 and patched 2008 R2).
    if (-not $downloaded) {
        try {
            Invoke-WebRequest -Uri $Url -OutFile $TargetFile -UseBasicParsing -ErrorAction Stop
            $downloaded = $true
        }
        catch {
            Write-Warning "Invoke-WebRequest failed: $($_.Exception.Message). Trying BITS..."
        }
    }

    # Stage 3: BITS — available on 2008 R2+ but requires the BITS service to be running.
    if (-not $downloaded) {
        try {
            Start-BitsTransfer -Source $Url -Destination $TargetFile -ErrorAction Stop
            $downloaded = $true
        }
        catch {
            Error-Exit "Error: Failed to download certificate with all available methods."
        }
    }

    if (-not (Test-Path -LiteralPath $TargetFile)) {
        Error-Exit "Error: Download reported success but file not found at $TargetFile."
    }
    Write-Host "Certificate downloaded successfully to $TargetFile."
    Set-CertFilePermissions -TargetFile $TargetFile
}

function Install-LocalCertificate {
    param([string]$SourceFile, [string]$TargetFile)
    Write-Host "Using local certificate file: $SourceFile"
    if (-not (Test-Path -LiteralPath $SourceFile)) {
        Error-Exit "Error: Local certificate file '$SourceFile' not found."
    }
    try {
        Copy-Item -LiteralPath $SourceFile -Destination $TargetFile -Force -ErrorAction Stop
    }
    catch {
        Error-Exit "Error: Failed to copy '$SourceFile' to '$TargetFile'. $($_.Exception.Message)"
    }
    Write-Host "Certificate copied successfully to $TargetFile."
    Set-CertFilePermissions -TargetFile $TargetFile
}

function Test-Certificate {
    param([string]$CertFile)
    Write-Host "Verifying the installed certificate..."

    # Verify the certificate file is a non-empty PEM file.
    if (-not (Test-Path -LiteralPath $CertFile)) {
        Error-Exit "Error: Certificate file not found at $CertFile after installation."
    }
    # [System.IO.File]::ReadAllText works from .NET 2.0 (Get-Content -Raw requires PS 3.0).
    $content = [System.IO.File]::ReadAllText($CertFile)
    if (-not ($content -match "BEGIN CERTIFICATE")) {
        Error-Exit "Error: $CertFile does not appear to be a valid PEM certificate file."
    }
    Write-Host "Certificate file looks valid (PEM format confirmed)."

    # Connectivity check against the Datadog endpoint.
    # Note: this uses the machine trust store, not the installed cert file, so it
    # confirms network reachability rather than cert correctness. The definitive
    # check is the Agent log scan performed after restart.
    $testUrl = "https://app.datadoghq.com"
    Enable-Tls12
    try {
        $request = [System.Net.WebRequest]::Create($testUrl)
        $request.Timeout = 10000
        $response = $request.GetResponse()
        $response.Close()
        Write-Host "Connectivity check successful: can reach $testUrl."
    }
    catch {
        Write-Warning "Could not reach ${testUrl}: $($_.Exception.Message)"
        Write-Warning "This may be a network restriction, firewall rule, or temporary issue."
        Write-Warning "The certificate has been installed; connectivity will be confirmed after the Agent restarts."
        $script:ConnectivityWarning = $true
    }
}

# ------------------ Distrusted-root scrub (-ScrubBundles) ------------
# The Agent package ships several CA bundles of its own (certifi, tornado,
# boto, httplib2, embedded OpenSSL, …). They are independent of the Windows
# certificate store, so an OS update cannot fix them and Agent v5 has no
# release vehicle. We delete the distrusted roots in place and guarantee the
# bundle still carries the anchor the Datadog intake chain terminates in —
# removing the cross-signer without that anchor would break the Agent.
#
# The anchor is pinned by fingerprint. It is NOT "whatever -CertFile happens
# to contain", or a substituted file would become a trust anchor in every
# bundle in the install.

# Distrusted following the eMudhra intermediate CA key compromise. The six TLS
# intermediates are cross-signed by Sectigo's "AAA Certificate Services", so
# that root has to go too or the cross-signed path still validates.
$DISTRUSTED_ROOTS = @{
    "D7A7A0FB5D7E2731D771E9484EBCDEF71D5F0C3E0A2948782BC83EE0EA699EF4" = "AAA Certificate Services";
    "40F6AF0346A99AA1CD1D555A4E9CCE62C7F9634603EE406615833DC8C8D00367" = "emSign Root CA - G1";
    "86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B" = "emSign ECC Root CA - G3";
    "125609AA301DA0A249B97A8239CB6A34216F44DCAC9F3954B14292F2E8C8608F" = "emSign Root CA - C1";
    "BC4D809B15189D78DB3E1D8CF4F9726A795DA1643CA5F1358E1DDB0EDC0D7EB3" = "emSign ECC Root CA - C3"
}
$ANCHOR_SHA256     = "E793C9B02FD8AA13E21C31228ACCB08119643B749C898964B1746D46C3D4CBD2"
$BUNDLE_MIN_PARSED = 10   # below this we do not treat the file as a trust store

function Get-PemMatches {
    param([string] $Text)
    $opts = [System.Text.RegularExpressions.RegexOptions]::Singleline
    # @() keeps a single match a collection: PowerShell 2 cannot index or call
    # .Count on a scalar, and the anchor file holds exactly one certificate.
    return @([regex]::Matches($Text, "-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", $opts))
}

function Get-PemFingerprint {
    param([string] $Block)
    $lines = $Block -split "`r?`n" | Where-Object { $_ -notmatch "-----" -and $_.Trim() -ne "" }
    $b64 = ($lines | ForEach-Object { $_.Trim() }) -join ""
    try { $der = [Convert]::FromBase64String($b64) } catch { return $null }
    # CryptoServiceProvider, not SHA256Managed: the managed implementation
    # throws when the FIPS algorithm policy is enabled, which is common on the
    # regulated hosts still running Agent v5.
    $sha = New-Object System.Security.Cryptography.SHA256CryptoServiceProvider
    try { return [BitConverter]::ToString($sha.ComputeHash($der)).Replace("-", "") }
    finally { $sha.Clear() }
}

function Test-PathWithinRoot {
    # Older PowerShell follows directory junctions during -Recurse, so a file
    # can look like a plain file while physically living outside the install.
    # Walk the ancestors up to (and including) the root and reject anything
    # reached through a reparse point.
    param([string] $Path, [string] $Root)
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    $current  = Split-Path -Path $Path -Parent
    while ($current) {
        $currentFull = [System.IO.Path]::GetFullPath($current).TrimEnd([System.IO.Path]::DirectorySeparatorChar)
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($item -and ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            # The install root itself being a junction is a legitimate way to
            # relocate the Agent; only reject junctions *below* it.
            if ($currentFull -ne $rootFull) { return $false }
        }
        if ($currentFull -eq $rootFull) { return $true }
        $parent = Split-Path -Path $current -Parent
        if ($parent -eq $current) { break }
        $current = $parent
    }
    return $false
}

# Failures here are deliberately non-fatal: the certificate rotation is the
# primary remediation and must still complete.
function Repair-CaBundles {
    param([string] $AgentRoot, [string] $AnchorFile)

    Write-Host ""
    Write-Host "=== Removing distrusted roots from the Agent's bundled CA stores ==="

    $anchorBlocks = Get-PemMatches ([System.IO.File]::ReadAllText($AnchorFile))
    if ($anchorBlocks.Count -eq 0) {
        Write-Warning "No certificate found in $AnchorFile; skipping the scrub."
        $script:ScrubWarning = $true
        return
    }
    $anchorPem = $anchorBlocks[0].Value
    $anchorFp  = Get-PemFingerprint $anchorPem
    if ($anchorFp -eq $null) {
        Write-Warning "Could not read a certificate from $AnchorFile; skipping the scrub."
        $script:ScrubWarning = $true
        return
    }
    if ($anchorFp -ne $ANCHOR_SHA256) {
        Write-Warning "$AnchorFile is not the expected trust anchor."
        Write-Warning "  expected SHA-256 $ANCHOR_SHA256"
        Write-Warning "  found    SHA-256 $anchorFp"
        Write-Warning "  Refusing to modify any CA bundle."
        $script:ScrubWarning = $true
        return
    }

    if ($DryRunScrub) { Write-Host "Dry run: reporting only, no bundle will be written." }

    $stamp   = Get-Date -Format "yyyyMMddHHmmss"
    $ascii   = New-Object System.Text.ASCIIEncoding   # no BOM: a BOM breaks PEM parsing
    $changed = 0
    $skipped = New-Object System.Collections.ArrayList

    $bundles = @(Get-ChildItem -LiteralPath $AgentRoot -Recurse -Force -ErrorAction SilentlyContinue |
                 Where-Object {
                     -not $_.PSIsContainer -and
                     ($_.Name -eq "cacert.pem" -or $_.Name -eq "ca-certificates.crt" -or $_.Name -eq "cacerts.txt")
                 })
    if ($bundles.Count -eq 0) {
        Write-Host "  No CA bundles found under $AgentRoot."
        return
    }

    foreach ($bundle in $bundles) {
        $path = $bundle.FullName

        if ($bundle.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            [void]$skipped.Add("$path (reparse point)"); continue
        }
        if (-not (Test-PathWithinRoot -Path $path -Root $AgentRoot)) {
            [void]$skipped.Add("$path (reached via a junction outside the install)"); continue
        }

        try { $text = [System.IO.File]::ReadAllText($path) }
        catch { [void]$skipped.Add("$path (not readable)"); continue }

        $pemMatches = Get-PemMatches $text
        if ($pemMatches.Count -eq 0) { continue }
        if ($pemMatches.Count -lt $BUNDLE_MIN_PARSED) {
            [void]$skipped.Add("$path ($($pemMatches.Count) certificate(s) - not treated as a trust store)")
            continue
        }

        $removed = New-Object System.Collections.ArrayList
        $cut     = New-Object System.Collections.ArrayList
        $seen    = @{}
        foreach ($m in $pemMatches) {
            $fp = Get-PemFingerprint $m.Value
            if ($fp -ne $null -and $DISTRUSTED_ROOTS.ContainsKey($fp)) {
                [void]$removed.Add($DISTRUSTED_ROOTS[$fp])
                [void]$cut.Add($m)
            } elseif ($fp -ne $null) {
                $seen[$fp] = $true
            }
        }

        $added = -not $seen.ContainsKey($anchorFp)
        if ($removed.Count -eq 0 -and -not $added) { continue }

        # Splice out only the distrusted spans so comments, labels and any
        # other non-CERTIFICATE content survive byte-for-byte.
        $sb = New-Object System.Text.StringBuilder
        $prev = 0
        foreach ($m in $cut) {
            [void]$sb.Append($text.Substring($prev, $m.Index - $prev))
            $prev = $m.Index + $m.Length
            while ($prev -lt $text.Length -and ($text[$prev] -eq "`n" -or $text[$prev] -eq "`r")) { $prev++ }
        }
        [void]$sb.Append($text.Substring($prev))
        $newText = $sb.ToString()
        if ($added) {
            if ($newText.Length -gt 0 -and -not $newText.EndsWith("`n")) { $newText += "`r`n" }
            $newText += $anchorPem + "`r`n"
        }

        # Real pre-write validation against the bytes we are about to commit.
        $check = Get-PemMatches $newText
        $expected = $pemMatches.Count - $removed.Count
        if ($added) { $expected = $expected + 1 }
        $bad = $false
        if ($check.Count -ne $expected) { $bad = $true }
        $checkFps = @{}
        foreach ($c in $check) { $f = Get-PemFingerprint $c.Value; if ($f -ne $null) { $checkFps[$f] = $true } }
        foreach ($k in $DISTRUSTED_ROOTS.Keys) { if ($checkFps.ContainsKey($k)) { $bad = $true } }
        if (-not $checkFps.ContainsKey($anchorFp)) { $bad = $true }
        if ($bad) {
            [void]$skipped.Add("$path (post-edit validation failed)"); continue
        }

        # Atomic replace: write a sibling temp file, then swap it in. An
        # in-place WriteAllText would truncate a live trust store.
        if ($DryRunScrub) {
            $changed = $changed + 1
            $rt = "none"; if ($removed.Count -gt 0) { $rt = ($removed -join ", ") }
            $at = ""; if ($added) { $at = " | would append anchor" }
            Write-Host "  $path"
            Write-Host ("    would change {0} -> {1} certs | would remove: {2}{3}" -f $pemMatches.Count, $check.Count, $rt, $at)
            continue
        }

        # File.Replace moves the original aside to $backup and swaps the temp
        # in as one operation, so there is no window in which the live trust
        # store is truncated. Do NOT pass $null for the backup: PowerShell
        # marshals it to an empty string and Replace rejects that.
        $backup = "$path.bak-$stamp"
        $tmp    = "$path.$stamp.tmp"
        try {
            [System.IO.File]::WriteAllText($tmp, $newText, $ascii)
            [System.IO.File]::Replace($tmp, $path, $backup)
        }
        catch {
            if (Test-Path -LiteralPath $tmp) {
                Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
            }
            [void]$skipped.Add("$path (could not be rewritten: $($_.Exception.Message))")
            continue
        }
        $changed = $changed + 1

        $removedText = "none"
        if ($removed.Count -gt 0) { $removedText = ($removed -join ", ") }
        $anchorText = ""
        if ($added) { $anchorText = " | anchor appended" }
        Write-Host "  $path"
        Write-Host ("    {0} -> {1} certs | removed: {2}{3}" -f $pemMatches.Count, $check.Count, $removedText, $anchorText)
        Write-Host "    backup: $backup"
    }

    foreach ($entry in $skipped) { Write-Warning "  SKIPPED $entry - left untouched" }

    if ($changed -eq 0) { Write-Host "  No changes needed - bundles already clean." }
    elseif ($DryRunScrub) { Write-Host ("  {0} bundle(s) would be updated. Re-run without -DryRunScrub to apply." -f $changed) }
    else { Write-Host ("  {0} bundle(s) updated." -f $changed) }
    if ($skipped.Count -gt 0) {
        Write-Warning ("  {0} bundle(s) skipped (listed above); review them by hand." -f $skipped.Count)
    }
}

function Update-DatadogConfig {
    param([string]$ConfFile)
    if (-not (Test-Path -LiteralPath $ConfFile)) { Error-Exit "Error: Configuration file $ConfFile not found." }
    Write-Host "Updating $ConfFile for use_curl_http_client..."

    $stamp = (Get-Date).ToString('yyyyMMdd-HHmmss')
    $backup = "$ConfFile.bak-$stamp"
    try { Copy-Item -LiteralPath $ConfFile -Destination $backup -Force } catch { Write-Warning "Backup failed: $($_.Exception.Message)" }

    # [System.IO.File]::ReadAllText works from .NET 2.0 (Get-Content -Raw requires PS 3.0).
    $raw = [System.IO.File]::ReadAllText($ConfFile)
    $lines = $raw -split "`r?`n"
    $filtered = @()
    foreach ($line in $lines) {
        if ($line -match '^\s*#?\s*use_curl_http_client\s*[:=].*$') { continue }
        $filtered += $line
    }
    $filtered += 'use_curl_http_client: true'
    $updated = ($filtered -join "`r`n") + "`r`n"

    try { [System.IO.File]::WriteAllText($ConfFile, $updated, (New-Object System.Text.UTF8Encoding($false))) }
    catch { Error-Exit "Error: Failed to update $ConfFile. $($_.Exception.Message)" }

    Write-Host "Configuration file updated successfully. Backup saved to $backup"
}

function Rotate-Logs {
    param([string[]]$LogFiles)
    Write-Host "Rotating log files before restart for easier troubleshooting..."
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($f in $LogFiles) {
        if (Test-Path -LiteralPath $f) {
            $backup = "$f.pre-cert-update-$timestamp"
            Write-Host ("  Backing up {0} to {1}" -f ([IO.Path]::GetFileName($f)), ([IO.Path]::GetFileName($backup)))
            try { Copy-Item -LiteralPath $f -Destination $backup -Force -ErrorAction Stop }
            catch { Write-Warning "Could not back up ${f}: $($_.Exception.Message)" }
            try { Clear-Content -LiteralPath $f -Force -ErrorAction Stop }
            catch { Write-Warning "Could not truncate ${f}: $($_.Exception.Message)" }
        }
    }

    $PreTs = [DateTime]::UtcNow

    # Manual epoch calculation — avoids [DateTimeOffset]::ToUnixTimeSeconds() which
    # was added in .NET 4.6 and is absent on 2008 R2 (.NET 4.0) and 2012 R2 (.NET 4.5.1).
    $unixEpoch = New-Object System.DateTime(1970, 1, 1, 0, 0, 0, [System.DateTimeKind]::Utc)
    $epoch = [int]($PreTs - $unixEpoch).TotalSeconds

    Write-Host ("Restart timestamp: {0:yyyy-MM-dd HH:mm:ss} UTC (epoch: {1})" -f $PreTs, $epoch)
}

function Restart-Agent {
    param([string[]]$ServiceNames, [int]$WaitSeconds = 30)
    Write-Host "Restarting the Datadog Agent..."
    $restarted = $false
    foreach ($name in $ServiceNames) {
        $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
        if ($svc) {
            try {
                Restart-Service -Name $name -Force -ErrorAction Stop
                $restarted = $true
                break
            }
            catch {
                Error-Exit "Error: Failed to restart service '${name}': $($_.Exception.Message)"
            }
        }
    }
    if (-not $restarted) { Error-Exit "Error: Failed to restart the Datadog Agent (service not found)." }
    Write-Host "Waiting $WaitSeconds seconds for the Datadog Agent to restart..."
    Start-Sleep -Seconds $WaitSeconds
}

function Test-ConnectivitySinceRestart {
    param([string[]]$LogFiles, [regex]$ErrorPattern)
    Write-Host "=== Connectivity test (since this restart) ==="

    foreach ($logPath in $LogFiles) {
        if (Test-Path -LiteralPath $logPath) {
            $fileInfo = Get-Item -LiteralPath $logPath
            if ($fileInfo.Length -gt 0) {
                Write-Host ("  Checking {0}..." -f $fileInfo.Name)
                try {
                    # [System.IO.File]::ReadAllText works from .NET 2.0.
                    # Get-Content -Raw requires PS 3.0 and fails silently on PS 2.0
                    # (returns an array instead of a string, breaking the regex match).
                    $content = [System.IO.File]::ReadAllText($logPath)
                    if ($content -and $ErrorPattern.IsMatch($content)) {
                        Write-Host ""
                        Write-Warning ("Detected SSL/cert verification failure in {0}:" -f $fileInfo.Name)
                        $hits = Select-String -Path $logPath -Pattern $ErrorPattern | Select-Object -First 10
                        $hits | ForEach-Object { Write-Host $_.Line }
                        Write-Warning ("The certificate has been replaced. Please review the log at: {0} and test connectivity manually (see summary below)." -f $logPath)
                        $script:ConnectivityWarning = $true
                    }
                }
                catch {
                    Write-Warning ("Could not read {0}: {1}" -f $logPath, $_.Exception.Message)
                }
            }
        }
    }

    Write-Host "  Checking agent status..."
    if ($CUSTOM_DD_AGENT_DIR) {
        $agentInfoPaths = @(
            "$CUSTOM_DD_AGENT_DIR\agent.exe",
            "$CUSTOM_DD_AGENT_DIR\embedded\agent.exe"
        )
    }
    else {
        $agentInfoPaths = @(
            "C:\Program Files\Datadog\Datadog Agent\agent.exe",
            "C:\Program Files\Datadog\Datadog Agent\embedded\agent.exe",
            "C:\Program Files (x86)\Datadog\Datadog Agent\agent.exe",
            "C:\Program Files (x86)\Datadog\Datadog Agent\embedded\agent.exe"
        )
    }
    $infoOk = $false
    foreach ($p in $agentInfoPaths) {
        if (Test-Path -LiteralPath $p) {
            try {
                $out = & $p info 2>&1
                if ($out -match 'API Key is valid') { $infoOk = $true; break }
            }
            catch { }
        }
    }
    if ($infoOk) { Write-Host "API key validation: OK" } else { Write-Warning "Could not confirm 'API Key is valid' from agent info." }

    if (-not $script:ConnectivityWarning) {
        Write-Host "Connectivity test passed: no certificate verification errors detected."
    }
    Write-Host ""
    Write-Host "Fresh logs are available at:"
    foreach ($logPath in $LogFiles) {
        if (Test-Path -LiteralPath $logPath) { Write-Host ("  - {0}" -f $logPath) }
    }
}

# ------------------------------ Main flow ------------------------------
$script:ConnectivityWarning = $false   # set to $true when a non-fatal connectivity check fails

try {
    Assert-Admin

    $CertPath     = Get-DdV5-CertPath
    $TargetDir    = Split-Path -Path $CertPath -Parent
    $TargetFile   = $CertPath
    $ConfFile     = Get-DdV5-ConfigFile
    $LogFiles     = Get-DdV5-LogFiles
    $ServiceNames = Get-DdV5-ServiceNames

    Write-Host "Using certificate path: $TargetFile"
    Ensure-Directory $TargetDir

    if ($LOCAL_CERT_FILE) {
        Install-LocalCertificate -SourceFile $LOCAL_CERT_FILE -TargetFile $TargetFile
    }
    else {
        Download-Certificate -Url $CERT_URL -TargetFile $TargetFile
    }

    Test-Certificate -CertFile $TargetFile

    if ($ScrubBundles) {
        # agent root sits two levels above datadog-cert.pem on every version
        # (see the agent.exe note below for the >=5.12 / <=5.11 layouts).
        $agentRoot = Split-Path -Path (Split-Path -Path $TargetFile -Parent) -Parent
        try { Repair-CaBundles -AgentRoot $agentRoot -AnchorFile $TargetFile }
        catch {
            Write-Warning "The CA bundle scrub did not complete: $($_.Exception.Message)"
            Write-Warning "The certificate update below is unaffected."
            $script:ScrubWarning = $true
        }
    }

    Update-DatadogConfig -ConfFile $ConfFile
    Rotate-Logs -LogFiles $LogFiles
    Restart-Agent -ServiceNames $ServiceNames -WaitSeconds $RESTART_WAIT_SECONDS

    $ErrorPattern = [regex]'(?i)CERTIFICATE_VERIFY_FAILED|certificate verify failed|ssl[\s\p{P}]*error'
    Test-ConnectivitySinceRestart -LogFiles $LogFiles -ErrorPattern $ErrorPattern

    Write-Host ""
    Write-Host "=============================="
    if ($script:ConnectivityWarning) {
        Write-Host "DONE — certificate replaced, but connectivity could not be fully verified automatically."
        Write-Host ""
        Write-Host "The Datadog certificate has been installed at: $TargetFile"
        Write-Host "The Agent configuration has been updated and the Agent has been restarted."
        Write-Host ""
        # agent.exe lives two levels above datadog-cert.pem regardless of version:
        #   >=5.12:  ...\Datadog Agent\agent\datadog-cert.pem  → ...\Datadog Agent\agent.exe
        #   <=5.11:  ...\Datadog Agent\files\datadog-cert.pem  → ...\Datadog Agent\agent.exe
        $agentExe = Join-Path (Split-Path -Path (Split-Path -Path $TargetFile -Parent) -Parent) "agent.exe"
        Write-Host "Please verify connectivity manually:"
        Write-Host "  - Check the Datadog Agent service:  Get-Service DatadogAgent"
        Write-Host "  - Run agent info:                   & '$agentExe' info"
        Write-Host "  - Check logs for SSL errors:"
        foreach ($logPath in $LogFiles) { Write-Host "      $logPath" }
        Write-Host ""
        Write-Host "If SSL errors persist, contact support with the log output above."
    }
    else {
        Write-Host "DONE — certificate replaced and connectivity verified successfully."
        Write-Host ""
        Write-Host "The Datadog certificate has been installed at: $TargetFile"
        Write-Host "The Agent configuration has been updated, the Agent has been restarted,"
        Write-Host "and no SSL/certificate errors were detected in the logs."
    }
    if ($ScrubBundles) {
        Write-Host ""
        if ($DryRunScrub) {
            Write-Host "Dry run only: no CA bundle was modified."
        } elseif ($script:ScrubWarning) {
            Write-Host "The CA bundle scrub did NOT complete - see the warnings above."
            Write-Host "The certificate update itself succeeded; re-run with -ScrubBundles"
            Write-Host "once the cause is resolved, or remediate the bundles by hand."
        } else {
            Write-Host "Distrusted roots were also removed from the Agent's bundled CA stores."
            Write-Host "Each modified bundle was backed up alongside itself as"
            Write-Host "  <bundle>.bak-<timestamp>"
        }
    }
    Write-Host "=============================="
}
catch {
    Error-Exit $_.Exception.Message
}
