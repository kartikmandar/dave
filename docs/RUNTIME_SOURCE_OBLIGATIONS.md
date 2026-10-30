# Bundled runtime notices, sources and modification rights

DAVE includes GNU libiconv 1.18 and libcharset under LGPL-2.1, GNU Readline 8.3
under GPL-3.0, and GCC runtime libraries under GPL-3.0 with the GCC Runtime Library
Exception 3.1. These licenses apply to those components, independently of DAVE's
Apache-2.0 license. Python's Readline extension links to GNU Readline. Python's
PSF notices and the GPL terms for the linked Readline component accompany it.
FreeType is distributed under its FreeType License option. Electron additionally
includes FFmpeg under LGPL-2.1-or-later and WebKit-derived Blink files under their
file-specific BSD/LGPL-2.0/2.1 terms. Those engine/media obligations are included
in this review, independently of the conda package inventory.

The full copyright notices and licenses are in THIRD_PARTY_NOTICES inside the app
and beside it in the distribution ZIP. GNU libiconv copyright belongs to the
Free Software Foundation, Inc.; the exact year ranges and individual attributions
are retained in its source files and COPYING.LIB. GNU Readline copyright and GPL
terms are retained in its source files and COPYING. No DAVE term restricts your
right to modify these components for your own use or to reverse engineer the
combined work to debug modifications to the LGPL components.

## Corresponding source and continuing availability

DAVE-2.0.0-RUNTIME-SOURCES.tar.gz is provided alongside the binary from the same
GitHub Release, without an additional charge or an account restriction beyond
that applying to the binary. Keep that source asset available for as long as the
binary is offered; retain the exact source asset with any redistributed binary.
This is direct source distribution, not a promise to send source on request.

The source companion includes exact, SHA-256-verified upstream sources for
Readline, libiconv/libcharset, Python and ncurses, plus the GCC runtime build
sources and zlib. It includes the exact conda-forge build recipes, declared
patches, build configuration, scripts and source manifests. Python and ncurses
sources accompany the Readline-linked Python extension. DAVE's source snapshot,
dependency lock, relocation and packaging scripts are included as well; see its
recorded source commit and file hashes. The electron-chromium directory contains exact
FFmpeg and Blink product source archives, the full Electron source archive with
its FFmpeg patch, Chromium GN/build files, the applicable macOS arm64 FFmpeg
configurations, and complete dependency pins. It also supplies Mozilla-derived
URL/certificate sources conservatively. Electron is 43.8.4 (21d45d34fab5df606a08487790f691b4f4911e65),
Chromium is 150.0.7871.250 (f916f1b7136907af19d96b95b891533d091d932a),
and FFmpeg is ad41607c61898cf7150e0fb20fe4bbabd44922a3. Both macOS arm64
FFmpeg configurations disable GPL, nonfree and version-3 build flags. Full
licenses and source headers remain intact. Non-product Blink manual/performance/
web-test fixtures are omitted; renderer/public/common/tools sources are supplied. Machine-specific caches, credentials,
private signing material and user workspaces are excluded.

Conda-forge supplied the native binaries. DAVE changes native load paths to make
the runtime relocatable and signs the final app. The source companion includes
the scripts for those transformations. It does not claim a byte-for-byte
independent rebuild of every scientific dependency. Developer ID credentials
are not required to build or run a local modified copy.

## LGPL shared-library replacement

libiconv/libcharset remain separate dynamically loaded libraries. DAVE uses the
LGPL-2.1 section 6(b) shared-library mechanism, with the library source also supplied
under section 4. Recipient changes must retain the compatible ABI and install
names. The replacement helper creates a new private app copy and never changes
the official app:

```sh
python3 scripts/replace-runtime-library.py \
  --app /Applications/DAVE.app \
  --library /path/to/modified/libiconv.2.dylib \
  --output "$HOME/Applications/DAVE-modified.app"
```

Use the source companion's libiconv recipe and utf_8_mac.patch to build an
interface-compatible replacement. Its build configuration enables extra encodings.
The helper signs the replacement, private Python interpreter and outer app ad hoc,
so the modified library can load without Kartik Mandar's signing key. Its local
signature is deliberately distinct from the official Developer ID identity.
Changes invalidate the official notarization seal; they do not turn the modified
copy into an official DAVE distribution. Keep the official app for the separate
clean-Mac Gatekeeper test. Do not remove quarantine or disable Gatekeeper as part
of that acceptance test.

The release review records the actual replacement build and execution checks.
This document describes the engineering disposition of the stated obligations;
it does not change any upstream license or certify an untested platform.

Primary license texts: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html,
https://www.gnu.org/licenses/gpl-3.0.html and
https://www.gnu.org/licenses/gcc-exception-3.1.html.


## Electron/Chromium shared-library replacement

FFmpeg is a separate libffmpeg.dylib; Blink facilities reside in the shared
Electron Framework. Compatible replacement of either library is permitted.
scripts/replace-electron-library.py creates a fresh private app copy and locally
signs the replacement, framework, every loading Electron helper and outer app.
Signing helpers is necessary: leaving their Developer ID library validation
unchanged rejects the recipient's new library. The publisher key is not needed.

A recipient-built compatible replacement/re-export shim for each library was
compiled and installed in a private copy. Both constructors were observed during
real app startup, and the complete scientific/export/workspace workflow passed
in 25.0 seconds. This demonstrates the shared-library replacement mechanism; it
is not a claim that the complete Chromium engine was independently rebuilt.
The independent libiconv source rebuild is separate evidence described above.
See ELECTRON_SOURCE_REBUILD.md for exact source pins, build instructions and
replacement commands. The official engine/media binaries are unchanged.
