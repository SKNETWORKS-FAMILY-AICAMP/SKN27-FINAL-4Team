const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const toFiniteNumber = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const hexToRgb = (hex) => {
  const value = String(hex).replace("#", "");
  return {
    r: Number.parseInt(value.slice(0, 2), 16),
    g: Number.parseInt(value.slice(2, 4), 16),
    b: Number.parseInt(value.slice(4, 6), 16),
  };
};

const mixColor = (from, to, ratio) => {
  const start = hexToRgb(from);
  const end = hexToRgb(to);
  const amount = clamp(ratio, 0, 1);
  const channel = (key) => Math.round(start[key] + (end[key] - start[key]) * amount)
    .toString(16)
    .padStart(2, "0");
  return `#${channel("r")}${channel("g")}${channel("b")}`;
};

const colorWithAlpha = (color, alpha) => {
  const { r, g, b } = hexToRgb(color);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const MORNING_SKY_STOPS = [
  { altitude: -18, top: "#0b1b31", mid: "#1d304b", bottom: "#343c55" },
  { altitude: -10, top: "#152c49", mid: "#374c67", bottom: "#715c6d" },
  { altitude: -5, top: "#294d6d", mid: "#6a7186", bottom: "#cf8d78" },
  { altitude: 0, top: "#47789e", mid: "#979aaa", bottom: "#eead7f" },
  { altitude: 7, top: "#5f98c2", mid: "#aab9c5", bottom: "#f1c28f" },
  { altitude: 22, top: "#4f91c5", mid: "#94bad5", bottom: "#d2dfe5" },
  { altitude: 55, top: "#3f86bd", mid: "#82b2d6", bottom: "#d6e5eb" },
];

const EVENING_SKY_STOPS = [
  { altitude: -18, top: "#0b1b31", mid: "#1d304b", bottom: "#343c55" },
  { altitude: -10, top: "#172945", mid: "#45445f", bottom: "#795563" },
  { altitude: -5, top: "#2d4969", mid: "#76647b", bottom: "#d27f6d" },
  { altitude: 0, top: "#4d7194", mid: "#9b8496", bottom: "#ef9971" },
  { altitude: 7, top: "#6391b4", mid: "#b19fac", bottom: "#efaf81" },
  { altitude: 22, top: "#528fbe", mid: "#9ab6ce", bottom: "#d8d8dd" },
  { altitude: 55, top: "#3f86bd", mid: "#82b2d6", bottom: "#d6e5eb" },
];

const interpolateSkyStops = (stops, altitude) => {
  if (altitude <= stops[0].altitude) return { ...stops[0] };
  const last = stops[stops.length - 1];
  if (altitude >= last.altitude) return { ...last };

  for (let index = 1; index < stops.length; index += 1) {
    const upper = stops[index];
    if (altitude > upper.altitude) continue;
    const lower = stops[index - 1];
    const ratio = (altitude - lower.altitude) / (upper.altitude - lower.altitude);
    return {
      top: mixColor(lower.top, upper.top, ratio),
      mid: mixColor(lower.mid, upper.mid, ratio),
      bottom: mixColor(lower.bottom, upper.bottom, ratio),
    };
  }

  return { ...last };
};

export const getWeatherSkyPalette = (astronomy = {}) => {
  const solar = astronomy?.solar || {};
  const rawAltitude = Number(solar.altitudeDegrees);
  const altitude = clamp(Number.isFinite(rawAltitude) ? rawAltitude : -18, -18, 90);
  const skyStops = solar.progress >= 0.5 ? EVENING_SKY_STOPS : MORNING_SKY_STOPS;
  const sky = interpolateSkyStops(skyStops, altitude);
  const strength = clamp(Number(solar.strength) || 0, 0, 1);
  const stormMix = 0.56 + strength * 0.16;
  const warmth = 1 - clamp((altitude + 1) / 28, 0, 1);
  const sunlightCore = mixColor("#fff8dc", "#ffd0a0", warmth);
  const sunlightMid = mixColor("#dceeff", "#f0a274", warmth);
  const sunMid = mixColor("#ffe9a5", "#ffd080", warmth);
  const sunEdge = mixColor("#f2bd62", "#f17f67", warmth);

  return {
    ...sky,
    stormTop: mixColor(sky.top, "#30485a", stormMix),
    stormMid: mixColor(sky.mid, "#566777", stormMix),
    stormBottom: mixColor(sky.bottom, "#82777b", stormMix),
    sunlightCore,
    sunlightMid,
    sunMid,
    sunEdge,
    sunAura: colorWithAlpha(sunEdge, 0.2),
    sunRay: colorWithAlpha(sunlightCore, 0.64),
    starOpacity: clamp((-altitude - 2) / 10, 0, 0.84).toFixed(2),
  };
};

export const parseWeatherAmount = (value) => {
  if (value === null || value === undefined || value === "" || value === "-") return null;
  if (typeof value === "number") return Number.isFinite(value) ? Math.max(0, value) : null;

  const text = String(value).trim().replace(/,/g, "");
  if (!text || text === "강수없음") return 0;

  const amounts = [...text.matchAll(/\d+(?:\.\d+)?/g)].map((match) => Number(match[0]));
  if (!amounts.length) return null;
  if (text.includes("미만")) return Math.max(0, amounts[0] * 0.5);
  if (amounts.length > 1 && /[~～-]/.test(text)) return (amounts[0] + amounts[1]) / 2;
  return Math.max(0, amounts[0]);
};

export const getWeatherVisualState = (weather = {}) => {
  const condition = String(weather?.condition || "");
  const rainfall = parseWeatherAmount(weather?.rainfall_1h);
  const windSpeed = clamp(toFiniteNumber(weather?.wind_speed) ?? 1.5, 0, 20);
  const humidity = clamp(toFiniteNumber(weather?.humidity) ?? 55, 0, 100);
  const isPrecipitation = condition.includes("비") || condition.includes("눈") || condition.includes("소나기");
  const isLightLabel = condition.includes("약한") || condition.includes("날림");
  const isShower = condition.includes("소나기");

  let precipitationStrength = isPrecipitation ? 0.58 : 0;
  if (condition.includes("비/눈")) precipitationStrength = 0.54;
  if (condition.includes("눈") && !condition.includes("비/눈")) precipitationStrength = 0.5;
  if (isLightLabel) precipitationStrength = 0.34;
  if (isShower) precipitationStrength = 0.72;

  if (isPrecipitation && rainfall !== null && rainfall > 0) {
    const measuredStrength = 0.26 + Math.sqrt(clamp(rainfall / 20, 0, 1)) * 0.74;
    precipitationStrength = isLightLabel
      ? Math.min(0.48, Math.max(precipitationStrength, measuredStrength))
      : Math.max(precipitationStrength, measuredStrength);
  }

  precipitationStrength = clamp(precipitationStrength, 0, 1);
  const isLight = isPrecipitation && precipitationStrength < 0.49;
  const isHeavy = isPrecipitation && precipitationStrength >= 0.8;
  const windRatio = windSpeed / 20;
  const humidityRatio = humidity / 100;

  const snowDuration = 4.65 - precipitationStrength * 1.35;

  return {
    classes: {
      "is-light-precip": isLight,
      "is-heavy-precip": isHeavy,
      "is-shower": isShower,
    },
    style: {
      "--rain-opacity": (0.48 + precipitationStrength * 0.52).toFixed(2),
      "--rain-stroke": `${(1.8 + precipitationStrength * 1.7).toFixed(2)}px`,
      "--rain-duration": `${(1.48 - precipitationStrength * 0.55).toFixed(2)}s`,
      "--rain-splash-opacity": (0.32 + precipitationStrength * 0.58).toFixed(2),
      "--snow-opacity": (0.5 + precipitationStrength * 0.5).toFixed(2),
      "--snow-stroke": `${(1.05 + precipitationStrength * 0.55).toFixed(2)}px`,
      "--snow-duration": `${snowDuration.toFixed(2)}s`,
      "--snow-duration-2": `${(snowDuration * 1.14).toFixed(2)}s`,
      "--snow-duration-3": `${(snowDuration * 1.04).toFixed(2)}s`,
      "--snow-duration-4": `${(snowDuration * 1.22).toFixed(2)}s`,
      "--snow-duration-5": `${(snowDuration * 1.1).toFixed(2)}s`,
      "--cloud-front-duration": `${(8.1 - windRatio * 3).toFixed(2)}s`,
      "--cloud-rear-duration": `${(10.2 - windRatio * 3.4).toFixed(2)}s`,
      "--cloud-front-start": `${(-2 - windRatio * 5).toFixed(2)}px`,
      "--cloud-front-end": `${(3 + windRatio * 7).toFixed(2)}px`,
      "--cloud-rear-start": `${(1 + windRatio * 4).toFixed(2)}px`,
      "--cloud-rear-end": `${(-4 - windRatio * 6).toFixed(2)}px`,
      "--rain-start-x": `${(-7 - windRatio * 8).toFixed(2)}px`,
      "--rain-end-x": `${(8 + windRatio * 15).toFixed(2)}px`,
      "--snow-start-x": `${(-3 - windRatio * 5).toFixed(2)}px`,
      "--snow-mid-x": `${(5 + windRatio * 8).toFixed(2)}px`,
      "--snow-end-x": `${(-4 + windRatio * 12).toFixed(2)}px`,
      "--haze-min-opacity": (0.18 + humidityRatio * 0.25).toFixed(2),
      "--haze-max-opacity": (0.31 + humidityRatio * 0.36).toFixed(2),
    },
  };
};
