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

import geopandas as gpd
import pandas as pd


def distribute_load_to_nuts_old(
    load_df: pd.DataFrame,  # DataFrame with country-level load data
    regions: gpd.GeoDataFrame,  # GeoDataFrame with existing gdp and pop columns
    distribution_key: dict = {"gdp": 0.6, "pop": 0.4},  # 60/40 split
) -> gpd.GeoDataFrame:
    """
    Distribute country-level load data to NUTS regions based on existing GDP and population columns.

    Parameters:
    - load_df: pd.DataFrame, country-level load data with columns as countries and rows as time
    - regions: gpd.GeoDataFrame, GeoDataFrame with NUTS regions including 'gdp' and 'pop' columns
    - distribution_key: dict, weights for GDP and population (default: 60/40 split)

    Returns:
    - gpd.GeoDataFrame: GeoDataFrame with distributed load mapped to NUTS regions
    """
    # Apply 60/40 split for load distribution
    gdp_weight = distribution_key["gdp"]  # GDP weight (default 60%)
    pop_weight = distribution_key["pop"]  # Population weight (default 40%)
    regions["load_factor"] = gdp_weight * (
        regions["gdp"] / regions["gdp"].sum()
    ) + pop_weight * (regions["pop"] / regions["pop"].sum())

    # Scale load data to NUTS regions
    for country in load_df.columns:
        if country in regions["country"].unique():
            regions.loc[regions["country"] == country, "load"] = (
                regions["load_factor"] * load_df[country].sum()
            )

    # Return the processed GeoDataFrame with updated loads
    return regions


def distribute_load_to_nuts(
    load_df: pd.DataFrame,  # Country-level load data
    regions: gpd.GeoDataFrame,  # GeoDataFrame with GDP and population columns
    distribution_key: dict = {"gdp": 0.6, "pop": 0.4},  # Load distribution weights
) -> gpd.GeoDataFrame:
    """
    Compute load factor and distribute load per country based on GDP and population.

    Parameters:
    - load_df: pd.DataFrame, country-level load data with countries as columns and rows as time
    - regions: gpd.GeoDataFrame, GeoDataFrame with NUTS regions including 'gdp' and 'pop' columns
    - distribution_key: dict, weights for GDP and population (default: 60/40 split)

    Returns:
    - gpd.GeoDataFrame: GeoDataFrame with calculated load factors and distributed load per country.
    """

    # Initialize load_factor to ensure all regions have a value
    regions["load_factor"] = 0.0
    regions["load"] = 0.0  # Initialize load column

    # Compute load factor independently per country
    for country in regions["country"].unique():
        country_mask = regions["country"] == country

        total_gdp = regions.loc[country_mask, "gdp"].sum()
        total_pop = regions.loc[country_mask, "pop"].sum()

        if total_gdp > 0 and total_pop > 0:
            regions.loc[country_mask, "load_factor"] = distribution_key["gdp"] * (
                regions.loc[country_mask, "gdp"] / total_gdp
            ) + distribution_key["pop"] * (regions.loc[country_mask, "pop"] / total_pop)

    # Scale load data to NUTS regions per country
    for country in load_df.columns:
        if country in regions["country"].unique():
            country_mask = regions["country"] == country
            total_load = load_df[country].sum()  # Get total load for the country

            if total_load > 0:
                regions.loc[country_mask, "load"] = (
                    regions.loc[country_mask, "load_factor"] * total_load
                )

    return regions
