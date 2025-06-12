# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

# Plot nuts regions
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_regions(processed_regions):
    regions = processed_regions.copy()
    # Reproject to an appropriate projected CRS (change EPSG code as needed)
    regions = regions.to_crs(epsg=3857)  # Example: Web Mercator (adjust as needed)
    # Plot the geometry of processed_regions
    fig, ax = plt.subplots(figsize=(10, 10))
    regions.plot(ax=ax, edgecolor="black", cmap="Pastel1")

    # Now compute centroids safely
    for x, y, label in zip(
        regions.geometry.centroid.x, regions.geometry.centroid.y, regions["id"]
    ):
        ax.annotate(
            label,
            xy=(x, y),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=8,
            color="blue",
        )
    # Add a title to the plot
    plt.title("Processed Regions with Annotations", fontsize=16)
    # Show the plot
    plt.show()


def plot_bus_nuts_connections(processed_regions, bus_geo, net):
    """
    Plot NUTS regions and their connected buses using a predefined mapping.

    Parameters:
    nuts_regions (GeoDataFrame): NUTS region boundaries.
    bus_geo (GeoDataFrame): Pandapower bus geodata with coordinates.
    bus_region_mapping (DataFrame): DataFrame with 'bus_id' and 'nuts_region'.
    """

    # Create the plot
    fig, ax = plt.subplots(figsize=(16, 14))

    nuts_regions = processed_regions.copy()
    nuts_regions = nuts_regions.to_crs(epsg=32633)  # Example for Central Europe
    nuts_regions["centroid"] = nuts_regions.geometry.centroid
    nuts_regions["centroid"] = nuts_regions["centroid"].to_crs(epsg=4326)
    nuts_regions = nuts_regions.to_crs(epsg=4326)

    # Plot NUTS regions
    nuts_regions.plot(
        ax=ax, color="lightgray", edgecolor="black", alpha=0.5, label="NUTS Regions"
    )

    # Compute and plot centroids for NUTS regions
    nuts_regions["centroid"].plot(
        ax=ax, color="blue", markersize=20, label="NUTS Centroid"
    )

    # Plot Buses
    bus_geo.plot.scatter(
        x="x", y="y", ax=ax, color="red", s=20, label="Buses"  # Marker size
    )

    # Connect Buses to NUTS Regions
    for _, row in net.load.iterrows():
        nuts_region = row["name"]
        bus_idx = row["bus"]

        # Get the corresponding NUTS centroid
        nuts_row = nuts_regions[
            nuts_regions["id"] == nuts_region
        ]  # Replace 'name' with actual column
        if not nuts_row.empty:
            # nuts_centroid = nuts_row.geometry.centroid.iloc[0]
            nuts_centroid = nuts_row["centroid"].iloc[0]

            # Get the corresponding bus coordinates
            bus_row = bus_geo.loc[bus_idx]
            if not bus_row.empty:
                ax.plot(
                    [bus_row["x"], nuts_centroid.x],
                    [bus_row["y"], nuts_centroid.y],
                    color="green",
                    linestyle="-",
                    linewidth=1,
                    alpha=0.7,
                    label="Connection",
                )

    # **Manually define legend handles**
    bus_handle = mpatches.Patch(color="red", label="Buses")
    nuts_handle = mpatches.Patch(color="lightgray", label="NUTS Regions")
    centroid_handle = mpatches.Patch(color="blue", label="NUTS Centroid")
    connection_handle = mpatches.Patch(color="green", label="Connections")

    # Apply the legend manually
    ax.legend(
        handles=[bus_handle, nuts_handle, centroid_handle, connection_handle],
        loc="best",
    )
    ax.set_title("Buses Connected to NUTS Regions", fontsize=16)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid()
    plt.show()


def plot_bus_gen_connections(network, bus_geo, nuts_regions, plants):
    # Create the plot
    fig, ax = plt.subplots(figsize=(16, 14))

    # **Step 1: Match Generators with Plants**
    # matched_gens = plants.merge(network.gen, on="name")  # Replace "name" with your actual matching column
    matched_gens = plants.merge(network.gen, left_index=True, right_on="idx")

    # Plot NUTS regions in the background
    nuts_regions.plot(
        ax=ax, color="lightgray", edgecolor="black", alpha=0.3, label="NUTS Regions"
    )

    # Correct way to plot generators using lat/lon columns
    gen_plot = matched_gens.plot.scatter(
        x="lon", y="lat", ax=ax, color="blue", s=30, label="Generators"
    )

    # **Step 3: Plot Buses**
    bus_plot = bus_geo.plot.scatter(
        x="x", y="y", ax=ax, color="red", s=20, label="Buses"
    )

    # **Step 4: Connect Generators to Buses**
    for _, row in matched_gens.iterrows():
        bus_idx = row["bus"]  # Each generator has an associated bus
        bus_row = bus_geo.loc[bus_idx]
        if not bus_row.empty:
            connection = ax.plot(
                [bus_row["x"], row.geometry.x],  # Using generator geometry
                [bus_row["y"], row.geometry.y],
                color="green",
                linestyle="-",
                linewidth=1,
                alpha=0.7,
            )

            # Ensure "Connection" is only added once to the legend
            if "Connection" not in locals():
                connection_handle = mpatches.Patch(color="green", label="Connection")
                locals()["Connection"] = connection_handle  # Prevent duplicate entries

    # **Step 5: Create a Clean Legend**
    bus_handle = mpatches.Patch(color="red", label="Buses")
    gen_handle = mpatches.Patch(color="blue", label="Generators")

    ax.legend(handles=[bus_handle, gen_handle, connection_handle], loc="best")

    # Get bounding box of NUTS locations
    xmin, ymin, xmax, ymax = nuts_regions.total_bounds  # Extract bounds
    # Apply zoom limits
    # ax.set_xlim(xmin, xmax)
    # ax.set_ylim(ymin, ymax)

    # Expand the boundaries by 10% of their original range
    x_buffer = (xmax - xmin) * 0.10
    y_buffer = (ymax - ymin) * 0.10

    # Apply the expanded zoom limits
    ax.set_xlim(xmin - x_buffer, xmax + x_buffer)
    ax.set_ylim(ymin - y_buffer, ymax + y_buffer)

    # Add labels, title, and grid
    ax.set_title("Buses Connected to Generators", fontsize=16)
    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.grid()
    plt.show()
