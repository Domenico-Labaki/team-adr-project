// static/js/destinations.js
// Runs on the /destinations browse page only (country -> city).
//
// Nothing from your prototype belongs here either.
//
// PLAN:
//  1. Flask renders the country list (or this file fetches /api/countries, which
//     wraps CountriesNow, cached server-side).
//  2. Add a filter box: as the user types, hide/show matching items in the list
//     (case-insensitive, trim the input). No server call is needed per keystroke.
//  3. When a country is selected, show its cities (/api/cities?country=...) as links
//     to /search?country=<country>&city=<city>. Encode both values in the URL.
//  4. Bound the list size (pagination or a "show more" button): some countries
//     have thousands of cities. This is a non-functional requirement in the proposal.
//  5. Show empty ("No matches") and error ("Couldn't load cities") states.
//
// RULES:
//  - Build every list item with createElement/textContent (no innerHTML).
//  - When adding requests, use fetch(), check response.ok, then read response.json().
//  - Make the page usable without JS if you can (server-rendered links first,
//    filter box as an enhancement).
