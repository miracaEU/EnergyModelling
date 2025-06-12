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
import geopandas as gpd
import logging
from shapely.geometry import MultiPolygon
import os

# Set up logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

EXCHANGE_EUR_USD_2019 = 1.1
EXCHANGE_EUR_USD_2014 = 1.246

OTHER_GDP_TOTAL_2019 = {  # in bn. USD
    "BA": 20.48,  # World Bank
    "MD": 11.74,  # World Bank
    "UA": 153.9,  # World Bank
    "XK": 7.9,  # https://de.statista.com/statistik/daten/studie/415738/umfrage/bruttoinlandsprodukt-bip-des-kosovo/
    "UK": 3006 / EXCHANGE_EUR_USD_2014,  # World Bank 2014 EUR
    "GB": 3006 / EXCHANGE_EUR_USD_2014,  # World Bank 2014 EUR
}
OTHER_POP_2019 = {  # in 1000 persons
    "BA": 3361,  # World Bank
    "MD": 2664,  # World Bank
    "UA": 44470,  # World Bank
    "XK": 1782,  # World Bank
}


# Function to normalize text fields
def normalize_text(text):
    """
    Normalize region identifiers by removing diacritics and special characters.
    """
    import unicodedata

    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    return text.replace("*", "")


# Function to simplify geometries
def simplify_geometries(regions, min_area=500_000_000, max_distance=200_000):
    """
    Simplify regions by removing small islands and distant geometries.
    """

    def simplify_polygon(polygon, min_area, max_distance):
        if isinstance(polygon, MultiPolygon):
            main_polygon = max(polygon.geoms, key=lambda p: p.area)
            return main_polygon if main_polygon.area > min_area else polygon
        return polygon

    regions["geometry"] = regions.geometry.map(
        lambda geom: simplify_polygon(geom, min_area, max_distance)
    )
    return regions


# Function to clean GDP and population datasets
def clean(df, period):
    """
    Clean the dataset by filtering rows and columns, removing missing values, and renaming columns.
    """
    # Step 1: Filter rows and columns
    df_cleaned = df[["geo", "TIME_PERIOD", "OBS_VALUE"]]

    # Step 2: Drop rows with missing values
    df_cleaned = df_cleaned.dropna()

    # Step 3: Filter by year
    df_cleaned = df_cleaned[df_cleaned["TIME_PERIOD"] == period]

    # Step 4: Rename columns for clarity
    df_cleaned.rename(columns={"geo": "region_id", "OBS_VALUE": "value"}, inplace=True)

    return df_cleaned


def map_attributes(regions, gdp_data, pop_data):
    """
    Map GDP and population data to regions with hierarchical fallback logic, handling duplicates and missing values.
    """
    regions["id"] = regions["id"].apply(normalize_text)

    gdp_data.index = gdp_data.index.str.replace(r"^GR", "EL", regex=True)
    pop_data.index = pop_data.index.str.replace(r"^GR", "EL", regex=True)
    # gdp_data.index = gdp_data.index.str.replace(r"^UK", "GB", regex=True)
    # pop_data.index = pop_data.index.str.replace(r"^UK", "GB", regex=True)

    # Remove duplicate entries in GDP and population data
    gdp_data = gdp_data[~gdp_data.index.duplicated(keep="first")]
    pop_data = pop_data[~pop_data.index.duplicated(keep="first")]

    """ 
    Adding Non NUTS Countries 
    """
    # Non NUTS countries
    logger.info("Processing non-NUTS regions.")

    ba_adm1 = gpd.read_file(
        os.path.join(
            os.getcwd(),
            "Data\\geoBoundaries-BIH-ADM1-all\\geoBoundaries-BIH-ADM1.geojson",
        )
    )
    md_adm1 = gpd.read_file(
        os.path.join(
            os.getcwd(),
            "Data\\geoBoundaries-MDA-ADM1-all\\geoBoundaries-MDA-ADM1.geojson",
        )
    )
    ua_adm1 = gpd.read_file(
        os.path.join(
            os.getcwd(),
            "Data\\geoBoundaries-UKR-ADM1-all\\geoBoundaries-UKR-ADM1.geojson",
        )
    )

    regions_non_nuts = pd.concat([ba_adm1, md_adm1, ua_adm1])
    regions_non_nuts = regions_non_nuts.drop(columns=["shapeID"])

    # Normalise text
    regions_non_nuts["id"] = regions_non_nuts["shapeISO"].apply(normalize_text)
    regions_non_nuts["name"] = regions_non_nuts["shapeName"].apply(normalize_text)
    # Extract first two letters OR substring before "-"
    regions_non_nuts["country"] = regions_non_nuts["id"].apply(
        lambda x: x.split("-")[0] if "-" in x else x[:2]
    )

    # Add level columns
    regions_non_nuts["level1"] = regions_non_nuts["id"]
    regions_non_nuts["level2"] = regions_non_nuts["id"]
    regions_non_nuts["level3"] = regions_non_nuts["id"]

    # Concatenate NUTS and non-NUTS regions
    logger.info("Harmonising NUTS and non-NUTS regions.")
    regions = pd.concat([regions, regions_non_nuts])

    # Map GDP data
    try:
        regions["gdp"] = (
            gdp_data.loc[regions["id"], "value"]
            .reindex(regions["id"], fill_value=0)
            .values
        )
    except KeyError:
        missing_gdp = list(set(regions["id"]) - set(gdp_data.index))
        # logger.warning(f"Missing GDP data for regions: {missing_gdp}")
        regions["gdp"] = regions["id"].map(
            lambda region: gdp_data["value"].get(region, 0)
        )

    # Map Population data
    try:
        regions["pop"] = (
            pop_data.loc[regions["id"], "value"]
            .reindex(regions["id"], fill_value=0)
            .values
        )
    except KeyError:
        # missing_pop = list(set(regions["id"]) - set(pop_data.index))
        # logger.warning(f"Missing population data for regions: {missing_pop}")
        regions["pop"] = regions["id"].map(
            lambda region: pop_data["value"].get(region, float("nan"))
        )

    # Define the countries we want to assign values for
    specified_countries = ["BA", "MD", "UA", "XK"]

    # Filter regions for only the specified countries
    regions_filtered = regions[regions["id"].str[:2].isin(specified_countries)].copy()

    # Assign population values explicitly for each country
    for country_code in specified_countries:
        regions_filtered.loc[regions_filtered["id"].str[:2] == country_code, "pop"] = (
            OTHER_POP_2019[country_code]
        )

    # Scale population values proportionally
    total_pop = regions_filtered["pop"].sum()
    if total_pop > 0:
        for country_code in specified_countries:
            country_mask = regions_filtered["id"].str[:2] == country_code
            regions_filtered.loc[country_mask, "pop"] = (
                regions_filtered.loc[country_mask, "pop"]
                / total_pop
                * OTHER_POP_2019[country_code]
            ).round(0)

    # Assign GDP values explicitly for each country
    for country_code in specified_countries:
        regions_filtered.loc[regions_filtered["id"].str[:2] == country_code, "gdp"] = (
            OTHER_GDP_TOTAL_2019[country_code]
        )

    # Assign correct population distribution per region
    for country_code in specified_countries:
        country_mask = regions_filtered["id"].str[:2] == country_code
        country_region_count = country_mask.sum()  # Number of regions in that country

        if country_region_count > 0:
            population = (OTHER_POP_2019[country_code] / country_region_count).round(
                0
            )  # Divide total population equally among regions
            regions_filtered.loc[country_mask, "pop"] = population

            regions_gdp = (
                OTHER_GDP_TOTAL_2019[country_code]
                * 1e9
                / country_region_count
                / EXCHANGE_EUR_USD_2019
            ).round(
                0
            )  # Properly distribute GDP across regions

            regions_filtered.loc[country_mask, "gdp"] = regions_gdp / (
                population * 1000
            )

    # Merge updated values back into the main dataframe
    regions = regions.merge(
        regions_filtered, on="id", how="left", suffixes=("", "_new")
    )

    # Ensure only new population and GDP values are applied
    # regions["pop"] = regions["pop_new"].fillna(regions["pop"])
    regions["pop"] = regions["pop_new"].fillna(regions["pop"]).astype(float)

    regions["gdp"] = regions["gdp_new"].fillna(regions["gdp"])

    # Drop temporary columns
    regions.drop(columns=["pop_new", "gdp_new"], inplace=True)

    # Fallback for regions still missing GDP
    missing_gdp = regions[regions["gdp"] == 0]  # GDP fallback
    if not missing_gdp.empty:
        for idx, row in missing_gdp.iterrows():
            # Extract country code from the first two letters of region ID
            country_code = row["id"][:2]

            country_subset = regions[
                regions["country"] == country_code
            ]  # Select regions belonging to the country
            country_subset["pop"] = pd.to_numeric(
                country_subset["pop"], errors="coerce"
            )  # Ensure numeric
            # total_population = country_subset["pop"].sum()  # Get population sum for that country
            # print(f"Total population for {country_code}: {total_population}")

            # Fallback to country-level GDP using the derived country code
            if country_code in OTHER_GDP_TOTAL_2019:
                total_gdp = (
                    OTHER_GDP_TOTAL_2019[country_code] * 1e9
                )  # Convert to full amount
                country_subset["pop"] = country_subset["pop"].fillna(
                    country_subset["pop"].median()
                )
                # country_subset["pop"].fillna(country_subset["pop"].median(), inplace=True)  # Uses median as a fallback
                if not pd.isna(
                    country_subset.loc[idx, "pop"]
                ):  # Check valid population
                    # regions.loc[idx, "gdp"] = (regions.loc[idx, "pop"] / regions["pop"].sum()) * total_gdp
                    region_gdp = (
                        country_subset["pop"] / country_subset["pop"].sum()
                    ) * total_gdp  # in Euros
                    country_subset["gdp"] = region_gdp / (country_subset["pop"] * 1000)

        # Merge updated values back into the main dataframe
        regions = regions.merge(
            country_subset, on="id", how="left", suffixes=("", "_new")
        )

    # Ensure only new population and GDP values are applied
    # regions["pop"] = regions["pop_new"].fillna(regions["pop"])
    regions["pop"] = regions["pop_new"].fillna(regions["pop"]).astype(float)

    regions["gdp"] = regions["gdp_new"].fillna(regions["gdp"])

    # Identify columns that end with '_new'
    columns_to_drop = [col for col in regions.columns if col.endswith("_new")]

    # Drop them from the DataFrame
    regions.drop(columns=columns_to_drop, inplace=True)

    return regions


def load_and_modify_UK():
    """
    nama_10r_3popgdp.tsv.gz

    Population by NUTS3 region
    Source: http://appsso.eurostat.ec.europa.eu/nui/show.do?dataset=nama_10r_3popgdp&lang=en
    Terms of Use:
    https://ec.europa.eu/eurostat/about/policies/copyright

    from:
        Hörsch, J., Hofmann, F., Schlachtberger, D., Glaum, P., Neumann, F., Brown, T., Riepin, I., & Xiong, B. (2025). Data Bundle for PyPSA-Eur: An Open Optimisation Model of the European Transmission System (v0.6.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.15143557

    Returns
    -------
    df_uk : TYPE
        DESCRIPTION.

    """

    # Load the TSV file
    df = pd.read_csv("Data\\nama_10r_3popgdp.tsv", sep="\t", encoding="utf-8")
    # Split 'unit,geo' into separate columns
    df[["unit", "geo"]] = df["unit,geo\\time"].str.split(",", expand=True)
    # Convert years to proper columns
    df = df.drop(columns=["unit,geo\\time"])  # Remove old merged column
    # Restructure dataframe to include TIME_PERIOD and OBS_VALUE for 2014
    df_uk = df[["geo", "2014 "]].rename(columns={"geo": "GEO", "2014 ": "value"})
    # Add TIME_PERIOD column
    df_uk["TIME_PERIOD"] = 2014
    # Reorder columns
    df_uk = df_uk[["GEO", "TIME_PERIOD", "value"]]
    # Rename 'geo' to 'region_id' and set it as the index
    df_uk = df_uk.rename(columns={"GEO": "region_id"}).set_index("region_id")
    # Filter index for regions that start with 'UK'
    df_uk = df_uk[df_uk.index.str.startswith("UK")]
    return df_uk


def process_regions(
    nuts_path,
    uk_path,
    gdp_data_path,
    pop_data_path,
    country_list,
    period=2019,
    nuts_level="NUTS3",
):
    """
    Process and harmonize NUTS regions with GDP and population data, handling duplicates and missing values.
    """
    # Load NUTS regions
    logger.info(f"Loading {nuts_level} regions from shapefile.")
    regions = gpd.read_file(nuts_path)

    uk_nuts_2021 = gpd.read_file(uk_path)
    # Ensure both datasets have the same CRS
    uk_nuts_2021 = uk_nuts_2021.to_crs(regions.crs)
    # Concatenate UK data with NUTS 2024 dataset
    regions = gpd.GeoDataFrame(pd.concat([regions, uk_nuts_2021], ignore_index=True))

    # Filter based on NUTS level
    if nuts_level == "NUTS3":
        logger.info("Filtering for NUTS3 regions.")
        regions = regions[regions["LEVL_CODE"] == 3]
    elif nuts_level == "NUTS2":
        logger.info("Fallback to NUTS2 regions as NUTS3 is unavailable.")
        regions = regions[regions["LEVL_CODE"] == 2]

    # Rename columns and add hierarchical levels
    logger.info("Renaming columns and adding hierarchical levels.")
    regions = regions.rename(
        columns={"NUTS_ID": "id", "CNTR_CODE": "country", "NAME_LATN": "name"}
    )
    regions["level1"] = regions["id"].str[:3]  # NUTS1
    regions["level2"] = regions["id"].str[:4]  # NUTS2
    regions["level3"] = regions["id"] if nuts_level == "NUTS3" else None

    # Load and clean GDP and population data
    logger.info("Cleaning GDP and population data.")
    gdp_raw = pd.read_csv(gdp_data_path)
    pop_raw = pd.read_csv(pop_data_path)

    gdp_cleaned = clean(gdp_raw, period).set_index("region_id")
    pop_cleaned = clean(pop_raw, period).set_index("region_id")
    # Added later
    pop_uk = load_and_modify_UK()
    pop_cleaned = pd.concat([pop_cleaned, pop_uk])

    # Map attributes to regions
    logger.info("Mapping GDP and population data to regions.")
    regions = map_attributes(regions, gdp_cleaned, pop_cleaned)

    # Filter by country list
    logger.info("Filtering regions by country list.")
    regions = regions.query("country in @country_list")

    # Drop rows with nan values in pop, gdp
    regions = regions.dropna(subset=["pop", "gdp"])

    regions = regions.dropna(axis=1, how="all")
    # Simplify geometries
    logger.info("Simplifying geometries for efficiency.")
    regions = simplify_geometries(regions)

    return regions
