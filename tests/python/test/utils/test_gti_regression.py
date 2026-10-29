"""Scientific invariants for GTI selection, using only in-memory datasets."""

import numpy as np
import pytest

from model import dataset as DataSet
from utils import dataset_helper as DsHelper


def _events(times, gtis, origin=0.0):
    dataset = DataSet.get_hdu_type_dataset("events", ["TIME", "PI"], "EVENTS")
    table = dataset.tables["EVENTS"]
    table.set_header_info({"TSTART": str(origin), "BACKSCAL": "0.5"}, {"TSTART": "origin"})
    table.columns["TIME"].add_values(times, np.arange(len(times), dtype=float) + 0.01)
    table.columns["TIME"].set_extra("TSTART", origin)
    table.columns["PI"].add_values(np.arange(len(times)) + 10, np.arange(len(times)) + 0.1)
    table.columns["PI"].set_extra("UNIT", "channel")
    dataset.tables["GTI"] = DsHelper.get_gti_table_from_stingray_gti(
        np.asarray(gtis, dtype=float).reshape(-1, 2)
    )
    return dataset


def _select(times, gtis, window=None):
    source = _events(times, gtis)
    table = source.tables["EVENTS"]
    return DataSet.get_dataset_applying_gtis(
        "filtered",
        table.header,
        table.header_comments,
        {"PI": table.columns["PI"].values},
        {"PI": table.columns["PI"].error_values},
        table.columns["TIME"].values,
        table.columns["TIME"].error_values,
        source.tables["GTI"].columns["START"].values,
        source.tables["GTI"].columns["STOP"].values,
        *(window or (None, None)),
    )


@pytest.mark.parametrize(
    ("times", "gtis", "window", "expected"),
    [
        ([0.5, 1.5, 2.5], [[0, 3]], None, [0.5, 1.5, 2.5]),
        ([1.5], [[1, 2]], None, [1.5]),
        ([], [[0, 3]], None, []),
        ([0.5, 1.5], [[2, 3]], None, []),
        ([2.5, 3.5], [[0, 1]], None, []),
        ([0, 1, 2, 3], [[1, 2]], None, [1, 2]),
        ([0, 1, 2, 3], [[0, 3]], (1, 2), [1, 2]),
        ([0, 1, 2, 3], [[0, 3]], (4, 5), []),
        ([0, 1, 2, 3, 4], [[0, 1], [3, 4]], None, [0, 1, 3, 4]),
        ([0, 1, 2, 3, 4], [[0, 3], [1, 4]], None, [0, 1, 2, 3, 4]),
        ([0, 1, 2], [[0, 1], [1, 2]], None, [0, 1, 2]),
    ],
)
def test_gti_selection_preserves_each_valid_event_once(times, gtis, window, expected):
    filtered = _select(times, gtis, window)
    assert filtered.tables["EVENTS"].columns["TIME"].values == expected


def test_gti_selection_keeps_values_and_uncertainties_aligned():
    filtered = _select([0, 1, 2, 3, 4], [[0, 4]], (1, 3))
    table = filtered.tables["EVENTS"]
    assert table.columns["TIME"].values == [1, 2, 3]
    np.testing.assert_allclose(table.columns["TIME"].error_values, [1.01, 2.01, 3.01])
    assert table.columns["PI"].values == [11, 12, 13]
    np.testing.assert_allclose(table.columns["PI"].error_values, [1.1, 2.1, 3.1])
    assert table.columns["PI"].has_error_values
    assert table.header == {"TSTART": "0.0", "BACKSCAL": "0.5"}
    assert table.header_comments == {"TSTART": "origin"}


def test_external_gtis_intersect_source_gaps_and_preserve_metadata():
    source = _events([0, 1, 2, 3, 8, 9, 10], [[0, 3], [8, 10]], origin=100)
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[100.0, 110.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    np.testing.assert_array_equal(
        DsHelper.get_stingray_gti_from_gti_table(filtered.tables["GTI"]), [[0, 3], [8, 10]]
    )
    assert DsHelper.get_exposure_time(filtered.tables["GTI"]) == 5.0
    table = filtered.tables["EVENTS"]
    assert table.columns["TIME"].values == [0, 1, 2, 3, 8, 9, 10]
    assert table.header == source.tables["EVENTS"].header
    assert table.columns["TIME"].get_extra("TSTART") == 100
    assert table.columns["PI"].get_extra("UNIT") == "channel"
    assert table.columns["PI"].error_values == source.tables["EVENTS"].columns["PI"].error_values
    assert source.tables["EVENTS"].columns["TIME"].values == [0, 1, 2, 3, 8, 9, 10]


@pytest.mark.parametrize("external_gtis", [[], [[200.0, 210.0]]])
def test_empty_external_intersection_stays_empty(external_gtis):
    source = _events([0, 1, 2, 3], [[0, 3]], origin=100)
    external = DataSet.get_gti_dataset_from_stingray_gti(
        np.asarray(external_gtis, dtype=float).reshape(-1, 2)
    )
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["EVENTS"].columns["TIME"].values == []
    assert DsHelper.get_stingray_gti_from_gti_table(filtered.tables["GTI"]).shape == (0, 2)


def test_external_gtis_use_the_recorded_source_time_origin():
    source = _events([0, 1, 2, 3], [[0, 3]], origin=100)
    # A transformed dataset's explicit time origin takes precedence over the FITS header.
    source.tables["EVENTS"].header["TSTART"] = "90"
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[101.0, 102.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["EVENTS"].columns["TIME"].values == [1, 2]


def test_numpy_gti_override_builds_lightcurve_without_ambiguous_truth_check():
    dataset = DataSet.get_hdu_type_dataset("lc", ["TIME", "RATE"], "RATE")
    dataset.tables["RATE"].columns["TIME"].add_values([0.5, 1.5, 2.5])
    dataset.tables["RATE"].columns["RATE"].add_values([10, 20, 30], [1, 2, 3])
    dataset.tables["GTI"] = DsHelper.get_gti_table_from_stingray_gti(np.array([[0.0, 3.0]]))
    lightcurve = DsHelper.get_lightcurve_from_lc_dataset(dataset, np.array([[0.0, 2.0]]))
    np.testing.assert_array_equal(lightcurve.gti, [[0, 2]])


def test_gti_interval_without_photons_preserves_its_exposure():
    filtered = _select([0, 2], [[0.5, 1.5]])
    assert filtered.tables["EVENTS"].columns["TIME"].values == []
    np.testing.assert_array_equal(
        DsHelper.get_stingray_gti_from_gti_table(filtered.tables["GTI"]), [[0.5, 1.5]]
    )


def test_external_gtis_fall_back_to_the_source_header_time_origin():
    source = _events([0, 1, 2, 3], [[0, 3]], origin=100)
    source.tables["EVENTS"].columns["TIME"].extra = None
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[101.0, 102.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["EVENTS"].columns["TIME"].values == [1, 2]


def test_external_gtis_are_absolute_without_guessing_from_their_range():
    source = _events([0, 1, 2, 3], [[0, 3]], origin=100)
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[1.0, 2.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["EVENTS"].columns["TIME"].values == []


def test_external_gtis_cannot_restore_an_empty_source_interval():
    source = _events([0, 1, 2, 3], [], origin=100)
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[100.0, 103.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["EVENTS"].columns["TIME"].values == []
    assert DsHelper.get_stingray_gti_from_gti_table(filtered.tables["GTI"]).shape == (0, 2)


def test_external_gtis_filter_lightcurve_rows_and_keep_their_uncertainties():
    source = DataSet.get_hdu_type_dataset("lc", ["TIME", "RATE"], "RATE")
    table = source.tables["RATE"]
    table.set_header_info({"TSTART": "100", "TIMEDEL": "1", "BACKSCAL": "0.5"}, {})
    table.columns["TIME"].add_values([0.5, 1.5, 2.5, 3.5])
    table.columns["TIME"].set_extra("TSTART", 100)
    table.columns["RATE"].add_values([10, 20, 30, 40], [1, 2, 3, 4])
    source.tables["GTI"] = DsHelper.get_gti_table_from_stingray_gti(np.array([[0.0, 4.0]]))
    external = DataSet.get_gti_dataset_from_stingray_gti(np.array([[101.0, 103.0]]))
    filtered = DsHelper.get_dataset_applying_gti_dataset(source, external)
    assert filtered.tables["RATE"].columns["TIME"].values == [1.5, 2.5]
    assert filtered.tables["RATE"].columns["RATE"].values == [20, 30]
    assert filtered.tables["RATE"].columns["RATE"].error_values == [2, 3]
    assert filtered.tables["RATE"].header == table.header
    assert filtered.tables["RATE"].columns["TIME"].get_extra("TSTART") == 100
    np.testing.assert_array_equal(DsHelper.get_lightcurve_from_lc_dataset(filtered).gti, [[1, 3]])


def test_empty_gti_override_does_not_restore_the_lightcurve_observation():
    dataset = DataSet.get_hdu_type_dataset("lc", ["TIME", "RATE"], "RATE")
    dataset.tables["RATE"].columns["TIME"].add_values([0.5, 1.5, 2.5])
    dataset.tables["RATE"].columns["RATE"].add_values([10, 20, 30], [1, 2, 3])
    dataset.tables["GTI"] = DsHelper.get_gti_table_from_stingray_gti(np.array([[0.0, 3.0]]))
    assert DsHelper.get_lightcurve_from_lc_dataset(dataset, np.empty((0, 2))) is None
