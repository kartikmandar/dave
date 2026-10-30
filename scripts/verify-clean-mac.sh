#!/bin/sh
# Read-only diagnostics for a manually installed app. No developer tools required.
set -eu
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
app=${1:-/Applications/DAVE.app}
output=${2:-./DAVE-clean-mac-evidence}
if [ ! -d "$app/Contents" ]; then
  echo "Usage: sh verify-clean-mac.sh /Applications/DAVE.app /path/to/evidence" >&2
  exit 2
fi
app=$(cd "$app" && pwd -P)
if [ -d "$output" ]; then
  output=$(cd "$output" && pwd -P)
else
  parent=$(cd "$(dirname "$output")" && pwd -P)
  output="$parent/$(basename "$output")"
fi
case "$output/" in
  "$app/"*) echo 'Evidence directory must be outside the signed app' >&2; exit 2 ;;
esac
mkdir -p "$output"
report="$output/diagnostics.txt"
failures=0
{
  echo "DAVE 2.0.0 clean-Mac diagnostics (manual test evidence required separately)"
  date -u '+UTC: %Y-%m-%dT%H:%M:%SZ'
  sw_vers
  uname -m
  echo "App: $app"
} > "$report"
if [ "$(uname -m)" != arm64 ]; then
  echo 'FAIL: this candidate is for Apple Silicon' >> "$report"
  failures=$((failures + 1))
fi
version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$app/Contents/Info.plist")
identifier=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$app/Contents/Info.plist")
if [ "$version" != 2.0.0 ] || [ "$identifier" != science.stingray.dave ]; then
  echo "FAIL: unexpected app version or identifier: $version / $identifier" >> "$report"
  failures=$((failures + 1))
fi
if ! codesign --verify --deep --strict "$app" >> "$report" 2>&1; then
  failures=$((failures + 1))
fi
codesign -d --verbose=4 "$app" >> "$report" 2>&1
if ! grep -q '^TeamIdentifier=BQN364P8SY$' "$report" ||
   ! grep -q '^CDHash=e23b4f6d1700d628f1540257d24afa78f37a1531$' "$report"; then
  echo 'FAIL: signed app does not match the reviewed candidate' >> "$report"
  failures=$((failures + 1))
fi
if ! spctl --assess --type execute --verbose=2 "$app" >> "$report" 2>&1; then
  failures=$((failures + 1))
fi
if ! grep -q 'source=Notarized Developer ID' "$report"; then
  echo 'FAIL: no notarized Developer ID assessment' >> "$report"
  failures=$((failures + 1))
fi
if ! xattr -p com.apple.quarantine "$app" > "$output/quarantine.txt" 2>&1; then
  echo 'INCOMPLETE: quarantine evidence missing; use a real browser download on the clean test Mac' >> "$report"
  failures=$((failures + 1))
fi
echo "Diagnostic failures/incomplete checks: $failures" >> "$report"
echo 'These diagnostics alone do not certify a clean Mac, Finder launch, or the scientific workflow.' >> "$report"
cat "$report"
[ "$failures" -eq 0 ]
