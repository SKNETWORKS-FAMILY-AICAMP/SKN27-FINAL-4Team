export async function fetchCurrentWeather(location = {}, { rotateHobby = false } = {}) {
  const params = new URLSearchParams();
  if (location.lat != null && location.lon != null) {
    params.set("lat", location.lat);
    params.set("lon", location.lon);
  }
  if (location.region) {
    params.set("region", location.region);
  }
  if (rotateHobby) {
    params.set("rotate_hobby", "true");
  }

  const query = params.toString();
  const response = await fetch(`/api/myweather/current/${query ? `?${query}` : ""}`, {
    cache: "no-store",
    credentials: "include"
  });
  if (!response.ok) {
    let detail = `Failed to fetch weather: ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch (error) {
      // The status code remains useful when an upstream proxy returns non-JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

export async function fetchWeatherRegions() {
  const response = await fetch("/api/myweather/regions/", { credentials: "include" });
  if (!response.ok) {
    throw new Error(`Failed to fetch weather regions: ${response.status}`);
  }
  return response.json();
}
