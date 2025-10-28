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

### Linux: `linux.sh`

- **Supported distributions**: Ubuntu/Debian, RHEL/CentOS, Fedora, and similar
- **Requirements**: Root or sudo access
- **Automatic features**: Will attempt to install `curl` temporarily if neither `curl` nor `wget` is available

### Windows: `windows.ps1`

- **Requirements**: PowerShell 3.0 or higher, Administrator privileges
- **Automatic features**: Auto-detects Agent v5 installation path (handles different versions and architectures)

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

### Windows

```powershell
# Download the script (run as Administrator)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/DataDog/dd-agent/master/runbooks/sectigo-root-ca-rotation-2025/windows.ps1" -OutFile "windows.ps1"

# Run the script
.\windows.ps1
```

## What the Scripts Do

Both scripts perform the following steps automatically:

1. **Download Updated Certificate**: Fetches the latest Datadog certificate bundle
2. **Install Certificate**: Places the certificate in the correct location for your Agent installation
3. **Update Configuration**: Enables `use_curl_http_client: true` in your datadog.conf to allow the agent to use OS-provided certificates
4. **Restart Agent**: Restarts the Datadog Agent to apply changes
5. **Verify Connectivity**: Checks logs for certificate errors and confirms API key validation

The scripts will output detailed progress information and report any errors encountered.

## Expected Output

When the script completes successfully, you should see:

```
Downloading the DataDog certificate...
Certificate downloaded successfully to [path]
Updating configuration file...
Configuration file updated successfully.
Restarting the DataDog Agent...
Waiting 30 seconds for the DataDog Agent to restart...
=== Connectivity test (since this restart) ===
API key validation: OK
Connectivity test passed: no certificate verification errors since restart.
```

If errors are detected, the script will display a specific error message and prompt you to contact support.

## Important Notes

### Operating System Support

The fallback mechanism (`use_curl_http_client: true`) relies on your operating system's certificate store. If your operating system is no longer receiving security updates (end-of-life), the OS certificate store may not contain the necessary certificates, and connectivity issues may persist.

### Configuration Changes

The script modifies your `/etc/dd-agent/datadog.conf` (Linux) or `C:\ProgramData\Datadog\datadog.conf` (Windows) file. On Windows, a backup is automatically created before modification.

### Network Requirements

The scripts require outbound HTTPS connectivity to:

- `raw.githubusercontent.com` (to download the certificate)

Ensure your firewall allows these connections.

## Troubleshooting

### Script Fails to Download Certificate

Ensure you have network connectivity and your firewall allows outbound HTTPS connections to GitHub.

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

### Connectivity Test Fails

If certificate errors persist after running the script:

1. Verify your operating system is receiving security updates
2. Check the Agent logs for detailed error messages:
   - Linux: `/var/log/datadog/forwarder.log` and `/var/log/datadog/collector.log`
   - Windows: `C:\ProgramData\Datadog\logs\forwarder.log` and `collector.log`
3. Contact Datadog Support with the script output and log excerpts

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
