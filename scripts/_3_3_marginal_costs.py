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

[2] International Renewable Energy Agency. (2012). Renewable energy technologies: Cost analysis series – Hydropower.
IRENA. Retrieved from https://www.irena.org/Publications/2012/Jun/Renewable-Energy-Cost-Analysis---Hydropower
"""

import pandas as pd


def calculate_annuity(n: float, r: float | pd.Series) -> float | pd.Series:
    """
    Calculate the annuity factor for an asset with lifetime n years and discount rate r.

    The annuity factor is used to calculate the annual payment required to pay off a loan
    over n years at interest rate r. For example, annuity(20, 0.05) * 20 = 1.6.

    Parameters
    ----------
    n : float
        Lifetime of the asset in years
    r : float | pd.Series
        Discount rate (interest rate). Can be a single float or a pandas Series of rates.

    Returns
    -------
    float | pd.Series
        Annuity factor. Returns a float if r is float, or pd.Series if r is pd.Series.

    Examples
    --------
    >>> calculate_annuity(20, 0.05)
    0.08024258718774728
    """
    if isinstance(r, pd.Series):
        return pd.Series(1 / n, index=r.index).where(
            r == 0, r / (1.0 - 1.0 / (1.0 + r) ** n)
        )
    elif r > 0:
        return r / (1.0 - 1.0 / (1.0 + r) ** n)
    else:
        return 1 / n


# Fill missing values in the costs DataFrame using fill_values
fill_values = {
    "FOM": 0,
    "VOM": 0,
    "efficiency": 1,
    "fuel": 0,
    "investment": 0,
    "lifetime": 25,
    "CO2 intensity": 0,
    "discount rate": 0.07,
}

# Define marginal cost overwrites
marginal_cost = {
    "solar": 0.01,
    "onwind": 0.015,
    "offwind": 0.015,
    "hydro": 0.0,
    "H2": 0.0,
    "electrolysis": 0.0,
    "fuel cell": 0.0,
    "battery": 0.0,
    "battery inverter": 0.0,
    "home battery storage": 0.0,
    "water tank charger": 0.03,
    "central water pit charger": 0.025,
}


def load_costs(cost_file: str, nyears) -> pd.DataFrame:
    """
    Load cost data from CSV and prepare it.

    Parameters
    ----------
    cost_file : str
        Path to the CSV file containing cost data
    nyears : float, optional
        Number of years for investment, by default 1.0

    Returns
    -------
    costs : pd.DataFrame
        DataFrame containing the processed cost data
    """
    # set all asset costs and other parameters
    costs = pd.read_csv(cost_file, index_col=[0, 1]).sort_index()
    # correct units to MW and EUR
    costs.loc[costs.unit.str.contains("/kW"), "value"] *= 1e3
    costs.loc[costs.unit.str.contains("/GW"), "value"] /= 1e3

    costs.unit = costs.unit.str.replace("/kW", "/MW")
    costs.unit = costs.unit.str.replace("/GW", "/MW")

    # min_count=1 is important to generate NaNs which are then filled by fillna
    costs = costs.value.unstack(level=1).groupby("technology").sum(min_count=1)
    costs = costs.fillna(fill_values)

    annuity_factor = calculate_annuity(costs["lifetime"], costs["discount rate"])
    annuity_factor_fom = annuity_factor + costs["FOM"] / 100.0
    costs["capital_cost"] = annuity_factor_fom * costs["investment"] * nyears

    costs.at["OCGT", "fuel"] = costs.at["gas", "fuel"]
    costs.at["CCGT", "fuel"] = costs.at["gas", "fuel"]

    costs["marginal_cost"] = costs["VOM"] + costs["fuel"] / costs["efficiency"]

    costs.at["OCGT", "CO2 intensity"] = costs.at["gas", "CO2 intensity"]
    costs.at["CCGT", "CO2 intensity"] = costs.at["gas", "CO2 intensity"]

    costs.at["solar", "capital_cost"] = costs.at["solar-utility", "capital_cost"]
    costs = costs.rename({"solar-utility single-axis tracking": "solar-hsat"})

    # Map marginal costs and combine with existing column
    mapped_costs = pd.Series(costs.index.map(marginal_cost), index=costs.index)
    costs["marginal_cost"] = mapped_costs.combine_first(costs["marginal_cost"])

    return costs


# Mapping dictionary
tech_to_carrier = {
    "Pumped Storage": "hydro",
    "Run-Of-River": "hydro",
    "Steam Turbine": "nuclear",
    "Wind": "wind",
}

"""
# Map technology to carrier
costs["carrier"] = costs["technology"].map(tech_to_carrier)
# Set carrier as part of the index
costs = costs.set_index("carrier", append=True)
"""


def replace_natural_gas_technology(
    df, fuel_type="Natural Gas", default_technology="CCGT"
):
    """
    Replace technologies based on a mapping for a specific fuel type.

    Parameters:
    df (DataFrame): Input data frame containing 'Technology' and 'Fueltype' columns.
    fuel_type (str): The fuel type to apply the replacement logic (default is 'Natural Gas').
    default_technology (str): Default technology to assign if not mapped (default is 'CCGT').

    Returns:
    Series: Updated 'Technology' column.
    """
    mapping = {
        "Steam Turbine": "CCGT",
        "Combustion Engine": "OCGT",
        "Not Found": "CCGT",
    }
    # Apply mapping and default technology
    tech = df.Technology.replace(mapping).fillna(default_technology)
    return df.Technology.mask(df.Fueltype == fuel_type, tech)


def replace_natural_gas_fueltype(
    df, technology_list=("OCGT", "CCGT"), target_fuel_type="Natural Gas"
):
    """
    Replace fuel types for specific technologies.

    Parameters:
    df (DataFrame): Input data frame containing 'Technology' and 'Fueltype' columns.
    technology_list (tuple): List of technologies to apply the replacement logic (default includes 'OCGT' and 'CCGT').
    target_fuel_type (str): Fuel type to assign to matching technologies (default is 'Natural Gas').

    Returns:
    Series: Updated 'Fueltype' column.
    """
    return df.Fueltype.mask(df.Technology.isin(technology_list), target_fuel_type)


def calculate_hydro_marginal_cost(
    capacity_mw,
    efficiency,
    investment_cost,
    lifetime_years,
    hours_per_year,
    annual_operating_cost,
    pumping_cost=None,
):
    """
    Calculate the marginal cost of a hydro power plant (conventional or PHS).

    Parameters:
    capacity_mw (float): Installed capacity of the plant in MW.
    efficiency (float): Efficiency of the plant (e.g., 0.9 for 90%).
    hours_per_year (int): Expected hours of operation per year.
    investment_cost (float): Total investment cost in currency units.
    lifetime_years (int): Expected lifetime of the plant in years.
    annual_operating_cost (float): Total annual operating cost in currency units.
    pumping_cost (float, optional): Cost of pumping energy for PHS in €/MWh. Defaults to None for conventional hydro.
    round_trip_efficiency (float, optional): Round-trip efficiency for PHS (e.g., 0.8 for 80%). Defaults to None for conventional hydro.

    Returns:
    float: Marginal cost per MWh.
    """
    if capacity_mw == 0:
        return 0

    # Determine if PHS-specific parameters are provided
    if pumping_cost is not None:
        # Effective energy output for PHS considering round-trip efficiency
        effective_energy_output_mwh = capacity_mw * efficiency * hours_per_year
        # Total annual cost including pumping cost for PHS
        total_annual_cost = (
            (investment_cost / lifetime_years)
            + annual_operating_cost
            + (pumping_cost * capacity_mw * hours_per_year)
        )
    else:
        # Conventional hydro: annual energy production
        effective_energy_output_mwh = capacity_mw * efficiency * hours_per_year
        # Total annual cost for conventional hydro
        total_annual_cost = (investment_cost / lifetime_years) + annual_operating_cost

    # Calculate marginal cost per MWh
    marginal_cost_per_mwh = total_annual_cost / effective_energy_output_mwh

    return marginal_cost_per_mwh


def dynamic_operating_cost_and_time(capacity_mw, is_phs=False):
    """
    Calculate operating cost and time dynamically based on [1]:

    Hydropower Type	Capacity Factor (%)	Operating Hours (hours/year)
    Large hydro	25 – 90	2,190 – 7,884
    Small hydro	20 – 95	1,752 – 8,322

    Large-scale hydropower: $45/kW/year
    Small-scale hydropower: $52/kW/year

    Large hydro:
    Average capacity factor: (25% + 90%) / 2 = 57.5%
    Average operating hours: 57.5% × 8,760 = ~5,038 hours/year
    Small hydro:
    Average capacity factor: (20% + 95%) / 2 = 57.5%
    Average operating hours: 57.5% × 8,760 = ~5,038 hours/year

    [2] International Renewable Energy Agency. (2012). Renewable energy technologies: Cost analysis series – Hydropower.
    IRENA. Retrieved from https://www.irena.org/Publications/2012/Jun/Renewable-Energy-Cost-Analysis---Hydropower

    Parameters:
    capacity_mw (float): Installed capacity of the plant in MW.
    is_phs (bool): Whether the plant is PHS. Defaults to False.

    Returns:
    tuple: Updated operating cost and time.
    """
    # Base values for EU hydro plants
    base_cost_per_mw_small = 52000  # Small hydro O&M cost per MW in euros
    base_cost_per_mw_large = 45000  # Large hydro O&M cost per MW in euros
    base_hours_per_year = 5000

    # PHS-specific adjustment (if applicable)
    if is_phs:
        base_hours_per_year = 4000  # PHS typically operates fewer hours per year

    # Adjust base cost per MW using capacity (smaller plants have higher cost per MW)
    if capacity_mw <= 20:  # Small hydro
        base_cost_per_mw = base_cost_per_mw_small
    else:  # Medium to large hydro
        base_cost_per_mw = base_cost_per_mw_large

    # Calculate dynamic operating cost and operating time
    operating_cost = base_cost_per_mw * capacity_mw
    operating_time = base_hours_per_year

    return operating_cost, operating_time


def process_powerplants_data(
    ppl_fn: str,
    costs: pd.DataFrame,
    fuel_price: pd.DataFrame,
    relevant_columns: list = None,
    exclude_carriers: list = None,
) -> pd.DataFrame:
    """
    Load and preprocess powerplant data with relevant cost attributes for mapping.

    Parameters:
        ppl_fn : str
            Path to the CSV file containing powerplant data.
        costs : pd.DataFrame
            DataFrame containing cost data for technologies.
        relevant_columns : list, optional
            List of cost columns to include in the final DataFrame (default: basic attributes).
        exclude_carriers : list, optional
            List of carriers to exclude (default: empty).

    Returns:
        pd.DataFrame
            Processed powerplant data with relevant attributes for mapping.
    """
    if not relevant_columns:
        relevant_columns = [
            "VOM",
            "efficiency",
            "marginal_cost",
            "fuel",
            "CO2 intensity",
            "capital_cost",
            "lifetime",
        ]

    if not exclude_carriers:
        exclude_carriers = []

    # Simplify carrier and technology mappings
    carrier_dict = {
        "ocgt": "OCGT",
        "ccgt": "CCGT",
        "bioenergy": "biomass",
        "ccgt, thermal": "CCGT",
        "hard coal": "coal",
        "waste": "waste CHP",
    }
    tech_dict = {
        "Run-Of-River": "ror",
        "Reservoir": "hydro",
        "Pumped Storage": "PHS",
        "PV": "solar",
        "Onshore": "onwind",
        "Offshore": "offwind",
    }

    ppl = (
        pd.read_csv(ppl_fn, index_col=0)
        .assign(
            Technology=replace_natural_gas_technology
        )  # Replace technology for natural gas
        .assign(
            Fueltype=replace_natural_gas_fueltype
        )  # Replace fuel type for specific technologies
        .replace(
            {"Solid Biomass": "Bioenergy", "Biogas": "Bioenergy"}
        )  # Replace specific fuel types
    )

    # Load powerplant data and map carriers/technologies
    ppl = (
        ppl.assign(
            Fueltype=ppl["Fueltype"].str.lower()
        )  # Convert Fueltype to lowercase
        .rename(columns=str.lower)  # Rename columns to lowercase
        .replace({"fueltype": carrier_dict, "technology": tech_dict})  # Replace values
    )

    # Filter out excluded carriers
    ppl = ppl[~ppl["fueltype"].isin(exclude_carriers)]

    # Map costs based on carriers
    cost_columns = relevant_columns + ["technology"]  # Add tech column for joins

    # Replace carriers "natural gas" and "hydro" with the respective technology;
    # OCGT or CCGT and hydro, PHS, or ror)
    ppl["fueltype"] = ppl.fueltype.where(
        ~ppl.fueltype.isin(["hydro", "natural gas"]), ppl.technology
    )

    # Move index to a regular column
    costs = costs.reset_index()

    ppl_save = ppl.copy()

    ppl = pd.merge(
        ppl,
        costs[cost_columns],
        how="left",
        left_on="fueltype",
        right_on="technology",
        suffixes=("", "_r"),
    )

    # Perform the merge
    merged = ppl_save.merge(
        costs[cost_columns],
        how="left",
        left_on="technology",
        right_on="technology",
        suffixes=("", "_r"),
    )

    # Only overwrite values where technology is 'onwind' or 'offwind'
    ppl.loc[ppl["technology"].isin(["onwind", "offwind"]), cost_columns] = merged[
        cost_columns
    ]

    # Get the marginal cost for "onwind"
    onwind_cost = ppl.loc[ppl["technology"] == "onwind", "marginal_cost"].values[0]

    # Fill NaN values in "marginal_cost" for all "wind" types
    ppl.loc[
        (ppl["fueltype"].str.contains("wind")) & (ppl["marginal_cost"].isna()),
        "marginal_cost",
    ] = onwind_cost

    if fuel_price is not None:
        ppl["fuel"] = ppl.apply(
            lambda row: fuel_price.iloc[0].get(row["fueltype"], row["fuel"]), axis=1
        )

    ppl["efficiency"] = ppl.efficiency.combine_first(ppl.efficiency_r)
    ppl["lifetime"] = (ppl.dateout - ppl.datein).fillna(ppl["lifetime"])
    ppl["build_year"] = ppl.datein.fillna(0).astype(int)

    # Fill missing values in efficiency using efficiency_r
    ppl["efficiency"] = ppl["efficiency"].combine_first(ppl["efficiency_r"]).fillna(1)

    # Apply marginal cost formula only to fuel types in fuel_price
    ppl.loc[ppl["fueltype"].isin(fuel_price.keys()), "marginal_cost"] = (
        ppl["VOM"] + ppl["fuel"] / ppl["efficiency"]
    )

    if ppl["fueltype"].isin(["hydro", "ror"]).any():
        # Update only rows where fueltype is "hydro" or "ror"
        ppl.loc[ppl["fueltype"].isin(["hydro", "ror"]), "marginal_cost"] = ppl.loc[
            ppl["fueltype"].isin(["hydro", "ror"])
        ].apply(
            lambda row: calculate_hydro_marginal_cost(
                capacity_mw=row["capacity"],
                efficiency=row["efficiency_r"],
                investment_cost=row["capital_cost"],
                lifetime_years=row["lifetime"],
                hours_per_year=dynamic_operating_cost_and_time(row["capacity"])[1],
                annual_operating_cost=dynamic_operating_cost_and_time(row["capacity"])[
                    0
                ],
            ),
            axis=1,
        )

    if ppl["fueltype"].isin(["PHS"]).any():
        # Update only rows where fueltype is "phs" (Pumped Hydro Storage)
        ppl.loc[ppl["fueltype"].isin(["PHS"]), "marginal_cost"] = ppl.loc[
            ppl["fueltype"].isin(["PHS"])
        ].apply(
            lambda row: calculate_hydro_marginal_cost(
                capacity_mw=row["capacity"],
                efficiency=row["efficiency_r"],
                investment_cost=row["capital_cost"],
                lifetime_years=row["lifetime"],
                hours_per_year=dynamic_operating_cost_and_time(row["capacity"])[1],
                annual_operating_cost=dynamic_operating_cost_and_time(row["capacity"])[
                    0
                ],
                pumping_cost=50,  # Example pumping cost in €/MWh
            ),
            axis=1,
        )

    return ppl
