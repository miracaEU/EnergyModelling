# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

import matplotlib.pyplot as plt


def plot_power_flow_with_lines(net, res, plants=None, sum_p_mw=None):
    """
    Plot bus locations with circles representing power generation and consumption,
    and transmission lines connecting the buses.

    Parameters:
    net (pandapowerNet): Pandapower network object containing geodata.
    """
    bus_geo = net.bus_geodata
    line_geo = net.line_geodata  # Transmission line data

    if plants is not None:
        plants[["x", "y", "p_mw"]] = plants[["lon", "lat", "capacity"]]
    else:
        if not res:
            gen_bus = net.gen
            load_bus = net.load
        else:
            gen_bus = net.res_gen.copy()  # Copy generator results
            gen_bus["bus"] = net.gen["bus"]  # Add the correct bus index
            load_bus = net.res_load.copy()  # Copy load results
            load_bus["bus"] = net.load["bus"]  # Add the correct bus index

        if sum_p_mw:
            gen_bus = gen_bus.groupby("bus")["p_mw"].sum().reset_index()
            load_bus = load_bus.groupby("bus")["p_mw"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot bus locations
    plt.scatter(bus_geo.x, bus_geo.y, color="black", label="Buses", alpha=0.5)

    if plants is not None:
        # Plot generation (green for positive, orange for negative)
        first_gen = True
        first_neg_gen = True
        for _, row in plants.iterrows():
            bus_x, bus_y = plants.loc[_, ["x", "y"]]
            power_value = row["p_mw"]
            color = "green" if power_value >= 0 else "orange"

            # Prikaže label samo za prvi element vsake kategorije
            label = "Generation" if power_value >= 0 and first_gen else ""
            if power_value >= 0:
                first_gen = False  # Oznaka se doda samo enkrat

            label = (
                "Negative Generation" if power_value < 0 and first_neg_gen else label
            )
            if power_value < 0:
                first_neg_gen = False  # Oznaka se doda samo enkrat

            plt.scatter(
                bus_x,
                bus_y,
                s=abs(power_value) * 1,
                color=color,
                alpha=0.6,
                label=label,
            )

    else:
        # Plot generation (green for positive, orange for negative)
        first_gen = True
        first_neg_gen = True

        for _, row in gen_bus.iterrows():
            bus_idx = row.bus
            if bus_idx in bus_geo.index:
                bus_x, bus_y = bus_geo.loc[bus_idx, ["x", "y"]]
                power_value = row["p_mw"]
                color = "green" if power_value >= 0 else "orange"

                # Prikaže label samo za prvi element vsake kategorije
                label = "Generation" if power_value >= 0 and first_gen else ""
                if power_value >= 0:
                    first_gen = False  # Oznaka se doda samo enkrat

                label = (
                    "Negative Generation"
                    if power_value < 0 and first_neg_gen
                    else label
                )
                if power_value < 0:
                    first_neg_gen = False  # Oznaka se doda samo enkrat

                plt.scatter(
                    bus_x,
                    bus_y,
                    s=abs(power_value) * 1,
                    color=color,
                    alpha=0.6,
                    label=label,
                )

        # Plot consumption (red for positive, blue for negative)
        first_load = True
        first_neg_load = True

        for _, row in load_bus.iterrows():
            bus_idx = row.bus
            if bus_idx in bus_geo.index:
                bus_x, bus_y = bus_geo.loc[bus_idx, ["x", "y"]]
                power_value = row["p_mw"]
                color = "red" if power_value >= 0 else "blue"

                # Prikaže label samo za prvi element vsake kategorije
                label = "Consumption" if power_value >= 0 and first_load else ""
                if power_value >= 0:
                    first_load = False  # Oznaka se doda samo enkrat

                label = (
                    "Negative Consumption"
                    if power_value < 0 and first_neg_load
                    else label
                )
                if power_value < 0:
                    first_neg_load = False  # Oznaka se doda samo enkrat

                plt.scatter(
                    bus_x,
                    bus_y,
                    s=abs(power_value) * 1,
                    color=color,
                    alpha=0.6,
                    label=label,
                )

    # Add transmission lines using geodata
    first_line = True
    for _, row in line_geo.iterrows():
        coords = row["coords"]
        x_vals = [point[0] for point in coords]
        y_vals = [point[1] for point in coords]

        # Prikaže oznako samo za prvo linijo
        plt.plot(
            x_vals,
            y_vals,
            color="black",
            alpha=0.7,
            label="Lines" if first_line else "",
        )
        first_line = False

    # Adjust zoom by expanding axis limits
    plt.xlim(
        bus_geo.x.min() - 0.5, bus_geo.x.max() + 0.5
    )  # Adds extra space at left & right
    plt.ylim(
        bus_geo.y.min() - 0.5, bus_geo.y.max() + 0.5
    )  # Adds extra space at top & bottom

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    title_base = "Bus Locations & Transmission Lines with "
    if plants is not None:
        title_base += "Real Locations of Installed Capacities "
    else:
        title_base += "Power Generation/Consumption "
        title_base += "Installed Capacities " if not res else ""
    title_base += "Summed per Bus " if sum_p_mw else ""
    title_base += "from DC OPF Results" if res else ""
    plt.title(title_base)
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_solar_wind_generation(net, res, sum_p_mw=None, zoom=False):
    """
    Plot bus locations and only display generation from solar and wind sources.

    Parameters:
    net (pandapowerNet): Pandapower network object containing geodata.
    """
    bus_geo = net.bus_geodata
    line_geo = net.line_geodata  # Transmission line data

    # Select only solar and wind generators
    if not res:
        gen_bus = net.gen[net.gen["type"].isin(["solar", "wind"])]
    else:
        gen_bus = net.res_gen.copy()
        gen_bus["bus"] = net.gen["bus"]  # Add the correct bus index
        gen_bus = gen_bus[
            net.gen["type"].isin(["solar", "wind"])
        ]  # Filter only solar & wind

    if sum_p_mw:
        gen_bus = gen_bus.groupby("bus")["p_mw"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot bus locations
    plt.scatter(bus_geo.x, bus_geo.y, color="black", label="Buses", alpha=0.5)

    # Plot solar and wind generation
    first_solar = True
    first_wind = True

    for _, row in gen_bus.iterrows():
        bus_idx = row.bus

        if bus_idx in bus_geo.index:
            bus_x, bus_y = bus_geo.loc[bus_idx, ["x", "y"]]
            power_value = row["p_mw"]

            # Lookup generator type safely
            gen_type = net.gen.loc[net.gen["bus"] == bus_idx, "type"].values
            if len(gen_type) > 0:
                gen_type = gen_type[0]  # Extract type safely
                color = (
                    "orange"
                    if gen_type == "solar"
                    else "blue" if gen_type == "wind" else "gray"
                )
            else:
                print(f"Warning: Bus index {bus_idx} not found in net.gen.")
                continue  # Skip iteration if no valid type found

            # Label first instance of each type
            if gen_type == "solar" and first_solar:
                label = "Solar Generation"
                first_solar = False
            elif gen_type == "wind" and first_wind:
                label = "Wind Generation"
                first_wind = False
            else:
                label = ""  # Avoid None, which might cause issues

            # Plot solar and wind generation with proper scaling
            if zoom:
                plt.scatter(
                    bus_x,
                    bus_y,
                    s=abs(power_value) * 50,
                    color=color,
                    alpha=0.6,
                    label=label,
                )
            else:
                plt.scatter(
                    bus_x,
                    bus_y,
                    s=abs(power_value) * 5,
                    color=color,
                    alpha=0.6,
                    label=label,
                )
    # Add transmission lines using geodata
    first_line = True
    for _, row in line_geo.iterrows():
        coords = row["coords"]
        x_vals = [point[0] for point in coords]
        y_vals = [point[1] for point in coords]

        plt.plot(
            x_vals,
            y_vals,
            color="black",
            alpha=0.7,
            label="Lines" if first_line else "",
        )
        first_line = False

    # Labels & Plot adjustments
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    title_base = "Solar & Wind "
    title_base += (
        "Installed Power Capacity" if not res else "Power Generation Locations"
    )
    title_base += " Summed per Bus" if sum_p_mw else " per Bus"
    title_base += " from DC OPF Results" if res else ""
    title_base += " Zoomed In" if zoom else ""
    plt.title(title_base)
    plt.legend()
    plt.grid(True)
    plt.show()
