#!/bin/sh
# Fixture tests for the CA-bundle scrub embedded in linux.sh.
#
# The scrub program is a heredoc inside linux.sh so the runbook stays a single
# file customers can curl (see README). This harness extracts that same
# heredoc and exercises it directly, so the shipped code is what gets tested.
#
#   sh tests/test_scrub_bundles.sh [python]
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
SCRIPT="$HERE/../linux.sh"
PY="${1:-python3}"

# Fixture generation needs openssl. Prefer the Agent's own, for the same
# reason the scrub does: a minimal Agent 5 host may have no host openssl,
# and EL5's is ancient.
OPENSSL=""
for cand in /opt/datadog-agent/embedded/bin/openssl openssl; do
  if command -v "$cand" >/dev/null 2>&1; then OPENSSL="$cand"; break; fi
done
if [ -z "$OPENSSL" ]; then
  echo "SKIP: no openssl found (looked for /opt/datadog-agent/embedded/bin/openssl, openssl)" >&2
  echo "      fixture generation needs one; pass a host with openssl to run these tests." >&2
  exit 77
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

PASS=0
FAIL=0
check() { # check <label> <expected-substring> <file>
  if grep -qF "$2" "$3"; then
    PASS=$((PASS+1)); echo "  ok    $1"
  else
    FAIL=$((FAIL+1)); echo "  FAIL  $1 (expected: $2)"; sed 's/^/        /' "$3"
  fi
}
refute() {
  if grep -qF "$2" "$3"; then
    FAIL=$((FAIL+1)); echo "  FAIL  $1 (unexpected: $2)"
  else
    PASS=$((PASS+1)); echo "  ok    $1"
  fi
}

# Extract the heredoc body between the PYSCRUB markers.
sed -n "/<<'PYSCRUB'/,/^PYSCRUB$/p" "$SCRIPT" | sed '1d;$d' > "$WORK/scrub.py"
test -s "$WORK/scrub.py" || { echo "could not extract the scrub program"; exit 1; }

# Python 2 rejects non-ASCII source bytes without a coding declaration, while
# python3 accepts them -- so a stray em dash in a comment breaks only the
# interpreter this actually ships on. Fail here rather than on a customer host.
if LC_ALL=C grep -q '[^[:print:][:space:]]' "$WORK/scrub.py"; then
  echo "  FAIL  inline scrub program contains non-ASCII bytes (breaks Python 2)" >&2
  LC_ALL=C grep -n '[^[:print:][:space:]]' "$WORK/scrub.py" | head -3 >&2
  exit 1
fi

ANCHOR_FP="E793C9B02FD8AA13E21C31228ACCB08119643B749C898964B1746D46C3D4CBD2"

# The anchor is the repo's own datadog-cert.pem; AAA comes from the Agent
# bundle if present, otherwise the test skips the removal cases.
cp "$HERE/../../../datadog-cert.pem" "$WORK/anchor.pem"

make_filler() { # make_filler <n> <out>  — n self-signed certs
  : > "$2"
  i=0
  while [ "$i" -lt "$1" ]; do
    "$OPENSSL" req -x509 -newkey rsa:1024 -keyout /dev/null -nodes \
      -subj "/CN=filler$i" -days 2 -out "$WORK/f.pem" 2>/dev/null
    printf '# Label: "filler%s"\n' "$i" >> "$2"
    cat "$WORK/f.pem" >> "$2"
    i=$((i+1))
  done
}

echo "scrub fixture tests ($PY)"

# --- case 1: anchor pin rejects a wrong anchor, nothing is written ---------
mkdir -p "$WORK/a1/embedded"
make_filler 12 "$WORK/a1/embedded/cacert.pem"
cp "$WORK/a1/embedded/cacert.pem" "$WORK/a1.before"
"$OPENSSL" req -x509 -newkey rsa:1024 -keyout /dev/null -nodes -subj "/CN=wrong" -days 2 \
  -out "$WORK/wrong.pem" 2>/dev/null
set +e
"$PY" "$WORK/scrub.py" "$WORK/a1" "$WORK/wrong.pem" "$ANCHOR_FP" false > "$WORK/o1" 2>&1
rc=$?
set -e
check "anchor pin: refuses a non-anchor cert" "not the expected trust anchor" "$WORK/o1"
[ "$rc" -ne 0 ] && { PASS=$((PASS+1)); echo "  ok    anchor pin: exits non-zero"; } \
                || { FAIL=$((FAIL+1)); echo "  FAIL  anchor pin: should exit non-zero"; }
cmp -s "$WORK/a1.before" "$WORK/a1/embedded/cacert.pem" \
  && { PASS=$((PASS+1)); echo "  ok    anchor pin: bundle untouched"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  anchor pin: bundle was modified"; }

# --- case 2: sub-threshold bundle is reported, not silently skipped -------
mkdir -p "$WORK/a2/embedded"
make_filler 3 "$WORK/a2/embedded/cacert.pem"
"$PY" "$WORK/scrub.py" "$WORK/a2" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o2" 2>&1
check "sub-threshold: reported as skipped" "not treated as a trust store" "$WORK/o2"

# --- case 3: anchor appended, comments preserved, idempotent --------------
mkdir -p "$WORK/a3/embedded"
make_filler 12 "$WORK/a3/embedded/cacert.pem"
before_comments=$(grep -c '^# Label:' "$WORK/a3/embedded/cacert.pem")
"$PY" "$WORK/scrub.py" "$WORK/a3" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o3" 2>&1
check "append: anchor added when absent" "anchor appended" "$WORK/o3"
after_comments=$(grep -c '^# Label:' "$WORK/a3/embedded/cacert.pem")
[ "$before_comments" = "$after_comments" ] \
  && { PASS=$((PASS+1)); echo "  ok    append: comments preserved ($after_comments)"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  append: comments lost ($before_comments -> $after_comments)"; }
"$PY" "$WORK/scrub.py" "$WORK/a3" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o3b" 2>&1
check "idempotency: second run is a no-op" "No changes needed" "$WORK/o3b"

# --- case 4: dry run writes nothing ---------------------------------------
mkdir -p "$WORK/a4/embedded"
make_filler 12 "$WORK/a4/embedded/cacert.pem"
cp "$WORK/a4/embedded/cacert.pem" "$WORK/a4.before"
"$PY" "$WORK/scrub.py" "$WORK/a4" "$WORK/anchor.pem" "$ANCHOR_FP" true > "$WORK/o4" 2>&1
check "dry run: reports intent" "would change" "$WORK/o4"
cmp -s "$WORK/a4.before" "$WORK/a4/embedded/cacert.pem" \
  && { PASS=$((PASS+1)); echo "  ok    dry run: bundle untouched"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  dry run: bundle was modified"; }

# --- case 5: symlinks are skipped, never followed -------------------------
mkdir -p "$WORK/a5/embedded"
make_filler 12 "$WORK/outside.pem"
cp "$WORK/outside.pem" "$WORK/outside.before"
ln -s "$WORK/outside.pem" "$WORK/a5/embedded/cacert.pem"
"$PY" "$WORK/scrub.py" "$WORK/a5" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o5" 2>&1
check "symlink: reported as skipped" "symlink ->" "$WORK/o5"
cmp -s "$WORK/outside.before" "$WORK/outside.pem" \
  && { PASS=$((PASS+1)); echo "  ok    symlink: target outside the root untouched"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  symlink: wrote outside the root"; }

# --- case 6: no bundles at all --------------------------------------------
mkdir -p "$WORK/a6/embedded"
"$PY" "$WORK/scrub.py" "$WORK/a6" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o6" 2>&1
check "empty install: distinct message" "No CA bundles found" "$WORK/o6"

# --- case 8: a damaged anchor is rejected, never silently repaired -------
mkdir -p "$WORK/a8/embedded"
make_filler 12 "$WORK/a8/embedded/cacert.pem"
cp "$WORK/a8/embedded/cacert.pem" "$WORK/a8.before"
# inject stray non-ASCII bytes into the anchor's base64 body
"$PY" - "$WORK/anchor.pem" "$WORK/anchor-damaged.pem" <<'PYEOF'
import sys
d = open(sys.argv[1], "rb").read()
i = d.index(b"\n", d.index(b"-----BEGIN")) + 20
open(sys.argv[2], "wb").write(d[:i] + b"\xc3\xa9" + d[i:])
PYEOF
set +e
"$PY" "$WORK/scrub.py" "$WORK/a8" "$WORK/anchor-damaged.pem" "$ANCHOR_FP" false > "$WORK/o8" 2>&1
rc8=$?
set -e
check "damaged anchor: rejected" "not the expected trust anchor" "$WORK/o8"
[ "$rc8" -ne 0 ] && { PASS=$((PASS+1)); echo "  ok    damaged anchor: exits non-zero"; }                  || { FAIL=$((FAIL+1)); echo "  FAIL  damaged anchor: should exit non-zero"; }
cmp -s "$WORK/a8.before" "$WORK/a8/embedded/cacert.pem" \
  && { PASS=$((PASS+1)); echo "  ok    damaged anchor: bundle untouched"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  damaged anchor: bundle was modified"; }

# --- case 7: non-ASCII comment bytes survive byte-for-byte ---------------
mkdir -p "$WORK/a7/embedded"
printf '# Label: "NetLock Arany (Class Gold) F\305\221tan\303\272s\303\255tv\303\241ny"\n' \
  > "$WORK/a7/embedded/cacert.pem"
make_filler 12 "$WORK/a7.filler"
cat "$WORK/a7.filler" >> "$WORK/a7/embedded/cacert.pem"
cp "$WORK/a7/embedded/cacert.pem" "$WORK/a7.before"
"$PY" "$WORK/scrub.py" "$WORK/a7" "$WORK/anchor.pem" "$ANCHOR_FP" false > "$WORK/o7" 2>&1
check "non-ASCII: bundle rewritten" "anchor appended" "$WORK/o7"
# Only the anchor is appended, so the original bytes must be an exact prefix.
head -c "$(wc -c < "$WORK/a7.before")" "$WORK/a7/embedded/cacert.pem" | cmp -s - "$WORK/a7.before" \
  && { PASS=$((PASS+1)); echo "  ok    non-ASCII: comment bytes preserved"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL  non-ASCII: comment bytes altered"; }

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
