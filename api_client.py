"""
api_client.py  --  ALL calls to your external API live here (one place).

RIGHT NOW this returns a few SAMPLE items so the app runs out of the box.
TODO (your team): replace the sample data with real calls to your chosen free
API, keeping the SAME return shapes so the rest of the app keeps working:

    search(query)   -> a list of dicts, each: {"id", "title", "image"}
    get_item(id)    -> one dict: {"id", "title", "image", "description"}
"""
import os

import requests  # you'll use this for the real API calls

from urllib.parse import quote

OVERPASS_API_URL = os.environ.get(
    "OVERPASS_API_URL", "https://overpass-api.de/api/interpreter"
)
OVERPASS_BACKUP_URLS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

WIKIPEDIA_API_URL = os.environ.get(
    "WIKIMEDIA_API_URL", "https://en.wikipedia.org/w/api.php"
)
_PLACES_CACHE = {}




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





def get_place_image(tags):
    """Return an image URL for a place, or None if no image is available."""

    # 1. Direct image URL from OpenStreetMap.
    image_url = tags.get("image")

    if image_url and image_url.startswith(("https://", "http://")):
        return image_url

    # 2. Wikimedia Commons file.
    commons_file = tags.get("wikimedia_commons", "")

    if commons_file.startswith("File:"):
        file_name = commons_file[len("File:"):]

        return (
            "https://commons.wikimedia.org/wiki/Special:FilePath/"
            + quote(file_name)
            + "?width=600"
        )

    # 3. Wikipedia article.
    wikipedia = tags.get("wikipedia", "")

    if ":" in wikipedia:
        language, article_title = wikipedia.split(":", 1)

        if language and article_title:
            try:
                response = requests.get(
                    f"https://{language}.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "titles": article_title,
                        "prop": "pageimages",
                        "format": "json",
                        "pithumbsize": 600,
                    },
                    headers={
                        "User-Agent": "BromElArd/1.0 (destination image lookup)"
                    },
                    timeout=3,
                )

                response.raise_for_status()

                data = response.json()
                pages = data.get("query", {}).get("pages", {})

                for page in pages.values():
                    thumbnail = page.get("thumbnail", {})
                    image_url = thumbnail.get("source")

                    if image_url:
                        return image_url

            except requests.RequestException as error:
                print(f"Could not retrieve Wikipedia image: {error}")

    return None


def search_places(latitude, longitude, limit=3):
    """Find named places and attractions near the searched destination."""
    cache_key = (round(float(latitude), 2), round(float(longitude), 2), limit)
    if cache_key in _PLACES_CACHE:
        return _PLACES_CACHE[cache_key]

    query = f"""
    [out:json][timeout:8];
    (
    node(around:1200,{latitude},{longitude})["tourism"~"attraction|museum|viewpoint|gallery"]["name"];
    way(around:1200,{latitude},{longitude})["tourism"~"attraction|museum|viewpoint|gallery"]["name"];
    node(around:1200,{latitude},{longitude})["historic"~"monument|castle|ruins|memorial"]["name"];
    way(around:1200,{latitude},{longitude})["historic"~"monument|castle|ruins|memorial"]["name"];
    );
    out center 15;
    """

    overpass_urls = [OVERPASS_API_URL] + OVERPASS_BACKUP_URLS
    overpass_data = None

    for url in dict.fromkeys(overpass_urls):
        try:
            response = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": "BromElArd/1.0 (destination places search)"},
                timeout=(2, 4),
            )
            response.raise_for_status()
            response_data = response.json()
            if not isinstance(response_data, dict) or not isinstance(response_data.get("elements"), list):
                raise requests.RequestException("Overpass returned an unexpected response.")
            if response_data.get("remark"):
                raise requests.RequestException("Overpass could not complete the query.")
            overpass_data = response_data
            break
        except requests.RequestException as error:
            print(f"Overpass server failed ({url}): {error}")

    if overpass_data is None:
        fallback_places = _wikipedia_nearby_places(latitude, longitude, limit=limit)
        if fallback_places:
            _PLACES_CACHE[cache_key] = fallback_places
        return fallback_places

    with_images = []
    without_images = []
    seen_names = set()

    for element in overpass_data.get("elements", []):
        tags = element.get("tags", {})
        name = (tags.get("name") or tags.get("name:en") or "").strip()
        if not name:
            continue

        norm_name = name.lower()
        if norm_name in seen_names:
            continue
        seen_names.add(norm_name)

        place_type = "Place to visit"
        if tags.get("tourism"):
            place_type = tags["tourism"].replace("_", " ").title()
        elif tags.get("historic"):
            place_type = "Historic place"
        elif tags.get("leisure"):
            place_type = tags["leisure"].replace("_", " ").title()
        elif tags.get("amenity") in ("restaurant", "cafe", "bar"):
            place_type = tags["amenity"].replace("_", " ").title()

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

        image_url = get_place_image(tags)

        place = {
            "id": f"{element.get('type')}/{element.get('id')}",
            "name": name,
            "type": place_type,
            "details": " · ".join(details),
            "url": url,
            "image": image_url,
            "lat": latitude_value,
            "lon": longitude_value,
        }

        if image_url:
            with_images.append(place)
        else:
            without_images.append(place)

        if len(with_images) >= limit:
            result = with_images[:limit]
            _PLACES_CACHE[cache_key] = result
            return result

    result = (with_images + without_images)[:limit]
    if result:
        _PLACES_CACHE[cache_key] = result
    return result

def _wikipedia_nearby_places(latitude, longitude, limit=3):
    """Fallback using Wikipedia GeoSearch when Overpass servers are down or slow."""
    try:
        geo_resp = requests.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{latitude}|{longitude}",
                "gsradius": 2500,
                "gslimit": 10,
                "format": "json",
            },
            headers={"User-Agent": "BromElArd/1.0 (nearby places fallback)"},
            timeout=5,
        )
        geo_resp.raise_for_status()
        results = geo_resp.json().get("query", {}).get("geosearch", [])
        if not results:
            return []

        titles = [item["title"] for item in results if item.get("title")]
        img_resp = requests.get(
            WIKIPEDIA_API_URL,
            params={
                "action": "query",
                "titles": "|".join(titles[:10]),
                "prop": "pageimages|extracts",
                "exintro": 1,
                "explaintext": 1,
                "exsentences": 1,
                "pithumbsize": 600,
                "format": "json",
            },
            headers={"User-Agent": "BromElArd/1.0 (nearby places images)"},
            timeout=5,
        )
        img_resp.raise_for_status()
        pages = img_resp.json().get("query", {}).get("pages", {})

        by_title = {}
        for page in pages.values():
            title = page.get("title")
            if title:
                by_title[title] = page

        with_images = []
        without_images = []

        for item in results:
            title = item.get("title", "").strip()
            if not title:
                continue
            page = by_title.get(title, {})
            thumb_url = page.get("thumbnail", {}).get("source")
            extract = (page.get("extract") or "").strip()
            pageid = item.get("pageid")
            url = f"https://en.wikipedia.org/?curid={pageid}" if pageid else ""

            place = {
                "id": f"wiki/{pageid or quote(title)}",
                "name": title,
                "type": "Attraction",
                "details": extract,
                "url": url,
                "image": thumb_url,
                "lat": item.get("lat"),
                "lon": item.get("lon"),
            }
            if thumb_url:
                with_images.append(place)
            else:
                without_images.append(place)

        return (with_images + without_images)[:limit]
    except requests.RequestException as error:
        print(f"Wikipedia fallback failed: {error}")
        return []

def get_item(item_id):
    """Return one item by its id, or None if not found."""
    # TODO: call your API for one item, e.g.
    #   r = requests.get(f"https://api.example.com/item/{item_id}", timeout=TIMEOUT)
    #   ...
    for it in _SAMPLE:
        if it["id"] == item_id:
            return it
    return None
