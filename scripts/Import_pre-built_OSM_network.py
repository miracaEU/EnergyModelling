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

# Network data from Zenodo repository (version 0.6) [2]

[2] Hörsch, J., Hofmann, F., Schlachtberger, D., & Brown, T. (2025).
PyPSA-EUR: An open optimisation model of the European transmission system.
Scientific Data, 12(4), Article 2. https://doi.org/10.1038/s41597-025-04550-7
"""

import pandapower as pp
import pandas as pd
import geopandas as gpd
import os
import math
from shapely import wkt
import numpy as np

""" 1 Import pre-built OSM network structure """

# Define the folder path
folder = "Data\\NetworkOSM"

lines = os.path.join(folder, "lines.csv")
buses = os.path.join(folder, "buses.csv")
converters = os.path.join(folder, "converters.csv")
lines = os.path.join(folder, "lines.csv")
links = os.path.join(folder, "links.csv")
transformers = os.path.join(folder, "transformers.csv")


# def _load_buses(buses, europe_shape, countries, config):
def _load_buses(buses):
    buses = (
        pd.read_csv(
            buses,
            quotechar="'",
            true_values=["t"],
            false_values=["f"],
            dtype=dict(bus_id="str"),
        )
        .set_index("bus_id")
        .rename(columns=dict(voltage="v_nom"))
    )

    if "station_id" in buses.columns:
        buses.drop("station_id", axis=1, inplace=True)

    buses["carrier"] = buses.pop("dc").map({True: "DC", False: "AC"})
    buses["under_construction"] = buses.under_construction.where(
        lambda s: s.notnull(), False
    ).astype(bool)

    return pd.DataFrame(buses)


def _remove_dangling_branches(branches, buses):
    return pd.DataFrame(
        branches.loc[branches.bus0.isin(buses.index) & branches.bus1.isin(buses.index)]
    )


def _load_transformers(buses, transformers):
    transformers = pd.read_csv(
        transformers,
        quotechar="'",
        true_values=["t"],
        false_values=["f"],
        dtype=dict(transformer_id="str", bus0="str", bus1="str"),
    ).set_index("transformer_id")

    transformers = _remove_dangling_branches(transformers, buses)

    return transformers


def _load_converters_from_osm(buses, converters):
    converters = pd.read_csv(
        converters,
        quotechar="'",
        true_values=["t"],
        false_values=["f"],
        dtype=dict(converter_id="str", bus0="str", bus1="str"),
    ).set_index("converter_id")

    converters = _remove_dangling_branches(converters, buses)

    converters["carrier"] = ""

    return converters


def _load_links_from_osm(buses, links):
    links = pd.read_csv(
        links,
        quotechar="'",
        true_values=["t"],
        false_values=["f"],
        dtype=dict(
            link_id="str",
            bus0="str",
            bus1="str",
            voltage="int",
            p_nom="float",
        ),
    ).set_index("link_id")

    links["length"] /= 1e3

    links = _remove_dangling_branches(links, buses)

    # Add DC line parameters
    links["carrier"] = "DC"

    return links


def _load_lines(buses, lines):
    lines = (
        pd.read_csv(
            lines,
            quotechar="'",
            true_values=["t"],
            false_values=["f"],
            dtype=dict(
                line_id="str",
                bus0="str",
                bus1="str",
                underground="bool",
                under_construction="bool",
            ),
        )
        .set_index("line_id")
        .rename(columns=dict(voltage="v_nom", circuits="num_parallel"))
    )

    lines["length"] /= 1e3

    lines["carrier"] = "AC"
    lines = _remove_dangling_branches(lines, buses)

    return lines


buses = _load_buses(buses=buses)
transformers = _load_transformers(buses, transformers)
converters = _load_converters_from_osm(buses, converters)
links = _load_links_from_osm(buses, links)
lines = _load_lines(buses, lines)

print("Import completed!")


def calculate_capacitance(Bch, frequency=50):
    """
    Calculate the capacitance (C) in nanofarads (nF) from the shunt susceptance (Bch) in siemens (S).

    Parameters:
        Bch (float): Shunt susceptance in siemens.
        frequency (float): Frequency in hertz (default is 50 Hz).

    Returns:
        float: Capacitance in nanofarads (nF).
    """
    # Calculate capacitance in farads (F)
    capacitance_f = Bch / (2 * math.pi * frequency)

    # Convert capacitance to nanofarads (nF)
    capacitance_nf = capacitance_f * 1e9

    return capacitance_nf


""" Pandapower network using pre-built structure """

net = pp.create_empty_network()

buses.apply(
    lambda row: pp.create_bus(
        net,
        vn_kv=row.v_nom,
        name=row.name,
        geodata=(row.x, row.y),
        max_vm_pu=1.1,
        min_vm_pu=0.9,
        coords=row.geometry,
        zone=row.country,
    ),
    axis=1,
)


# Define a function to determine custom_type
def get_custom_type(line_voltage):
    if line_voltage <= 225:
        return "220kV_custom_line"
    elif line_voltage >= 275 and line_voltage <= 330:
        return "330kV_custom_line"
    elif line_voltage >= 380 and line_voltage <= 420:
        return "400kV_custom_line"
    elif line_voltage == 500:
        return "500kV_custom_line"
    elif line_voltage >= 750:
        return "750kV_custom_line"
    else:
        return "Unknown"


""" Lines """

lines["geometry"] = lines["geometry"].apply(wkt.loads)
lines = gpd.GeoDataFrame(lines, geometry="geometry")
bus_name_to_index = net.bus.reset_index().set_index("name")["index"].to_dict()

lines["from_bus"] = lines["bus0"].map(bus_name_to_index)
lines["to_bus"] = lines["bus1"].map(bus_name_to_index)

lines.apply(
    lambda row: pp.create_line_from_parameters(
        net,
        from_bus=row.from_bus,
        to_bus=row.to_bus,
        length_km=row.length,
        r_ohm_per_km=row.r / row.length,
        x_ohm_per_km=row.x / row.length,
        c_nf_per_km=calculate_capacitance(row.b) / row.length,
        max_i_ka=row.i_nom,
        name=row.name,
        parallel=row.num_parallel,
        geodata=[(float(x), float(y)) for x, y in list(row.geometry.coords)],
        in_service=True,
    ),
    axis=1,
)

""" Transformers """

transformers["geometry"] = transformers["geometry"].apply(wkt.loads)
transformers = gpd.GeoDataFrame(transformers, geometry="geometry")

transformers["hv_bus"] = transformers["bus1"].map(bus_name_to_index)
transformers["lv_bus"] = transformers["bus0"].map(bus_name_to_index)


# empirical constants for transformer creation from parameters
a, b, c, d = 35, 0.004, 0.15, 1.2

transformers.apply(
    lambda row: pp.create_transformer_from_parameters(
        net,
        hv_bus=int(row.hv_bus),  # High-voltage bus index
        lv_bus=int(row.lv_bus),  # Low-voltage bus index
        sn_mva=row.s_nom,  # Nominal apparent power
        vn_hv_kv=row.voltage_bus1,  # Nominal voltage on the high-voltage side
        vn_lv_kv=row.voltage_bus0,  # Nominal voltage on the low-voltage side
        vk_percent=a * np.sqrt(row.s_nom) / row.voltage_bus1,  # Short-circuit voltage
        vkr_percent=b * row.s_nom / row.voltage_bus1,  # Short-circuit resistance
        pfe_kw=c * row.s_nom,  # Iron losses
        i0_percent=d / np.sqrt(row.s_nom),  # Open-circuit current
        name=row.name,  # Transformer name
    ),
    axis=1,
)

# simple_plotly(net, filename='Network_parameters_plot-Virtual_buses.html')

# Exporting net data to a CSV
net.bus.to_csv("bus_data.csv", index=False)
net.line.to_csv("line_data.csv", index=False)
net.trafo.to_csv("trafo_data.csv", index=False)
net.line_geodata.to_csv("line_geodata.csv", index=False)
net.bus_geodata.to_csv("bus_geodata.csv", index=False)

converters.to_csv("converters.csv", index=False)
links.to_csv("links.csv", index=False)
