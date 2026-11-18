// static/js/home.js
// Runs on the home page only (home.html). Enhances #destination-form.
//
// Nothing from your prototype belongs here: the prototype had no country list or
// autocomplete. This file is where the CountriesNow work will live.
//
// PLAN:
//  1. On load, fetch the country list ONCE from your Flask route (/api/countries),
//     which wraps CountriesNow (cached server-side for days). Never call
//     CountriesNow directly from the browser, and never send its whole raw response.
//  2. Offer those countries as suggestions on the #country input (e.g. a <datalist>).
//  3. When a country is chosen/typed, fetch its cities (/api/cities?country=...)
//     and offer them as suggestions on #city.
//  4. When adding requests, use fetch(), check response.ok, then read response.json().
//
// RULES:
//  - The form is a plain GET to /search. It MUST still submit and work with
//    JavaScript off or if the suggestion routes fail.
//  - Never block a search because a city isn't in the CountriesNow list; its data
//    has odd spellings and gaps. Suggestions help, they don't restrict.
//  - Put suggestion results in the DOM with createElement/textContent, not innerHTML.
//  - Debounce typing (wait ~200-300 ms) and cap how many suggestions you render.
//  - Load this file only on home.html, as <script type="module" ...>.
