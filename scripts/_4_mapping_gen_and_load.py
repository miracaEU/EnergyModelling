# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.

[1] International Renewable Energy Agency. (2018). Power system flexibility for the energy transition: Part 1, Overview for policy makers.
IRENA. Retrieved fromhttps://www.irena.org/publications/2018/Nov/Power-system-flexibility-for-the-energy-transition
[2] OECD/NEA (2021), Technical and Economic Aspects of Load Following with Nuclear Power Plants, Nuclear Development,
OECD Publishing, Paris, https://doi.org/10.1787/29e7df00-en.
[3] Mines, G., Richard, C., Nathwani, J., Hanson, H., & Wood, R. (2015). Geothermal plant capacity factors.
Idaho National Laboratory. Retrieved from https://inldigitallibrary.inl.gov/sites/sti/sti/6582262.pdf
"""

import pandapower as pp
from scipy.spatial import KDTree
import geopandas as gpd
from shapely.geometry import Point
import numpy as np


# Define regulation range based on generator type
def calculate_power_limits(fueltype, P_nom):
    """Data used from table 1 in literature [1]:
    OCGT - min. load: (40-50%) state of the art: (20-50%),
    CCGT - min. load: (40-50%) state of the art: (30-40%),
    Hard Coal - min.load: (25-40%) state of the art: (25-40),
    Liginite - min.load: (50-60%) state of the art: (35-50).

    Capacity factors from figure 1 in literature [3]:
    Nuclear: 80-100%,
    Geothermal: 65-75%, different scenarios (63%,73.3%,46.4%,57.4%),
    Coal: 40-75%,
    Natural gas: 35-65%,
    Wind: 20-40%,
    Hydro: 30-60%.

    Note: this does not take into the account the not available powerplants so the minimum value might change later if powerflow does not converge,
    because in reality not all of the powerplants are working simultaneously. Many conventional power plants may no longer be operating,
    so the minimum load for all in the event of non-convergence changes.
    """

    if fueltype == "nuclear":
        P_min, P_max = (
            P_nom * 0.50,
            P_nom * 1.00,
        )  # Nuclear EU minimum requirments at (50–100%) [2]
    elif fueltype in ["coal", "lignite"]:
        P_min, P_max = (
            P_nom * 0.40,
            P_nom * 1.00,
        )  # Baseload plants have moderate flexibility (40–100%)
    elif fueltype in ["CCGT", "OCGT"]:
        P_min, P_max = (
            P_nom * 0.40,
            P_nom * 1.00,
        )  # Baseload/moderate flexibility (40-100%)
    elif fueltype in ["biomass", "waste", "oil"]:
        P_min, P_max = (
            P_nom * 0.30,
            P_nom * 1.00,
        )  # Moderate flexibility (30–100%) similar to OCGT/CCGT but are more flexible
    elif fueltype in ["hydro", "PHS", "ror"]:
        P_min, P_max = P_nom * 0.10, P_nom * 1.00  # Excellent flexibility (10–100%)
    elif fueltype in ["wind", "solar"]:
        P_min, P_max = (
            0.00,
            P_nom * 1.00,
        )  # Variable flexibility (0–100%, later overwritten with stable power based on current generation)
    elif fueltype == "geothermal":
        P_min, P_max = (
            P_nom * 0.60,
            P_nom * 1.00,
        )  # Limited flexibility (60–100%) based on capacity factors [3]
    else:
        P_min, P_max = P_nom * 0.20, P_nom * 1.00  # Default flexibility (20–100%)

    # Ensure P_min and P_max are valid
    if P_min < 0 or P_max <= P_min:
        return None, None  # Invalid values

    return P_min, P_max


def create_gen_or_load(gdf, Type, net, distribute_gen=False, distribute_load=False):
    buses_geodata = net.bus_geodata
    # Create geometry from x and y columns
    buses_geodata["geometry"] = buses_geodata.apply(
        lambda row: Point(row["x"], row["y"]), axis=1
    )
    # Convert to GeoDataFrame
    buses_geodata = gpd.GeoDataFrame(buses_geodata, geometry="geometry")

    for i, element in gdf.iterrows():
        # Extract the geometry of the current element
        element_polygon = element.geometry  # Assuming this is a polygon

        # Filter buses within the same zone as the element
        country_buses = net.bus[net.bus["zone"] == element["zone"]]

        # Keep only buses where name starts with "relation" or "way"
        real_country_buses = country_buses[
            country_buses["name"].str.startswith(("relation", "way"))
            & country_buses["in_service"]
        ]

        # Create country_buses_geodata based on indexes that are also in buses_geodata
        real_country_buses_geodata = buses_geodata[
            buses_geodata.index.isin(real_country_buses.index)
        ]

        # Filter real substations (buses) that are within the current polygon
        buses_within_polygon = real_country_buses_geodata[
            real_country_buses_geodata.geometry.within(element_polygon)
        ]

        element_coords = (element.geometry.centroid.x, element.geometry.centroid.y)

        # Build a KDTree for real substations
        real_country_bus_kdtree = KDTree(
            real_country_buses_geodata[["x", "y"]]
        )  # Assumes buses have 'x' and 'y' coordinates

        if not buses_within_polygon.empty:
            # Retrieve buses within the polygon
            substations_within = net.bus.loc[buses_within_polygon.index]

            # Find buses with the lowest voltage level
            min_voltage = substations_within["vn_kv"].min()
            substations_with_lowest_voltage = substations_within[
                substations_within["vn_kv"] == min_voltage
            ]

            # Use KDTree to find the closest bus with the lowest voltage level
            substations_coords = real_country_buses_geodata.loc[
                substations_with_lowest_voltage.index, ["x", "y"]
            ].values
            distance, closest_bus_index = KDTree(substations_coords).query(
                element_coords
            )
            closest_bus = substations_with_lowest_voltage.index[closest_bus_index]

        else:
            # If no buses are found within the polygon, use KDTree to locate the nearest bus
            distance, closest_bus_index = real_country_bus_kdtree.query(element_coords)
            closest_bus = real_country_buses.index[closest_bus_index]

        # Process the generator or load and map it to the selected bus
        power_mw = element.get("capacity")

        if Type == "gen":
            P_min, P_max = calculate_power_limits(element.fueltype, power_mw)
            # Set controllable only if P_min and P_max are valid
            controllable = P_min is not None and P_max is not None

            # if not np.isnan(element.marginal_cost):
            #    marginal_cost = element.marginal_cost
            if not np.isnan(element.adjusted_marginal_price):
                marginal_cost = element.adjusted_marginal_price
            else:
                marginal_cost = 0
            if not controllable:
                P_min = 0
                P_max = 0

            if distribute_gen is True:
                country_buses_geodata = buses_geodata[
                    buses_geodata.index.isin(country_buses.index)
                ]
                # Build a KDTree for all country substations
                country_bus_kdtree = KDTree(
                    country_buses_geodata[["x", "y"]]
                )  # Assumes buses have 'x' and 'y' coordinates
                distance, closest_bus_index = country_bus_kdtree.query(element_coords)
                closest_bus = country_buses.index[closest_bus_index]

            pp.create_gen(
                net,
                closest_bus,
                p_mw=power_mw,
                vm_pu=1.0,
                idx=i,
                name=element["name"],
                slack=False,
                scaling=1,
                controllable=True,
                min_p_mw=P_min,
                max_p_mw=P_max,
                cost_per_mw=marginal_cost,
                type=element.fueltype,
                tech=element.technology,
                p_mw_original=power_mw,
            )

        elif Type == "load":
            if distribute_load is not True:
                pp.create_load(
                    net,
                    closest_bus,
                    p_mw=element.load_factor,
                    name=element["id"],
                    controllable=False,
                )
            else:
                # Iterate over rows
                num_buses = len(buses_within_polygon)
                if num_buses:
                    for index, row in buses_within_polygon.iterrows():
                        pp.create_load(
                            net,
                            index,
                            p_mw=element.load_factor / num_buses,
                            name=element["id"],
                            controllable=False,
                            num=num_buses,
                        )
                else:
                    pp.create_load(
                        net,
                        closest_bus,
                        p_mw=element.load_factor,
                        name=element["id"],
                        controllable=False,
                        num=1,
                    )
        else:
            return print("Incorrect element type")
            break
