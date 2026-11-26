// Runs on the results page. It reads city and country from the URL,
// gets the forecast and photo, and displays them with the map.

import { apiConfig } from "./modules/config.js";
import { showMap } from "./modules/map.js";

const forecastBox = document.getElementById("forecast-data");

const GEOCODING_API = apiConfig.geocodingUrl;
const FORECAST_API = apiConfig.forecastUrl;
const WIKIMEDIA_API = apiConfig.wikimediaUrl;

const countryCodes = {
    us: "US",
    usa: "US",
    "united states": "US",
    "united states of america": "US",
    uk: "GB",
    "united kingdom": "GB",
    uae: "AE",
    "united arab emirates": "AE"
};

// Converts a weather code into a matching emoji.
function getWeatherEmoji(weatherCode) {
    if (weatherCode === 0) return "☀️";
    if (weatherCode >= 1 && weatherCode <= 3) return "⛅";
    if (weatherCode >= 51 && weatherCode <= 67) return "🌧️";
    if (weatherCode >= 71 && weatherCode <= 77) return "❄️";
    if (weatherCode >= 95 && weatherCode <= 99) return "⛈️";
    return "🌡️";
}

// Converts a weather code into a short description.
function getWeatherDescription(weatherCode) {
    if (weatherCode === 0) return "Clear sky";
    if (weatherCode === 1) return "Mainly clear";
    if (weatherCode === 2) return "Partly cloudy";
    if (weatherCode === 3) return "Overcast";
    if (weatherCode >= 51 && weatherCode <= 55) return "Drizzle";
    if (weatherCode >= 61 && weatherCode <= 65) return "Rain";
    if (weatherCode >= 71 && weatherCode <= 75) return "Snow fall";
    if (weatherCode >= 95 && weatherCode <= 99) return "Thunderstorm";
    return "Fair weather";
}

// Loads the destination forecast, map, and nearby places.
async function BuildPage() {
    if (!forecastBox) return;

    const urlParameters = new URLSearchParams(window.location.search);
    const city = (urlParameters.get("city") || "").trim();
    const country = (urlParameters.get("country") || "").trim();
    if (city === "") return;

    forecastBox.textContent = `Loading weather for ${city}...`;

    try {
        const forecast = await getCityForecast(city, country);
        showMap(forecast.location.lat, forecast.location.lon, forecast);
        loadPlaces(
            forecast.location.lat,
            forecast.location.lon,
            forecast.location.city,
            forecast.location.country
        );
        const imageUrl = await getCityImage(forecast.location.city, forecast.location.country);
        displayWeather(forecast, imageUrl);
    } catch (error) {
        console.error(error);
        let isCountryMismatch = false;
        if (country !== "" && error.message.includes(`in "${country}"`)) {
            isCountryMismatch = true;
        }
        displayError(error.message, isCountryMismatch);
    }
}

// Finds the destination coordinates and retrieves its forecast.
async function getCityForecast(city, country) {
    const lowerCountry = country.toLowerCase();
    let countryCode = countryCodes[lowerCountry] || "";

    // A two-letter country code can be sent directly to Open-Meteo.
    if (countryCode === "" && /^[a-z]{2}$/i.test(country)) {
        countryCode = country.toUpperCase();
    }

    const geocodingParameters = new URLSearchParams();
    geocodingParameters.set("name", country && !countryCode ? `${city}, ${country}` : city);
    geocodingParameters.set("count", "100");
    geocodingParameters.set("language", "en");
    geocodingParameters.set("format", "json");
    if (countryCode) {
        geocodingParameters.set("countryCode", countryCode);
    }

    const geocodingResponse = await fetch(`${GEOCODING_API}?${geocodingParameters}`);
    if (!geocodingResponse.ok) {
        throw new Error("Could not fetch location data.");
    }
    const geocodingData = await geocodingResponse.json();
    const locations = geocodingData.results || [];

    let selectedLocation = null;
    let mostPopulatedLocation = null;

    // Keep only results in the requested country, when one was entered.
    for (let i = 0; i < locations.length; i++) {
        const location = locations[i];
        let isInCountry = true;

        if (countryCode) {
            isInCountry = location.country_code === countryCode;
        } else if (country !== "") {
            isInCountry = location.country && location.country.toLowerCase() === lowerCountry;
        }

        if (isInCountry) {
            if (!mostPopulatedLocation || (location.population || 0) > (mostPopulatedLocation.population || 0)) {
                mostPopulatedLocation = location;
            }

            // Prefer an exact city name match when one is available.
            if (location.name.toLowerCase() === city.toLowerCase()) {
                selectedLocation = location;
                break;
            }
        }
    }

    if (!selectedLocation) {
        selectedLocation = mostPopulatedLocation;
    }

    if (!selectedLocation) {
        if (country !== "") {
            throw new Error(`We couldn't find "${city}" in "${country}". Please check both entries and try again.`);
        }
        throw new Error(`We couldn't find "${city}". Check the spelling and try again.`);
    }

    const forecastParameters = new URLSearchParams();
    forecastParameters.set("latitude", selectedLocation.latitude);
    forecastParameters.set("longitude", selectedLocation.longitude);
    forecastParameters.set("current", "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m");
    forecastParameters.set("daily", "temperature_2m_max,temperature_2m_min,weather_code");
    forecastParameters.set("forecast_days", "5");
    forecastParameters.set("timezone", "auto");

    const forecastResponse = await fetch(`${FORECAST_API}?${forecastParameters}`);
    if (!forecastResponse.ok) {
        throw new Error("Could not fetch weather forecast.");
    }
    const forecastData = await forecastResponse.json();

    return {
        location: {
            city: selectedLocation.name,
            country: selectedLocation.country || "",
            lat: selectedLocation.latitude,
            lon: selectedLocation.longitude
        },
        currentWeather: forecastData.current,
        dailyForecast: forecastData.daily
    };
}

// Finds a Wikimedia photo for the destination.
async function getCityImage(city, country) {
    let searchText = `${city} ${country} landmark attraction`;
    const searchParameters = new URLSearchParams();
    searchParameters.set("action", "query");
    searchParameters.set("generator", "search");
    searchParameters.set("gsrsearch", searchText);
    searchParameters.set("gsrlimit", "3");
    searchParameters.set("prop", "pageimages");
    searchParameters.set("pithumbsize", "800");
    searchParameters.set("format", "json");
    searchParameters.set("origin", "*");

    try {
        const response = await fetch(`${WIKIMEDIA_API}?${searchParameters}`);
        if (!response.ok) {
            throw new Error("Wikimedia request failed.");
        }

        const data = await response.json();
        if (data.query && data.query.pages) {
            const pages = data.query.pages;
            for (const pageId in pages) {
                if (pages[pageId].thumbnail && pages[pageId].thumbnail.source) {
                    return pages[pageId].thumbnail.source;
                }
            }
        }
    } catch (error) {
        console.warn("Could not load a city photo.", error);
    }

    return makePlaceholder();
}

// Requests nearby places and builds their cards.
async function loadPlaces(latitude, longitude, city, country) {
    const placesBox = document.getElementById("places-list");
    if (!placesBox) return;

    placesBox.textContent = "Loading nearby places...";

    try {
        const response = await fetch(`/api/places?lat=${latitude}&lon=${longitude}`);
        if (!response.ok) {
            throw new Error("Could not get nearby places.");
        }

        const data = await response.json();
        placesBox.textContent = "";

        if (!data.places || data.places.length === 0) {
            placesBox.textContent = "No nearby places were found.";
            return;
        }

        const placeCards = document.createElement("div");
        placeCards.className = "place-cards";
        const placePhotos = [];

        for (let i = 0; i < data.places.length; i++) {
            const place = data.places[i];
            const card = document.createElement("article");
            card.className = "place-card";

            const photoBox = document.createElement("div");
            photoBox.className = "place-image-unavailable";
            photoBox.textContent = "No image available";
            card.appendChild(photoBox);
            placePhotos.push(photoBox);

            const placeName = document.createElement("h3");
            placeName.textContent = place.name;
            card.appendChild(placeName);

            const placeType = document.createElement("p");
            placeType.className = "place-type";
            placeType.textContent = place.type;
            card.appendChild(placeType);

            if (place.details) {
                const details = document.createElement("p");
                details.textContent = place.details;
                card.appendChild(details);
            }

            const mapLink = document.createElement("a");
            mapLink.href = place.url;
            mapLink.target = "_blank";
            mapLink.rel = "noopener";
            mapLink.textContent = "View on OpenStreetMap";
            card.appendChild(mapLink);

            placeCards.appendChild(card);
        }

        placesBox.appendChild(placeCards);

        // Look for a Wikimedia photo for each place. Keep the text message if none is found.
        for (let i = 0; i < data.places.length; i++) {
            const imageUrl = await getPlaceImage(data.places[i].name, city, country);

            if (imageUrl) {
                const placeImage = document.createElement("img");
                placeImage.className = "place-image";
                placeImage.src = imageUrl;
                placeImage.alt = `Photo of ${data.places[i].name}`;
                placeImage.onerror = function () {
                    placeImage.replaceWith(createNoImageMessage());
                };
                placePhotos[i].replaceWith(placeImage);
            }
        }
    } catch (error) {
        console.error(error);
        placesBox.textContent = "Nearby places could not be loaded right now. Please try again later.";
    }
}

// Finds a Wikimedia photo for a nearby place.
async function getPlaceImage(placeName, city, country) {
    const searchParameters = new URLSearchParams();
    searchParameters.set("action", "query");
    searchParameters.set("generator", "search");
    searchParameters.set("gsrsearch", `${placeName} ${city} ${country}`.trim());
    searchParameters.set("gsrlimit", "3");
    searchParameters.set("prop", "pageimages");
    searchParameters.set("pithumbsize", "500");
    searchParameters.set("format", "json");
    searchParameters.set("origin", "*");

    try {
        const response = await fetch(`${WIKIMEDIA_API}?${searchParameters}`);
        if (!response.ok) {
            throw new Error("Wikimedia photo search failed.");
        }

        const data = await response.json();
        if (data.query && data.query.pages) {
            const pages = data.query.pages;
            for (const pageId in pages) {
                if (pages[pageId].thumbnail && pages[pageId].thumbnail.source) {
                    return pages[pageId].thumbnail.source;
                }
            }
        }
    } catch (error) {
        console.warn(`Could not load a photo for ${placeName}.`, error);
    }

    return "";
}

// Creates the message shown when a place has no working photo.
function createNoImageMessage() {
    const message = document.createElement("div");
    message.className = "place-image-unavailable";
    message.textContent = "No image available";
    return message;
}

// Creates a simple image shown when no suitable photo is available.
function makePlaceholder() {
    const svg = `
        <svg xmlns="http://www.w3.org/2000/svg" width="600" height="300">
            <rect width="100%" height="100%" fill="#e9ecef" />
            <text x="50%" y="54%" text-anchor="middle" fill="#6c757d" font-size="18">Photo unavailable</text>
        </svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

// Displays current conditions and the five-day forecast.
function displayWeather(forecast, imageUrl) {
    forecastBox.textContent = "";
    forecastBox.style.display = "block";

    const summary = document.createElement("div");
    summary.className = "weather-summary";

    const cityImage = document.createElement("img");
    cityImage.src = imageUrl;
    cityImage.alt = forecast.location.city;
    cityImage.className = "cityCardImage";
    // Uses a placeholder if the photo URL cannot be loaded by the browser.
    cityImage.onerror = function () {
        cityImage.onerror = null;
        cityImage.src = makePlaceholder();
    };
    summary.appendChild(cityImage);

    const weatherInfo = document.createElement("div");
    weatherInfo.className = "current-weather-info";

    const cityTitle = document.createElement("h3");
    cityTitle.textContent = forecast.location.country
        ? `${forecast.location.city}, ${forecast.location.country}`
        : forecast.location.city;
    cityTitle.className = "cityDisplay";
    weatherInfo.appendChild(cityTitle);

    const current = forecast.currentWeather;
    const temperatureText = document.createElement("p");
    temperatureText.textContent = `${current.temperature_2m}°C`;
    temperatureText.className = "tempDisplay";
    weatherInfo.appendChild(temperatureText);

    const condition = document.createElement("p");
    condition.className = "weather-condition";
    condition.textContent = `${getWeatherEmoji(current.weather_code)} ${getWeatherDescription(current.weather_code)}`;
    weatherInfo.appendChild(condition);

    const weatherDetails = document.createElement("div");
    weatherDetails.className = "weather-details";
    const humidityText = document.createElement("p");
    const humidityLabel = document.createElement("span");
    humidityLabel.textContent = "Humidity";
    const humidityValue = document.createElement("strong");
    humidityValue.textContent = `${current.relative_humidity_2m}%`;
    humidityText.appendChild(humidityLabel);
    humidityText.appendChild(humidityValue);
    weatherDetails.appendChild(humidityText);

    const windText = document.createElement("p");
    const windLabel = document.createElement("span");
    windLabel.textContent = "Wind";
    const windValue = document.createElement("strong");
    windValue.textContent = `${current.wind_speed_10m} km/h`;
    windText.appendChild(windLabel);
    windText.appendChild(windValue);
    weatherDetails.appendChild(windText);

    weatherInfo.appendChild(weatherDetails);
    summary.appendChild(weatherInfo);
    forecastBox.appendChild(summary);

    const dailyTitle = document.createElement("h3");
    dailyTitle.textContent = "Next five days";
    dailyTitle.className = "daily-forecast-title";
    forecastBox.appendChild(dailyTitle);

    const dailyList = document.createElement("div");
    dailyList.className = "daily-forecast";

    for (let i = 0; i < forecast.dailyForecast.time.length; i++) {
        const card = document.createElement("article");
        card.className = "daily-forecast-card";

        const date = forecast.dailyForecast.time[i];
        const day = document.createElement("strong");
        day.textContent = new Intl.DateTimeFormat(undefined, {
            weekday: "short", month: "short", day: "numeric", timeZone: "UTC"
        }).format(new Date(`${date}T12:00:00Z`));

        const condition = document.createElement("span");
        condition.textContent = getWeatherEmoji(forecast.dailyForecast.weather_code[i]);

        const temperature = document.createElement("span");
        const low = Math.round(forecast.dailyForecast.temperature_2m_min[i]);
        const high = Math.round(forecast.dailyForecast.temperature_2m_max[i]);
        temperature.textContent = `${low}° / ${high}°C`;

        card.appendChild(day);
        card.appendChild(condition);
        card.appendChild(temperature);
        dailyList.appendChild(card);
    }

    forecastBox.appendChild(dailyList);
}

// Shows the error and a link back to the destination form.
function displayError(message, countryMismatch) {
    forecastBox.textContent = "";
    forecastBox.style.display = "block";

    const errorText = document.createElement("p");
    errorText.textContent = message || "Could not load this destination. Please try again.";
    errorText.className = "error";
    errorText.setAttribute("role", "alert");
    forecastBox.appendChild(errorText);

    const mapBox = document.getElementById("map");
    if (mapBox) {
        if (countryMismatch) {
            mapBox.textContent = "The map is hidden because the city does not match the selected country.";
        } else {
            mapBox.textContent = "The map could not be loaded for this destination.";
        }
    }

    const homeLink = document.createElement("a");
    homeLink.href = "/";
    homeLink.textContent = "Return to the destination form";
    forecastBox.appendChild(homeLink);
}

BuildPage();
