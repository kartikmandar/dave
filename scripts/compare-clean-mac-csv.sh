#!/bin/sh
# Compare an exported DAVE CSV against the independent reference; stock macOS awk.
set -eu
if [ "$#" -ne 2 ] || [ ! -s "$1" ] || [ ! -s "$2" ]; then
  echo "Usage: sh compare-clean-mac-csv.sh expected.csv actual-export.csv" >&2
  exit 2
fi
/usr/bin/awk -F, '
function absolute(x) { return x < 0 ? -x : x }
NR == FNR { rows++; columns=NF; for(i=1;i<=NF;i++) expected[FNR,i]=$i; next }
{
  actual++;
  if(NF < columns || NF > columns+1) { print "FAIL: column count at row " FNR; failed=1; next }
  for(i=1;i<=columns;i++) {
    gsub(/\r/, "", $i);
    if($i !~ /^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$/ || absolute(($i+0)-(expected[FNR,i]+0))>0.000001) {
      print "FAIL: numeric mismatch at row " FNR ", column " i; failed=1
    }
  }
}
END {
  if(actual != rows) { print "FAIL: row count " actual " expected " rows; failed=1 }
  if(!failed) print "PASS: " rows " rows match the independent reference within 1e-6";
  exit failed
}' "$1" "$2"
