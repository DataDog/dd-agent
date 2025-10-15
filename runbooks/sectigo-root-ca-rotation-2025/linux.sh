#!/bin/bash
# Datadog Agent v5 runbook — checks only logs since this script's restart.
# Hardened: uses sudo where needed, avoids assoc arrays, robust log slicing.

TARGET_DIR="/opt/datadog-agent/agent"
TARGET_FILE="${TARGET_DIR}/datadog-cert.pem"
URL="https://raw.githubusercontent.com/DataDog/dd-agent/master/datadog-cert.pem"
CONF_FILE="/etc/dd-agent/datadog.conf"
LOG_FILES="/var/log/datadog/forwarder.log /var/log/datadog/collector.log"

TEMP_INSTALLED=0
DOWNLOADER=""
OFFSETS_FILE="$(mktemp -t dd_offsets_XXXXXX)"
PRE_TS_UNIX=""
PRE_TS_READABLE=""
REMOVE_CMD=""

error_exit() {
  echo "$1" >&2
  echo "Please contact support for further help." >&2
  exit 1
}

install_curl() {
  echo "Neither curl nor wget found. Attempting to install curl temporarily..."
  if command -v apt-get &>/dev/null; then
    INSTALL_CMD="sudo apt-get update && sudo apt-get install -y curl"
    REMOVE_CMD="sudo apt-get remove -y curl"
  elif command -v yum &>/dev/null; then
    INSTALL_CMD="sudo yum install -y curl"
    REMOVE_CMD="sudo yum remove -y curl"
  elif command -v dnf &>/dev/null; then
    INSTALL_CMD="sudo dnf install -y curl"
    REMOVE_CMD="sudo dnf remove -y curl"
  else
    error_exit "Error: No supported package manager found to install curl. Please install curl or wget manually."
  fi
  if eval "$INSTALL_CMD"; then
    echo "Successfully installed curl."
    TEMP_INSTALLED=1
    DOWNLOADER="curl"
  else
    error_exit "Error: Failed to install curl."
  fi
}

check_downloader() {
  if command -v curl &>/dev/null; then
    DOWNLOADER="curl"
  elif command -v wget &>/dev/null; then
    DOWNLOADER="wget"
  else
    install_curl
  fi
}

ensure_target_directory() {
  if ! sudo test -d "$TARGET_DIR"; then
    echo "Directory $TARGET_DIR does not exist. Creating it..."
    sudo mkdir -p "$TARGET_DIR" || error_exit "Error: Failed to create $TARGET_DIR."
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
}

update_datadog_config() {
  if ! sudo test -f "$CONF_FILE"; then
    error_exit "Error: Configuration file $CONF_FILE not found."
  fi

  echo "Updating $CONF_FILE for use_curl_http_client..."
  if sudo grep -q '^[[:space:]]*use_curl_http_client' "$CONF_FILE"; then
    echo "Parameter 'use_curl_http_client' found. Setting its value to true..."
    sudo sed -i 's/^[[:space:]]*use_curl_http_client.*/use_curl_http_client: true/' "$CONF_FILE" \
      || error_exit "Error: Failed to update $CONF_FILE."
  else
    echo "Parameter 'use_curl_http_client' not found. Adding it with value true..."
    echo "use_curl_http_client: true" | sudo tee -a "$CONF_FILE" >/dev/null \
      || error_exit "Error: Failed to update $CONF_FILE."
  fi
  echo "Configuration file updated successfully."
}

record_pre_restart_state() {
  echo "Recording log offsets before restart..."
  : > "$OFFSETS_FILE"
  for f in $LOG_FILES; do
    if sudo test -f "$f"; then
      size="$(sudo stat -c%s "$f" 2>/dev/null || echo 0)"
      echo "$f:$size" >> "$OFFSETS_FILE"
    else
      echo "$f:-1" >> "$OFFSETS_FILE"
    fi
  done
  PRE_TS_UNIX="$(date +%s)"
  PRE_TS_READABLE="$(date -u '+%Y-%m-%d %H:%M:%S UTC')"
  echo "Pre-restart timestamp: $PRE_TS_READABLE (epoch: $PRE_TS_UNIX)"
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
  local pattern='CERTIFICATE_VERIFY_FAILED|certificate verify failed|ssl[[:space:][:punct:]]*error'

  # Scan only new bytes appended to each log since restart
  while IFS= read -r line; do
    log_file="${line%%:*}"
    pre_size="${line##*:}"
    if sudo test -f "$log_file"; then
      if [ "$pre_size" -ge 0 ]; then
        sudo tail -c "+$((pre_size+1))" "$log_file" 2>/dev/null | grep -qiE "$pattern" \
          && error_exit "Detected SSL/cert verification failure in $(basename "$log_file") since restart."
      else
        sudo tail -n 500 "$log_file" 2>/dev/null | grep -qiE "$pattern" \
          && error_exit "Detected SSL/cert verification failure in new $(basename "$log_file") since restart."
      fi
    fi
  done < "$OFFSETS_FILE"

  # Journald: only entries since PRE_TS
  if command -v journalctl >/dev/null 2>&1; then
    # Prefer epoch form; fall back to a readable UTC timestamp if needed
    local SINCE_ARG="@${PRE_TS_UNIX}"
    if ! sudo journalctl --since "$SINCE_ARG" -n 0 &>/dev/null; then
      SINCE_ARG="$PRE_TS_READABLE"
    fi
    sudo journalctl -u datadog-agent --since "$SINCE_ARG" --no-pager | grep -qiE "$pattern" \
      && error_exit "Detected SSL/cert verification failure in journald since restart."
  fi

  # Confirm API key
  if sudo /etc/init.d/datadog-agent info 2>/dev/null | grep -q "API Key is valid"; then
    echo "API key validation: OK"
  else
    echo "Warning: Could not confirm 'API Key is valid' from agent info." >&2
  fi

  echo "Connectivity test passed: no certificate verification errors since restart."
}

restore_environment() {
  rm -f "$OFFSETS_FILE" || true
  if [ "$TEMP_INSTALLED" -eq 1 ]; then
    echo "Restoring environment: Removing temporarily installed curl."
    if ! eval "$REMOVE_CMD"; then
      echo "Warning: Failed to remove curl. Please remove it manually if necessary." >&2
      echo "Please contact support for further help." >&2
    else
      echo "Temporarily installed curl has been removed."
    fi
  fi
}

main() {
  check_downloader
  ensure_target_directory
  download_certificate
  update_datadog_config
  record_pre_restart_state
  restart_agent
  test_connectivity_since_restart
  restore_environment
}

main