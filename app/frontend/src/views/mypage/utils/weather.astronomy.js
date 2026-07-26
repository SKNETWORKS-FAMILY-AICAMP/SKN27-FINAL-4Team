const KOREA_TIMEZONE_OFFSET = 9;
const DEFAULT_LATITUDE = 37.5665;
const DEFAULT_LONGITUDE = 126.978;
const SYNODIC_MONTH_DAYS = 29.530588853;
const KNOWN_NEW_MOON_JULIAN_DAY = 2451550.1;

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const positiveModulo = (value, divisor) => ((value % divisor) + divisor) % divisor;

function parseObservation(baseDate, baseTime) {
  const now = new Date();
  const dateDigits = String(baseDate || "").replace(/\D/g, "");
  const rawTimeDigits = String(baseTime ?? "").replace(/\D/g, "");
  const timeDigits = rawTimeDigits.padStart(4, "0");
  const hasObservationTime = rawTimeDigits.length >= 3;

  const year = dateDigits.length >= 8 ? Number(dateDigits.slice(0, 4)) : now.getFullYear();
  const month = dateDigits.length >= 8 ? Number(dateDigits.slice(4, 6)) : now.getMonth() + 1;
  const day = dateDigits.length >= 8 ? Number(dateDigits.slice(6, 8)) : now.getDate();
  const hour = hasObservationTime ? Number(timeDigits.slice(0, 2)) : now.getHours();
  const minute = hasObservationTime ? Number(timeDigits.slice(2, 4)) : now.getMinutes();

  return {
    year,
    month,
    day,
    hour: clamp(Number.isFinite(hour) ? hour : now.getHours(), 0, 23),
    minute: clamp(Number.isFinite(minute) ? minute : now.getMinutes(), 0, 59),
  };
}

function getDayOfYear({ year, month, day }) {
  const start = Date.UTC(year, 0, 0);
  const current = Date.UTC(year, month - 1, day);
  return Math.floor((current - start) / 86400000);
}

function getSolarCycle(observation, latitude, longitude) {
  const dayOfYear = getDayOfYear(observation);
  const localHour = observation.hour + observation.minute / 60;
  const gamma = (2 * Math.PI / 365) * (dayOfYear - 1 + (localHour - 12) / 24);
  const equationOfTime = 229.18 * (
    0.000075
    + 0.001868 * Math.cos(gamma)
    - 0.032077 * Math.sin(gamma)
    - 0.014615 * Math.cos(2 * gamma)
    - 0.040849 * Math.sin(2 * gamma)
  );
  const declination = (
    0.006918
    - 0.399912 * Math.cos(gamma)
    + 0.070257 * Math.sin(gamma)
    - 0.006758 * Math.cos(2 * gamma)
    + 0.000907 * Math.sin(2 * gamma)
    - 0.002697 * Math.cos(3 * gamma)
    + 0.00148 * Math.sin(3 * gamma)
  );
  const latitudeRadians = latitude * Math.PI / 180;
  const solarAltitude = -0.833 * Math.PI / 180;
  const hourAngleCosine = clamp(
    (Math.sin(solarAltitude) - Math.sin(latitudeRadians) * Math.sin(declination))
      / (Math.cos(latitudeRadians) * Math.cos(declination)),
    -1,
    1,
  );
  const hourAngleDegrees = Math.acos(hourAngleCosine) * 180 / Math.PI;
  const solarNoonMinutes = 720 - 4 * longitude - equationOfTime + KOREA_TIMEZONE_OFFSET * 60;
  const sunrise = (solarNoonMinutes - hourAngleDegrees * 4) / 60;
  const sunset = (solarNoonMinutes + hourAngleDegrees * 4) / 60;
  const currentHourAngle = (localHour - solarNoonMinutes / 60) * 15 * Math.PI / 180;
  const altitudeRadians = Math.asin(clamp(
    Math.sin(latitudeRadians) * Math.sin(declination)
      + Math.cos(latitudeRadians) * Math.cos(declination) * Math.cos(currentHourAngle),
    -1,
    1,
  ));
  const noonAltitudeRadians = Math.asin(clamp(
    Math.sin(latitudeRadians) * Math.sin(declination)
      + Math.cos(latitudeRadians) * Math.cos(declination),
    -1,
    1,
  ));
  const altitudeDegrees = altitudeRadians * 180 / Math.PI;
  const maxAltitudeDegrees = noonAltitudeRadians * 180 / Math.PI;
  const isDay = localHour >= sunrise && localHour <= sunset;
  const progress = clamp((localHour - sunrise) / Math.max(0.1, sunset - sunrise), 0, 1);
  const elevation = isDay
    ? clamp((altitudeDegrees + 0.833) / Math.max(1, maxAltitudeDegrees + 0.833), 0, 1)
    : 0;
  const strength = Math.pow(elevation, 0.58);

  return {
    sunrise,
    sunset,
    isDay,
    progress,
    altitudeDegrees,
    maxAltitudeDegrees,
    strength,
    x: 46 + progress * 228,
    y: 130 - elevation * 88,
    scale: 0.84 + strength * 0.16,
    opacity: 0.68 + strength * 0.32,
  };
}

function getMoonPhase(observation) {
  const utcMilliseconds = Date.UTC(
    observation.year,
    observation.month - 1,
    observation.day,
    observation.hour - KOREA_TIMEZONE_OFFSET,
    observation.minute,
  );
  const julianDay = utcMilliseconds / 86400000 + 2440587.5;
  const phase = positiveModulo(
    (julianDay - KNOWN_NEW_MOON_JULIAN_DAY) / SYNODIC_MONTH_DAYS,
    1,
  );

  return {
    phase,
    illumination: (1 - Math.cos(2 * Math.PI * phase)) / 2,
    waxing: phase < 0.5,
  };
}

function getMoonPosition(localHour, sunrise, sunset) {
  const nightDuration = Math.max(1, 24 - sunset + sunrise);
  const elapsed = localHour >= sunset
    ? localHour - sunset
    : 24 - sunset + localHour;
  const progress = clamp(elapsed / nightDuration, 0, 1);
  const altitude = Math.max(0, Math.sin(Math.PI * progress));

  return {
    progress,
    x: 48 + progress * 224,
    y: 126 - altitude * 80,
    scale: 0.9 + altitude * 0.1,
    opacity: 0.76 + altitude * 0.24,
  };
}

export function getWeatherAstronomy({ baseDate, baseTime, latitude, longitude } = {}) {
  const observation = parseObservation(baseDate, baseTime);
  const hasLatitude = latitude !== null && latitude !== "" && Number.isFinite(Number(latitude));
  const hasLongitude = longitude !== null && longitude !== "" && Number.isFinite(Number(longitude));
  const lat = hasLatitude ? Number(latitude) : DEFAULT_LATITUDE;
  const lon = hasLongitude ? Number(longitude) : DEFAULT_LONGITUDE;
  const solar = getSolarCycle(observation, lat, lon);
  const localHour = observation.hour + observation.minute / 60;

  return {
    observation,
    solar,
    moon: {
      ...getMoonPhase(observation),
      ...getMoonPosition(localHour, solar.sunrise, solar.sunset),
    },
  };
}

export function getMoonIlluminatedPath(phase, cx = 88, cy = 58, radius = 27) {
  const normalizedPhase = positiveModulo(Number(phase) || 0, 1);
  const terminatorRadius = Math.max(0.01, radius * Math.abs(Math.cos(2 * Math.PI * normalizedPhase)));
  const waxing = normalizedPhase <= 0.5;
  const outerSweep = waxing ? 1 : 0;
  let terminatorSweep;

  if (waxing) {
    terminatorSweep = normalizedPhase < 0.25 ? 0 : 1;
  } else {
    terminatorSweep = normalizedPhase < 0.75 ? 0 : 1;
  }

  return [
    `M ${cx} ${cy - radius}`,
    `A ${radius} ${radius} 0 0 ${outerSweep} ${cx} ${cy + radius}`,
    `A ${terminatorRadius.toFixed(3)} ${radius} 0 0 ${terminatorSweep} ${cx} ${cy - radius}`,
    "Z",
  ].join(" ");
}
