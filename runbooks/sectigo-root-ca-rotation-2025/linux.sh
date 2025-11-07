#!/bin/bash
# Datadog Agent v5 runbook — checks only logs since this script's restart.
# Hardened: uses sudo where needed, avoids assoc arrays, robust log slicing.

# Parse command-line arguments
show_usage() {
  echo "Usage: $0 [-p <agent_directory>]"
  echo "  -p <agent_directory>  Custom Datadog Agent installation directory"
  echo "                        (default: /opt/datadog-agent/agent)"
  exit 1
}

# Parse arguments
while getopts "p:h" opt; do
  case $opt in
    p)
      ARG_AGENT_DIR="$OPTARG"
      ;;
    h)
      show_usage
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      show_usage
      ;;
  esac
done

# -------------------------- Configuration ---------------------------
URL="https://raw.githubusercontent.com/DataDog/dd-agent/master/datadog-cert.pem"

# CUSTOM INSTALLATION PATHS (optional)
# If you have a custom Datadog Agent installation, set these variables.
# Leave empty for auto-detection of standard paths.
# Command-line argument takes precedence.
CUSTOM_DD_AGENT_DIR="${ARG_AGENT_DIR:-}"
CUSTOM_DD_CONFIG_FILE=""
CUSTOM_DD_LOG_DIR=""

# Auto-detect or use custom paths
if [ -n "$CUSTOM_DD_AGENT_DIR" ]; then
  TARGET_DIR="$CUSTOM_DD_AGENT_DIR"
else
  TARGET_DIR="/opt/datadog-agent/agent"
fi

if [ -n "$CUSTOM_DD_CONFIG_FILE" ]; then
  CONF_FILE="$CUSTOM_DD_CONFIG_FILE"
else
  CONF_FILE="/etc/dd-agent/datadog.conf"
fi

if [ -n "$CUSTOM_DD_LOG_DIR" ]; then
  LOG_FILES="$CUSTOM_DD_LOG_DIR/forwarder.log $CUSTOM_DD_LOG_DIR/collector.log"
else
  LOG_FILES="/var/log/datadog/forwarder.log /var/log/datadog/collector.log"
fi

TARGET_FILE="${TARGET_DIR}/datadog-cert.pem"

DOWNLOADER=""
PRE_TS_UNIX=""
PRE_TS_READABLE=""

error_exit() {
  echo "$1" >&2
  echo "Please contact support for further help." >&2
  exit 1
}

check_downloader() {
  if command -v curl &>/dev/null; then
    DOWNLOADER="curl"
  elif command -v wget &>/dev/null; then
    DOWNLOADER="wget"
  else
    error_exit "Error: Neither curl nor wget found. Please install curl or wget and try again."
  fi
}

ensure_target_directory() {
  if ! sudo test -d "$TARGET_DIR"; then
    echo "Directory $TARGET_DIR does not exist. Creating it..."
    sudo mkdir -p "$TARGET_DIR" || error_exit "Error: Failed to create $TARGET_DIR."
    # Set ownership to dd-agent user if it exists (standard for Agent v5)
    if id dd-agent &>/dev/null; then
      echo "Setting directory ownership to dd-agent:dd-agent..."
      sudo chown dd-agent:dd-agent "$TARGET_DIR" || echo "Warning: Failed to set ownership, but continuing..."
    fi
  fi
}

download_certificate() {
  echo "Downloading the DataDog certificate using $DOWNLOADER..."
  if [ "$DOWNLOADER" = "curl" ]; then
    sudo curl -fsSL "$URL" -o "$TARGET_FILE" || error_exit "Error: Failed to download certificate with curl."
  else
    sudo wget -qO "$TARGET_FILE" "$URL" || error_exit "Error: Failed to download certificate with wget."
  fi
  echo "Certificate downloaded successfully to $TARGET_FILE."
  
  # Set proper ownership for the certificate file (readable by dd-agent user)
  if id dd-agent &>/dev/null; then
    echo "Setting certificate file ownership to dd-agent:dd-agent..."
    sudo chown dd-agent:dd-agent "$TARGET_FILE" || echo "Warning: Failed to set certificate ownership, but continuing..."
  fi
  # Ensure the file is readable
  sudo chmod 644 "$TARGET_FILE" || echo "Warning: Failed to set certificate permissions, but continuing..."
}

verify_certificate() {
  echo "Verifying the downloaded certificate..."
  local test_url
  test_url="https://app.datadoghq.com"
  
  if [ "$DOWNLOADER" = "curl" ]; then
    if sudo curl -fsSL --cacert "$TARGET_FILE" --connect-timeout 10 "$test_url" >/dev/null 2>&1; then
      echo "Certificate verification successful: can connect to Datadog."
    else
      error_exit "Error: Certificate verification failed. Cannot establish SSL connection to $test_url using the downloaded certificate."
    fi
  else
    if sudo wget --ca-certificate="$TARGET_FILE" --timeout=10 -q -O /dev/null "$test_url" 2>&1; then
      echo "Certificate verification successful: can connect to Datadog."
    else
      error_exit "Error: Certificate verification failed. Cannot establish SSL connection to $test_url using the downloaded certificate."
    fi
  fi
}

update_datadog_config() {
  if ! sudo test -f "$CONF_FILE"; then
    error_exit "Error: Configuration file $CONF_FILE not found."
  fi

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
      sudo cp "$f" "$backup" 2>/dev/null || echo "  Warning: Could not back up $f"
      # Truncate the log file so we start fresh
      sudo truncate -s 0 "$f" 2>/dev/null || echo "  Warning: Could not truncate $f"
    fi
  done
  PRE_TS_UNIX="$(date +%s)"
  PRE_TS_READABLE="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  echo "Restart timestamp: $PRE_TS_READABLE (epoch: $PRE_TS_UNIX)"
}

restart_agent() {
  echo "Restarting the DataDog Agent..."
  if ! sudo service datadog-agent restart; then
    error_exit "Error: Failed to restart the DataDog agent."
  fi
  echo "Waiting 30 seconds for the DataDog Agent to restart..."
  sleep 30
}

test_connectivity_since_restart() {
  echo "=== Connectivity test (since this restart) ==="
  local pattern
  pattern='CERTIFICATE_VERIFY_FAILED|certificate verify failed|ssl[[:space:][:punct:]]*error'

  # Check the fresh (rotated) log files
  for log_file in $LOG_FILES; do
    if sudo test -f "$log_file" && sudo test -s "$log_file"; then
      echo "  Checking $(basename "$log_file")..."
      if sudo grep -qiE "$pattern" "$log_file" 2>/dev/null; then
        echo ""
        echo "ERROR: Detected SSL/cert verification failure in $(basename "$log_file"):"
        sudo grep -iE "$pattern" "$log_file" | head -10
        error_exit "Certificate verification failed. Please review the log at: $log_file"
      fi
    fi
  done

  # Journald: only entries since restart
  if command -v journalctl >/dev/null 2>&1; then
    echo "  Checking journald logs..."
    # Prefer epoch form; fall back to a readable UTC timestamp if needed
    local SINCE_ARG
    SINCE_ARG="@${PRE_TS_UNIX}"
    if ! sudo journalctl --since "$SINCE_ARG" -n 0 &>/dev/null; then
      SINCE_ARG="$PRE_TS_READABLE"
    fi
    if sudo journalctl -u datadog-agent --since "$SINCE_ARG" --no-pager 2>/dev/null | grep -qiE "$pattern"; then
      error_exit "Detected SSL/cert verification failure in journald since restart."
    fi
  fi

  # Confirm API key
  echo "  Checking agent status..."
  if sudo /etc/init.d/datadog-agent info 2>/dev/null | grep -q "API Key is valid"; then
    echo "API key validation: OK"
  else
    echo "Warning: Could not confirm 'API Key is valid' from agent info." >&2
  fi

  echo "Connectivity test passed: no certificate verification errors detected."
  echo ""
  echo "Fresh logs are available at:"
  for log_file in $LOG_FILES; do
    if sudo test -f "$log_file"; then
      echo "  - $log_file"
    fi
  done
}

main() {
  check_downloader
  ensure_target_directory
  download_certificate
  verify_certificate
  update_datadog_config
  rotate_logs
  restart_agent
  test_connectivity_since_restart
}

main