// Flask serializes an explicit allowlist of browser-visible API settings.
export const apiConfig = JSON.parse(document.getElementById("api-config").textContent);
