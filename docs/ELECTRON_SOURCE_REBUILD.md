# Electron/Chromium source and replacement instructions

The source companion's electron-chromium/source-manifest.json records the actual
Electron 43.8.4 source commit 21d45d34fab5df606a08487790f691b4f4911e65,
Chromium 150.0.7871.250 commit f916f1b7136907af19d96b95b891533d091d932a,
and FFmpeg revision ad41607c61898cf7150e0fb20fe4bbabd44922a3. Archives are obtained
from the projects' official servers at those immutable revisions and hash-checked
on cache reuse. The manifest records their SHA-256 values and exact URLs.

The full Electron source archive includes its patch series, build arguments,
DEPS and build scripts. Its FFmpeg patch link_with_loader_path.patch is retained.
FFmpeg source includes BUILD.gn, Chromium scripts and both Chrome/Chromium macOS
arm64 configuration headers, whose GPL/NONFREE/VERSION3 options are all disabled.
The complete Blink renderer/public/common/tools product sources and its root
license/DEPS are supplied; non-product manual/performance/web-test trees are omitted.
Chromium GN/build files, the full Chromium DEPS and conservative Mozilla-derived
URL/certificate source are included. File-specific copyrights/licenses remain.
Additional permissive dependencies for a full engine build are pinned in DEPS;
no claim of an independently compiled full Chromium build is made.

Use Apple's Command Line Tools and the build prerequisites documented in the
supplied Electron source, docs/development/build-instructions-gn.md and
build-instructions-macos.md. With depot_tools installed, create a fresh checkout:

```sh
mkdir electron-source
cd electron-source
gclient config --name src/electron --unmanaged https://github.com/electron/electron
gclient sync --with_branch_heads --with_tags --revision src/electron@21d45d34fab5df606a08487790f691b4f4911e65
cd src
gn gen out/Release --args='import("//electron/build/args/release.gn") target_cpu="arm64"'
ninja -C out/Release electron
```

Verify the resolved Chromium/FFmpeg pins against the manifest. Electron's hooks
apply its supplied patches. The archives may be unpacked into the matching
checkout paths to provide the LGPL product sources locally. Consult the exact
source's build instructions if the host toolchain differs. Building the complete
engine requires substantial resources; these commands are a reproducible source
route, not a recorded complete-engine build result.

To install a locally built interface-compatible library, use the DAVE source
snapshot's scripts/replace-electron-library.py. The input's filename must be
libffmpeg.dylib or Electron Framework, respectively. For example:

```sh
python3 scripts/replace-electron-library.py \
  --app /Applications/DAVE.app \
  --library /path/to/built/libffmpeg.dylib \
  --output "$HOME/Applications/DAVE-media-modified.app"
```

The helper creates a private copy and signs the replacement, framework, loading
helpers and outer app ad hoc, preserving required entitlements. It needs no
publisher key, does not alter the official app, does not remove quarantine and
does not disable Gatekeeper. Modified copies do not retain the official
Developer ID/notarization identity. Keep the official app for clean-Mac acceptance.
A compatible replacement must retain the original ABI and install-name/dependency
layout; the supplied sources and configuration support building that interface.

In the recorded mechanism test, recipient-compiled compatible re-export shims for
FFmpeg and the Electron Framework were installed in a private app copy. Both
constructors wrote observable startup markers. Initially unchanged Developer ID
helper signatures rejected the replacements; locally signing all loading helpers
resolved that requirement. The full import/light-curve/PDS/CSV/PNG/PDF/workspace
workflow then passed in 25.0 seconds. This proves replacement operation, not an
independent rebuild of the full engine. The official engine/media binaries are
unchanged. The libiconv independent source rebuild is separately recorded.

The Chromium credits cover multiple platforms. Android/Windows/Linux-only LGPL
entries are not silently treated as Mac libraries. FFmpeg and WebKit-derived Blink
are included conservatively because their code actually ships. Mac hyphenation
uses CoreFoundation; no .hyb/.bdic/.jar/Linux .so payloads are in this app. The
app's full Chromium license/attribution document is preserved regardless of this
platform classification. Re-review when the Electron version or shipped payloads change.
