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

# Predefined parameters
keywords = {
    "coal": " GP09-051 Hard coal",
    "lignite": " GP09-052 Lignite and lignite briquettes",
    "oil": " GP09-0610 10 Mineral oil, crude",
    "gas": "GP09-062 Natural gas",
}

sheet_name_map = {
    "coal": "5.1 Hard coal and lignite",
    "lignite": "5.1 Hard coal and lignite",
    "oil": "5.2 Mineral oil",
    "gas": "5.3.1 Natural gas - indices",
}

price_2020 = (
    pd.Series({"coal": 3.0, "oil": 10.6, "gas": 5.6, "lignite": 1.1}) * 3.6
)  # Eur/MWh

# Manual adjustments
price_2020["coal"] = 2.4 * 3.6
price_2020["lignite"] = 1.6 * 3.6


def get_fuel_price(fuel_price_raw_path):
    """
    Processes and returns monthly fuel prices adjusted to 2020 values.

    Parameters:
        fuel_price_raw_path (str): Path to the raw fuel price Excel file.

    Returns:
        pd.DataFrame: A DataFrame containing monthly fuel prices for each carrier.
    """
    price = {}
    for carrier, keyword in keywords.items():
        sheet_name = sheet_name_map[carrier]
        df = pd.read_excel(
            fuel_price_raw_path,
            sheet_name=sheet_name,
            index_col=0,
            skiprows=6,
            nrows=18,
        )
        df = df.dropna(axis=0).iloc[:, :12]
        start, end = df.index[0], str(int(df.index[-1][:4]) + 1)
        df = df.stack()
        df.index = pd.date_range(start=start, end=end, freq="MS", inclusive="left")
        scale = price_2020[carrier] / df["2020"].mean()  # Scale to 2020 price
        df = df.mul(scale)
        price[carrier] = df

    return pd.concat(price, axis=1)


def get_co2_price(co2_price_raw_path):
    # emission price
    co2_price = pd.read_excel(co2_price_raw_path, index_col=1, header=5)
    return co2_price["Auction Price €/tCO2"]


def get_co2_prices(data_folder, start_interval, end_interval):
    import os

    # Extract relevant years
    years_needed = list(range(start_interval.year, end_interval.year + 1))
    # Load only necessary datasets
    dfs = []
    for year in years_needed:
        print(year)
        # Determine correct file extension
        file_extension = "xls" if year <= 2020 else "xlsx"
        file_path = os.path.join(
            data_folder,
            f"emission-spot-primary-market-auction-report-{year}-data.{file_extension}",
        )

        if os.path.exists(file_path):  # Ensure file exists before loading
            try:
                df = pd.read_excel(
                    file_path, header=None
                )  # Load without setting a header
                header_row_mask = df.apply(
                    lambda row: row.astype(str)
                    .str.contains(
                        r"Auction Price (?:€/tCO2|EUR/tCO2)", regex=True, na=False
                    )
                    .any(),
                    axis=1,
                )
                header_row_index = df[header_row_mask].index[0]
                # Reload data using detected header row
                df = pd.read_excel(file_path, header=header_row_index)
                df["Date"] = pd.to_datetime(
                    df["Date"]
                )  # Convert Date to datetime format
                dfs.append(df)
            except Exception as e:
                print(f"Error loading {year} dataset: {e}")
    # Merge all available years dynamically
    if dfs:
        full_data = pd.concat(dfs, ignore_index=True)
        # Filter data based on the provided time interval
        co2_price = full_data[
            (full_data["Date"] >= start_interval) & (full_data["Date"] <= end_interval)
        ]

        # Ensure full_data is sorted by Date in ascending order
        full_data = full_data.sort_values(by="Date", ascending=True)

        # If the filtered DataFrame is empty, find the first row where Date >= start_interval
        if co2_price.empty:
            fallback_row = full_data[full_data["Date"] >= start_interval].iloc[[0]]
            if not fallback_row.empty:
                co2_price = fallback_row.iloc[[0]]  # Select only the first row

        # Handle cases where no valid data is found
        if co2_price.empty:
            print("No valid data found for the given interval.")

        # Ensure column name consistency for joining
        co2_price.rename(
            columns={"Auction Price EUR/tCO2": "Auction Price €/tCO2"}, inplace=True
        )
        # Ensure 'Date' column is in datetime format
        co2_price["Date"] = pd.to_datetime(co2_price["Date"])
        # Set 'Date' column as index
        co2_price = co2_price.set_index("Date")
    else:
        print("No matching data found for the selected interval.")

    return co2_price["Auction Price €/tCO2"]
