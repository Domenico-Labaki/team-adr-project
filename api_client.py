"""Place provider requests for nearby search and favorites."""
import os

import requests

OVERPASS_API_URL = os.environ.get(
    "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter"
)


class ProviderLookupUnavailable(Exception):
    """The place provider could not be queried."""


def validate_favorite_reference(provider, place_id):
    """Return a canonical reference or None for an invalid or missing place."""
    # SCRUM-12 will provide the shared place lookup.
    raise ProviderLookupUnavailable


def search_places(latitude, longitude):
    """Find named attractions, food, and lodging within 1.2 km using up to 12 elements."""
    query = f"""
    [out:json][timeout:15];
    (
      nwr(around:1200,{latitude},{longitude})["tourism"~"attraction|museum|viewpoint|gallery|zoo|theme_park"];
      nwr(around:1200,{latitude},{longitude})["historic"];
      nwr(around:1200,{latitude},{longitude})["leisure"~"park|garden"];
      nwr(around:1200,{latitude},{longitude})["amenity"~"restaurant|cafe|bar"];
      nwr(around:1200,{latitude},{longitude})["tourism"~"hotel|guest_house|hostel"];
    );
    out center 12;
    """
    response = requests.post(
        OVERPASS_API_URL,
        data={"data": query},
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        raise requests.RequestException("Overpass returned an unexpected response.")
    if data.get("remark"):
        raise requests.RequestException("Overpass could not complete the query.")

    places = []
    for element in data["elements"]:
        if not isinstance(element, dict):
            continue
        element_type = element.get("type")
        element_id = element.get("id")
        if (
            element_type not in ("node", "way", "relation")
            or type(element_id) is not int
            or element_id <= 0
        ):
            continue
        place_id = f"{element_type}/{element_id}"
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        place_type = "Place to visit"
        if tags.get("amenity") in ("restaurant", "cafe", "bar"):
            place_type = tags["amenity"].replace("_", " ").title()
        elif tags.get("tourism"):
            place_type = tags["tourism"].replace("_", " ").title()
        elif tags.get("historic"):
            place_type = "Historic place"
        elif tags.get("leisure"):
            place_type = tags["leisure"].replace("_", " ").title()

        details = []
        if tags.get("cuisine"):
            details.append("Cuisine: " + tags["cuisine"].replace(";", ", "))
        if tags.get("opening_hours"):
            details.append("Hours: " + tags["opening_hours"])
        if tags.get("addr:street"):
            address = tags["addr:street"]
            if tags.get("addr:housenumber"):
                address = tags["addr:housenumber"] + " " + address
            details.append(address)

        center = element.get("center", {})
        latitude_value = element.get("lat", center.get("lat"))
        longitude_value = element.get("lon", center.get("lon"))
        places.append({
            "id": place_id,
            "name": name,
            "type": place_type,
            "details": " · ".join(details),
            "url": f"https://www.openstreetmap.org/{place_id}",
            "lat": latitude_value,
            "lon": longitude_value,
        })

    return places
