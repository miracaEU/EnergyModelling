# -*- coding: utf-8 -*-
"""
# Project: MIRACA
# License: MIT License
# Copyright (c) 2024 miracaEU Contributors
# See LICENSE file for details.
"""

# List of ENTSO-E member countries
eu_countries = [
    "Albania",
    "Austria",
    "Belgium",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Czech Republic",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Montenegro",
    "Netherlands",
    "North Macedonia",
    "Norway",
    "Poland",
    "Portugal",
    "Romania",
    "Serbia",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "Switzerland",
    "Ukraine",
    "United Kingdom",
    "Kosovo",
    "Moldova",
]
print()
print(f"Available EU countries: {eu_countries}")
print()


def get_country_code(country_name, iso=False):
    country_codes = {
        "Austria": "AT",
        "Albania": "AL",
        "Belgium": "BE",
        "Bosnia and Herzegovina": "BA",
        "Bulgaria": "BG",
        "Switzerland": "CH",
        "Czech Republic": "CZ",
        "Germany": "DE",
        "Denmark": "DK",
        "Estonia": "EE",
        "Spain": "ES",
        "Finland": "FI",
        "France": "FR",
        "Greece": "EL",
        "Croatia": "HR",
        "Hungary": "HU",
        "Ireland": "IE",
        "Italy": "IT",
        "Lithuania": "LT",
        "Luxembourg": "LU",
        "Latvia": "LV",
        "Montenegro": "ME",
        "Netherlands": "NL",
        "Norway": "NO",
        "North Macedonia": "MK",
        "Poland": "PL",
        "Portugal": "PT",
        "Romania": "RO",
        "Serbia": "RS",
        "Sweden": "SE",
        "Slovenia": "SI",
        "Slovakia": "SK",
        "Ukraine": "UA",
        "United Kingdom": "UK",
        "Kosovo": "XK",
        "Moldova": "MD",
    }

    iso_country_codes = {"Greece": "GR", "United Kingdom": "GB"}

    # Reverse lookup to convert codes to ISO where applicable
    reverse_lookup = {
        v: iso_country_codes[k]
        for k, v in country_codes.items()
        if k in iso_country_codes
    }

    def get_code(name):
        if name in country_codes:
            return (
                iso_country_codes.get(name, country_codes[name])
                if iso
                else country_codes[name]
            )
        return reverse_lookup.get(name, name)  # Convert existing code to ISO if needed

    if isinstance(country_name, list):
        return [get_code(name) for name in country_name]
    else:
        return get_code(country_name)


def transform_iso_code(iso_code):
    iso_mapping = {"GB": "UK", "GR": "EL"}

    return iso_mapping.get(
        iso_code, iso_code
    )  # Return transformed code or keep original


# Prompt user for countries
def prompt_for_countries():
    """
    Prompts the user to input the countries, or accepts 'all' or 'EU' to process accordingly.
    """
    user_input = input(
        "Enter country or countries (e.g., 'Slovenia, Austria' or 'SI, AT'). You can use full names or country codes. Type 'all' or 'EU' to process all available options: "
    )

    # Handle special cases
    if user_input.lower() == "all":
        print("You selected 'all': Processing all EU countries.")
        return eu_countries

    if user_input.lower() == "eu":
        print("You selected 'EU': Processing all EU countries.")
        return eu_countries

    # Convert input into a list of country names
    countries = [
        country.strip() for country in user_input.split(",") if country.strip()
    ]
    return countries


def normalize_country_name(user_input):
    """
    Matches user input (case-insensitive) to the correct country name from eu_countries.
    """
    if not user_input:  # Ensure input is not None or empty
        return None

    user_input = user_input.strip()  # Remove unnecessary spaces

    # Get all valid full names & ISO codes
    valid_country_names = set(eu_countries)  # Full names
    valid_country_codes = set(
        get_country_code(list(valid_country_names), iso=False)
    )  # Convert names to codes
    valid_iso_codes = set(
        get_country_code(list(valid_country_names), iso=True)
    )  # Convert names to ISO codes
    valid_country_codes = valid_country_codes.union(valid_iso_codes)  # Combine codes

    # Check if input is an ISO code and convert it to full country name
    if user_input.upper() in valid_country_codes:
        return get_country_code(
            user_input.upper(), iso=False
        )  # Convert code to full name

    # Create a lookup table for full names (case-insensitive)
    valid_lookup = {c.lower(): c for c in valid_country_names}

    return valid_lookup.get(
        user_input.lower(), None
    )  # Return correct formatting or None if invalid


def prompt_for_valid_countries():
    """
    Prompts the user for valid country names or ISO codes, ensuring proper name formatting.
    """
    while True:
        countries_to_filter_full = prompt_for_countries()

        normalized_countries = [
            normalize_country_name(c) for c in countries_to_filter_full
        ]

        # Check for missing matches
        missing_countries = [
            c
            for c, normalized in zip(countries_to_filter_full, normalized_countries)
            if normalized is None
        ]

        if not missing_countries:
            return normalized_countries, get_country_code(
                normalized_countries, False
            )  # Valid input

        # If invalid, prompt user again
        print("\n Invalid country name(s):", ", ".join(missing_countries))
        print("Please enter valid country names as listed in the dataset.\n")
