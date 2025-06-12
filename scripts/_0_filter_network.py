# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

import pandapower as pp
from shapely import wkt
import geopandas as gpd
import os
import pandas as pd


def filter_network_by_countries(net, countries):
    """
    Filters pandapower network data for specified countries.

    Parameters:
        net: pandapower network object
        countries: str or list
            A single country name or a list of country names.

    Returns:
        net: Updated pandapower network object with filtered infrastructure.
    """
    # Ensure countries is a list
    if isinstance(countries, str):
        countries = [countries]

    # Step 1: Filter buses for specified countries
    filtered_buses = net.bus[net.bus["zone"].isin(countries)]
    filtered_bus_indices = filtered_buses.index

    # Step 2: Filter lines connected to filtered buses
    filtered_lines = net.line[
        (net.line["from_bus"].isin(filtered_bus_indices))
        & (net.line["to_bus"].isin(filtered_bus_indices))  # |
    ]

    # Step 3: Filter transformers connected to filtered buses
    filtered_trafos = net.trafo[
        (net.trafo["hv_bus"].isin(filtered_bus_indices))
        & (net.trafo["lv_bus"].isin(filtered_bus_indices))  # |
    ]

    # Step 4: Filter geodata for buses and lines
    filtered_bus_geodata = net.bus_geodata[
        net.bus_geodata.index.isin(filtered_bus_indices)
    ]
    filtered_line_geodata = net.line_geodata[
        net.line_geodata.index.isin(filtered_lines.index)
    ]

    # Step 5: Update the pandapower network object
    net.bus = filtered_buses
    net.line = filtered_lines
    net.trafo = filtered_trafos
    net.bus_geodata = filtered_bus_geodata
    net.line_geodata = filtered_line_geodata

    # Convert geodata to proper form
    net.line_geodata["coords"] = net.line_geodata["coords"].apply(
        lambda x: eval(x) if isinstance(x, str) else x
    )

    return net


def connect_DC_elements(net):
    """
    Connects HVDC converters using AC connections based on bus names.

    Parameters:
    net (pandapower.network): The Pandapower network object.
    converters (pd.DataFrame): DataFrame containing converter information (bus0 and bus1 names).

    Returns:
    None
    """
    folder = "Data\\Net_structure_data"
    links = pd.read_csv(os.path.join(folder, "links.csv"))
    converters = pd.read_csv(os.path.join(folder, "converters.csv"))

    links["geometry"] = links["geometry"].apply(wkt.loads)
    links = gpd.GeoDataFrame(links, geometry="geometry")
    converters["geometry"] = converters["geometry"].apply(wkt.loads)
    converters = gpd.GeoDataFrame(converters, geometry="geometry")

    for index, row in converters.iterrows():
        bus0_name = row["bus0"]
        bus1_name = row["bus1"]

        # Find corresponding bus indices in net.bus
        bus0_idx = net.bus[net.bus["name"] == bus0_name].index
        bus1_idx = net.bus[net.bus["name"] == bus1_name].index
        if not bus0_idx.empty and not bus1_idx.empty:
            # Define converters as controllable generators
            pp.create_gen(
                net,
                bus=bus0_idx[0],
                p_mw=row["p_nom"],
                vm_pu=1.0,
                controllable=True,
                name=f"Converter {bus0_idx[0]}",
            )

            # Create the AC line
            line_idx = pp.create_line(
                net,
                from_bus=bus0_idx[0],
                to_bus=bus1_idx[0],
                length_km=0.1,
                std_type="NAYY 4x150 SE",
                name=f"Converter Link {bus0_idx[0]}",
            )

            # Assign straight-line geodata directly
            net.line_geodata.loc[line_idx, "coords"] = [
                (
                    net.bus_geodata.loc[bus0_idx[0], "x"],
                    net.bus_geodata.loc[bus0_idx[0], "y"],
                ),
                (
                    net.bus_geodata.loc[bus1_idx[0], "x"],
                    net.bus_geodata.loc[bus1_idx[0], "y"],
                ),
            ]

    # Step 2: Create HVDC transmission lines between DC buses
    for index, row in links.iterrows():
        bus0_id = row["bus0"]
        bus1_id = row["bus1"]

        # Check if each bus exists in net.bus
        bus0_index = (
            net.bus[net.bus["name"] == bus0_id].index[0]
            if bus0_id in net.bus["name"].values
            else None
        )
        bus1_index = (
            net.bus[net.bus["name"] == bus1_id].index[0]
            if bus1_id in net.bus["name"].values
            else None
        )

        if bus0_index is not None and bus1_index is not None:
            # Convert power to current (assuming balanced operation)
            max_i_ka = row.p_nom / (
                row.voltage * 1.732
            )  # 1.732 accounts for three-phase equivalence

            # Create HVDC connection with adjusted parameters
            pp.create_line_from_parameters(
                net,
                from_bus=bus0_index,
                to_bus=bus1_index,
                length_km=row["length"],
                r_ohm_per_km=0.02,
                x_ohm_per_km=0.005,
                c_nf_per_km=0.01,
                max_i_ka=max_i_ka,
                name=f"HVDC Link {bus0_index}",
                geodata=[(float(x), float(y)) for x, y in list(row.geometry.coords)],
                parallel=1,
            )

    # Ensure converters are controllable
    net.gen.loc[net.gen["name"].str.contains("HVDC Converter"), "controllable"] = True

    hvdc_lines = net.line[net.line["name"].str.contains("HVDC Link", na=False)]
    # Update parameters to improve HVDC stability
    net.line.loc[
        hvdc_lines.index, ["r_ohm_per_km", "x_ohm_per_km", "max_loading_percent"]
    ] = [0.02, 0.005, 90]

    # Set high thermal limit for HVDC-AC link to prevent overload
    hvdc_ac_line_index = net.line[net.line["name"].str.contains("Converter Link")].index

    if not hvdc_ac_line_index.empty:
        net.line.loc[hvdc_ac_line_index, "max_i_ka"] = 3.5
        net.line.loc[hvdc_ac_line_index, "parallel"] = 2

    net.line.loc[
        net.line["name"].str.contains("Converter Link"),
        ["r_ohm_per_km", "x_ohm_per_km", "max_loading_percent"],
    ] = [0.05, 0.02, 80]
