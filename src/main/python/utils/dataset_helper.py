import bisect

import numpy as np
from stingray import Lightcurve
from stingray.events import EventList
from stingray.gti import cross_two_gtis, gti_len, join_gtis

import utils.dave_logger as logging
from config import CONFIG
from model.table import Table


# Returns an Stingray EventList from a given events dataset
def get_eventlist_from_evt_dataset(dataset):
    if not is_events_dataset(dataset):
        logging.warn("get_eventlist_from_evt_dataset: dataset is not a events dataset instance")
        return None

    # TODO: Probably all this check can be moved to dave_reader for doing it only once
    # instead with every call to get_eventlist_from_evt_dataset
    if "PHA" not in dataset.tables["EVENTS"].columns:
        logging.warn("get_eventlist_from_evt_dataset: PHA column not found in dataset")
        dataset.tables["EVENTS"].add_columns(["PHA"])
        dataset.tables["EVENTS"].columns["PHA"].set_extra("FAKE_COLUMN", True)
        try:
            dataset.tables["EVENTS"].columns["PHA"].values = (
                dataset.tables["EVENTS"].columns["PI"].values
            )
            logging.warn("Using PI instead of PHA")
        except Exception:
            dataset.tables["EVENTS"].columns["PHA"].values = np.zeros(
                len(dataset.tables["EVENTS"].columns[CONFIG.TIME_COLUMN].values), dtype=int
            )
            logging.warn("PHA column will be empty")

    # Extract axis values
    time_data = np.array(dataset.tables["EVENTS"].columns[CONFIG.TIME_COLUMN].values)
    pha_data = np.array(dataset.tables["EVENTS"].columns["PHA"].values)

    # Extract GTIs
    gti = get_stingray_gti_from_gti_table(dataset.tables["GTI"])

    # Returns the EventList
    if len(gti) > 0:
        return EventList(time_data, gti=gti, pi=pha_data)
    else:
        return EventList(time_data, pi=pha_data)


# Returns an Stingray Lightcurve from a given lightcurve dataset
def get_lightcurve_from_lc_dataset(dataset, gti=None):
    if not is_lightcurve_dataset(dataset):
        logging.warn("get_eventlist_from_evt_dataset: dataset is not a events dataset instance")
        return None

    # Extract axis values
    time_data = np.array(dataset.tables["RATE"].columns[CONFIG.TIME_COLUMN].values)
    counts = np.array(dataset.tables["RATE"].columns["RATE"].values)
    err_counts = np.array(dataset.tables["RATE"].columns["RATE"].error_values)

    if len(time_data) == 0:
        return None

    # Extract GTIs
    if gti is None:
        gti = get_stingray_gti_from_gti_table(dataset.tables["GTI"])
    elif len(gti) == 0:
        # An explicit empty selection must not restore the full observation.
        return None

    # Returns the EventList
    if len(gti) > 0:
        return Lightcurve(time_data, counts, err=err_counts, input_counts=True, gti=gti)
    else:
        return Lightcurve(time_data, counts, err=err_counts, input_counts=True)


# Returns an Stingray Lightcurve
def get_lightcurve(time_data, counts, err_counts, gti):
    return Lightcurve(time_data, counts, err=err_counts, input_counts=True, gti=gti)


def get_empty_gti_table():
    table = Table("GTI")
    table.add_columns(["START", "STOP", "START_EVENT_IDX", "END_EVENT_IDX"])
    return table


def get_gti_table(from_val, to_val):
    table = get_empty_gti_table()
    table.columns["START"].add_value(from_val)
    table.columns["STOP"].add_value(to_val)
    return table


# Finds the idx of the nearest value on the array, array must be sorted
def find_idx_nearest_val(array, value):
    # idx = np.searchsorted(array, value, side="left")
    idx = bisect.bisect_left(
        array, value
    )  #  Looks like bisec is faster with structured data than searchsorted

    if idx >= len(array):
        idx_nearest = len(array) - 1
    elif idx == 0:
        idx_nearest = 0
    else:
        if abs(value - array[idx - 1]) < abs(value - array[idx]):
            idx_nearest = idx - 1
        else:
            idx_nearest = idx
    return idx_nearest


def is_events_dataset(dataset):
    return is_hdu_dataset(dataset, "EVENTS")


def is_lightcurve_dataset(dataset):
    return is_hdu_dataset(dataset, "RATE")


def is_hdu_dataset(dataset, hduname):
    return (
        dataset
        and hduname in dataset.tables
        and CONFIG.TIME_COLUMN in dataset.tables[hduname].columns
        and "GTI" in dataset.tables
    )


def is_rmf_dataset(dataset):
    return (
        dataset and "EBOUNDS" in dataset.tables and "CHANNEL" in dataset.tables["EBOUNDS"].columns
    )


def is_gti_dataset(dataset):
    return dataset and "GTI" in dataset.tables and "START" in dataset.tables["GTI"].columns


def are_datasets_of_same_type(dataset1, dataset2):
    return get_hdutable_from_dataset(dataset1).id == get_hdutable_from_dataset(dataset2).id


def get_hdutable_from_dataset(dataset):
    if is_events_dataset(dataset):
        return dataset.tables["EVENTS"]
    elif is_lightcurve_dataset(dataset):
        return dataset.tables["RATE"]
    else:
        logging.warn("get_hdutable_from_dataset: dataset is no Events or Lightcurve type")
        return None


def get_dataset_start_time(dataset):
    hdutable = get_hdutable_from_dataset(dataset)
    if hdutable:
        return get_column_start_time(hdutable.columns[CONFIG.TIME_COLUMN])
    else:
        logging.warn("get_dataset_start_time: hdutable is None")
        return 0


def get_column_start_time(column):
    if column.has_extra("TSTART"):
        return column.get_extra("TSTART")
    else:
        logging.warn("get_column_start_time: Couldn't read TSTART from extras, using column[0]")
        if len(column.values) > 0:
            return column.values[0]
    return 0


def get_binsize_from_lightcurve_ds(dataset):
    if is_lightcurve_dataset(dataset):
        table = dataset.tables["RATE"]
        if "TIMEDEL" in table.header:
            return float(table.header["TIMEDEL"])
        elif "FRMTIME" in table.header:
            return float(table.header["FRMTIME"]) / 1000
    else:
        logging.warn(
            "get_binsize_from_lightcurve_ds: Couldn't read TIMEDEL or FRMTIME from RATE HEADER!"
        )
        return 0


def get_stingray_gti_from_gti_table(gti_table):
    return np.column_stack((gti_table.columns["START"].values, gti_table.columns["STOP"].values))


def get_gti_table_from_stingray_gti(gti):
    gti_table = get_empty_gti_table()
    gti_table.columns["START"].add_values(gti[:, 0])
    gti_table.columns["STOP"].add_values(gti[:, 1])
    return gti_table


def join_gti_tables(gti_table_0, gti_table_1):
    if not gti_table_0:
        logging.warn("join_gti_tables: gti_table_0 is None, returned gti_table_1")
        return gti_table_1

    if not gti_table_1:
        logging.warn("join_gti_tables: gti_table_1 is None, returned gti_table_0")
        return gti_table_0

    gti_0 = get_stingray_gti_from_gti_table(gti_table_0)
    gti_1 = get_stingray_gti_from_gti_table(gti_table_1)
    joined_gti = join_gtis(gti_0, gti_1)

    return get_gti_table_from_stingray_gti(joined_gti)


def get_exposure_time(gti_table):
    return gti_len(get_stingray_gti_from_gti_table(gti_table))


# Returns True if there is a GAP in the time_vals values
def hasGTIGaps(time_vals):
    trigger_ratio = 100  # The ratio of elapsed time versus prev elapsed for triggering a gap

    if len(time_vals > 1):
        prev_val = time_vals[0]
        elapsed_avg = 0
        for val in time_vals:
            elapsed = val - prev_val
            prev_val = val

            if elapsed_avg > 0:
                ratio = elapsed / elapsed_avg
                if ratio > trigger_ratio:
                    return True

                # Calulates the ne elapsed_avg with the latest 5 vals
                elapsed_avg += (elapsed - elapsed_avg) * 0.2

            else:
                elapsed_avg = elapsed

    return False


# Returns Gtis from an unique gti splited by time_interval
def get_splited_gti(gti, ti):
    if ti <= (gti[1] - gti[0]) / 2:
        # If the gti is splitable by ti
        start = gti[0]
        num_gtis = int((gti[1] - gti[0]) / ti)
        new_gtis = []

        for _ in range(num_gtis):
            end = start + ti
            new_gtis.append([start, end])
            start = end

        return np.array(new_gtis)

    else:
        logging.warn("get_splited_gti: gti is not splitable by time_interval")
        return None


# Returns a list of columns excluding passed columnName
def get_additional_column_names(columns, column):
    additional_columns = []
    for column_name in columns:
        if column_name != column:
            additional_columns.extend([column_name])
    return additional_columns


# Returns a dictionary with the values of the table columns values
def get_columns_as_dict(columns, column):
    ds_columns = {}
    for column_name in columns:
        if column_name != column:
            ds_columns[column_name] = columns[column_name].values
    return ds_columns


# Returns a dictionary with the error_values of the table columns values
def get_columns_errors_as_dict(columns, column):
    ds_columns_errors = {}
    for column_name in columns:
        if column_name != column:
            ds_columns_errors[column_name] = columns[column_name].error_values
    return ds_columns_errors


# Returns a new dataset filtered by a GTI_Dataset
def get_dataset_applying_gti_dataset(
    src_dataset, gti_dataset, hduname="EVENTS", column=CONFIG.TIME_COLUMN
):
    if not (is_events_dataset(src_dataset) or is_lightcurve_dataset(src_dataset)):
        logging.warn(
            "get_dataset_applying_gti_dataset: src_dataset is not an events or lightcurve dataset"
        )
        return None

    if not is_gti_dataset(gti_dataset):
        logging.warn("get_dataset_applying_gti_dataset: gti_dataset is not a gti dataset instance")
        return None

    if hduname == "EVENTS" and is_lightcurve_dataset(src_dataset):
        hduname = "RATE"

    # Clone metadata while rebuilding only the selected rows and intervals.
    dataset = src_dataset.clone(False)
    additional_columns = get_additional_column_names(dataset.tables[hduname].columns, column)
    hdu_table = src_dataset.tables[hduname]

    st_gtis = get_stingray_gti_from_gti_table(gti_dataset.tables["GTI"])
    ev_list = hdu_table.columns[column].values
    ev_list_err = hdu_table.columns[column].error_values
    ds_columns = get_columns_as_dict(src_dataset.tables[hduname].columns, column)
    ds_columns_errors = get_columns_errors_as_dict(src_dataset.tables[hduname].columns, column)

    # GTI-only FITS inputs carry absolute mission times. Source times and
    # source GTIs have already had their recorded observation origin removed.
    time_column = hdu_table.columns[column]
    events_start_time = float(
        time_column.get_extra("TSTART")
        if time_column.has_extra("TSTART")
        else hdu_table.header.get("TSTART", 0)
    )
    st_gtis = _merge_gti_intervals(st_gtis[:, 0], st_gtis[:, 1]) - events_start_time
    source_gtis = get_stingray_gti_from_gti_table(src_dataset.tables["GTI"])
    source_gtis = _merge_gti_intervals(source_gtis[:, 0], source_gtis[:, 1])
    if len(st_gtis) and len(source_gtis):
        st_gtis = np.asarray(cross_two_gtis(source_gtis, st_gtis)).reshape(-1, 2)
    else:
        st_gtis = np.empty((0, 2))

    update_dataset_filtering_by_gti(
        dataset.tables[hduname],
        dataset.tables["GTI"],
        ev_list,
        ev_list_err,
        ds_columns,
        ds_columns_errors,
        st_gtis[:, 0],
        st_gtis[:, 1],
        additional_columns,
        column,
    )
    return dataset


def _merge_gti_intervals(gti_start, gti_end):
    """Order GTIs and unite overlaps/touching edges so rows are never repeated."""
    intervals = []
    for start, end in sorted(zip(gti_start, gti_end, strict=True)):
        if not np.isfinite(start) or not np.isfinite(end) or end < start:
            raise ValueError("GTIs must have finite, ordered start/stop times")
        if intervals and start <= intervals[-1][1]:
            intervals[-1][1] = max(intervals[-1][1], end)
        else:
            intervals.append([start, end])
    return np.asarray(intervals).reshape(-1, 2)


# Returns a Dataset filtered by Gtis
def update_dataset_filtering_by_gti(
    hdu_table,
    gti_table,
    ev_list,
    ev_list_err,
    ds_columns,
    ds_columns_errors,
    gti_start,
    gti_end,
    additional_columns,
    column=CONFIG.TIME_COLUMN,
    filter_start=None,
    filter_end=None,
    must_filter=False,
):
    # Events exactly at either endpoint are included, matching DAVE's range
    # filters. A right insertion point supplies the exclusive Python slice end.
    for start, end in _merge_gti_intervals(gti_start, gti_end):
        if must_filter:
            start = max(start, filter_start)
            end = min(end, filter_end)
        if start > end:
            continue

        start_event_idx = bisect.bisect_left(ev_list, start)
        stop_event_idx = bisect.bisect_right(ev_list, end)

        # Zero detected photons do not remove valid observing exposure.
        gti_table.columns["START"].add_value(start)
        gti_table.columns["STOP"].add_value(end)
        gti_table.columns["START_EVENT_IDX"].add_value(start_event_idx)
        gti_table.columns["END_EVENT_IDX"].add_value(stop_event_idx - 1)

        selected = slice(start_event_idx, stop_event_idx)
        time_errors = ev_list_err[selected] if len(ev_list_err) == len(ev_list) else None
        hdu_table.columns[column].add_values(ev_list[selected], time_errors)
        for additional_column in additional_columns:
            values = np.nan_to_num(ds_columns[additional_column][selected])
            error_values = None
            if additional_column in ds_columns_errors and len(
                ds_columns_errors[additional_column]
            ) == len(ev_list):
                error_values = np.nan_to_num(ds_columns_errors[additional_column][selected])
            hdu_table.columns[additional_column].add_values(values, error_values)


# Returns a tuple with the counts and the key values
# of applying the histogram to an array
#
# @param: array: the array with the data to generate the histogram
# @param: precision: the precision for matching/bining values of array,
#         default will be 1.0 but is set as 0.01 will have a two decimal
#         binning for example
def get_histogram(array, precision=1.0):
    histogram = {}
    values = []
    for val in array:
        match_val = val
        if precision != 1.0:
            match_val = int(val / precision) * precision

        if match_val not in histogram:
            histogram[match_val] = 0
            values.append(match_val)
        histogram[match_val] += 1

    return histogram, np.sort(values)


def add_time_offset_to_dataset(dataset, time_offset):
    if time_offset != 0:
        logging.debug(
            "add_time_offset_to_dataset: dataset: "
            + str(dataset.id)
            + ", time_offset: "
            + str(time_offset)
        )

        ds_gti = get_stingray_gti_from_gti_table(dataset.tables["GTI"])
        ds_gti[:, 0] = ds_gti[:, 0] + time_offset
        ds_gti[:, 1] = ds_gti[:, 1] + time_offset
        dataset.tables["GTI"] = get_gti_table_from_stingray_gti(ds_gti)

        hdutable = get_hdutable_from_dataset(dataset)
        if hdutable:
            hdutable.columns[CONFIG.TIME_COLUMN].values = (
                hdutable.columns[CONFIG.TIME_COLUMN].values + time_offset
            )

    return dataset
