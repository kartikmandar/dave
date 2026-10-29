# DAVE - Data Analysis of Variable Events

<div align="center">
<img src="src/main/resources/static/img/icon.png" alt="DAVE Icon" width="200"/>
</div>

A modern desktop GUI application for astronomical X-ray timing analysis built on the Stingray library. DAVE provides an intuitive interface for analyzing variable X-ray sources with enterprise-grade performance and security.

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![Electron](https://img.shields.io/badge/electron-42.4.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Quick Start

### Prerequisites
- **Pixi Package Manager** ([install here](https://pixi.sh))
### Installation

```bash
# Clone the repository
git clone https://github.com/StingraySoftware/dave.git
cd dave

# Switch to modernization branch (required)
git checkout modernization-2025

# Install Python environment and dependencies
pixi install

# Install Node.js dependencies for Electron frontend
pixi run install-node-deps

# Verify installation
pixi run test                    # Python tests
pixi run test-e2e-install        # Install browser and Electron test dependencies
pixi run test-browser            # Numeric-control browser regressions (Chromium)
pixi run test-workflow           # Electron import/analyze/export/workspace acceptance
pixi run test-e2e               # Other Electron end-to-end checks
```

The scientific workflow test drives the existing Electron controls through event
import, a typed bin size, light-curve and averaged-PDS calculation, CSV export,
and workspace save/reopen after restarting both Electron and Python. Its
deterministic synthetic FITS file includes an observing gap and an injected
signal. Numerical values and uncertainties are compared with direct Stingray
calculations to an absolute tolerance of `1e-6`, matching DAVE's six-decimal API
precision. Test artifacts include the reference, CSV files, saved workspace,
and a screenshot. On headless Linux, run `xvfb-run -a pixi run test-workflow`.

### Running the Application

```bash
# Start the full application (recommended)
pixi run electron

# Alternative: Start components separately
pixi run server          # Flask backend only
# Then in another terminal:
cd src/main/js/electron && npm start  # Electron frontend
```

## Architecture

### Standalone macOS preview

The native-architecture standalone build includes an expanded, immutable Python
environment inside `DAVE.app`. It runs directly from the bundle without installing
or rewriting executable files on first launch. Python, Pixi and Node are not
required on the target Mac. Logs, uploads and scientific caches use writable
application data directories rather than the app bundle.

Build tools require Node 22 or 24 and `conda-pack==0.9.2`. With the locked Pixi
environment and Electron dependencies installed:

```bash
python3 -m pip install --target build/macos-tools -r scripts/macos-build-requirements.txt
PYTHONPATH=build/macos-tools .pixi/envs/default/bin/python scripts/build-standalone-macos.py --node /path/to/node24
```

Output: `build/standalone/DAVE-darwin-arm64/DAVE.app` on Apple Silicon
(`darwin-x64` on Intel). This path builds a local preview without Developer ID
signing or notarization. Automatic update checks are disabled for this preview.
For Developer ID signing, notarization and public ZIP preparation, follow
[the macOS distribution guide](docs/MACOS_DISTRIBUTION.md). Legacy CI jobs no
longer publish macOS builds; the signing pipeline never publishes automatically.

To validate a copy outside the checkout, the workflow harness accepts:

```bash
cd tests
DAVE_PACKAGED_APP=/absolute/path/to/DAVE.app npm run test:workflow
```

The packaged test starts the app's own Python backend with a system-only PATH,
an empty application profile, a read restriction on the checkout and Homebrew,
and no external test server. The outer macOS sandbox requires disabling the
nested Chromium sandbox for this isolation test only; normal app launches keep
the existing Chromium settings. The test runner prepares the independent
Stingray reference outside the app before applying these restrictions.

DAVE uses a hybrid client-server architecture:

```
┌─────────────────────────────────────────┐
│           ELECTRON FRONTEND             │
│    (Desktop Wrapper + Web UI)          │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │   Main      │    │  Renderer   │    │
│  │  Process    │◄──►│   Process   │    │
│  │  (Node.js)  │    │ (Chromium)  │    │
│  └─────────────┘    └─────────────┘    │
└─────────────┬───────────────────────────┘
              │ HTTP Requests (localhost:5001)
              │
┌─────────────▼───────────────────────────┐
│           PYTHON BACKEND                │
│         (Flask REST API)                │
│                                         │
│  ┌─────────────┐    ┌─────────────┐    │
│  │   Flask     │    │  Scientific │    │
│  │   Server    │◄──►│   Engine    │    │
│  │  (Routes)   │    │ (Stingray)  │    │
│  └─────────────┘    └─────────────┘    │
└─────────────────────────────────────────┘
```

## Development Commands

### Code Quality & Linting

```bash
# Python linting (uses ruff)
pixi run lint                   # Check Python code for issues
pixi run format                 # Auto-format Python code

# Fix all linting issues before committing
pixi run lint                   # Must show 0 errors before commit
```

### Building the Application

```bash
# Build for current platform (macOS/Linux/Windows)
pixi run build                  # Full build with tests
pixi run build --no-tests      # Skip tests during build

# Build for specific platforms
python build.py --platform linux --no-tests    # Linux build
python build.py --platform windows --no-tests  # Windows build  
python build.py --platform macos --no-tests    # macOS build

# Use legacy Electron Builder instead of Forge
python build.py --legacy --no-tests

# Clean build artifacts
python build.py --clean
```

### Build Output Locations

After building, find your packages at:
- **macOS**: `src/main/js/electron/out/make/DAVE.dmg`
- **Linux**: `src/main/js/electron/out/make/deb/` and `src/main/js/electron/out/make/rpm/`
- **Windows**: `src/main/js/electron/out/make/squirrel.windows/`

