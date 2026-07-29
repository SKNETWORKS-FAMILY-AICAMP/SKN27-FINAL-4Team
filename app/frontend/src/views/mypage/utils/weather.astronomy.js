const KOREA_TIMEZONE_OFFSET = 9;
const DEFAULT_LATITUDE = 37.5665;
const DEFAULT_LONGITUDE = 126.978;
const JULIAN_DAY_J2000 = 2451545;
const RADIANS = Math.PI / 180;
const DEGREES = 180 / Math.PI;
const EARTH_RADIUS_KM = 6378.14;

// Bright-star subset of the Hipparcos reference sky (J2000 equatorial
// coordinates). The weather card only needs naked-eye anchors around the Moon,
// so stars fainter than roughly magnitude 3 are intentionally omitted.
const BRIGHT_STAR_CATALOG = Object.freeze([
  ["Alpheratz", 0.1398, 29.0904, 2.06],
  ["Ankaa", 0.4381, -42.3061, 2.40],
  ["Schedar", 0.6751, 56.5373, 2.24],
  ["Diphda", 0.7265, -17.9866, 2.04],
  ["Achernar", 1.6286, -57.2368, 0.46],
  ["Hamal", 2.1196, 23.4624, 2.00],
  ["Sheratan", 1.9107, 20.8080, 2.64],
  ["Polaris", 2.5303, 89.2641, 1.98],
  ["Acamar", 2.9710, -40.3047, 2.88],
  ["Menkar", 3.0380, 4.0897, 2.54],
  ["Mirfak", 3.4054, 49.8612, 1.79],
  ["Alcyone", 3.7914, 24.1051, 2.87],
  ["Aldebaran", 4.5987, 16.5093, 0.85],
  ["Rigel", 5.2423, -8.2016, 0.13],
  ["Capella", 5.2782, 45.9980, 0.08],
  ["Bellatrix", 5.4189, 6.3497, 1.64],
  ["Elnath", 5.4382, 28.6075, 1.65],
  ["Alnilam", 5.6036, -1.2019, 1.69],
  ["Betelgeuse", 5.9195, 7.4071, 0.42],
  ["Canopus", 6.3992, -52.6957, -0.74],
  ["Sirius", 6.7525, -16.7161, -1.46],
  ["Adhara", 6.9771, -28.9721, 1.50],
  ["Wasat", 7.3354, 21.9823, 3.53],
  ["Procyon", 7.6550, 5.2250, 0.34],
  ["Pollux", 7.7553, 28.0262, 1.14],
  ["Avior", 8.3752, -59.5095, 1.86],
  ["Suhail", 9.1333, -43.4326, 2.23],
  ["Alphard", 9.4598, -8.6586, 1.98],
  ["Regulus", 10.1395, 11.9672, 1.35],
  ["Dubhe", 11.0621, 61.7510, 1.79],
  ["Denebola", 11.8177, 14.5721, 2.14],
  ["Acrux", 12.4433, -63.0991, 0.76],
  ["Gacrux", 12.5194, -57.1132, 1.63],
  ["Alioth", 12.9005, 55.9598, 1.76],
  ["Vindemiatrix", 13.0363, 10.9592, 2.83],
  ["Spica", 13.4199, -11.1613, 0.98],
  ["Alkaid", 13.7923, 49.3133, 1.85],
  ["Hadar", 14.0637, -60.3730, 0.61],
  ["Arcturus", 14.2610, 19.1824, -0.05],
  ["Rigil Kentaurus", 14.6601, -60.8351, -0.27],
  ["Kochab", 14.8451, 74.1555, 2.08],
  ["Zubenelgenubi", 14.8479, -16.0418, 2.75],
  ["Zubeneschamali", 15.2834, -9.3830, 2.61],
  ["Alphecca", 15.5781, 26.7147, 2.23],
  ["Unukalhai", 15.7378, 6.4256, 2.65],
  ["Dschubba", 16.0056, -22.6217, 2.32],
  ["Antares", 16.4901, -26.4320, 1.06],
  ["Atria", 16.8111, -69.0277, 1.91],
  ["Sabik", 17.1729, -15.7249, 2.43],
  ["Shaula", 17.5601, -37.1038, 1.62],
  ["Rasalhague", 17.5822, 12.5600, 2.08],
  ["Sargas", 17.6219, -42.9978, 1.86],
  ["Etamin", 17.9434, 51.4889, 2.24],
  ["Kaus Australis", 18.4029, -34.3846, 1.79],
  ["Vega", 18.6156, 38.7837, 0.03],
  ["Nunki", 18.9211, -26.2967, 2.05],
  ["Altair", 19.8464, 8.8683, 0.77],
  ["Dabih", 20.3502, -14.7814, 3.08],
  ["Peacock", 20.4275, -56.7351, 1.94],
  ["Deneb", 20.6905, 45.2803, 1.25],
  ["Sadalsuud", 21.5260, -5.5712, 2.87],
  ["Enif", 21.7364, 9.8750, 2.39],
  ["Deneb Algedi", 21.7840, -16.1273, 2.85],
  ["Al Na'ir", 22.1372, -46.9610, 1.74],
  ["Skat", 22.9108, -15.8208, 3.27],
  ["Fomalhaut", 22.9608, -29.6222, 1.16],
  ["Scheat", 23.0629, 28.0828, 2.42],
  ["Markab", 23.0793, 15.2053, 2.49],
].map(([name, rightAscensionHours, declinationDegrees, magnitude]) => Object.freeze({
  name,
  rightAscension: rightAscensionHours * 15 * RADIANS,
  declination: declinationDegrees * RADIANS,
  magnitude,
})));

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const positiveModulo = (value, divisor) => ((value % divisor) + divisor) % divisor;
const signedAngle = angle => positiveModulo(angle + Math.PI, Math.PI * 2) - Math.PI;

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

function getObservationDate(observation) {
  return new Date(Date.UTC(
    observation.year,
    observation.month - 1,
    observation.day,
    observation.hour - KOREA_TIMEZONE_OFFSET,
    observation.minute,
  ));
}

function getJulianDay(date) {
  return date.getTime() / 86400000 + 2440587.5;
}

function equatorialFromEcliptic(longitude, latitude, obliquity) {
  return {
    rightAscension: Math.atan2(
      Math.sin(longitude) * Math.cos(obliquity)
        - Math.tan(latitude) * Math.sin(obliquity),
      Math.cos(longitude),
    ),
    declination: Math.asin(clamp(
      Math.sin(latitude) * Math.cos(obliquity)
        + Math.cos(latitude) * Math.sin(obliquity) * Math.sin(longitude),
      -1,
      1,
    )),
  };
}

function getSunCoordinates(daysSinceJ2000) {
  const meanAnomaly = positiveModulo(
    (357.529 + 0.98560028 * daysSinceJ2000) * RADIANS,
    Math.PI * 2,
  );
  const meanLongitude = positiveModulo(
    (280.459 + 0.98564736 * daysSinceJ2000) * RADIANS,
    Math.PI * 2,
  );
  const longitude = positiveModulo(
    meanLongitude
      + 1.915 * RADIANS * Math.sin(meanAnomaly)
      + 0.020 * RADIANS * Math.sin(2 * meanAnomaly),
    Math.PI * 2,
  );
  const obliquity = (23.439 - 0.00000036 * daysSinceJ2000) * RADIANS;
  const distanceAu = (
    1.00014
    - 0.01671 * Math.cos(meanAnomaly)
    - 0.00014 * Math.cos(2 * meanAnomaly)
  );
  return {
    longitude,
    distanceAu,
    angularDiameterDegrees: 0.533128 / distanceAu,
    ...equatorialFromEcliptic(longitude, 0, obliquity),
  };
}

function getMoonCoordinates(daysSinceJ2000) {
  const meanLongitude = (218.316 + 13.176396 * daysSinceJ2000) * RADIANS;
  const meanAnomaly = (134.963 + 13.064993 * daysSinceJ2000) * RADIANS;
  const meanDistance = (93.272 + 13.229350 * daysSinceJ2000) * RADIANS;
  const longitude = positiveModulo(
    meanLongitude + 6.289 * RADIANS * Math.sin(meanAnomaly),
    Math.PI * 2,
  );
  const latitude = 5.128 * RADIANS * Math.sin(meanDistance);
  const distanceKm = 385001 - 20905 * Math.cos(meanAnomaly);
  const obliquity = (23.439 - 0.00000036 * daysSinceJ2000) * RADIANS;
  return {
    longitude,
    latitude,
    distanceKm,
    ...equatorialFromEcliptic(longitude, latitude, obliquity),
  };
}

function getLocalSiderealAngle(daysSinceJ2000, longitude) {
  const greenwichSiderealDegrees = 280.46061837 + 360.98564736629 * daysSinceJ2000;
  return positiveModulo(
    greenwichSiderealDegrees * RADIANS + longitude,
    Math.PI * 2,
  );
}

function getHorizontalCoordinates(rightAscension, declination, latitude, siderealAngle) {
  const hourAngle = signedAngle(siderealAngle - rightAscension);
  const altitude = Math.asin(clamp(
    Math.sin(latitude) * Math.sin(declination)
      + Math.cos(latitude) * Math.cos(declination) * Math.cos(hourAngle),
    -1,
    1,
  ));
  const azimuth = positiveModulo(Math.atan2(
    -Math.sin(hourAngle) * Math.cos(declination),
    Math.sin(declination) * Math.cos(latitude)
      - Math.cos(declination) * Math.sin(latitude) * Math.cos(hourAngle),
  ), Math.PI * 2);
  const parallacticAngle = Math.atan2(
    Math.sin(hourAngle),
    Math.tan(latitude) * Math.cos(declination)
      - Math.sin(declination) * Math.cos(hourAngle),
  );
  return { altitude, azimuth, hourAngle, parallacticAngle };
}

function precessJ2000(rightAscension, declination, julianDay) {
  const centuries = (julianDay - JULIAN_DAY_J2000) / 36525;
  const zeta = (
    2306.2181 * centuries
    + 0.30188 * centuries ** 2
    + 0.017998 * centuries ** 3
  ) / 3600 * RADIANS;
  const z = (
    2306.2181 * centuries
    + 1.09468 * centuries ** 2
    + 0.018203 * centuries ** 3
  ) / 3600 * RADIANS;
  const theta = (
    2004.3109 * centuries
    - 0.42665 * centuries ** 2
    - 0.041833 * centuries ** 3
  ) / 3600 * RADIANS;
  const shiftedRightAscension = rightAscension + zeta;
  const a = Math.cos(declination) * Math.sin(shiftedRightAscension);
  const b = (
    Math.cos(theta) * Math.cos(declination) * Math.cos(shiftedRightAscension)
    - Math.sin(theta) * Math.sin(declination)
  );
  const c = (
    Math.sin(theta) * Math.cos(declination) * Math.cos(shiftedRightAscension)
    + Math.cos(theta) * Math.sin(declination)
  );
  return {
    rightAscension: positiveModulo(Math.atan2(a, b) + z, Math.PI * 2),
    declination: Math.asin(clamp(c, -1, 1)),
  };
}

function angularSeparation(a, b) {
  return Math.acos(clamp(
    Math.sin(a.declination) * Math.sin(b.declination)
      + Math.cos(a.declination) * Math.cos(b.declination)
        * Math.cos(a.rightAscension - b.rightAscension),
    -1,
    1,
  ));
}

function getAtmosphericRefraction(altitudeDegrees) {
  if (altitudeDegrees < -1 || altitudeDegrees > 90) return 0;
  const denominator = Math.tan(
    (altitudeDegrees + 10.3 / (altitudeDegrees + 5.11)) * RADIANS,
  );
  if (!Number.isFinite(denominator) || Math.abs(denominator) < 0.0001) return 0;
  return Math.max(0, 1.02 / denominator / 60);
}

function getTwilightPhase(altitudeDegrees) {
  if (altitudeDegrees >= -0.833) return "daylight";
  if (altitudeDegrees >= -6) return "civil";
  if (altitudeDegrees >= -12) return "nautical";
  if (altitudeDegrees >= -18) return "astronomical";
  return "night";
}

function getSolarCycle(observation, latitude, longitude, horizontal, sunCoordinates) {
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
  const noonAltitudeRadians = Math.asin(clamp(
    Math.sin(latitudeRadians) * Math.sin(declination)
      + Math.cos(latitudeRadians) * Math.cos(declination),
    -1,
    1,
  ));
  const altitudeDegrees = horizontal.altitude * DEGREES;
  const azimuthDegrees = horizontal.azimuth * DEGREES;
  const refractionDegrees = getAtmosphericRefraction(altitudeDegrees);
  const apparentAltitudeDegrees = altitudeDegrees + refractionDegrees;
  const maxAltitudeDegrees = noonAltitudeRadians * 180 / Math.PI;
  const isDay = altitudeDegrees >= -0.833;
  const progress = clamp((localHour - sunrise) / Math.max(0.1, sunset - sunrise), 0, 1);
  const elevation = isDay
    ? clamp((apparentAltitudeDegrees + 0.833) / Math.max(1, maxAltitudeDegrees + 0.833), 0, 1)
    : 0;
  const strength = Math.pow(elevation, 0.58);
  const twilightStrength = clamp((altitudeDegrees + 18) / 17.167, 0, 1);
  const normalizedAzimuth = clamp((azimuthDegrees - 55) / 250, 0, 1);
  const screenAltitude = clamp((apparentAltitudeDegrees + 0.833) / 75, 0, 1);
  const apparentScale = clamp(sunCoordinates.angularDiameterDegrees / 0.533128, 0.975, 1.025);
  const horizonCompression = 0.86 + clamp((apparentAltitudeDegrees + 0.833) / 6, 0, 1) * 0.14;

  return {
    sunrise,
    sunset,
    isDay,
    twilightPhase: getTwilightPhase(altitudeDegrees),
    twilightStrength,
    progress,
    altitudeDegrees,
    apparentAltitudeDegrees,
    azimuthDegrees,
    refractionDegrees,
    maxAltitudeDegrees,
    distanceAu: sunCoordinates.distanceAu,
    angularDiameterDegrees: sunCoordinates.angularDiameterDegrees,
    strength,
    x: 34 + normalizedAzimuth * 252,
    y: 142 - screenAltitude * 104,
    scale: apparentScale,
    verticalScale: horizonCompression,
    opacity: 0.68 + strength * 0.32,
  };
}

function getMoonPhase(sunCoordinates, moonCoordinates) {
  const elongation = positiveModulo(
    moonCoordinates.longitude - sunCoordinates.longitude,
    Math.PI * 2,
  );
  return {
    phase: elongation / (Math.PI * 2),
    illumination: (1 - Math.cos(elongation)) / 2,
    waxing: elongation < Math.PI,
  };
}

function getMoonPosition(localHour, sunrise, sunset, horizontal) {
  const nightDuration = Math.max(1, 24 - sunset + sunrise);
  const elapsed = localHour >= sunset
    ? localHour - sunset
    : 24 - sunset + localHour;
  const progress = clamp(elapsed / nightDuration, 0, 1);
  const altitudeDegrees = horizontal.altitude * DEGREES;
  const elevation = clamp((altitudeDegrees + 2) / 68, 0, 1);

  return {
    progress,
    x: 48 + progress * 224,
    y: 126 - elevation * 80,
    scale: 0.88 + elevation * 0.12,
    opacity: 0.74 + elevation * 0.26,
    visibility: clamp((altitudeDegrees + 1.5) / 5, 0, 1),
    altitudeDegrees,
    azimuthDegrees: horizontal.azimuth * DEGREES,
    surfaceRotationDegrees: horizontal.parallacticAngle * DEGREES,
  };
}

function getNearbyMoonStars({
  julianDay,
  latitude,
  siderealAngle,
  moonCoordinates,
  moonHorizontal,
  moonPosition,
}) {
  const maximumSeparation = 58 * RADIANS;
  const moonAltitude = moonHorizontal.altitude;

  return BRIGHT_STAR_CATALOG.map((star, index) => {
    const equatorial = precessJ2000(
      star.rightAscension,
      star.declination,
      julianDay,
    );
    const separation = angularSeparation(equatorial, moonCoordinates);
    if (separation > maximumSeparation) return null;

    const horizontal = getHorizontalCoordinates(
      equatorial.rightAscension,
      equatorial.declination,
      latitude,
      siderealAngle,
    );
    const altitudeDegrees = horizontal.altitude * DEGREES;
    if (altitudeDegrees < -1.5) return null;

    const deltaAzimuth = signedAngle(horizontal.azimuth - moonHorizontal.azimuth);
    const averageAltitude = (horizontal.altitude + moonAltitude) / 2;
    const x = (
      moonPosition.x
      + deltaAzimuth * DEGREES * Math.max(0.32, Math.cos(averageAltitude)) * 1.8
    );
    const y = (
      moonPosition.y
      - (horizontal.altitude - moonAltitude) * DEGREES * 1.42
    );
    if (x < 8 || x > 312 || y < 7 || y > 128) return null;

    return {
      id: `${star.name}-${index}`,
      name: star.name,
      magnitude: star.magnitude,
      x: Number(x.toFixed(2)),
      y: Number(y.toFixed(2)),
      radius: Number(clamp(1.7 - star.magnitude * 0.27, 0.58, 2.15).toFixed(2)),
      opacity: Number(clamp(1.05 - star.magnitude * 0.12, 0.54, 1).toFixed(2)),
      prominent: star.magnitude <= 1.2,
      twinkleDelay: Number((-(index % 9) * 0.43).toFixed(2)),
    };
  }).filter(Boolean);
}

export function getWeatherAstronomy({ baseDate, baseTime, latitude, longitude } = {}) {
  const observation = parseObservation(baseDate, baseTime);
  const hasLatitude = latitude !== null && latitude !== "" && Number.isFinite(Number(latitude));
  const hasLongitude = longitude !== null && longitude !== "" && Number.isFinite(Number(longitude));
  const lat = hasLatitude ? Number(latitude) : DEFAULT_LATITUDE;
  const lon = hasLongitude ? Number(longitude) : DEFAULT_LONGITUDE;
  const localHour = observation.hour + observation.minute / 60;
  const observationDate = getObservationDate(observation);
  const julianDay = getJulianDay(observationDate);
  const daysSinceJ2000 = julianDay - JULIAN_DAY_J2000;
  const latitudeRadians = lat * RADIANS;
  const longitudeRadians = lon * RADIANS;
  const siderealAngle = getLocalSiderealAngle(daysSinceJ2000, longitudeRadians);
  const sunCoordinates = getSunCoordinates(daysSinceJ2000);
  const sunHorizontal = getHorizontalCoordinates(
    sunCoordinates.rightAscension,
    sunCoordinates.declination,
    latitudeRadians,
    siderealAngle,
  );
  const solar = getSolarCycle(
    observation,
    lat,
    lon,
    sunHorizontal,
    sunCoordinates,
  );
  const moonCoordinates = getMoonCoordinates(daysSinceJ2000);
  const geocentricMoonHorizontal = getHorizontalCoordinates(
    moonCoordinates.rightAscension,
    moonCoordinates.declination,
    latitudeRadians,
    siderealAngle,
  );
  const horizontalParallax = Math.asin(clamp(
    EARTH_RADIUS_KM / moonCoordinates.distanceKm,
    -1,
    1,
  ));
  const moonHorizontal = {
    ...geocentricMoonHorizontal,
    altitude: (
      geocentricMoonHorizontal.altitude
      - horizontalParallax * Math.cos(geocentricMoonHorizontal.altitude)
    ),
  };
  const moonPosition = getMoonPosition(
    localHour,
    solar.sunrise,
    solar.sunset,
    moonHorizontal,
  );
  const moon = {
    ...getMoonPhase(sunCoordinates, moonCoordinates),
    ...moonPosition,
    rightAscension: moonCoordinates.rightAscension,
    declination: moonCoordinates.declination,
    distanceKm: moonCoordinates.distanceKm,
  };

  return {
    observation,
    solar,
    moon,
    stars: getNearbyMoonStars({
      julianDay,
      latitude: latitudeRadians,
      siderealAngle,
      moonCoordinates,
      moonHorizontal,
      moonPosition,
    }),
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
