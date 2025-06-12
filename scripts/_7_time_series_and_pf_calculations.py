# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

import pandas as pd


def run_dc_opf(net, pp):
    """
    Run DC Optimal Power Flow (DC OPF) on a Pandapower network.

    Parameters:
    net (pandapowerNet): Pandapower network object with costs and constraints.

    Returns:
    dict: OPF results for buses, generators, and lines.
    """
    try:
        # Execute DC OPF
        pp.rundcopp(
            net,
            delta=0.01,
            trafo_model="t",
            enforce_q_lims=False,
            check_connectivity=True,
        )

    except Exception as e:
        print(f"DC OPF did not converge: {e}")
        return None


def run_ac_opf(net, pp):
    """
    Run AC Optimal Power Flow (AC OPF) on a Pandapower network.

    Parameters:
    net (pandapowerNet): Pandapower network object with costs and constraints.

    Returns:
    dict: OPF results for buses, generators, and lines.
    """
    try:
        # Execute AC OPF
        pp.runopp(net)

        # Collect results
        results = {
            "bus": net.res_bus,  # Bus voltage and angles
            "gen": net.res_gen,  # Generator outputs and costs
            "load": net.res_load,  # Load power consumption
            "line": net.res_line,  # Line flows and loading
        }
        return results
    except Exception as e:
        print(f"AC OPF did not converge: {e}")
        return None


def adjust_hvdc_link_capacity(network):
    """
    Adjusts max_i_ka for HVDC lines based on system size.

    Parameters:
    - network: Pandapower network object

    Returns:
    - network: Updated network object with adjusted HVDC capacities.
    """

    # Get total bus count
    num_buses = len(network.bus)

    # Define scaling factor based on thresholds
    if num_buses >= 1000:
        increase_factor = 5
    elif num_buses >= 500:
        increase_factor = 2.5

    if num_buses >= 500:
        # Identify HVDC lines
        hvdc_lines = network.line[
            network.line["name"].str.startswith("HVDC Link", na=False)
        ]

        # Apply the scaling factor
        network.line.loc[hvdc_lines.index, "max_i_ka"] *= increase_factor


def allocate_renewable_generation(network, country_generation, renewable):
    """
    Allocates generation for a specified renewable technology (solar, wind, onwind, offwind).

    Parameters:
    - network: The energy network containing generator data.
    - country_generation: The total generation capacity to be allocated.
    - renewable: The type of renewable energy ('solar', 'wind', 'onwind', 'offwind').
    """

    # Ensure valid input
    if renewable not in ["Solar", "onwind", "offwind", "wind"]:
        raise ValueError(
            "Invalid renewable type. Choose from 'solar', 'onwind', 'offwind' or 'wind'."
        )

    # Get total maximum capacity for selected renewable type
    total_max_capacity = network.gen.loc[
        network.gen["tech"] == renewable, "p_mw_original"
    ].sum()

    # Ensure total generation does not exceed network max capacity
    country_generation = min(country_generation, total_max_capacity)

    # Assign initial generation values
    network.gen.loc[network.gen["tech"] == renewable, "p_mw"] = (
        network.gen.loc[network.gen["tech"] == renewable, "normed_p_mw"]
        * country_generation
    )

    # Check for excess generation beyond p_max
    excess_generation = (
        network.gen.loc[network.gen["tech"] == renewable, "p_mw"]
        - network.gen.loc[network.gen["tech"] == renewable, "p_mw_original"]
    )
    excess_generation = excess_generation.where(excess_generation > 0, 0)

    # Reduce generation to meet p_max limits
    network.gen.loc[network.gen["tech"] == renewable, "p_mw"] -= excess_generation

    # Redistribute excess to generators with available capacity
    available_generators = network.gen.loc[
        network.gen["p_mw"] < network.gen["p_mw_original"]
    ]

    if not available_generators.empty:
        total_available_capacity = (
            available_generators["p_mw_original"] - available_generators["p_mw"]
        ).sum()

        if total_available_capacity > 0:
            scaling_factor = excess_generation.sum() / total_available_capacity
            network.gen.loc[available_generators.index, "p_mw"] += (
                available_generators["p_mw_original"] - available_generators["p_mw"]
            ) * scaling_factor

    # Assign initial generation values
    network.gen.loc[network.gen["tech"] == renewable, "min_p_mw"] = network.gen.loc[
        network.gen["tech"] == renewable, "p_mw"
    ]
    network.gen.loc[network.gen["tech"] == renewable, "max_p_mw"] = network.gen.loc[
        network.gen["tech"] == renewable, "p_mw"
    ]


def create_values_per_country(network, processed_regions, force_update):
    # Define mapping for generation types and technologies
    categories = {"solar": "type", "wind": "type", "onwind": "tech", "offwind": "tech"}

    # Extract unique countries
    countries = processed_regions["country"].unique()

    # Match generators to buses and retrieve the country
    network.gen["country"] = network.gen["bus"].map(network.bus["zone"])

    # Initialize storage for cached values
    if force_update or not hasattr(create_values_per_country, "cached_values"):
        create_values_per_country.cached_values = {}

        for country in countries:
            # Filter generators based on country
            if country == "UK":
                country = "GB"
            country_gen = network.gen[network.gen["country"] == country]

            # Compute total maximum for each category
            totals = {
                key: country_gen[country_gen[value] == key]["p_mw_original"].sum()
                for key, value in categories.items()
            }

            # Normalize values per country
            for key, value in categories.items():
                if totals[key] > 0:
                    network.gen.loc[
                        (network.gen["country"] == country)
                        & (network.gen[value] == key),
                        "normed_p_mw",
                    ] = (
                        network.gen.loc[
                            (network.gen["country"] == country)
                            & (network.gen[value] == key),
                            "p_mw_original",
                        ]
                        / totals[key]
                    )
                else:
                    # print(f"Warning: total_max_{key} for {country} is zero. Cannot normalize values.")
                    None
            # Store values in cache
            create_values_per_country.cached_values[country] = totals

    # Return cached values for each country
    return create_values_per_country.cached_values


# Step 1: Use Time-Series Data to Dynamically Update Loads and Generation (Solar, Wind)
def update_loads(network, time_series, regions, time_step, force_update, variable):
    """
    Update the active power of loads in the pandapower network for the given time step.

    Parameters:
    - network: pandapowerNet, the pandapower network model
    - time_series: pd.DataFrame, country-level time-series electricity demand
    - regions: gpd.GeoDataFrame, GeoDataFrame with region-level load factors
    - time_step: int or datetime, the current time step index or timestamp

    Returns:
    - None: Updates the network in place
    """
    create_values_per_country(network, regions, force_update)

    expected_prefix_onwind = expected_prefix_offwind = expected_prefix_wind = (
        matching_columns_wind
    ) = matching_columns_onwind = matching_columns_offwind = None

    network.gen.loc[network.gen["type"] == "solar", "tech"] = "solar"

    for _, region in regions.iterrows():
        country_code = region["country"]

        # Define expected prefix based on country
        if country_code == "UK":
            country_code = "GB"
            expected_prefix = "GB_UKM_load_actual"
            expected_prefix_solar = "GB_UKM_solar_generation_actual"

            onshore_col = "GB_UKM_wind_onshore_generation_actual"
            offshore_col = "GB_UKM_wind_offshore_generation_actual"

            # Check if separated onwind and offwind tech are available
            if "onwind" in network.gen.tech.values:
                if onshore_col in time_series.columns:
                    # Combine separate onshore and offshore data (here by summing)
                    expected_prefix_onwind = onshore_col
            if "offwind" in network.gen.tech.values:
                if offshore_col in time_series.columns:
                    # Combine separate onshore and offshore data (here by summing)
                    expected_prefix_offwind = offshore_col
            else:
                expected_prefix_wind = "GB_UKM_wind_generation_actual"

        else:
            expected_prefix = f"{country_code}_load_actual"
            expected_prefix_solar = f"{country_code}_solar_generation_actual"

            # Define column names for onshore and offshore wind (non-UK)
            onshore_col = f"{country_code}_wind_onshore_generation_actual"
            offshore_col = f"{country_code}_wind_offshore_generation_actual"

            if "onwind" in network.gen.tech.values:
                if onshore_col in time_series.columns:
                    expected_prefix_onwind = onshore_col
            if "offwind" in network.gen.tech.values:
                if offshore_col in time_series.columns:
                    expected_prefix_offwind = offshore_col
                else:
                    expected_prefix_wind = f"{country_code}_wind_generation_actual"

        total_max_solar = create_values_per_country.cached_values[country_code]["solar"]
        total_max_onwind = create_values_per_country.cached_values[country_code][
            "onwind"
        ]
        total_max_offwind = create_values_per_country.cached_values[country_code][
            "offwind"
        ]

        # Use a flag to ensure the message prints only once
        if not hasattr(update_loads, "has_printed"):
            print()
            has_printed_wind_data = any(
                [
                    expected_prefix_onwind
                    and print(
                        f"Using onwind generation data from column: {expected_prefix_onwind}"
                    ),
                    expected_prefix_offwind
                    and print(
                        f"Using offwind generation data from column: {expected_prefix_offwind}"
                    ),
                    expected_prefix_wind
                    and print(
                        f"Using wind generation data from column: {expected_prefix_wind}"
                    ),
                ]
            )
            if has_printed_wind_data:
                print("Warning: No matching wind generation column found.")
            print()
            print(
                "Updating loads and generators (solar, wind) profiles - this might take a while depends on countries input size"
            )
            print()
            update_loads.has_printed = True  # Prevent re-printing

        # Find columns that start with the expected prefix
        matching_columns = [
            col for col in time_series.columns if col.startswith(expected_prefix)
        ]
        matching_columns_solar = [
            col for col in time_series.columns if col.startswith(expected_prefix_solar)
        ]
        if expected_prefix_onwind:
            matching_columns_onwind = [
                col
                for col in time_series.columns
                if col.startswith(expected_prefix_onwind)
            ]
        if expected_prefix_offwind:
            matching_columns_offwind = [
                col
                for col in time_series.columns
                if col.startswith(expected_prefix_offwind)
            ]
        if (
            expected_prefix_onwind is None
            and expected_prefix_offwind is None
            and expected_prefix_wind is not None
        ):
            matching_columns_wind = [
                col
                for col in time_series.columns
                if col.startswith(expected_prefix_wind)
            ]

        # Proceed if at least one matching column exists
        if matching_columns:
            country_load = time_series.loc[
                time_step, matching_columns[0]
            ]  # Use the first matching column
            country_load = (
                float(country_load.values[0])
                if isinstance(country_load, pd.Series)
                else country_load
            )
            region_load = country_load * region["load_factor"]
            load_idx = network.load[network.load["name"] == region["id"]].index
            if not load_idx.empty:
                if "num" in network.load.columns:
                    network.load.loc[load_idx, "p_mw"] = (
                        region_load / network.load.loc[load_idx, "num"]
                    )
                else:
                    network.load.loc[load_idx, "p_mw"] = region_load

        if not variable:
            if matching_columns_solar and total_max_solar > 0:
                country_generation = time_series.loc[
                    time_step, matching_columns_solar[0]
                ]  # Take the first match
                country_generation = (
                    float(country_generation.values[0])
                    if isinstance(country_generation, pd.Series)
                    else country_generation
                )
                allocate_renewable_generation(network, country_generation, "Solar")

            if matching_columns_onwind and total_max_onwind > 0:
                country_generation = time_series.loc[
                    time_step, matching_columns_onwind[0]
                ]  # Take the first match
                country_generation = (
                    float(country_generation.values[0])
                    if isinstance(country_generation, pd.Series)
                    else country_generation
                )
                allocate_renewable_generation(network, country_generation, "onwind")

            if matching_columns_offwind and total_max_offwind > 0:
                country_generation = time_series.loc[
                    time_step, matching_columns_offwind[0]
                ]  # Take the first match
                country_generation = (
                    float(country_generation.values[0])
                    if isinstance(country_generation, pd.Series)
                    else country_generation
                )
                allocate_renewable_generation(network, country_generation, "offwind")

            if (
                matching_columns_offwind is None
                and matching_columns_onwind is None
                and matching_columns_wind is not None
            ):
                country_generation = time_series.loc[
                    time_step, matching_columns_wind[0]
                ]  # Take the first match
                country_generation = (
                    float(country_generation.values[0])
                    if isinstance(country_generation, pd.Series)
                    else country_generation
                )
                allocate_renewable_generation(network, country_generation, "wind")


# Step 2: Simulate Power Flows for Each Time Step
""" 
    Joined results - total load/generation and maximum line loading 
    
"""


def time_series_pf_results(
    calculation,
    time_series_short,
    net,
    processed_regions,
    pp,
    force_update,
    variable=False,
):
    # Initialize an empty list to collect results
    results_list = []
    first_iteration = force_update
    for time_step in time_series_short.index:
        # Update loads in the network for the current time step
        update_loads(
            network=net,
            time_series=time_series_short,
            regions=processed_regions,
            time_step=time_step,
            force_update=first_iteration,
            variable=variable,
        )
        first_iteration = (
            False  # Set force_update to False after the first loop iteration
        )

        # Replace NaN values in p_mw with 0
        net.gen["p_mw"] = net.gen["p_mw"].fillna(0)
        net.gen["min_p_mw"] = net.gen["min_p_mw"].fillna(0)
        net.gen["max_p_mw"] = net.gen["max_p_mw"].fillna(0)

        if calculation == "ac_pf":
            pp.runpp(net)
        elif calculation == "dc_opf":
            pp.rundcopp(net)
        elif calculation == "ac_opf":
            run_ac_opf(net, pp)
        else:
            raise ValueError(
                "Invalid value for 'pf'. Choose 'ac_pf','dc_opf' or 'ac_opf'."
            )

        # Collect key results
        results_list.append(
            {
                "time_step": time_step,
                "total_load": net.res_load["p_mw"].sum(),
                "total_generation": net.res_gen["p_mw"].sum(),
                "max_line_loading": net.res_line["loading_percent"].max(),
                "max_loading_index": net.res_line["loading_percent"].idxmax(),
            }
        )

    # Convert list to DataFrame at the end
    pf_results = pd.DataFrame(results_list)
    return pf_results


# 3 Separate results
def time_series_pf_results_separate_exports(
    calculation, time_series_short, processed_regions, net, pp
):
    # Create dictionaries to store individual results
    bus_results = {}
    line_results = {}
    gen_results = {}
    load_results = {}

    first_iteration = True

    for time_step in time_series_short.index:
        # Update loads in the network for the current time step
        update_loads(
            network=net,
            time_series=time_series_short,
            regions=processed_regions,
            time_step=time_step,
            force_update=first_iteration,
        )

        first_iteration = False

        # Replace NaN values in p_mw with 0
        net.gen["p_mw"] = net.gen["p_mw"].fillna(0)
        net.gen["min_p_mw"] = net.gen["min_p_mw"].fillna(0)
        net.gen["max_p_mw"] = net.gen["max_p_mw"].fillna(0)

        if calculation == "ac_pf":
            pp.runpp(net)
        elif calculation == "dc_opf":
            run_dc_opf(net, pp)
        elif calculation == "ac_opf":
            run_ac_opf(net, pp)
        else:
            raise ValueError(
                "Invalid value for 'pf'. Choose 'ac_pf','dc_opf' or 'ac_opf'."
            )

        # Store full results for each component at each time step
        bus_results[time_step] = net.res_bus.copy()
        line_results[time_step] = net.res_line.copy()
        gen_results[time_step] = net.res_gen.copy()
        load_results[time_step] = net.res_load.copy()

    # Convert dictionaries to DataFrames for easier access
    bus_df = pd.concat(bus_results, names=["time_step"])
    line_df = pd.concat(line_results, names=["time_step"])
    gen_df = pd.concat(gen_results, names=["time_step"])
    load_df = pd.concat(load_results, names=["time_step"])

    # Save each results table for later analysis
    bus_df.to_csv("bus_results.csv")
    line_df.to_csv("line_results.csv")
    gen_df.to_csv("gen_results.csv")
    load_df.to_csv("load_results.csv")
