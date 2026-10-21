#!/bin/bash
# Datadog Agent v5 runbook — Linux (all supported distributions).
# Compatible with bash 3.1+ (RHEL/CentOS/Oracle Linux 5 and 6, EL 7+, Ubuntu, Debian, Fedora, …)
#
# On RHEL/CentOS/Oracle Linux 5 and 6 the script automatically applies compatibility
# adjustments:
#   - Falls back to --insecure / --no-check-certificate if the system CA bundle is too
#     old to verify raw.githubusercontent.com (common on RHEL/CentOS 5); the downloaded
#     certificate is then validated against the Datadog endpoint.
#   - Uses a portable log-truncation fallback (truncate absent from coreutils 5.97 / EL5).
#   - Skips journalctl checks — EL5/6 use SysV init, not systemd.

set -eo pipefail

show_usage() {
  echo "Usage: $0 [-p <agent_directory>] [-c <cert_file>] [-s] [-n]"
  echo "  -p <agent_directory>  Custom Datadog Agent installation directory"
  echo "                        (default: /opt/datadog-agent/agent)"
  echo "  -c <cert_file>        Path to a local copy of datadog-cert.pem"
  echo "                        Use this when the host cannot reach raw.githubusercontent.com."
  echo "                        The file is copied in place; no download is attempted."
  echo "  -s                    Also remove the distrusted eMudhra/emSign roots and the"
  echo "                        Comodo \"AAA Certificate Services\" cross-signer from the CA"
  echo "                        bundles shipped inside the Agent package (IR-62343)."
  echo "  -n                    Dry run for -s: report what the scrub would change"
  echo "                        and write nothing. Does not affect the certificate"
  echo "                        update, which always applies."
  exit 1
}

while getopts "p:c:snh" opt; do
  case $opt in
    p) ARG_AGENT_DIR="$OPTARG" ;;
    c) ARG_CERT_FILE="$OPTARG" ;;
    s) ARG_SCRUB=true ;;
    n) ARG_SCRUB_DRYRUN=true ;;
    h) show_usage ;;
    \?) echo "Invalid option: -$OPTARG" >&2; show_usage ;;
  esac
done

# -------------------------- Configuration ---------------------------
URL="https://raw.githubusercontent.com/DataDog/dd-agent/master/datadog-cert.pem"

TARGET_DIR="${ARG_AGENT_DIR:-/opt/datadog-agent/agent}"
LOCAL_CERT_FILE="${ARG_CERT_FILE:-}"
CONF_FILE="/etc/dd-agent/datadog.conf"
LOG_FILES="/var/log/datadog/forwarder.log /var/log/datadog/collector.log"

TARGET_FILE="${TARGET_DIR}/datadog-cert.pem"
DOWNLOADER=""
OS_MAJOR=""
IS_LEGACY_EL=false
PRE_TS_UNIX=""
PRE_TS_READABLE=""
CONNECTIVITY_WARNING=false   # set to true when a non-fatal connectivity check fails
DO_SCRUB="${ARG_SCRUB:-false}"
AGENT_ROOT=""
SCRUB_WARNING=false   # set when -s could not complete
SCRUB_DRYRUN="${ARG_SCRUB_DRYRUN:-false}"

# ------------------------------- Helpers ----------------------------

error_exit() {
  echo "$1" >&2
  echo "Please contact support for further help." >&2
  exit 1
}

detect_os_version() {
  if [ -f /etc/redhat-release ]; then
    local release_line
    release_line="$(cat /etc/redhat-release 2>/dev/null)"
    OS_MAJOR=$(echo "$release_line" | sed 's/.*release \([0-9]\).*/\1/' 2>/dev/null)

    # Identify the specific distro from the release string.
    # All three write to /etc/redhat-release but with different prefixes:
    #   RHEL:          "Red Hat Enterprise Linux * release X.Y (...)"
    #   CentOS:        "CentOS release X.Y (Final)"  [v5]
    #                  "CentOS Linux release X.Y (Core)"  [v6]
    #   Oracle Linux:  "Oracle Linux Server release X.Y"
    #                  "Enterprise Linux Enterprise Linux Server release X.Y"  [early OL5]
    local distro
    case "$release_line" in
      *"Red Hat"*)    distro="RHEL" ;;
      *"CentOS"*)     distro="CentOS" ;;
      *"Oracle"*)     distro="Oracle Linux" ;;
      *"Enterprise"*) distro="Oracle Linux (early release string)" ;;
      *)              distro="Unknown RHEL-based distro" ;;
    esac

    echo "Detected: $distro ${OS_MAJOR:-?} (from: $release_line)"

    if [ "$OS_MAJOR" = "5" ] || [ "$OS_MAJOR" = "6" ]; then
      IS_LEGACY_EL=true
      echo "Note: Applying EL5/6 compatibility mode" \
           "(portable truncation, insecure download fallback, no journalctl)."
    fi
  fi
}

check_downloader() {
  # When a local cert is provided we only need a downloader for verify_certificate.
  # If neither tool is present in that case we skip verification with a warning
  # instead of aborting; the cert came from a trusted local source.
  if command -v curl >/dev/null 2>&1; then
    DOWNLOADER="curl"
  elif command -v wget >/dev/null 2>&1; then
    DOWNLOADER="wget"
  else
    if [ -n "$LOCAL_CERT_FILE" ]; then
      echo "Warning: Neither curl nor wget found; skipping connectivity verification."
      DOWNLOADER="none"
    else
      error_exit "Error: Neither curl nor wget found. Please install curl or wget and try again."
    fi
  fi
  echo "Using downloader: $DOWNLOADER"
}

# Portable log truncation.
# RHEL 5 ships coreutils 5.97 which does NOT include the `truncate` binary.
# We fall back to an empty redirect executed via sudo sh -c.
truncate_log_file() {
  local f="$1"
  if command -v truncate >/dev/null 2>&1; then
    sudo truncate -s 0 "$f" 2>/dev/null \
      || echo "  Warning: Could not truncate $f"
  else
    # Works on bash 3.1 + RHEL 5: sudo opens the file for writing via sh, which
    # truncates it to zero bytes without requiring the truncate binary.
    sudo sh -c "> \"$f\"" 2>/dev/null \
      || echo "  Warning: Could not clear $f"
  fi
}

ensure_target_directory() {
  if ! sudo test -d "$TARGET_DIR"; then
    echo "Directory $TARGET_DIR does not exist. Creating it..."
    sudo mkdir -p "$TARGET_DIR" \
      || error_exit "Error: Failed to create $TARGET_DIR."
    if id dd-agent >/dev/null 2>&1; then
      echo "Setting directory ownership to dd-agent:dd-agent..."
      sudo chown dd-agent:dd-agent "$TARGET_DIR" \
        || echo "Warning: Failed to set ownership, but continuing..."
    fi
  fi
}

# Download helper with a two-stage approach for legacy EL5/6:
#   Stage 1 — standard TLS verification (preferred).
#   Stage 2 — skip TLS verification if stage 1 fails; prints a clear warning.
#             Only attempted on EL5/6 where the system CA bundle may predate
#             the DigiCert roots used by GitHub. The cert being retrieved is the
#             Datadog application cert, NOT a system CA, so the integrity risk is
#             limited; verify_certificate() checks usability against the Datadog
#             endpoint afterwards.
download_url() {
  local url="$1"
  local outfile="$2"

  if [ "$DOWNLOADER" = "curl" ]; then
    if sudo curl -fsSL --connect-timeout 30 "$url" -o "$outfile" 2>/dev/null; then
      return 0
    fi
    if [ "$IS_LEGACY_EL" = "true" ]; then
      echo "  Warning: TLS-verified download failed." \
           "System CA bundle on this OS version may be too old to verify raw.githubusercontent.com."
      echo "  Retrying with --insecure. The downloaded certificate will be validated"
      echo "  against the Datadog endpoint in the next step."
      sudo curl -fsSL --insecure --connect-timeout 30 "$url" -o "$outfile" \
        || return 1
    else
      return 1
    fi
  else
    if sudo wget -q --timeout=30 -O "$outfile" "$url" 2>/dev/null; then
      return 0
    fi
    if [ "$IS_LEGACY_EL" = "true" ]; then
      echo "  Warning: TLS-verified download failed." \
           "System CA bundle on this OS version may be too old to verify raw.githubusercontent.com."
      echo "  Retrying with --no-check-certificate. The downloaded certificate will be"
      echo "  validated against the Datadog endpoint in the next step."
      sudo wget -q --no-check-certificate --timeout=30 -O "$outfile" "$url" \
        || return 1
    else
      return 1
    fi
  fi
}

install_local_certificate() {
  echo "Using local certificate file: $LOCAL_CERT_FILE"
  if [ ! -f "$LOCAL_CERT_FILE" ]; then
    error_exit "Error: Local certificate file '$LOCAL_CERT_FILE' not found."
  fi
  sudo cp "$LOCAL_CERT_FILE" "$TARGET_FILE" \
    || error_exit "Error: Failed to copy '$LOCAL_CERT_FILE' to '$TARGET_FILE'."
  echo "Certificate copied successfully to $TARGET_FILE."

  if id dd-agent >/dev/null 2>&1; then
    sudo chown dd-agent:dd-agent "$TARGET_FILE" \
      || echo "Warning: Failed to set certificate ownership, but continuing..."
  fi
  sudo chmod 644 "$TARGET_FILE" \
    || echo "Warning: Failed to set certificate permissions, but continuing..."
}

download_certificate() {
  echo "Downloading the Datadog certificate using $DOWNLOADER..."
  download_url "$URL" "$TARGET_FILE" \
    || error_exit "Error: Failed to download certificate."
  echo "Certificate downloaded successfully to $TARGET_FILE."

  if id dd-agent >/dev/null 2>&1; then
    echo "Setting certificate file ownership to dd-agent:dd-agent..."
    sudo chown dd-agent:dd-agent "$TARGET_FILE" \
      || echo "Warning: Failed to set certificate ownership, but continuing..."
  fi
  sudo chmod 644 "$TARGET_FILE" \
    || echo "Warning: Failed to set certificate permissions, but continuing..."
}

verify_certificate() {
  if [ "$DOWNLOADER" = "none" ]; then
    echo "Skipping connectivity verification (no curl or wget available)."
    echo "The Agent logs will confirm certificate validity after restart."
    CONNECTIVITY_WARNING=true
    return 0
  fi

  echo "Verifying the downloaded certificate..."
  local test_url
  test_url="https://app.datadoghq.com"

  if [ "$DOWNLOADER" = "curl" ]; then
    if sudo curl -fsSL --cacert "$TARGET_FILE" --connect-timeout 10 \
        "$test_url" >/dev/null 2>&1; then
      echo "Certificate verification successful: can connect to Datadog."
    else
      echo "Warning: Could not verify connectivity to $test_url using the installed certificate." >&2
      echo "  This may be a network restriction, firewall rule, or temporary issue." >&2
      echo "  The certificate has been installed; connectivity will be confirmed after the Agent restarts." >&2
      CONNECTIVITY_WARNING=true
    fi
  else
    if sudo wget --ca-certificate="$TARGET_FILE" --timeout=10 \
        -q -O /dev/null "$test_url" 2>/dev/null; then
      echo "Certificate verification successful: can connect to Datadog."
    else
      echo "Warning: Could not verify connectivity to $test_url using the installed certificate." >&2
      echo "  This may be a network restriction, firewall rule, or temporary issue." >&2
      echo "  The certificate has been installed; connectivity will be confirmed after the Agent restarts." >&2
      CONNECTIVITY_WARNING=true
    fi
  fi
}

update_datadog_config() {
  if ! sudo test -f "$CONF_FILE"; then
    error_exit "Error: Configuration file $CONF_FILE not found."
  fi

  local timestamp backup
  timestamp="$(date +%Y%m%d-%H%M%S)"
  backup="${CONF_FILE}.pre-cert-update-${timestamp}"
  echo "Backing up $CONF_FILE to $backup"
  sudo cp -p "$CONF_FILE" "$backup" \
    || error_exit "Error: Failed to back up $CONF_FILE to $backup."

  echo "Updating $CONF_FILE for use_curl_http_client..."
  if sudo grep -q '^[[:space:]]*use_curl_http_client' "$CONF_FILE"; then
    echo "Parameter 'use_curl_http_client' found. Setting its value to true..."
    sudo sed -i 's/^\([[:space:]]*\)use_curl_http_client.*/\1use_curl_http_client: true/' "$CONF_FILE" \
      || error_exit "Error: Failed to update $CONF_FILE."
  else
    echo "Parameter 'use_curl_http_client' not found. Adding it with value true..."
    echo "use_curl_http_client: true" | sudo tee -a "$CONF_FILE" >/dev/null \
      || error_exit "Error: Failed to update $CONF_FILE."
  fi
  echo "Configuration file updated successfully."
}

rotate_logs() {
  echo "Rotating log files before restart for easier troubleshooting..."
  local timestamp
  timestamp="$(date +%Y%m%d-%H%M%S)"
  for f in $LOG_FILES; do
    if sudo test -f "$f"; then
      local backup
      backup="${f}.pre-cert-update-${timestamp}"
      echo "  Backing up $(basename "$f") to $(basename "$backup")"
      sudo cp "$f" "$backup" 2>/dev/null \
        || echo "  Warning: Could not back up $f"
      truncate_log_file "$f"
    fi
  done
  PRE_TS_UNIX="$(date +%s)"
  PRE_TS_READABLE="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  echo "Restart timestamp: $PRE_TS_READABLE (epoch: $PRE_TS_UNIX)"
}

restart_agent() {
  echo "Restarting the Datadog Agent..."
  if ! sudo service datadog-agent restart; then
    error_exit "Error: Failed to restart the Datadog agent."
  fi
  echo "Waiting 30 seconds for the Datadog Agent to restart..."
  sleep 30
}

test_connectivity_since_restart() {
  echo "=== Connectivity test (since this restart) ==="
  local pattern
  # The last two alternatives are libcurl's wording; update_datadog_config
  # turns on use_curl_http_client, so after this runbook they are the only
  # form a forwarder TLS failure takes.
  pattern='CERTIFICATE_VERIFY_FAILED|certificate verify failed|ssl[[:space:][:punct:]]*error|SSL certificate problem|SSL peer certificate'

  # Check the freshly-rotated log files (truncated just before restart).
  for log_file in $LOG_FILES; do
    if sudo test -f "$log_file" && sudo test -s "$log_file"; then
      echo "  Checking $(basename "$log_file")..."
      if sudo grep -qiE "$pattern" "$log_file" 2>/dev/null; then
        echo ""
        echo "Warning: Detected SSL/cert verification failure in $(basename "$log_file"):" >&2
        # `|| true` prevents set -o pipefail from aborting when head closes the pipe
        # early after 10 lines (grep receives SIGPIPE → exits 141).
        sudo grep -iE "$pattern" "$log_file" | head -10 || true
        echo "  The certificate has been replaced. Please review the log at: $log_file" >&2
        echo "  and test Agent connectivity manually (see summary below)." >&2
        CONNECTIVITY_WARNING=true
      fi
    fi
  done

  # journalctl is only available on systemd-based systems (EL 7+, Ubuntu, Debian, …).
  # EL 5 and 6 use SysV init and do not ship journald.
  if [ "$IS_LEGACY_EL" = "false" ] && command -v journalctl >/dev/null 2>&1; then
    echo "  Checking journald logs..."
    # Prefer epoch form; fall back to a readable UTC timestamp if needed.
    local SINCE_ARG
    SINCE_ARG="@${PRE_TS_UNIX}"
    if ! sudo journalctl --since "$SINCE_ARG" -n 0 >/dev/null 2>&1; then
      SINCE_ARG="$PRE_TS_READABLE"
    fi
    # `|| true` prevents set -o pipefail from aborting when grep -q closes the pipe
    # on first match (journalctl receives SIGPIPE → exits 141).
    local journal_match
    journal_match="$(sudo journalctl -u datadog-agent --since "$SINCE_ARG" --no-pager 2>/dev/null | grep -iE "$pattern" | head -1 || true)"
    if [ -n "$journal_match" ]; then
      echo "Warning: Detected SSL/cert verification failure in journald since restart." >&2
      echo "  The certificate has been replaced. Please test Agent connectivity manually (see summary below)." >&2
      CONNECTIVITY_WARNING=true
    fi
  fi

  echo "  Checking agent status..."
  if sudo /etc/init.d/datadog-agent info 2>/dev/null | grep -q "API Key is valid"; then
    echo "API key validation: OK"
  else
    echo "Warning: Could not confirm 'API Key is valid' from agent info." >&2
  fi

  if [ "$CONNECTIVITY_WARNING" = "false" ]; then
    echo "Connectivity test passed: no certificate verification errors detected."
  fi
  echo ""
  echo "Fresh logs are available at:"
  for log_file in $LOG_FILES; do
    if sudo test -f "$log_file"; then
      echo "  - $log_file"
    fi
  done
}

# ------------------- Distrusted-root scrub (-s) ---------------------
# The Agent package ships several CA bundles of its own (certifi, tornado,
# boto, httplib2, embedded OpenSSL, …). They are independent of the OS trust
# store, so an OS update cannot fix them and Agent v5 has no release vehicle.
# We delete the distrusted roots in place and guarantee the bundle still
# carries the anchor the Datadog intake chain terminates in — removing the
# cross-signer without that anchor would break the Agent.
#
# The anchor is pinned by fingerprint. It is NOT "whatever $TARGET_FILE
# happens to contain": -c accepts an arbitrary file, and on EL5/6 the download
# may have fallen back to --insecure (see download_url), so an unpinned anchor
# would let a substituted or intercepted file become a trust anchor in every
# bundle in the install.
ANCHOR_SHA256="E793C9B02FD8AA13E21C31228ACCB08119643B749C898964B1746D46C3D4CBD2"

find_scrub_python() {
  # The Agent's OWN interpreter only. A host Python is deliberately not used:
  # EL5/6 ship 2.4, the scrub must not depend on the host toolchain, and a
  # host interpreter that merely imports the modules can still differ in
  # behaviour from the 2.7 the bundles were written by. -x alone is not
  # enough — confirm it runs here and is new enough for
  # os.walk(followlinks=...) (Python 2.6+).
  for cand in "$AGENT_ROOT/embedded/bin/python" "$AGENT_ROOT/embedded/bin/python2.7"; do
    if [ -x "$cand" ] && "$cand" -c "import hashlib, base64, os, sys; sys.exit(0 if sys.version_info[:2] >= (2,6) else 1)" >/dev/null 2>&1; then
      echo "$cand"
      return 0
    fi
  done
  return 1
}

# Failures here are deliberately non-fatal: the certificate rotation is the
# primary remediation and must still complete (see ca3e4d80).
scrub_ca_bundles() {
  if [ "$DO_SCRUB" != "true" ]; then
    return 0
  fi

  local scrub_py
  AGENT_ROOT=$(dirname "$TARGET_DIR")
  echo ""
  echo "=== Removing distrusted roots from the Agent's bundled CA stores ==="

  # Guard against -p pointing somewhere that is not an Agent install: the walk
  # root is the parent of the certificate directory, so a mistaken -p would
  # otherwise rewrite bundles belonging to unrelated software.
  if [ ! -d "$AGENT_ROOT/embedded" ]; then
    echo "  Warning: $AGENT_ROOT does not look like an Agent installation" \
         "(no embedded/ directory); skipping the scrub." >&2
    echo "  If your Agent lives elsewhere, pass -p <install-dir>/agent." >&2
    SCRUB_WARNING=true
    return 0
  fi

  scrub_py=$(find_scrub_python) || {
    echo "  Warning: the Agent's embedded Python was not found under" \
         "$AGENT_ROOT/embedded/bin; skipping the scrub." >&2
    echo "  The certificate update below is unaffected." >&2
    SCRUB_WARNING=true
    return 0
  }
  echo "Using interpreter: $scrub_py"

  if [ "$SCRUB_DRYRUN" = "true" ]; then
    echo "Dry run: reporting only, no bundle will be written."
  fi

  # The program below is inline on purpose: the runbook is distributed as a
  # single file customers curl down (see README), and EL5/6 and air-gapped
  # hosts must not need a second fetch. tests/test_scrub_bundles.sh extracts
  # this same heredoc and exercises it against fixtures.
  if ! sudo "$scrub_py" - "$AGENT_ROOT" "$TARGET_FILE" "$ANCHOR_SHA256" "$SCRUB_DRYRUN" <<'PYSCRUB'
import base64, hashlib, os, re, shutil, sys, tempfile, time

# Distrusted following the eMudhra intermediate CA key compromise. The six TLS
# intermediates are cross-signed by Sectigo's "AAA Certificate Services", so
# that root has to go too or the cross-signed path still validates.
DISTRUST = {
    "D7A7A0FB5D7E2731D771E9484EBCDEF71D5F0C3E0A2948782BC83EE0EA699EF4": "AAA Certificate Services",
    "40F6AF0346A99AA1CD1D555A4E9CCE62C7F9634603EE406615833DC8C8D00367": "emSign Root CA - G1",
    "86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B": "emSign ECC Root CA - G3",
    "125609AA301DA0A249B97A8239CB6A34216F44DCAC9F3954B14292F2E8C8608F": "emSign Root CA - C1",
    "BC4D809B15189D78DB3E1D8CF4F9726A795DA1643CA5F1358E1DDB0EDC0D7EB3": "emSign ECC Root CA - C3",
}
BUNDLE_NAMES = ("cacert.pem", "ca-certificates.crt", "cacerts.txt")
BLOCK = re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.S)
MIN_PARSED = 10   # below this we do not treat the file as a trust store

agent_root, anchor_path, expected_fp = sys.argv[1], sys.argv[2], sys.argv[3]
dry_run = (len(sys.argv) > 4 and sys.argv[4] == "true")
agent_real = os.path.realpath(agent_root)

def fingerprint(block):
    body = "".join(l.strip() for l in block.splitlines()[1:-1])
    try:
        return hashlib.sha256(base64.b64decode(body)).hexdigest().upper()
    except Exception:
        return None

try:
    anchor_text = open(anchor_path, "rb").read().decode("ascii", "ignore")
except Exception:
    sys.stderr.write("cannot read %s\n" % anchor_path)
    sys.exit(2)
anchor_blocks = BLOCK.findall(anchor_text)
if not anchor_blocks:
    sys.stderr.write("no certificate found in %s\n" % anchor_path)
    sys.exit(2)
anchor_pem = anchor_blocks[0]
anchor_fp = fingerprint(anchor_pem)

# Pinned: refuse to append anything but the expected anchor.
if anchor_fp != expected_fp:
    sys.stderr.write(
        "%s is not the expected trust anchor\n"
        "  expected SHA-256 %s\n"
        "  found    SHA-256 %s\n"
        "  Refusing to modify any CA bundle.\n"
        % (anchor_path, expected_fp, anchor_fp))
    sys.exit(2)

stamp = time.strftime("%Y%m%d%H%M%S")
changed = 0
found = 0
skipped = []

def note(path, reason):
    skipped.append((path, reason))

def on_walk_error(err):
    note(getattr(err, "filename", agent_root), "could not be traversed (%s)" % err.strerror)

# os.walk does not follow directory symlinks by default - keep it that way so
# the scrub can never leave the Agent installation directory.
for dirpath, _dirnames, filenames in os.walk(agent_root, followlinks=False, onerror=on_walk_error):
    for name in sorted(filenames):
        if name not in BUNDLE_NAMES:
            continue
        path = os.path.join(dirpath, name)
        found += 1

        # Never rewrite a symlink. Writing through it could modify a file
        # outside the Agent install, and replacing it would silently discard a
        # deliberate link (e.g. an admin pointing a bundle at the OS store).
        if os.path.islink(path):
            note(path, "symlink -> %s" % os.path.realpath(path))
            continue
        if not os.path.realpath(path).startswith(agent_real + os.sep):
            note(path, "resolves outside the Agent install")
            continue

        try:
            # latin-1 maps every byte to one code point, so non-ASCII comment
            # text (accented CA names in the "# Label:" lines) round-trips
            # byte-for-byte. PEM bodies are ASCII either way.
            text = open(path, "rb").read().decode("latin-1")
        except Exception:
            note(path, "not readable")
            continue

        matches = list(BLOCK.finditer(text))
        if not matches:
            continue
        if len(matches) < MIN_PARSED:
            note(path, "only %d certificate(s) - not treated as a trust store" % len(matches))
            continue

        removed = []
        cut = []
        seen = set()
        for m in matches:
            fp = fingerprint(m.group(0))
            if fp in DISTRUST:
                removed.append(DISTRUST[fp])
                cut.append(m.span())
            else:
                seen.add(fp)

        added = anchor_fp not in seen
        if not removed and not added:
            continue

        # Splice out only the distrusted spans so comments, labels and any
        # other non-CERTIFICATE content survive byte-for-byte.
        out, prev = [], 0
        for a, b in cut:
            out.append(text[prev:a])
            prev = b
            while prev < len(text) and text[prev] == "\n":
                prev += 1
        out.append(text[prev:])
        new_text = "".join(out)
        if added:
            if new_text and not new_text.endswith("\n"):
                new_text += "\n"
            new_text += anchor_pem + "\n"

        # Real pre-write validation against the bytes we are about to commit.
        check = BLOCK.findall(new_text)
        check_fps = set(fingerprint(b) for b in check)
        if len(check) != len(matches) - len(removed) + (1 if added else 0):
            note(path, "post-edit certificate count unexpected"); continue
        if check_fps & set(DISTRUST):
            note(path, "a distrusted root survived the edit"); continue
        if anchor_fp not in check_fps:
            note(path, "anchor missing after the edit"); continue

        if dry_run:
            changed += 1
            print("  %s" % path)
            print("    would change %d -> %d certs | would remove: %s%s"
                  % (len(matches), len(check),
                     ", ".join(removed) if removed else "none",
                     " | would append anchor" if added else ""))
            continue

        backup = "%s.pre-cert-update-%s" % (path, stamp)
        tmp = None
        try:
            st = os.stat(path)
            shutil.copy2(path, backup)
            try:
                os.chown(backup, st.st_uid, st.st_gid)
            except Exception:
                pass          # not privileged enough; contents still recoverable
            fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=name + ".", suffix=".tmp")
            handle = os.fdopen(fd, "wb")
            handle.write(new_text.encode("latin-1"))
            handle.flush()
            os.fsync(handle.fileno())
            handle.close()
            shutil.copymode(path, tmp)
            try:
                os.chown(tmp, st.st_uid, st.st_gid)
            except Exception:
                pass          # not privileged enough; mode still carried over
            os.rename(tmp, path)
            tmp = None
        except Exception:
            for leftover in (tmp, backup):
                if leftover and os.path.exists(leftover):
                    try:
                        os.unlink(leftover)
                    except Exception:
                        pass
            note(path, "could not be rewritten - left untouched")
            continue
        changed += 1

        print("  %s" % path)
        print("    %d -> %d certs | removed: %s%s"
              % (len(matches), len(check),
                 ", ".join(removed) if removed else "none",
                 " | anchor appended" if added else ""))
        print("    backup: %s" % backup)

for path, reason in skipped:
    print("  SKIPPED %s" % path)
    print("    %s - left untouched" % reason)

if found == 0:
    print("  No CA bundles found under %s." % agent_root)
elif changed == 0:
    print("  No changes needed - bundles already clean.")
elif dry_run:
    print("  %d bundle(s) would be updated. Re-run without -n to apply." % changed)
else:
    print("  %d bundle(s) updated." % changed)
if skipped:
    print("  %d bundle(s) skipped (listed above); review them by hand." % len(skipped))
PYSCRUB
  then
    echo "  Warning: the CA bundle scrub did not complete." >&2
    echo "  The certificate update below is unaffected." >&2
    SCRUB_WARNING=true
  fi
}

main() {
  detect_os_version
  check_downloader
  ensure_target_directory
  if [ -n "$LOCAL_CERT_FILE" ]; then
    install_local_certificate
  else
    download_certificate
  fi
  verify_certificate
  scrub_ca_bundles
  update_datadog_config
  rotate_logs
  restart_agent
  test_connectivity_since_restart

  echo ""
  echo "=============================="
  if [ "$CONNECTIVITY_WARNING" = "true" ]; then
    echo "DONE — certificate replaced, but connectivity could not be fully verified automatically."
    echo ""
    echo "The Datadog certificate has been installed at: $TARGET_FILE"
    echo "The Agent configuration has been updated and the Agent has been restarted."
    echo ""
    echo "Please verify connectivity manually:"
    echo "  sudo service datadog-agent status"
    echo "  sudo /etc/init.d/datadog-agent info"
    echo "  Check logs for SSL errors:"
    for log_file in $LOG_FILES; do
      echo "    $log_file"
    done
    echo ""
    echo "If SSL errors persist, contact support with the log output above."
  else
    echo "DONE — certificate replaced and connectivity verified successfully."
    echo ""
    echo "The Datadog certificate has been installed at: $TARGET_FILE"
    echo "The Agent configuration has been updated, the Agent has been restarted,"
    echo "and no SSL/certificate errors were detected in the logs."
  fi
  if [ "$DO_SCRUB" = "true" ]; then
    echo ""
    if [ "$SCRUB_DRYRUN" = "true" ]; then
      echo "Dry run only: no CA bundle was modified."
    elif [ "$SCRUB_WARNING" = "true" ]; then
      echo "The CA bundle scrub did NOT complete - see the warnings above."
      echo "The certificate update itself succeeded; re-run with -s once the"
      echo "cause is resolved, or remediate the bundles by hand."
    else
      echo "Distrusted roots were also removed from the Agent's bundled CA stores."
      echo "Each modified bundle was backed up alongside itself as"
      echo "  <bundle>.pre-cert-update-<timestamp>"
    fi
  fi
  echo "=============================="
}

main
