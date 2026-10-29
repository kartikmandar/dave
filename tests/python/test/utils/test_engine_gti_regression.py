"""Scientific regressions for external GTIs across the analysis boundary.

The fixtures use DAVE's real dataset cache and real Stingray calculations,
with absolute external GTIs and a source stored in TSTART-relative seconds.
"""

import numpy as np
import pytest
from stingray import (
    AveragedCrossspectrum,
    AveragedPowerspectrum,
    DynamicalPowerspectrum,
    Lightcurve,
    Powerspectrum,
)

import model.dataset as DataSet
import utils.dataset_cache as DsCache
import utils.dataset_helper as DsHelper
import utils.dave_engine as DaveEngine

EVENTS_AXIS = [
    {"table": "EVENTS", "column": "TIME"},
    {"table": "EVENTS", "column": "PHA"},
]


@pytest.fixture(autouse=True)
def clear_cache():
    random_state = np.random.get_state()  # noqa: NPY002 -- isolate Stingray's legacy RNG
    np.random.seed(0)  # noqa: NPY002 -- Stingray's optimizer uses the legacy RNG
    DsCache.clear()
    yield
    DsCache.clear()
    np.random.set_state(random_state)  # noqa: NPY002 -- restore Stingray's legacy RNG


def _cache_events(source_gtis):
    counts = 2 + np.arange(64) % 5
    times = np.repeat(np.arange(64) + 0.25, counts)
    selected = np.zeros(len(times), dtype=bool)
    for start, stop in source_gtis:
        selected |= (times >= start) & (times <= stop)
    times = times[selected]

    dataset = DataSet.get_hdu_type_dataset("source", ["TIME", "PHA"])
    dataset.tables["EVENTS"].set_header_info({"TSTART": "1000"}, {})
    dataset.tables["EVENTS"].columns["TIME"].add_values(times)
    dataset.tables["EVENTS"].columns["TIME"].set_extra("TSTART", 1000.0)
    dataset.tables["EVENTS"].columns["PHA"].add_values(np.ones(len(times)))
    dataset.tables["GTI"] = DsHelper.get_gti_table_from_stingray_gti(np.array(source_gtis))
    DsCache.add("source", dataset)
    return counts


def _cache_external_gtis(intervals):
    dataset = DataSet.get_gti_dataset_from_stingray_gti(np.asarray(intervals, dtype=float))
    DsCache.add("external", dataset)


@pytest.mark.parametrize("pds_type", ["Sng", "Avg"])
def test_power_spectrum_uses_final_relative_filtered_gtis(pds_type):
    counts = _cache_events([[0.0, 64.0]])
    _cache_external_gtis([[1008.0, 1056.0]])
    filters = [{"table": "EVENTS", "column": "TIME", "from": 16.0, "to": 48.0}]

    spectrum, lightcurve, gtis = DaveEngine.create_power_density_spectrum(
        "source", "", "external", filters, EVENTS_AXIS, 1.0, 1, 4.0, "leahy", pds_type
    )

    np.testing.assert_array_equal(gtis, [[16.0, 48.0]])
    np.testing.assert_array_equal(lightcurve.gti, gtis)
    expected_lc = Lightcurve(np.arange(16, 48) + 0.5, counts[16:48], dt=1.0, gti=gtis)
    if pds_type == "Avg":
        expected = AveragedPowerspectrum(expected_lc, segment_size=4.0, norm="leahy")
    else:
        expected = Powerspectrum(expected_lc, norm="leahy")
    np.testing.assert_allclose(spectrum.freq, expected.freq)
    np.testing.assert_allclose(spectrum.power, expected.power)


def test_averaged_power_spectrum_preserves_source_gaps():
    counts = _cache_events([[0.0, 16.0], [24.0, 64.0]])
    _cache_external_gtis([[1008.0, 1056.0]])

    spectrum, lightcurve, gtis = DaveEngine.create_power_density_spectrum(
        "source", "", "external", [], EVENTS_AXIS, 1.0, 1, 4.0, "leahy", "Avg"
    )

    expected_gtis = np.array([[8.0, 16.0], [24.0, 56.0]])
    np.testing.assert_array_equal(gtis, expected_gtis)
    np.testing.assert_array_equal(lightcurve.gti, expected_gtis)
    expected_lc = Lightcurve(np.arange(64) + 0.5, counts, dt=1.0, gti=expected_gtis)
    expected = AveragedPowerspectrum(expected_lc, segment_size=4.0, norm="leahy")
    np.testing.assert_allclose(spectrum.freq, expected.freq)
    np.testing.assert_allclose(spectrum.power, expected.power)
    assert spectrum.m == expected.m == 10


@pytest.mark.parametrize("frequency_bin", [0, 0.25])
def test_pds_reports_actual_time_segment_count_before_frequency_rebinning(frequency_bin):
    _cache_events([[0.0, 16.0], [24.0, 64.0]])
    result = DaveEngine.get_power_density_spectrum(
        "source", "", "", [], EVENTS_AXIS, 1.0, 8, 8.0, "leahy", "Avg", frequency_bin
    )
    # Two segments before the gap, five after it; elapsed duration would give eight.
    assert result[1]["n_segments"] == 7
    assert len(result[0]["values"]) > 0


def test_external_gti_without_overlap_does_not_restore_source_data():
    _cache_events([[0.0, 64.0]])
    _cache_external_gtis([[1100.0, 1120.0]])

    filtered = DaveEngine.get_filtered_dataset("source", [], "external")
    assert len(filtered.tables["EVENTS"].columns["TIME"].values) == 0
    assert len(filtered.tables["GTI"].columns["START"].values) == 0
    assert DaveEngine.create_power_density_spectrum(
        "source", "", "external", [], EVENTS_AXIS, 1.0, 1, 4.0, "leahy", "Avg"
    ) == (None, None, None)


def test_white_noise_estimation_accepts_numpy_gtis():
    times = np.repeat(np.arange(32) + 0.25, 2 + np.arange(32) % 5)
    event_array = np.column_stack((times, np.ones(len(times))))

    result = DaveEngine.get_white_noise_offset(
        event_array, np.array([[0.0, 32.0]]), 1.0, "Sng", 0, 0
    )

    assert np.isfinite(result)


def test_dynamical_spectrum_uses_the_intersected_relative_gtis():
    counts = _cache_events([[0.0, 16.0], [24.0, 64.0]])
    _cache_external_gtis([[1008.0, 1056.0]])
    result = DaveEngine.get_dynamical_spectrum(
        "source", "", "external", [], EVENTS_AXIS, 1.0, 1, 4.0, "leahy", [0.0, 0.5]
    )
    expected_lc = Lightcurve(np.arange(64) + 0.5, counts, dt=1.0, gti=[[8.0, 16.0], [24.0, 56.0]])
    expected = DynamicalPowerspectrum(expected_lc, segment_size=4.0, norm="leahy")
    np.testing.assert_allclose(result[0]["values"], expected.freq)
    np.testing.assert_allclose(result[2]["values"], expected.time)
    np.testing.assert_allclose(
        [column["values"] for column in result[1]["values"]], expected.dyn_ps.T, atol=1e-6
    )


def test_cross_spectrum_uses_the_intersected_relative_gtis():
    counts = _cache_events([[0.0, 16.0], [24.0, 64.0]])
    _cache_external_gtis([[1008.0, 1056.0]])
    result = DaveEngine.get_cross_spectrum(
        "source",
        "",
        "external",
        [],
        EVENTS_AXIS,
        1.0,
        "source",
        "",
        "external",
        [],
        EVENTS_AXIS,
        1.0,
        1,
        4.0,
        "leahy",
        "Avg",
    )
    expected_lc = Lightcurve(np.arange(64) + 0.5, counts, dt=1.0, gti=[[8.0, 16.0], [24.0, 56.0]])
    expected = AveragedCrossspectrum(expected_lc, expected_lc, segment_size=4.0, norm="leahy")
    np.testing.assert_allclose(result[0]["values"], expected.freq)
    np.testing.assert_allclose(result[1]["values"], expected.power.real, atol=1e-6)


def test_gapped_white_noise_estimation_pools_contiguous_segments():
    _cache_events([[0.0, 16.0], [24.0, 64.0]])
    source = DsCache.get("source")
    times = source.tables["EVENTS"].columns["TIME"].values
    events = np.column_stack((times, np.ones(len(times))))
    gtis = np.array([[0.0, 16.0], [24.0, 64.0]])

    automatic = DaveEngine.get_white_noise_offset(events, gtis, 1.0, "Sng", 0, 0)
    np.random.seed(0)  # noqa: NPY002 -- compare the same optimizer initialization
    averaged = DaveEngine.get_white_noise_offset(events, gtis, 1.0, "Avg", 16.0, 0)
    assert np.isfinite(automatic)
    assert automatic == pytest.approx(averaged)


def test_white_noise_estimation_omits_short_fragments_without_losing_usable_gtis():
    times = np.concatenate(([0.25], np.repeat(np.arange(8, 32) + 0.25, 2 + np.arange(24) % 5)))
    events = np.column_stack((times, np.ones(len(times))))
    gtis = np.array([[0.0, 0.5], [8.0, 32.0]])

    automatic = DaveEngine.get_white_noise_offset(events, gtis, 1.0, "Sng", 0, 0)
    np.random.seed(0)  # noqa: NPY002 -- compare the same optimizer initialization
    expected = DaveEngine.get_white_noise_offset(events, gtis[1:], 1.0, "Avg", 24.0, 0)

    assert np.isfinite(automatic)
    assert automatic == pytest.approx(expected)
    np.testing.assert_array_equal(gtis, [[0.0, 0.5], [8.0, 32.0]])


def test_cross_spectrum_without_common_gtis_reports_an_empty_selection():
    _cache_events([[0.0, 64.0]])
    _cache_external_gtis([[1000.0, 1016.0]])
    later = DataSet.get_gti_dataset_from_stingray_gti(np.array([[1024.0, 1064.0]]))
    DsCache.add("later", later)

    result = DaveEngine.get_cross_spectrum(
        "source",
        "",
        "external",
        [],
        EVENTS_AXIS,
        1.0,
        "source",
        "",
        "later",
        [],
        EVENTS_AXIS,
        1.0,
        1,
        4.0,
        "leahy",
        "Avg",
    )

    assert result == {"error": "@WARN@The selected lightcurves have no overlapping GTIs"}


def test_lightcurve_engine_uses_final_relative_rate_dataset_gtis():
    counts = 2 + np.arange(64) % 5
    original = Lightcurve(np.arange(64) + 0.5, counts, dt=1.0, gti=[[0.0, 64.0]])
    dataset = DataSet.get_lightcurve_dataset_from_stingray_Lightcurve(
        original, header={"TSTART": "1000", "TIMEDEL": "1"}
    )
    dataset.tables["RATE"].columns["TIME"].set_extra("TSTART", 1000.0)
    DsCache.add("rate", dataset)
    _cache_external_gtis([[1016.0, 1048.0]])

    lightcurve = DaveEngine.get_lightcurve_any_dataset("rate", "", "external", [], 1.0)

    np.testing.assert_array_equal(lightcurve.gti, [[16.0, 48.0]])
    np.testing.assert_array_equal(lightcurve.time, np.arange(16, 48) + 0.5)
    np.testing.assert_array_equal(lightcurve.counts, counts[16:48])


def test_gapped_rms_countrate_keeps_contiguous_segments_and_warns_about_gaps():
    _cache_events([[0.0, 16.0], [24.0, 64.0]])
    source = DsCache.get("source")
    source.tables["EVENTS"].add_columns(["E"])
    source.tables["EVENTS"].columns["E"].add_values(
        np.ones(len(source.tables["EVENTS"].columns["TIME"].values))
    )
    result = DaveEngine.get_rms_vs_countrate(
        "source", "", "", [], EVENTS_AXIS, 1.0, 2, 0, [0.0, 0.5], [0.0, 10.0], 0.0
    )
    assert len(result[0]["values"]) == 1
    assert result[0]["values"][0] > 0
    assert result[3]["values"] == ["@WARN@Time segments crossing GTI gaps were skipped"]


def test_single_rms_spectrum_reports_gaps_instead_of_returning_zero_bands():
    _cache_events([[0.0, 16.0], [24.0, 64.0]])
    result = DaveEngine.get_rms_spectrum(
        "source",
        "",
        "",
        [],
        EVENTS_AXIS,
        1.0,
        1,
        0,
        "leahy",
        "Sng",
        0,
        [0.0, 0.5],
        [0.0, 10.0],
        2,
        0.0,
    )
    assert "one continuous GTI" in result["error"]
