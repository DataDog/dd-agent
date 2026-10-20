# Datadog Agent v5 — Distrusted CA Scrub Runbook (2026 eMudhra compromise)

## Overview

In October 2026, private keys for eight eMudhra/emSign intermediate certificate
authorities were reported compromised and revoked. Six of them are TLS CAs, and
all are cross-signed by Sectigo's **AAA Certificate Services** root — so a trust
store that still carries *either* the emSign roots *or* the AAA cross-signer will
accept certificates minted with the compromised keys.

Operating systems and language ecosystems have shipped updated trust stores. The
Datadog Agent v5 cannot pick those up: it bundles **its own** CA stores inside the
package, Python 2.7 cannot run a fixed `certifi` (the clean release is Python 3
only), and Agent v5 is end-of-life with no release vehicle. The bundles therefore
have to be rewritten in place.

## Who Is Affected

Any **Datadog Agent v5** installation, up to and including **5.32.9** (an
RHEL/CentOS RPM-only release that refreshed `cacerts`). Every shipped bundle
revision still carries these roots, so the remediation applies regardless of
which v5 you run.

Operating-system trust stores are **not** in scope here. If your OS still trusts
these roots, fix that through your OS vendor's `ca-certificates` update; it is
patched separately from the Agent and this runbook does not touch it.

## What Is Affected

A stock Agent v5 install ships these CA bundles. Only the forwarder's pinned
certificate (`datadog-cert.pem`) is unaffected — it contains a single root.

| Bundle | Used by |
|---|---|
| `certifi/cacert.pem` | every `requests` call: checks, flare, cloud metadata, API-key validation |
| `embedded/ssl/certs/cacert.pem` | the embedded OpenSSL / Python `ssl` default |
| `tornado/ca-certificates.crt` | the forwarder, when no pinned certificate is present |
| `boto/cacerts/cacerts.txt` | AWS/EC2 metadata calls |
| `httplib2/cacerts.txt` | `httplib2`-based integrations |
| `websocket/cacert.pem` | `docker-py` websocket connections |
| `pip/_vendor/certifi/cacert.pem` | `pip`, when installing custom checks |
| `agent/ca-certificates.crt` | Windows installs only |

## What running this does

The scrub is a flag on the existing Agent v5 **certificate update** runbook, so
running it performs that runbook's work as well. In one invocation it will:

1. Replace `datadog-cert.pem` (downloaded, or supplied with `-c`/`-CertFile`),
2. **Scrub the CA bundles** (the subject of this page),
3. Set `use_curl_http_client: true` in `datadog.conf` — the file is backed up
   first, and on Windows it is rewritten rather than edited in place,
4. Back up and truncate `/var/log/datadog/*.log`,
5. **Restart the Agent.**

There is no scrub-only mode. If you want only steps 1 and 3, run the runbook
without `-s`/`-ScrubBundles`.

## Solution

The scrub is built into the existing Agent v5 certificate scripts, behind an
opt-in flag. It shares those scripts' compatibility work (bash 3.1 / EL5-6,
PowerShell 2.0 / Server 2008 R2, air-gapped hosts, timestamped backups) rather
than duplicating it.

### Linux

```bash
curl -O https://raw.githubusercontent.com/DataDog/dd-agent/master/runbooks/sectigo-root-ca-rotation-2025/linux.sh
chmod +x linux.sh
sudo ./linux.sh -s -n     # preview: reports what would change, writes nothing
sudo ./linux.sh -s        # apply
```

### Windows

```powershell
# run as Administrator
.\windows.ps1 -ScrubBundles -DryRunScrub   # preview, writes nothing
.\windows.ps1 -ScrubBundles                # apply
```

See the [certificate update runbook](../sectigo-root-ca-rotation-2025/) for
download instructions on older PowerShell versions, the `-c` / `-CertFile`
option for hosts that cannot reach GitHub, and the EL5/6 notes.

## What the Scrub Does

For every CA bundle inside the Agent install:

1. Removes the distrusted roots — `AAA Certificate Services` plus
   `emSign Root CA - G1`, `emSign ECC Root CA - G3`, `emSign Root CA - C1` and
   `emSign ECC Root CA - C3` — matched by SHA-256 fingerprint, not by name.
2. Ensures the bundle still contains the anchor the Datadog intake chain
   terminates in, appending it if absent.
3. Writes a timestamped backup next to each modified file.

Bundles are **discovered** by walking the install, not read from a hardcoded
list, because the layout differs by platform (`embedded/lib/python2.7/site-packages`
on Linux, `embedded/lib/site-packages` on Windows).

The scrub runs on the Agent's own embedded Python on Linux, so it needs nothing
from the host — EL5/6 `openssl` predates `-fingerprint -sha256`.

### What the scrub will not touch

The scrub is confined to the Agent installation directory. It never modifies the
operating system trust store, the system Python, or anything else on the host.
Specifically:

- The search starts at the Agent install directory (or the path given with
  `-p` / `-AgentDirectory`) and never traverses above it.
- Symlinks and reparse points are **skipped, not rewritten** — both because
  writing through one could modify a file outside the install, and because
  replacing one would silently discard deliberate wiring (for example an admin
  pointing an Agent bundle at the OS trust store so it tracks OS updates).
- On Linux a bundle whose resolved path escapes the install directory is
  skipped; on Windows a bundle reached through a directory junction is skipped.
- A bundle that cannot be read or rewritten is skipped and reported.
- Scrub failures never abort the run: the certificate update, config change and
  restart still complete, and the final summary says the scrub did not finish.

Skipped bundles are listed in the output with the reason, and are left for you
to review by hand. On a stock install the 7 bundles on Linux and 8 on Windows
are ordinary files, so no skips are expected.

### What else this can affect

These bundles are not Datadog-specific. Removing `AAA Certificate Services`
changes certificate validation for **every** HTTPS endpoint the Agent reaches
through them — integration checks, flare upload, cloud metadata, and `pip` when
installing custom checks. If one of your integration targets still presents a
chain that depends on the AAA cross-sign, that check will start failing. The
Datadog intake itself is unaffected (the anchor step below covers it).

### Why the anchor step matters

The Datadog intake chain terminates in:

```
*.agent.datadoghq.com <- Sectigo DV R36 <- Sectigo Root R46 <- USERTrust RSA <- AAA Certificate Services
```

The bundled Tornado trust store contains **no USERTrust RSA anchor**, so it
reaches the intake *only* through the AAA cross-sign. Removing AAA without
adding that anchor breaks Agent connectivity. Always use the scripts rather than
deleting certificates by hand.

## Testing

`runbooks/sectigo-root-ca-rotation-2025/tests/test_scrub_bundles.sh` extracts the
scrub program from `linux.sh` and exercises it against fixtures (anchor pinning,
sub-threshold bundles, comment preservation, idempotency, dry run, symlink
containment). Run it with `sh tests/test_scrub_bundles.sh`.

## Rollback

Every modified bundle is backed up next to itself. To revert:

Substitute your own install path if you used `-p` / `-AgentDirectory`, or if you
are on Agent 5.11 or earlier (where the certificate lives under `files\`).

**Linux**
```bash
# newest backup wins if you ran the scrub more than once
find /opt/datadog-agent -name '*.pre-cert-update-*' -print0 | sort -z | while IFS= read -r -d '' b; do
  sudo cp -f "$b" "${b%%.pre-cert-update-*}"
done
sudo service datadog-agent restart
```

`datadog.conf` is backed up separately as
`/etc/dd-agent/datadog.conf.pre-cert-update-<timestamp>`; restore it too if you
want to undo the `use_curl_http_client` change.

**Windows**
```powershell
Get-ChildItem -LiteralPath "C:\Program Files\Datadog\Datadog Agent" -Recurse -Force |
  Where-Object { $_.Name -like '*.bak-*' } | Sort-Object Name |
  ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination ($_.FullName -replace '\.bak-\d+$','') -Force }
Restart-Service DatadogAgent
```

`datadog.conf` is backed up separately as
`C:\ProgramData\Datadog\datadog.conf.bak-<timestamp>`.

## Verification

After the scrub, the Agent should still report normally. To confirm the roots are
gone, the eMudhra project publishes test endpoints: a patched bundle must *fail*
to validate both of these, while the Datadog intake continues to work.

```bash
# use the Agent's own openssl: EL5/6 ships 0.9.8e, which has no -servername (SNI)
/opt/datadog-agent/embedded/bin/openssl s_client \
  -connect dv-g3b-aaa-emudhra.we-have-a-problem.com:443 \
  -servername dv-g3b-aaa-emudhra.we-have-a-problem.com \
  -CAfile /opt/datadog-agent/embedded/lib/python2.7/site-packages/certifi/cacert.pem </dev/null
# expect: Verify return code: 20 (unable to get local issuer certificate)
```

A purely local check, with no outbound connection, is to confirm the
fingerprints are gone:

```bash
grep -c 'BEGIN CERTIFICATE' /opt/datadog-agent/embedded/lib/python2.7/site-packages/certifi/cacert.pem
# compare against the .pre-cert-update-<timestamp> backup alongside it
```

## Long-Term Recommendation

Agent v5 is end-of-life and cannot receive dependency updates. This scrub is a
containment measure, not a fix. **Upgrade to Agent v6 or v7**, where CA bundles
are maintained through normal releases. See the
[upgrade documentation](https://docs.datadoghq.com/agent/guide/upgrade_agent_fleet_automation).

## Support

Contact [Datadog Support](https://www.datadoghq.com/support/) with your Agent
version, operating system, the complete script output, and recent Agent log
excerpts.
