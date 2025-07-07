import sys
from pycountry import countries, historic_countries, subdivisions


def find_country_from_pob(pob, verbose=False):
    search_term = pob.split(",")[-1].strip(" ,.:;-")
    if search_term == "":
        return None
    try:
        res = countries.search_fuzzy(search_term)
        country = res[0].name
        if verbose:
            print(f"{search_term} -> {country} ({pob})", file=sys.stderr)
        return country
    except (LookupError, AttributeError):
        try:
            res = subdivisions.search_fuzzy(search_term)
            country = res[0].country.name
            if verbose:
                print(f"{search_term} -> {country} ({pob})", file=sys.stderr)
            return country
        except (LookupError, AttributeError):
            try:
                res = historic_countries.search_fuzzy(search_term)
                country = res[0].name
                if verbose:
                    print(f"{search_term} -> {country} ({pob})",
                          file=sys.stderr)
                return country
            except (LookupError, AttributeError):
                if verbose:
                    print(f"{search_term} -> {None} ({pob})", file=sys.stderr)
                return None
