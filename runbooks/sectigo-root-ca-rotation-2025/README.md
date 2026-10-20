# Datadog Agent v5 - Certificate Update Runbook

## Overview

This runbook helps maintain connectivity for Datadog Agent v5 installations following certificate authority updates.

## Who Is Affected

If you are running **Datadog Agent v5**, particularly versions below **5.32.7**, you may experience connectivity issues with Datadog intake endpoints due to SSL certificate verification failures.

## Why This Matters

Agent v5 uses an embedded certificate bundle for SSL/TLS verification. When Datadog's SSL certificates are updated to use newer certificate authorities, older Agent v5 installations may not recognize these certificates, causing the Agent to lose connectivity with Datadog.

## Solution

This runbook provides automated scripts for both Linux and Windows that will:

1. Download and install an updated certificate bundle
2. Configure the Agent to use your operating system's certificate store as a fallback
3. Restart the Agent and verify connectivity

## Available Scripts

| Your OS | Script to use |
|---|---|
| Linux (all distributions) | [`linux.sh`](linux.sh) |
| Windows (all supported versions) | [`windows.ps1`](windows.ps1) |

### `linux.sh`

- **Supported distributions**: Ubuntu/Debian, RHEL/CentOS/Oracle Linux 5+, Fedora, and similar
- **Requirements**: Root or sudo access, `curl` or `wget`
- **Options**:
  - `-p <agent_directory>` — custom Agent installation path
  - `-c <cert_file>` — path to a local copy of `datadog-cert.pem` for hosts that cannot reach `raw.githubusercontent.com`
  - `-n` — with `-s`, dry run: report what the scrub would change, write nothing
  - `-s` — also scrub the distrusted eMudhra/emSign roots **and the Comodo
    "AAA Certificate Services" cross-signer** from the Agent's bundled CA stores.
    This changes validation for non-Datadog endpoints too — see
    [`../emudhra-ca-compromise-2026/`](../emudhra-ca-compromise-2026/)
- **Compatibility notes**:
  - Works with bash 3.1 (default on EL5) — no bash 4+ features
  - On RHEL/CentOS/Oracle Linux 5 and 6, the script automatically applies EL5/6
    compatibility mode: portable log truncation, insecure download fallback if the
    system CA bundle is too old to verify GitHub, and no `journalctl` (SysV init)

### `windows.ps1`

- **Requirements**: PowerShell 2.0+, .NET 3.5+, Administrator privileges
- **Options**:
  - `-AgentDirectory` / `-p` — custom Agent installation path
  - `-CertFile` / `-c` — path to a local copy of `datadog-cert.pem` for hosts that cannot reach `raw.githubusercontent.com`
  - `-DryRunScrub` / `-n` — with `-ScrubBundles`, dry run: report only, write nothing
  - `-ScrubBundles` / `-s` — also scrub the distrusted eMudhra/emSign roots **and
    the Comodo "AAA Certificate Services" cross-signer** from the Agent's bundled
    CA stores. This changes validation for non-Datadog endpoints too — see
    [`../emudhra-ca-compromise-2026/`](../emudhra-ca-compromise-2026/)
- **Compatibility notes**:
  - Works on Windows Server 2008 R2, 2012 R2, 2016, and later
  - Uses `System.Net.WebClient` (.NET 2.0) as the primary downloader so it works on
    PS 2.0 (default on 2008 R2); `Invoke-WebRequest` and BITS are kept as fallbacks
  - Forces TLS 1.2 using the raw integer value `3072` instead of the named enum
    `[Net.SecurityProtocolType]::Tls12` (.NET 4.5+)
  - **Windows 2008 R2 and TLS 1.2**: TLS 1.2 also requires a system-level fix
    (KB3140245 + SChannel registry changes). Without it, downloads from GitHub will
    fail. In that case, download `datadog-cert.pem` on another machine and use `-CertFile`.

## How to Use

### Linux

```bash
# Download the script
curl -O https://raw.githubusercontent.com/DataDog/dd-agent/master/runbooks/sectigo-root-ca-rotation-2025/linux.sh

# Make it executable
chmod +x linux.sh

# Run with sudo
sudo ./linux.sh
```

The script auto-detects the OS version and applies EL5/6 compatibility mode when needed.

If the host **cannot reach GitHub**, download `datadog-cert.pem` on another machine and transfer it manually, then pass it with `-c`:

```bash
sudo ./linux.sh -c /path/to/datadog-cert.pem
```

### Windows

On **Windows Server 2016+** (PS 3.0+):

```powershell
# Download the script (run as Administrator)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/DataDog/dd-agent/master/runbooks/sectigo-root-ca-rotation-2025/windows.ps1" -OutFile "windows.ps1" -UseBasicParsing

# Run the script
.\windows.ps1
```

On **Windows Server 2008 R2** (PS 2.0, no `Invoke-WebRequest`), use `System.Net.WebClient` to download:

```powershell
# Download the script (run as Administrator)
(New-Object System.Net.WebClient).DownloadFile(
    "https://raw.githubusercontent.com/DataDog/dd-agent/master/runbooks/sectigo-root-ca-rotation-2025/windows.ps1",
    "$env:TEMP\windows.ps1"
)

# Run the script
& "$env:TEMP\windows.ps1"
```

If the host **cannot reach GitHub** (or TLS 1.2 is not yet enabled at the OS level on 2008 R2), download `datadog-cert.pem` on another machine, transfer it, then pass it with `-CertFile`:

```powershell
.\windows.ps1 -CertFile "C:\Temp\datadog-cert.pem"
```

## What the Scripts Do

Both scripts perform the following steps automatically:

1. **Download Updated Certificate**: Fetches the latest Datadog certificate bundle (or uses the file you supply with `-c` / `-CertFile`)
2. **Install Certificate**: Places the certificate in the correct location for your Agent installation
3. **Update Configuration**: Enables `use_curl_http_client: true` in your `datadog.conf` to allow the Agent to use OS-provided certificates
4. **Restart Agent**: Restarts the Datadog Agent to apply changes
5. **Verify Connectivity** *(best-effort)*: Scans fresh Agent logs for SSL/certificate errors and confirms API key validation. If automatic verification is not possible (e.g., network restrictions, no curl/wget, or a firewall blocks the test endpoint), the script completes with a warning and clear instructions to test manually — the certificate is still installed.

The scripts output detailed progress information and always print a final summary indicating what was done and, if applicable, what you need to verify manually.

## Expected Output

### Certificate replaced and connectivity verified

```
...
=== Connectivity test (since this restart) ===
  Checking forwarder.log...
  Checking agent status...
API key validation: OK
Connectivity test passed: no certificate verification errors detected.

==============================
DONE — certificate replaced and connectivity verified successfully.

The Datadog certificate has been installed at: /opt/datadog-agent/agent/datadog-cert.pem
The Agent configuration has been updated, the Agent has been restarted,
and no SSL/certificate errors were detected in the logs.
==============================
```

### Certificate replaced but connectivity could not be auto-verified

This happens when network restrictions prevent the test connection, or when neither curl nor wget is available. The certificate is still correctly installed:

```
Warning: Could not verify connectivity to https://app.datadoghq.com using the installed certificate.
  This may be a network restriction, firewall rule, or temporary issue.
  The certificate has been installed; connectivity will be confirmed after the Agent restarts.
...
==============================
DONE — certificate replaced, but connectivity could not be fully verified automatically.

The Datadog certificate has been installed at: /opt/datadog-agent/agent/datadog-cert.pem
The Agent configuration has been updated and the Agent has been restarted.

Please verify connectivity manually:
  sudo service datadog-agent status
  sudo /etc/init.d/datadog-agent info
  Check logs for SSL errors:
    /var/log/datadog/forwarder.log
    /var/log/datadog/collector.log

If SSL errors persist, contact support with the log output above.
==============================
```

If a *fatal* step fails (certificate not found, config file missing, Agent failed to restart), the script exits immediately with a specific error message explaining why.

## Optional: scrubbing distrusted roots (`-s` / `-ScrubBundles`)

Off by default. When passed, the scripts additionally rewrite every CA bundle
shipped *inside* the Agent package to remove roots distrusted after the 2026
eMudhra intermediate CA compromise. This is a separate concern from certificate
rotation — see [`../emudhra-ca-compromise-2026/`](../emudhra-ca-compromise-2026/)
for the background, scope, and rollback instructions.

Preview first with `-n` / `-DryRunScrub`: it enumerates exactly what would be
removed from which bundles and writes nothing.

Each modified bundle is backed up alongside itself (`*.pre-cert-update-<timestamp>`
on Linux, `*.bak-<timestamp>` on Windows). The anchor appended to each bundle is
pinned by SHA-256: if the certificate in place is not the expected one, the
scrub refuses to touch any bundle. A scrub failure is never fatal — the
certificate update, config change and restart still complete.

## Important Notes

### Operating System Support

The fallback mechanism (`use_curl_http_client: true`) relies on your operating system's certificate store. If your operating system is no longer receiving security updates (end-of-life), the OS certificate store may not contain the necessary certificates, and connectivity issues may persist.

### Configuration Changes

The script modifies your `/etc/dd-agent/datadog.conf` (Linux) or `C:\ProgramData\Datadog\datadog.conf` (Windows) file. On both platforms, a timestamped backup (`*.pre-cert-update-<timestamp>` on Linux, `*.bak-<timestamp>` on Windows) is automatically created before modification.

### Network Requirements

The scripts require outbound HTTPS connectivity to:

- `raw.githubusercontent.com` (to download the certificate)

Ensure your firewall allows these connections.

## Troubleshooting

### Script Fails to Download Certificate

Ensure you have network connectivity and your firewall allows outbound HTTPS connections to GitHub.

If the host cannot reach GitHub at all, download `datadog-cert.pem` from another machine and pass it directly to the script:

**Linux (EL5/6)**:
```bash
sudo ./linux.sh -c /path/to/datadog-cert.pem
```

**Windows**:
```powershell
.\windows.ps1 -CertFile "C:\Temp\datadog-cert.pem"
```

### Agent Fails to Restart

Verify the Datadog Agent service is installed and running:

**Linux**:

```bash
sudo service datadog-agent status
```

**Windows**:

```powershell
Get-Service DatadogAgent
```

### Connectivity Could Not Be Verified Automatically

The script completes even when it cannot verify connectivity (e.g., the test endpoint is blocked by a firewall). It will print a warning and a manual checklist at the end.

If SSL/certificate errors **persist after the Agent has restarted**, check:

1. Verify your operating system is receiving security updates (the `use_curl_http_client: true` fallback relies on the OS certificate store)
2. Check the Agent logs for SSL/certificate error messages:
   - Linux: `/var/log/datadog/forwarder.log` and `/var/log/datadog/collector.log`
   - Windows: `C:\ProgramData\Datadog\logs\forwarder.log` and `collector.log`
3. Contact Datadog Support with the full script output and relevant log excerpts

### Permission Errors

- **Linux**: Ensure you run the script with `sudo`
- **Windows**: Right-click PowerShell and select "Run as Administrator"

## Verification

After running the script, verify your Agent is reporting metrics:

1. Wait 2-3 minutes for data to appear
2. Check your host in the Datadog Infrastructure List
3. Verify the "Last Seen" timestamp is recent

You can also manually check the Agent status:

**Linux**:

```bash
sudo /etc/init.d/datadog-agent info
```

**Windows** (path may vary):

```powershell
& "C:\Program Files\Datadog\Datadog Agent\agent.exe" info
```

## Long-Term Recommendation

While this runbook provides a working solution, **Datadog strongly recommends upgrading to Datadog Agent v6 or v7** to benefit from:

- Automatic certificate management (no manual intervention needed)
- Ongoing security updates and bug fixes
- Improved performance and new features
- Long-term support

Agent v5 reached end-of-life and no longer receives updates. For migration guidance, visit the [Datadog documentation](https://docs.datadoghq.com/agent/guide/upgrade_agent_fleet_automation).

## Support

If you encounter issues running this runbook or continue experiencing connectivity problems, please contact [Datadog Support](https://www.datadoghq.com/support/) with:

1. Your Agent version
2. Operating system and version
3. Complete output from the script
4. Recent Agent log excerpts showing any errors

## Additional Information

For more information about Datadog Agent installation and configuration, see the [official Datadog documentation](https://docs.datadoghq.com/agent/).
