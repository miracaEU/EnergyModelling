# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.

# This script is adapted from PyPSA-Eur [1]
# Original source: https://github.com/PyPSA/pypsa-eur
# License: MIT License

[1] Hörsch, J., Hofmann, F., Schlachtberger, D., & Brown, T. (2018).
PyPSA-Eur: An open optimisation model of the European transmission system.
Energy Strategy Reviews, 22, 207–215. https://doi.org/10.1016/j.esr.2018.09.002

"""


import pandas as pd
from datetime import timedelta as Delta
import logging

# Set up a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Function: Handle consecutive NaNs in time-series data
def consecutive_nans(ds):
    """
    Calculate consecutive NaNs in a time-series.

    Parameters:
    - ds : pd.Series
        The time-series data.

    Returns:
    - pd.Series
        Series with the count of consecutive NaNs.
    """
    return (
        ds.isnull()
        .astype(int)
        .groupby(ds.notnull().astype(int).cumsum()[ds.isnull()])
        .transform("sum")
        .fillna(0)
    )


# Function: Fill large gaps in time-series data
def fill_large_gaps(ds, shift):
    """
    Fill up large gaps with load data from the previous time slice.

    Parameters:
    - ds : pd.Series
        Time-series data.
    - shift : timedelta
        Time delta for filling gaps (e.g., one week).

    Returns:
    - pd.Series
        Gap-filled time-series data.
    """
    nhours = shift.total_seconds() / 3600  # Convert timedelta to hours
    if (consecutive_nans(ds) > nhours).any():
        logger.warning(
            "There exist gaps larger than the time shift used for copying time slices."
        )
    time_shift = pd.Series(ds.values, index=ds.index + shift)
    return ds.where(ds.notnull(), time_shift.reindex_like(ds))


# Function: Generate NaN statistics for a DataFrame
def nan_statistics(df):
    """
    Generate NaN statistics for a DataFrame.

    Parameters:
    - df : pd.DataFrame
        Time-series data.

    Returns:
    - pd.DataFrame
        DataFrame with total, consecutive, and max monthly NaNs.
    """

    def max_consecutive_nans(ds):
        return (
            ds.isnull()
            .astype(int)
            .groupby(ds.notnull().astype(int).cumsum())
            .sum()
            .max()
        )

    total = df.isnull().sum()
    consecutive = df.apply(max_consecutive_nans)
    max_total_per_month = df.isnull().resample("M").sum().max()
    return pd.concat(
        [total, consecutive, max_total_per_month],
        keys=["total", "consecutive", "max_total_per_month"],
        axis=1,
    )


# Function: Copy time slices to fill missing data
def copy_timeslice(load, cntry, start, stop, delta, fn_load=None):
    """
    Copy time slices to fill missing or erroneous data for a country.

    Parameters:
    - load : pd.DataFrame
        Load data with timestamps and country-specific columns.
    - cntry : str
        ISO-2 country code.
    - start : str
        Start timestamp for the range.
    - stop : str
        Stop timestamp for the range.
    - delta : timedelta
        Time delta for shifting time slices.
    - fn_load : str or None
        File path for additional load data.

    Returns:
    - pd.DataFrame
        Updated load data with copied time slices.
    """
    start = pd.Timestamp(start)
    stop = pd.Timestamp(stop)
    if start in load.index and stop in load.index:
        if (
            start - delta in load.index
            and stop - delta in load.index
            and cntry in load.columns
        ):
            load.loc[start:stop, cntry] = load.loc[
                start - delta : stop - delta, cntry
            ].values
        elif fn_load is not None and cntry in load.columns:
            # duration = pd.date_range(freq="H", start=start - delta, end=stop - delta)
            load_raw = pd.read_csv(fn_load, index_col=0, parse_dates=[0])
            load.loc[start:stop, cntry] = load_raw.loc[
                start - delta : stop - delta, cntry
            ].values
    else:
        logger.warning(
            f"Data for country {cntry} not available between {start} and {stop}."
        )
    return load


# Function: Perform manual adjustments for missing countries
def manual_adjustment(load, fn_load, countries):
    """
    Make manual adjustments for specific countries.

    Parameters:
    - load : pd.DataFrame
        Time-series data.
    - fn_load : str
        File path for additional data adjustments.
    - countries : list
        List of ISO country codes.

    Returns:
    - pd.DataFrame
        Updated load data with manual adjustments.
    """

    if "AL" in countries:
        try:
            load = load[[col for col in load.columns if col.startswith("ME")]] * (
                5.7 / 2.9
            )
            load = load.rename(columns=lambda col: col.replace("ME", "AL", 1))
        except Exception as e:  # Catch all errors, but ensure visibility
            print(f"Error encountered in ME processing: {e}")
            # Fallback processing for "MK" columns, keeping existing logic
            load = load[[col for col in load.columns if col.startswith("MK")]] * (
                4.1 / 7.4
            )
            load = load.rename(columns=lambda col: col.replace("MK", "AL", 1))
    if "MK" in countries:
        load = load[[col for col in load.columns if col.startswith("ME")]] * (6.7 / 2.9)
        load = load.rename(columns=lambda col: col.replace("ME", "MK", 1))
    if "BA" in countries:
        load = load[[col for col in load.columns if col.startswith("HR")]] * (
            11.0 / 16.2
        )
        load = load.rename(columns=lambda col: col.replace("HR", "BA", 1))
    if "XK" in countries:
        load = load[[col for col in load.columns if col.startswith("RS")]] * (
            4.8 / 27.0
        )
        load = load.rename(columns=lambda col: col.replace("RS", "XK", 1))

    copy_timeslice(
        fn_load, "GR", "2015-08-11 21:00", "2015-08-15 20:00", Delta(weeks=1)
    )
    copy_timeslice(fn_load, "AT", "2018-12-31 22:00", "2019-01-01 22:00", Delta(days=2))
    copy_timeslice(
        fn_load, "BG", "2018-10-27 21:00", "2018-10-28 22:00", Delta(weeks=1)
    )
    copy_timeslice(
        fn_load, "LU", "2019-01-02 11:00", "2019-01-05 05:00", Delta(weeks=-1)
    )
    copy_timeslice(
        fn_load, "LU", "2019-02-05 20:00", "2019-02-06 19:00", Delta(weeks=-1)
    )

    if "UA" in countries:
        copy_timeslice(
            load, "UA", "2013-01-25 14:00", "2013-01-28 21:00", Delta(weeks=1)
        )
        copy_timeslice(
            load, "UA", "2013-10-28 03:00", "2013-10-28 20:00", Delta(weeks=1)
        )

    return load


def process_and_save_profiles(
    data, countries, start_time=None, end_time=None, shift=pd.Timedelta(weeks=1)
):
    """
    Process profiles for all countries and combine them into a single DataFrame,
    with optional filtering by time intervals (e.g., hours).

    Parameters:
    - data : pd.DataFrame
        Input dataset with timestamps and country-specific columns.
    - countries : list
        List of ISO-2 country codes to process.
    - start_time : str, optional
        Start timestamp to filter the timeseries data (e.g., '2014-12-31 23:00:00+00:00').
    - end_time : str, optional
        End timestamp to filter the timeseries data (e.g., '2015-01-01 03:00:00+00:00').
    - shift : timedelta
        Time delta for filling large gaps.

    Returns:
    - pd.DataFrame
        Combined dataset with processed profiles for all countries.
    """
    combined_load_data = pd.DataFrame()

    # Convert timestamps and filter data by the specified time interval
    if start_time or end_time:
        filtered_index = data.index
        if start_time:
            start_time = pd.Timestamp(start_time)  # Convert to datetime object
            filtered_index = filtered_index[filtered_index >= start_time]
        if end_time:
            end_time = pd.Timestamp(end_time)  # Convert to datetime object
            filtered_index = filtered_index[filtered_index <= end_time]
        data_filtered = data.loc[filtered_index]

    for country in countries:
        country_cols = [col for col in data_filtered.columns if col.startswith(country)]
        if not country_cols:
            logger.info(f"No data found for country: {country}")

            # Try manual adjustment using data_filtered
            try:
                country_data = manual_adjustment(data_filtered, data, country)
            except Exception as e:
                print(f"Failed manual adjustment for {country}: {e}")
                continue  # Skip processing if adjustment fails

        else:
            # Initialize country-specific data
            country_data = data_filtered[country_cols]

            # Fill large gaps for each column in the country's data
            country_data = country_data.apply(
                lambda col: fill_large_gaps(col, shift) if col.isnull().any() else col
            )

            # Try manual adjustment, fall back to data_filtered if needed
            try:
                country_data = manual_adjustment(country_data, data, country)
            except Exception as e:
                print(f"Unexpected error for {country}, falling back: {e}")
                country_data = manual_adjustment(data_filtered, data, country)

            # Special handling for Ukraine (UA)
            if country == "UA":
                ua_cols = [col for col in data.columns if col.startswith("UA")]
                load_ua = data.loc[data.index.year == 2018, ua_cols].copy()

                # Time adjustment based on snapshot year
                snapshot_year = str(country_data.index.year.unique().item())
                time_diff = pd.Timestamp("2018-01-01") - pd.Timestamp(snapshot_year)
                load_ua.index -= time_diff

                # Fill NaNs in country_data with load_ua
                country_data = country_data.fillna(load_ua)

            # Special handling for Moldova (MD)
            if country == "MD":
                if "UA" in countries:
                    # attach load of MD (no time-series available, use 2020-totals and distribute according to UA):
                    # https://www.iea.org/data-and-statistics/data-browser/?country=MOLDOVA&fuel=Energy%20consumption&indicator=TotElecCons
                    load_ua = combined_load_data[
                        [
                            col
                            for col in combined_load_data.columns
                            if col.startswith("UA")
                        ]
                    ]
                    load_md = 6.2e6 * (load_ua / load_ua.sum())

                    # Fill NaNs in country_data with load_md
                    country_data = country_data.fillna(load_md)

        # Fill missing values using interpolation for smooth transitions
        # country_data = country_data.interpolate(method="time")

        # Interpolate using later values only (method='linear' ensures filling between non-NaN values)
        country_data = country_data.bfill().interpolate(
            method="linear", limit_direction="forward"
        )

        combined_load_data = pd.concat([combined_load_data, country_data], axis=1)

    # Ensure column names match the combined data structure
    if combined_load_data.shape[1] != len(countries):
        logger.info(
            "Warning: The number of combined columns does not match the number of countries."
        )
    return combined_load_data
