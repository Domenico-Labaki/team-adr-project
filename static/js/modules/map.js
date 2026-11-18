// Geoapify's map key is a browser key. It must be sent with tile requests.
// Tile requests are the individual HTTP calls your browser makes to a map server to fetch small, square image or data pieces (usually 256×256 or 512×512 pixels) that stitch together to form a seamless digital map.

import { apiConfig } from "./config.js";

let map; // it starts empty
let marker; // declares a variable for the current location marker,

// Displays the destination marker and its weather popup on the Leaflet map.
export function showMap(latitude, longitude, forecast) {
    const container = document.getElementById("map");  //div container in results.html where the map will be displayed
    if (!container) return; //Stops quietly if this page has no map element.

    if (!window.L) {  //Leaflet Js library attaches its exports directly to the browser's window object as window.L. Core classes and methods like L.map(), L.tileLayer(), and L.marker() live inside it.
        container.textContent = "The map library could not be loaded. Please refresh the page.";
        return;
    }
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        container.textContent = "Map coordinates are unavailable for this destination.";
        return;
    }

    if (!apiConfig.geoapifyKey) {
        container.textContent = "The map is unavailable because its API key is not configured.";
        return;
    }

    if (!map) {
        map = L.map(container, { scrollWheelZoom: false }).setView([latitude, longitude], 12); //Creates the Leaflet map in the container, disables zooming with the mouse wheel, and centers it on the destination at zoom level 12.
        L.tileLayer(
            `${apiConfig.geoapifyTileUrl}${apiConfig.geoapifyTileUrl.includes("?") ? "&" : "?"}apiKey=${encodeURIComponent(apiConfig.geoapifyKey)}`, {
            minZoom: 1,
            maxZoom: 20,
            attribution: 'Powered by <a href="https://www.geoapify.com/" target="_blank" rel="noopener">Geoapify</a> | <a href="https://openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> | <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap contributors</a>'
            // noopener: rel="noopener" prevents a page opened with target="_blank" from controlling the page that opened it through window.opener.
        }).addTo(map);
    } else {
        map.setView([latitude, longitude], 12);
    }

    if (marker) marker.remove();
    marker = L.marker([latitude, longitude]).addTo(map);
    const popup = document.createElement("div");
    const place = document.createElement("strong");
    place.textContent = forecast.location.city;
    const temperature = document.createElement("div");
    temperature.textContent = `Temperature: ${forecast.currentWeather.temperature_2m}°C`;
    popup.append(place, temperature); // adds the bold city name and temperature line to the popup content
    marker.bindPopup(popup).openPopup(); // leaflet method attaches the popup to the marker and openPopup opens it immediately.
    // Rechecks the map size after the browser finishes laying out the page.
    requestAnimationFrame(() => map.invalidateSize());   // asks Leaflet to recalculate the map size after layout
}
