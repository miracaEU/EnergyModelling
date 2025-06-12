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

import logging
import requests

logger = logging.getLogger(__name__)


def configure_logging():
    """
    Configures logging for the script.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )


def download_fuel_prices(url, output_path, disable_progressbar=False):
    """
    Downloads the fuel price data from the specified URL and saves it to the given output path.

    Parameters:
        url (str): URL to download the fuel price data.
        output_path (str): File path where the downloaded file will be saved.
        disable_progressbar (bool): Option to disable progress information (default: False).

    Returns:
        None
    """
    try:
        logger.info(f"Downloading fuel prices from: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Write content to the file
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        logger.info(f"Fuel prices successfully saved to: {output_path}")
    except requests.RequestException as e:
        logger.error(f"Failed to download fuel prices: {e}")
        raise


# Define the URL and output file path
url = "https://www.destatis.de/EN/Themes/Economy/Prices/Publications/Downloads-Energy-Price-Trends/energy-price-trends-xlsx-5619002.xlsx?__blob=publicationFile"
output_path = "fuel_prices.xlsx"  # Change this to the desired file path

# Call the function to download fuel prices
download_fuel_prices(url, output_path)
