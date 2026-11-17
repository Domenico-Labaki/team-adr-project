"""
api_client.py  --  ALL calls to your external API live here (one place).

RIGHT NOW this returns a few SAMPLE items so the app runs out of the box.
TODO (your team): replace the sample data with real calls to your chosen free
API, keeping the SAME return shapes so the rest of the app keeps working:

    search(query)   -> a list of dicts, each: {"id", "title", "image"}
    get_item(id)    -> one dict: {"id", "title", "image", "description"}
"""
import requests  # you'll use this for the real API calls

TIMEOUT = 6  # seconds; give up instead of hanging if the API is slow

# ----- temporary sample data (delete once your API works) -----
_SAMPLE = [
    {"id": "1", "title": "Example Item One",
     "image": "https://picsum.photos/id/1011/400/300",
     "description": "Replace this with a real description from your API."},
    {"id": "2", "title": "Example Item Two",
     "image": "https://picsum.photos/id/1025/400/300",
     "description": "Replace this with a real description from your API."},
    {"id": "3", "title": "Example Item Three",
     "image": "https://picsum.photos/id/1039/400/300",
     "description": "Replace this with a real description from your API."},
]


def search(query):
    """Return a list of items matching the query."""
    # TODO: call your API instead, e.g.
    #   r = requests.get("https://api.example.com/search",
    #                    params={"q": query}, timeout=TIMEOUT)
    #   if r.status_code != 200:
    #       return []
    #   data = r.json()
    #   return [{"id": x["id"], "title": x["name"], "image": x["thumb"]}
    #           for x in data["results"]]
    q = query.lower()
    hits = [it for it in _SAMPLE if q in it["title"].lower()]
    return hits or _SAMPLE


def search_places(latitude, longitude):
    """Find named attractions, food, and lodging near the searched destination. The query asks for relevant map tags within 5 km and limits output to 12 elements."""
    query = f"""
    [out:json][timeout:15];
    (
      nwr(around:5000,{latitude},{longitude})["tourism"~"attraction|museum|viewpoint|gallery|zoo|theme_park"];
      nwr(around:5000,{latitude},{longitude})["historic"];
      nwr(around:5000,{latitude},{longitude})["leisure"~"park|garden"];
      nwr(around:5000,{latitude},{longitude})["amenity"~"restaurant|cafe|bar"];
      nwr(around:5000,{latitude},{longitude})["tourism"~"hotel|guest_house|hostel"];
    );
    out center 12;
    """
    response = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": query},
        timeout=20,
    )
    response.raise_for_status()

    places = []
    elements = response.json().get("elements", [])
    for element in elements:
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        place_type = "Place to visit"
        if tags.get("amenity") in ("restaurant", "cafe", "bar"):
            place_type = tags["amenity"].replace("_", " ").title()
        elif tags.get("tourism") in ("hotel", "guest_house", "hostel"):
            place_type = tags["tourism"].replace("_", " ").title()
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
        url = "https://www.openstreetmap.org/{}/{}".format(
            element.get("type", "node"), element.get("id", "")
        )

        places.append({
            "name": name,
            "type": place_type,
            "details": " · ".join(details),
            "url": url,
            "lat": latitude_value,
            "lon": longitude_value,
        })

    return places


def get_item(item_id):
    """Return one item by its id, or None if not found."""
    # TODO: call your API for one item, e.g.
    #   r = requests.get(f"https://api.example.com/item/{item_id}", timeout=TIMEOUT)
    #   ...
    for it in _SAMPLE:
        if it["id"] == item_id:
            return it
    return None
