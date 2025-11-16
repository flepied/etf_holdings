#!/usr/bin/env python3
"""
Country Normalizer

Normalizes country names and codes from different data sources to ensure
consistency in geographic analysis. Handles variations like:
- ISO codes (US, GB, JP) → Full names
- Variations (USA, UK, HK) → Standard codes
- Full names → ISO alpha-2 codes
"""

# ISO 3166-1 alpha-2 country codes to full names mapping
ISO_COUNTRY_NAMES = {
    "AD": "Andorra",
    "AE": "United Arab Emirates",
    "AF": "Afghanistan",
    "AG": "Antigua and Barbuda",
    "AI": "Anguilla",
    "AL": "Albania",
    "AM": "Armenia",
    "AO": "Angola",
    "AQ": "Antarctica",
    "AR": "Argentina",
    "AS": "American Samoa",
    "AT": "Austria",
    "AU": "Australia",
    "AW": "Aruba",
    "AX": "Åland Islands",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BB": "Barbados",
    "BD": "Bangladesh",
    "BE": "Belgium",
    "BF": "Burkina Faso",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BI": "Burundi",
    "BJ": "Benin",
    "BL": "Saint Barthélemy",
    "BM": "Bermuda",
    "BN": "Brunei",
    "BO": "Bolivia",
    "BQ": "Caribbean Netherlands",
    "BR": "Brazil",
    "BS": "Bahamas",
    "BT": "Bhutan",
    "BV": "Bouvet Island",
    "BW": "Botswana",
    "BY": "Belarus",
    "BZ": "Belize",
    "CA": "Canada",
    "CC": "Cocos Islands",
    "CD": "Democratic Republic of the Congo",
    "CF": "Central African Republic",
    "CG": "Republic of the Congo",
    "CH": "Switzerland",
    "CI": "Côte d'Ivoire",
    "CK": "Cook Islands",
    "CL": "Chile",
    "CM": "Cameroon",
    "CN": "China",
    "CO": "Colombia",
    "CR": "Costa Rica",
    "CU": "Cuba",
    "CV": "Cape Verde",
    "CW": "Curaçao",
    "CX": "Christmas Island",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DJ": "Djibouti",
    "DK": "Denmark",
    "DM": "Dominica",
    "DO": "Dominican Republic",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EE": "Estonia",
    "EG": "Egypt",
    "EH": "Western Sahara",
    "ER": "Eritrea",
    "ES": "Spain",
    "ET": "Ethiopia",
    "FI": "Finland",
    "FJ": "Fiji",
    "FK": "Falkland Islands",
    "FM": "Micronesia",
    "FO": "Faroe Islands",
    "FR": "France",
    "GA": "Gabon",
    "GB": "United Kingdom",
    "GD": "Grenada",
    "GE": "Georgia",
    "GF": "French Guiana",
    "GG": "Guernsey",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GL": "Greenland",
    "GM": "Gambia",
    "GN": "Guinea",
    "GP": "Guadeloupe",
    "GQ": "Equatorial Guinea",
    "GR": "Greece",
    "GS": "South Georgia",
    "GT": "Guatemala",
    "GU": "Guam",
    "GW": "Guinea-Bissau",
    "GY": "Guyana",
    "HK": "Hong Kong",
    "HM": "Heard Island and McDonald Islands",
    "HN": "Honduras",
    "HR": "Croatia",
    "HT": "Haiti",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IM": "Isle of Man",
    "IN": "India",
    "IO": "British Indian Ocean Territory",
    "IQ": "Iraq",
    "IR": "Iran",
    "IS": "Iceland",
    "IT": "Italy",
    "JE": "Jersey",
    "JM": "Jamaica",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KG": "Kyrgyzstan",
    "KH": "Cambodia",
    "KI": "Kiribati",
    "KM": "Comoros",
    "KN": "Saint Kitts and Nevis",
    "KP": "North Korea",
    "KR": "South Korea",
    "KW": "Kuwait",
    "KY": "Cayman Islands",
    "KZ": "Kazakhstan",
    "LA": "Laos",
    "LB": "Lebanon",
    "LC": "Saint Lucia",
    "LI": "Liechtenstein",
    "LK": "Sri Lanka",
    "LR": "Liberia",
    "LS": "Lesotho",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "LY": "Libya",
    "MA": "Morocco",
    "MC": "Monaco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MF": "Saint Martin",
    "MG": "Madagascar",
    "MH": "Marshall Islands",
    "MK": "North Macedonia",
    "ML": "Mali",
    "MM": "Myanmar",
    "MN": "Mongolia",
    "MO": "Macau",
    "MP": "Northern Mariana Islands",
    "MQ": "Martinique",
    "MR": "Mauritania",
    "MS": "Montserrat",
    "MT": "Malta",
    "MU": "Mauritius",
    "MV": "Maldives",
    "MW": "Malawi",
    "MX": "Mexico",
    "MY": "Malaysia",
    "MZ": "Mozambique",
    "NA": "Namibia",
    "NC": "New Caledonia",
    "NE": "Niger",
    "NF": "Norfolk Island",
    "NG": "Nigeria",
    "NI": "Nicaragua",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NR": "Nauru",
    "NU": "Niue",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PA": "Panama",
    "PE": "Peru",
    "PF": "French Polynesia",
    "PG": "Papua New Guinea",
    "PH": "Philippines",
    "PK": "Pakistan",
    "PL": "Poland",
    "PM": "Saint Pierre and Miquelon",
    "PN": "Pitcairn Islands",
    "PR": "Puerto Rico",
    "PS": "Palestine",
    "PT": "Portugal",
    "PW": "Palau",
    "PY": "Paraguay",
    "QA": "Qatar",
    "RE": "Réunion",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "RW": "Rwanda",
    "SA": "Saudi Arabia",
    "SB": "Solomon Islands",
    "SC": "Seychelles",
    "SD": "Sudan",
    "SE": "Sweden",
    "SG": "Singapore",
    "SH": "Saint Helena",
    "SI": "Slovenia",
    "SJ": "Svalbard and Jan Mayen",
    "SK": "Slovakia",
    "SL": "Sierra Leone",
    "SM": "San Marino",
    "SN": "Senegal",
    "SO": "Somalia",
    "SR": "Suriname",
    "SS": "South Sudan",
    "ST": "São Tomé and Príncipe",
    "SV": "El Salvador",
    "SX": "Sint Maarten",
    "SY": "Syria",
    "SZ": "Eswatini",
    "TC": "Turks and Caicos Islands",
    "TD": "Chad",
    "TF": "French Southern Territories",
    "TG": "Togo",
    "TH": "Thailand",
    "TJ": "Tajikistan",
    "TK": "Tokelau",
    "TL": "Timor-Leste",
    "TM": "Turkmenistan",
    "TN": "Tunisia",
    "TO": "Tonga",
    "TR": "Turkey",
    "TT": "Trinidad and Tobago",
    "TV": "Tuvalu",
    "TW": "Taiwan",
    "TZ": "Tanzania",
    "UA": "Ukraine",
    "UG": "Uganda",
    "UM": "United States Minor Outlying Islands",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "VA": "Vatican City",
    "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela",
    "VG": "British Virgin Islands",
    "VI": "United States Virgin Islands",
    "VN": "Vietnam",
    "VU": "Vanuatu",
    "WF": "Wallis and Futuna",
    "WS": "Samoa",
    "YE": "Yemen",
    "YT": "Mayotte",
    "ZA": "South Africa",
    "ZM": "Zambia",
    "ZW": "Zimbabwe",
}

# Common variations and aliases that need to be normalized
COUNTRY_ALIASES = {
    # United States variations
    "USA": "US",
    "United States of America": "US",
    "U.S.A.": "US",
    "U.S.": "US",
    # United Kingdom variations
    "UK": "GB",
    "England": "GB",
    "Scotland": "GB",
    "Wales": "GB",
    "Northern Ireland": "GB",
    "Great Britain": "GB",
    # China variations
    "People's Republic of China": "CN",
    "PRC": "CN",
    # South Korea variations
    "Korea": "KR",
    "Republic of Korea": "KR",
    "South Korea": "KR",
    # Taiwan variations
    "Republic of China": "TW",
    "Chinese Taipei": "TW",
    # Russia variations
    "Russian Federation": "RU",
    # Vietnam variations
    "Viet Nam": "VN",
    # Czech Republic variations
    "Czechia": "CZ",
    # Netherlands variations
    "Holland": "NL",
    # Switzerland variations
    "Swiss": "CH",
    # Other common variations
    "Ivory Coast": "CI",
    "Cocos (Keeling) Islands": "CC",
    "Congo (DRC)": "CD",
    "Congo": "CG",
    "Heard and McDonald Islands": "HM",
}

# Reverse lookup: Full name to ISO code
NAME_TO_CODE = {name: code for code, name in ISO_COUNTRY_NAMES.items()}
# Add aliases
NAME_TO_CODE.update(COUNTRY_ALIASES)


def normalize_country(country_input: str) -> tuple:
    """
    Normalize a country name or code to ISO alpha-2 code and full name.

    Args:
        country_input: Country name, code, or variation

    Returns:
        Tuple of (iso_code, full_name), e.g. ("US", "United States")
        Returns ("UNKNOWN", "Unknown") if country cannot be normalized
    """
    if not country_input:
        return ("UNKNOWN", "Unknown")

    # Clean input
    country_clean = str(country_input).strip()

    if not country_clean or country_clean.upper() in ["N/A", "UNKNOWN", "NONE", ""]:
        return ("UNKNOWN", "Unknown")

    # Case 1: Already an ISO code (2 letters)
    country_upper = country_clean.upper()
    if len(country_upper) == 2 and country_upper in ISO_COUNTRY_NAMES:
        return (country_upper, ISO_COUNTRY_NAMES[country_upper])

    # Case 2: Check if it's a known alias or full name
    if country_clean in NAME_TO_CODE:
        iso_code = NAME_TO_CODE[country_clean]
        return (iso_code, ISO_COUNTRY_NAMES[iso_code])

    # Case 3: Case-insensitive lookup
    for name, code in NAME_TO_CODE.items():
        if name.lower() == country_clean.lower():
            return (code, ISO_COUNTRY_NAMES[code])

    # Case 4: Partial match on full names
    country_lower = country_clean.lower()
    for code, name in ISO_COUNTRY_NAMES.items():
        if country_lower == name.lower():
            return (code, name)

    # Case 5: Handle partial matches (e.g., "United States" in "United States of America")
    for name, code in NAME_TO_CODE.items():
        if country_lower in name.lower() or name.lower() in country_lower:
            return (code, ISO_COUNTRY_NAMES[code])

    # Unable to normalize - return original with UNKNOWN code
    return ("UNKNOWN", country_clean)


def normalize_holdings(holdings: list, field: str = "country") -> list:
    """
    Normalize country data in a list of holdings.

    Adds two fields to each holding:
    - country_code: ISO alpha-2 code (e.g., "US")
    - country_name: Full name (e.g., "United States")

    Args:
        holdings: List of holding dictionaries
        field: Field name to normalize (default: "country")

    Returns:
        List of holdings with normalized country data
    """
    normalized = []

    for holding in holdings:
        country_value = holding.get(field, "")
        iso_code, full_name = normalize_country(country_value)

        # Add normalized fields
        holding["country_code"] = iso_code
        holding["country_name"] = full_name

        # Keep original for reference
        holding["country_original"] = country_value

        normalized.append(holding)

    return normalized


if __name__ == "__main__":
    # Test normalization
    print("Country Normalization Tests")
    print("=" * 60)

    test_cases = [
        "US",
        "USA",
        "United States",
        "United States of America",
        "GB",
        "UK",
        "United Kingdom",
        "England",
        "JP",
        "Japan",
        "DE",
        "Germany",
        "FR",
        "France",
        "HK",
        "Hong Kong",
        "TW",
        "Taiwan",
        "KR",
        "South Korea",
        "Korea",
        "CN",
        "China",
        "AU",
        "Australia",
        "IT",
        "Italy",
        "",
        "Unknown",
        "N/A",
    ]

    for test in test_cases:
        code, name = normalize_country(test)
        print(f"{test:30} → {code:8} {name}")
