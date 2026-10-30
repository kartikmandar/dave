# Rebuild and replace libiconv locally

This example uses macOS Command Line Tools (clang, make, gperf, patch) and Python
for DAVE's copy/re-sign helper. It does not need the publisher's signing key.
It is for a private modified copy, separate from the official Gatekeeper test.

Extract the source companion. In its source-manifest.json select the libiconv
1.18 archive and verify its SHA-256 against SHA256SUMS. The matching conda recipe
and utf_8_mac.patch are under recipes/libiconv-1.18-h23cfdf5_2/parent.
In a new build directory, extract the libiconv source and enter libiconv-1.18.
Apply that exact utf_8_mac.patch with patch -p1. Make your own compatible library
changes there. The release validation added an exported marker function and
successfully called it in the private copy; that test modification is not in the
official binary or upstream source archive.

```sh
./configure --prefix="$PWD/installed" --disable-static --disable-rpath --enable-extra-encodings
make -f Makefile.devel CC=clang lib/flags.h lib/aliases.h lib/canonical.h lib/canonical_local.h
make -j4
make install
```

The explicit table-generation targets incorporate the macOS encoding patch
without requiring regeneration of unrelated autotools files. The full original
conda recipe remains supplied for its exact build environment and flags.

Use installed/lib/libiconv.2.dylib with scripts/replace-runtime-library.py from
the accompanying DAVE source snapshot. The helper refuses an existing destination,
an unrelated library or an output inside the official app. It creates a private
copy and locally signs changed code so an ABI-compatible replacement can load.
It does not remove quarantine, disable Gatekeeper or restore notarization.

In the release validation, the modified library's exported marker was observed
from the private bundled Python; Readline also imported, and the complete DAVE
Electron import/light-curve/PDS/PNG/PDF/CSV/workspace workflow passed in 42.0 s.
That is evidence for this library/build/platform, not an independent rebuild of
all third-party scientific dependencies. See replacement-validation.json.
