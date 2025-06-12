# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

import pandas as pd


def check_connections(net_bus, net_load, net_gen, net_line, net_trafo):
    # Step 1: Identify connected buses based on net_line
    connected_buses_set = set(
        pd.concat([net_line["from_bus"], net_line["to_bus"]]).unique()
    )

    # Step 2: Incorporate transformer connections (HV and LV buses)
    trafo_connections = set(
        pd.concat([net_trafo["hv_bus"], net_trafo["lv_bus"]]).unique()
    )
    connected_buses_set.update(trafo_connections)

    # Step 3: Check for disconnected buses
    all_buses_set = set(net_bus.index)
    disconnected_buses_set = all_buses_set - connected_buses_set

    # Step 4: Identify disconnected loads and generators
    disconnected_loads = net_load[
        ~net_load["bus"].isin(connected_buses_set)
    ].index.tolist()
    disconnected_gens = net_gen[
        ~net_gen["bus"].isin(connected_buses_set)
    ].index.tolist()

    # Step 5: Exclude buses with generators from being assigned extended grids
    buses_with_gens = set(net_gen["bus"].unique())
    disconnected_buses_no_gens = disconnected_buses_set - buses_with_gens

    return (
        disconnected_buses_set,
        disconnected_gens,
        disconnected_loads,
        disconnected_buses_no_gens,
    )


def verify_slack_connection(result, slack_gen_index, net):
    disconnected_buses = result[0]
    disconnected_gens = result[1]

    if (
        slack_gen_index in disconnected_gens
        or net.gen.loc[slack_gen_index, "bus"] in disconnected_buses
    ):
        # Set the current slack generator to False
        net.gen.loc[slack_gen_index, "slack"] = False

        # Filter available generators: Exclude both disconnected generators and those whose buses are disconnected
        available_gens = net.gen.loc[
            ~net.gen.index.isin(disconnected_gens)
            & ~net.gen["bus"].isin(disconnected_buses)
        ]

        if not available_gens.empty:
            # Select the generator with the highest power (p_mw)
            new_slack_index = available_gens["p_mw"].idxmax()
            net.gen.loc[new_slack_index, "slack"] = True
        else:
            print("No available generators to assign slack.")
