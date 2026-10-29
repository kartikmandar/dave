"""Generate an independent scientific oracle for the Electron workflow test.

The FITS file is synthetic, with NuSTAR-style event headers, a nonzero mission
time origin, two good-time intervals and deterministic Poisson variability.
Only Astropy, NumPy and Stingray are used: no DAVE implementation is imported.
"""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

import numpy as np
from astropy.io import fits
from stingray import AveragedPowerspectrum
from stingray.events import EventList

TIME_ORIGIN = 80_000_000.0
MJDREF = 55197 + 0.00076601852
GOOD_TIMES = np.array([[0.0, 64.0], [80.0, 144.0]])
BIN_TIME = 0.5
SEGMENT_SIZE = 16.0
NORMALIZATION = "leahy"
RANDOM_SEED = 825013
SIGNAL_FREQUENCY = 0.25


def generate_reference(output_dir):
    """Write a fixture and full-precision direct-Stingray reference to a directory."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "source.evt"
    reference_path = output_dir / "reference.json"
    if source_path.exists() or reference_path.exists():
        raise FileExistsError("Use an empty output directory for workflow reference generation")

    rng = np.random.default_rng(RANDOM_SEED)
    fine_bin_time = 0.125
    fine_centres = np.arange(fine_bin_time / 2, GOOD_TIMES[-1, 1], fine_bin_time)
    good_bins = np.zeros(len(fine_centres), dtype=bool)
    for start, stop in GOOD_TIMES:
        good_bins |= (fine_centres >= start) & (fine_centres < stop)
    fine_centres = fine_centres[good_bins]

    rate = (
        80.0
        + 25.0 * np.sin(2 * np.pi * SIGNAL_FREQUENCY * fine_centres)
        + 15.0 * np.sin(2 * np.pi * fine_centres)
    )
    counts = rng.poisson(rate * fine_bin_time)
    # Keep events clear of bin boundaries, even after the FITS absolute-time
    # representation rounds times at the 80-million-second mission origin.
    relative_times = np.repeat(fine_centres - fine_bin_time / 2, counts)
    relative_times += rng.uniform(0.1, 0.9, len(relative_times)) * fine_bin_time
    relative_times.sort()
    channels = rng.integers(25, 256, len(relative_times), dtype=np.int32)

    primary = fits.PrimaryHDU()
    events = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="TIME", format="D", unit="s", array=TIME_ORIGIN + relative_times),
            fits.Column(name="PI", format="J", array=channels),
        ],
        name="EVENTS",
    )
    intervals = fits.BinTableHDU.from_columns(
        [
            fits.Column(name="START", format="D", unit="s", array=TIME_ORIGIN + GOOD_TIMES[:, 0]),
            fits.Column(name="STOP", format="D", unit="s", array=TIME_ORIGIN + GOOD_TIMES[:, 1]),
        ],
        name="GTI",
    )
    for hdu in [primary, events, intervals]:
        hdu.header["TELESCOP"] = "NuSTAR"
        hdu.header["INSTRUME"] = "FPMA"
        hdu.header["TIMESYS"] = "TDB"
        hdu.header["TIMEREF"] = "SOLARSYSTEM"
        hdu.header["MJDREFI"] = 55197
        hdu.header["MJDREFF"] = 0.00076601852
        hdu.header["TIMEZERO"] = 0.0
        hdu.header["TIMEUNIT"] = "s"
        hdu.header["TSTART"] = TIME_ORIGIN
        hdu.header["TSTOP"] = TIME_ORIGIN + GOOD_TIMES[-1, 1]
    events.header["TIMEDEL"] = fine_bin_time
    events.header["HDUCLASS"] = "OGIP"
    events.header["HDUCLAS1"] = "EVENTS"
    events.header["HDUCLAS2"] = "ACCEPTED"
    events.header["SYNTHETC"] = (True, "Synthetic fixture, not mission data")
    fits.HDUList([primary, events, intervals]).writeto(source_path)

    # Read the actual serialized fixture with Astropy so the oracle includes
    # FITS precision effects independently of DAVE's reader and transformations.
    with fits.open(source_path) as hdus:
        stored_times = np.array(hdus["EVENTS"].data["TIME"]) - TIME_ORIGIN
        stored_gtis = (
            np.column_stack((hdus["GTI"].data["START"], hdus["GTI"].data["STOP"])) - TIME_ORIGIN
        )
        stored_channels = np.array(hdus["EVENTS"].data["PI"])

    event_list = EventList(stored_times, pi=stored_channels, gti=stored_gtis, mjdref=MJDREF)
    lightcurve = event_list.to_lc(BIN_TIME)
    spectrum = AveragedPowerspectrum(
        data=lightcurve, segment_size=SEGMENT_SIZE, norm=NORMALIZATION, silent=True
    )

    # These independent invariants make reference generation fail if the
    # fixture loses events, merges the gap or ceases to contain the injection.
    histogram, _ = np.histogram(stored_times, bins=np.arange(0, 144.0 + BIN_TIME, BIN_TIME))
    np.testing.assert_array_equal(lightcurve.counts, histogram)
    assert int(lightcurve.counts.sum()) == len(stored_times)
    assert sum(stop - start for start, stop in stored_gtis) == 128.0
    assert spectrum.m == 8
    assert spectrum.freq[np.argmax(spectrum.power)] == SIGNAL_FREQUENCY

    reference = {
        "schema_version": 1,
        "provenance": {
            "description": "Synthetic Poisson event list with a deterministic injected signal and GTI gap",
            "generator": "NumPy and Astropy; reference calculations use direct Stingray, never DAVE",
            "seed": RANDOM_SEED,
            "versions": {
                name: importlib.metadata.version(name) for name in ["numpy", "astropy", "stingray"]
            },
        },
        "parameters": {
            "dt": BIN_TIME,
            "segment_size": SEGMENT_SIZE,
            "norm": NORMALIZATION,
            "pds_type": "Avg",
            "df": 0.0,
        },
        "source": {
            "filename": source_path.name,
            "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "event_count": len(stored_times),
            "time_origin": TIME_ORIGIN,
            "duration": 144.0,
            "exposure": 128.0,
            "gti": stored_gtis.tolist(),
            "injected_frequency": SIGNAL_FREQUENCY,
        },
        "lightcurve": {
            "time": lightcurve.time.tolist(),
            "counts": lightcurve.counts.tolist(),
            "countrate": lightcurve.countrate.tolist(),
            "counts_err": lightcurve.counts_err.tolist(),
            "countrate_err": lightcurve.countrate_err.tolist(),
            "gti": lightcurve.gti.tolist(),
        },
        "pds": {
            "freq": spectrum.freq.tolist(),
            "power": spectrum.power.tolist(),
            "power_err": spectrum.power_err.tolist(),
            "m": int(spectrum.m),
            "norm": spectrum.norm,
        },
        "tolerances": {
            "serialized_absolute": 1e-6,
            "relative": 1e-9,
            "reason": "DAVE rounds API arrays to six decimal places before UI display and CSV export",
        },
    }
    reference_path.write_text(json.dumps(reference, indent=2) + "\n", encoding="utf-8")
    return reference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    reference = generate_reference(args.output_dir)
    print(
        json.dumps(
            {
                "source": str(args.output_dir / "source.evt"),
                "reference": str(args.output_dir / "reference.json"),
                "event_count": reference["source"]["event_count"],
                "segments": reference["pds"]["m"],
            }
        )
    )


if __name__ == "__main__":
    main()
