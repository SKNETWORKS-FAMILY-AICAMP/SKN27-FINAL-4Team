<template>
  <div
    :class="['weather-scene', conditionClass, timeClass, weatherVisual.classes]"
    :style="[weatherVisual.style, skyStyle]"
  >
    <svg
      class="weather-scene-svg"
      viewBox="0 0 320 190"
      preserveAspectRatio="xMidYMid slice"
      role="presentation"
      focusable="false"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="weather-day-sky" x1="0" y1="0" x2="0.82" y2="1">
          <stop class="sky-stop" offset="0" :stop-color="skyPalette.top" />
          <stop class="sky-stop" offset="0.5" :stop-color="skyPalette.mid" />
          <stop class="sky-stop" offset="1" :stop-color="skyPalette.bottom" />
        </linearGradient>
        <linearGradient id="weather-night-sky" x1="0.12" y1="0" x2="0.85" y2="1">
          <stop class="sky-stop" offset="0" :stop-color="skyPalette.top" />
          <stop class="sky-stop" offset="0.58" :stop-color="skyPalette.mid" />
          <stop class="sky-stop" offset="1" :stop-color="skyPalette.bottom" />
        </linearGradient>
        <linearGradient id="weather-storm-sky" x1="0" y1="0" x2="0.82" y2="1">
          <stop class="sky-stop" offset="0" :stop-color="skyPalette.stormTop" />
          <stop class="sky-stop" offset="0.58" :stop-color="skyPalette.stormMid" />
          <stop class="sky-stop" offset="1" :stop-color="skyPalette.stormBottom" />
        </linearGradient>
        <linearGradient id="weather-horizon" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#f5c5a2" stop-opacity="0.34" />
          <stop offset="1" stop-color="#26213e" stop-opacity="0" />
        </linearGradient>
        <radialGradient id="weather-sun-core" cx="0.35" cy="0.3" r="0.72">
          <stop offset="0" stop-color="#fffde9" />
          <stop offset="0.26" :stop-color="skyPalette.sunMid" />
          <stop offset="0.74" :stop-color="skyPalette.sunEdge" />
          <stop offset="1" :stop-color="skyPalette.sunEdge" />
        </radialGradient>
        <radialGradient id="weather-moon-core" cx="0.34" cy="0.28" r="0.78">
          <stop offset="0" stop-color="#fffcef" />
          <stop offset="0.55" stop-color="#e9e5ff" />
          <stop offset="1" stop-color="#a9acd8" />
        </radialGradient>
        <radialGradient id="weather-moon-shadow" cx="0.35" cy="0.28" r="0.8">
          <stop offset="0" stop-color="#6e7895" />
          <stop offset="0.62" stop-color="#3e4967" />
          <stop offset="1" stop-color="#26324e" />
        </radialGradient>
        <radialGradient
          id="weather-sunlight"
          gradientUnits="userSpaceOnUse"
          :cx="sceneAstronomy.solar.x"
          :cy="sceneAstronomy.solar.y"
          r="142"
        >
          <stop offset="0" :stop-color="skyPalette.sunlightCore" stop-opacity="0.82" />
          <stop offset="0.38" :stop-color="skyPalette.sunlightMid" stop-opacity="0.28" />
          <stop offset="1" :stop-color="skyPalette.sunlightMid" stop-opacity="0" />
        </radialGradient>
        <linearGradient id="weather-cloud-light" x1="0.2" y1="0" x2="0.72" y2="1">
          <stop offset="0" stop-color="#fffefa" />
          <stop offset="0.42" stop-color="#edf1f1" />
          <stop offset="1" stop-color="#bcc8cc" />
        </linearGradient>
        <linearGradient id="weather-cloud-mid" x1="0.18" y1="0" x2="0.78" y2="1">
          <stop offset="0" stop-color="#e5eaec" />
          <stop offset="0.48" stop-color="#b3c0c5" />
          <stop offset="1" stop-color="#73838c" />
        </linearGradient>
        <linearGradient id="weather-cloud-dark" x1="0.2" y1="0" x2="0.72" y2="1">
          <stop offset="0" stop-color="#a8b5bb" />
          <stop offset="0.46" stop-color="#71818a" />
          <stop offset="1" stop-color="#3d505b" />
        </linearGradient>
        <linearGradient id="weather-rain" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#d5edff" stop-opacity="0.15" />
          <stop offset="0.45" stop-color="#a6d7ff" />
          <stop offset="1" stop-color="#5bb8ff" stop-opacity="0.12" />
        </linearGradient>
        <filter id="weather-soft-glow" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="7" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="weather-cloud-depth" x="-35%" y="-55%" width="170%" height="210%">
          <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="8" result="cloud-noise" />
          <feDisplacementMap in="SourceGraphic" in2="cloud-noise" scale="1.6" xChannelSelector="R" yChannelSelector="B" result="cloud-shape" />
          <feDropShadow in="cloud-shape" dx="0" dy="8" stdDeviation="8" flood-color="#111d29" flood-opacity="0.27" />
        </filter>
        <filter id="weather-haze" x="-30%" y="-120%" width="160%" height="340%">
          <feGaussianBlur stdDeviation="8" />
        </filter>
        <filter id="weather-grain" x="0" y="0" width="100%" height="100%">
          <feTurbulence type="fractalNoise" baseFrequency="0.72" numOctaves="3" seed="21" stitchTiles="stitch" />
          <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 .11 0" />
        </filter>
      </defs>

      <rect class="scene-sky scene-sky-day" width="320" height="190" fill="url(#weather-day-sky)" />
      <rect class="scene-sky scene-sky-night" width="320" height="190" fill="url(#weather-night-sky)" />
      <rect class="scene-sky scene-sky-storm" width="320" height="190" fill="url(#weather-storm-sky)" />
      <rect
        class="scene-sunlight"
        width="320"
        height="190"
        fill="url(#weather-sunlight)"
        :style="sunlightStyle"
      />

      <g class="scene-stars">
        <circle cx="30" cy="29" r="1.3" />
        <circle cx="51" cy="61" r="0.9" />
        <circle cx="132" cy="25" r="1" />
        <circle cx="164" cy="51" r="1.4" />
        <circle cx="204" cy="23" r="0.8" />
        <circle cx="247" cy="44" r="1.2" />
        <circle cx="291" cy="25" r="0.8" />
        <path d="M277 67h8M281 63v8" />
        <path d="M115 66h6M118 63v6" />
      </g>

      <g class="scene-sun" filter="url(#weather-soft-glow)" :transform="sunTransform" :style="sunStyle">
        <circle class="sun-aura" cx="82" cy="61" r="39" />
        <g class="sun-rays">
          <path d="M82 8v13M82 101v13M29 61h13M122 61h13M45 24l9 9M110 89l9 9M45 98l9-9M110 33l9-9" />
        </g>
        <circle class="sun-disc" cx="82" cy="61" r="25" fill="url(#weather-sun-core)" />
        <ellipse class="sun-sheen" cx="73" cy="51" rx="7" ry="5" />
      </g>

      <g class="scene-moon" filter="url(#weather-soft-glow)" :transform="moonTransform" :style="moonStyle">
        <circle class="moon-aura" cx="88" cy="58" r="38" />
        <circle class="moon-shadow" cx="88" cy="58" r="27" fill="url(#weather-moon-shadow)" />
        <path class="moon-phase" :d="moonPhasePath" fill="url(#weather-moon-core)" />
        <circle class="moon-crater" cx="76" cy="66" r="3" />
        <circle class="moon-crater crater-small" cx="82" cy="43" r="1.8" />
      </g>

      <path class="scene-horizon" d="M0 130C54 114 92 127 132 120c58-10 87-27 188-9v79H0Z" fill="url(#weather-horizon)" />
      <path class="scene-ridge ridge-back" d="M0 152c35-14 58-9 84-20 35-14 67-7 95 2 35 11 58-5 89-7 19-1 35 5 52 10v53H0Z" />
      <path class="scene-ridge ridge-front" d="M0 167c42-9 68-3 104-10 47-8 81-1 116 7 38 9 67-1 100-6v32H0Z" />

      <g class="scene-haze">
        <path d="M-20 139C54 127 87 144 144 134s111 9 202-2" />
        <path d="M-18 157c67-10 112 7 173-2 74-11 104 8 187-4" />
      </g>

      <g class="scene-cloud scene-cloud-rear" filter="url(#weather-cloud-depth)">
        <path d="M120 107c0-13 10-23 23-23 3-17 18-30 36-30 17 0 32 12 36 28 4-2 9-3 14-3 17 0 30 13 30 29 14 1 25 12 25 26 0 15-12 27-28 27H126c-17 0-30-12-30-27 0-14 10-25 24-27Z" />
        <path class="cloud-highlight" d="M119 111c13-7 26-5 37-16 9-9 13-23 25-28 15-6 28 3 33 17-12-6-23-3-30 4-9 10-14 21-29 25-13 4-24 1-36-2Z" />
      </g>

      <g class="scene-cloud scene-cloud-front" filter="url(#weather-cloud-depth)">
        <path d="M50 123c0-11 9-20 21-21 3-14 16-25 31-25 15 0 27 9 31 22 4-2 8-2 12-2 15 0 27 11 27 26 12 1 21 10 21 22 0 13-10 23-24 23H56c-15 0-26-10-26-23 0-12 8-21 20-22Z" />
        <path class="cloud-highlight" d="M48 126c14-8 26-4 35-13 8-8 12-20 23-24 12-5 23 1 28 12-10-4-19-1-25 5-8 8-12 18-24 21-13 4-24 1-37-1Z" />
      </g>

      <g class="scene-rain">
        <path class="rain-drop rain-1" d="M83 137l-12 30" />
        <path class="rain-drop rain-2" d="M111 142l-12 30" />
        <path class="rain-drop rain-3" d="M143 136l-12 30" />
        <path class="rain-drop rain-4" d="M176 141l-12 30" />
        <path class="rain-drop rain-5" d="M207 135l-12 30" />
        <path class="rain-drop rain-6" d="M236 142l-12 30" />
        <ellipse class="rain-splash splash-1" cx="94" cy="176" rx="10" ry="2.4" />
        <ellipse class="rain-splash splash-2" cx="186" cy="179" rx="12" ry="2.7" />
      </g>

      <g class="scene-snow">
        <g class="snowflake snow-1" transform="translate(78 137)"><path d="M0-5V5M-4.3-2.5l8.6 5M4.3-2.5l-8.6 5" /></g>
        <g class="snowflake snow-2" transform="translate(111 150)"><path d="M0-4V4M-3.5-2l7 4M3.5-2l-7 4" /></g>
        <g class="snowflake snow-3" transform="translate(148 136)"><path d="M0-5V5M-4.3-2.5l8.6 5M4.3-2.5l-8.6 5" /></g>
        <g class="snowflake snow-4" transform="translate(184 149)"><path d="M0-4V4M-3.5-2l7 4M3.5-2l-7 4" /></g>
        <g class="snowflake snow-5" transform="translate(220 137)"><path d="M0-5V5M-4.3-2.5l8.6 5M4.3-2.5l-8.6 5" /></g>
      </g>

      <rect class="scene-grain" width="320" height="190" filter="url(#weather-grain)" />
      <rect class="scene-glass" x="0.5" y="0.5" width="319" height="189" rx="15" />
    </svg>
  </div>
</template>

<script>
import { getMoonIlluminatedPath, getWeatherAstronomy } from "../utils/weather.astronomy";
import { getWeatherSkyPalette, getWeatherVisualState } from "../utils/weather.visual";

export default {
  name: "WeatherScene",
  props: {
    conditionClass: { type: String, default: "is-cloudy" },
    timeClass: { type: String, default: "is-day" },
    astronomy: { type: Object, default: null },
    weather: { type: Object, default: null }
  },
  computed: {
    weatherVisual() {
      return getWeatherVisualState(this.weather || {});
    },
    skyPalette() {
      return getWeatherSkyPalette(this.sceneAstronomy);
    },
    skyStyle() {
      return {
        "--sun-aura-color": this.skyPalette.sunAura,
        "--sun-ray-color": this.skyPalette.sunRay,
        "--star-opacity": this.skyPalette.starOpacity,
      };
    },
    sceneAstronomy() {
      return this.astronomy || getWeatherAstronomy();
    },
    sunTransform() {
      const { x, y, scale } = this.sceneAstronomy.solar;
      return `translate(${x} ${y}) scale(${scale}) translate(-82 -61)`;
    },
    moonTransform() {
      const { x, y, scale } = this.sceneAstronomy.moon;
      return `translate(${x} ${y}) scale(${scale}) translate(-88 -58)`;
    },
    moonPhasePath() {
      return getMoonIlluminatedPath(this.sceneAstronomy.moon.phase);
    },
    sunStyle() {
      return {
        "--sun-opacity": this.sceneAstronomy.solar.opacity,
        "--sun-cloud-opacity": this.sceneAstronomy.solar.opacity * 0.56,
        "--sun-strength": this.sceneAstronomy.solar.strength,
      };
    },
    moonStyle() {
      return {
        "--moon-opacity": this.sceneAstronomy.moon.opacity,
        "--moon-cloud-opacity": this.sceneAstronomy.moon.opacity * 0.58,
      };
    },
    sunlightStyle() {
      const opacity = 0.07 + this.sceneAstronomy.solar.strength * 0.2;
      return {
        "--light-opacity": opacity,
        "--light-cloud-opacity": opacity * 0.52,
      };
    }
  }
};
</script>

<style scoped>
.weather-scene {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: inherit;
  isolation: isolate;
}

.weather-scene-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.sky-stop { transition: stop-color 1200ms ease; }
.scene-sky { transition: opacity 600ms ease; }
.scene-sunlight { opacity: var(--light-opacity, 0.2); mix-blend-mode: screen; transition: opacity 600ms ease; }
.is-night .scene-sunlight,
.is-overcast .scene-sunlight,
.is-rain .scene-sunlight,
.is-snow .scene-sunlight,
.is-mixed .scene-sunlight { opacity: 0; }
.is-cloudy .scene-sunlight { opacity: var(--light-cloud-opacity, 0.1); }
.scene-sky-night,
.scene-sky-storm { opacity: 0; }
.is-night .scene-sky-day { opacity: 0; }
.is-night .scene-sky-night { opacity: 1; }
.is-rain .scene-sky-day,
.is-rain .scene-sky-night,
.is-snow .scene-sky-day,
.is-snow .scene-sky-night,
.is-mixed .scene-sky-day,
.is-mixed .scene-sky-night,
.is-overcast .scene-sky-day,
.is-overcast .scene-sky-night { opacity: 0; }
.is-rain .scene-sky-storm,
.is-snow .scene-sky-storm,
.is-mixed .scene-sky-storm,
.is-overcast .scene-sky-storm { opacity: 1; }

.scene-stars {
  fill: #fffbea;
  stroke: #fffbea;
  stroke-width: 1;
  opacity: 0;
  filter: drop-shadow(0 0 4px rgba(255, 248, 218, 0.9));
}
.is-night:not(.is-rain):not(.is-snow):not(.is-mixed):not(.is-overcast) .scene-stars { opacity: var(--star-opacity, 0.84); }
.scene-stars > * { transform-box: fill-box; transform-origin: center; animation: weather-star 3.6s ease-in-out infinite; }
.scene-stars > *:nth-child(2n) { animation-delay: -1.4s; }
.scene-stars > *:nth-child(3n) { animation-delay: -2.3s; }

.scene-sun,
.scene-moon { opacity: 0; transform-box: fill-box; transform-origin: center; transition: opacity 500ms ease; }
.is-day.is-sunny .scene-sun { opacity: var(--sun-opacity, 1); }
.is-day.is-cloudy .scene-sun { opacity: var(--sun-cloud-opacity, 0.56); }
.is-night.is-sunny .scene-moon { opacity: var(--moon-opacity, 1); }
.is-night.is-cloudy .scene-moon { opacity: var(--moon-cloud-opacity, 0.58); }
.sun-aura { fill: var(--sun-aura-color, rgba(255, 197, 112, 0.22)); animation: weather-aura 4.8s ease-in-out infinite; }
.sun-rays { fill: none; stroke: var(--sun-ray-color, rgba(255, 226, 155, 0.66)); stroke-width: 2.2; stroke-linecap: round; transform-origin: 82px 61px; animation: weather-ray-turn 30s linear infinite; }
.sun-sheen { fill: rgba(255, 255, 255, 0.58); transform: rotate(-25deg); transform-origin: center; }
.moon-aura {
  fill: rgba(211, 220, 244, 0.09);
  opacity: 0.58;
}
.moon-shadow { stroke: rgba(219, 226, 245, 0.16); stroke-width: 0.8; }
.moon-phase { filter: drop-shadow(0 0 3px rgba(240, 239, 255, 0.25)); }
.moon-crater { fill: rgba(159, 170, 198, 0.22); }
.crater-small { fill: rgba(255, 255, 255, 0.18); }

.scene-horizon { opacity: 0.82; }
.scene-ridge { transition: fill 500ms ease, opacity 500ms ease; }
.ridge-back { fill: rgba(66, 73, 91, 0.34); }
.ridge-front { fill: rgba(39, 47, 63, 0.56); }
.is-night .ridge-back { fill: rgba(25, 36, 55, 0.62); }
.is-night .ridge-front { fill: rgba(14, 24, 40, 0.78); }

.scene-haze { fill: none; stroke: rgba(255, 241, 225, 0.2); stroke-width: 6; stroke-linecap: round; filter: url(#weather-haze); animation: weather-haze-drift 12s ease-in-out infinite alternate; }

.scene-cloud { transition: opacity 500ms ease; transform-box: fill-box; transform-origin: center; }
.scene-cloud path:first-child { fill: url(#weather-cloud-light); }
.scene-cloud .cloud-highlight { fill: rgba(255, 255, 255, 0.28); }
.scene-cloud-rear { opacity: 0; transform: translate(14px, 12px) scale(0.86); animation: weather-cloud-rear var(--cloud-rear-duration, 8s) ease-in-out infinite; }
.scene-cloud-front { opacity: 0; animation: weather-cloud-front var(--cloud-front-duration, 6.5s) ease-in-out infinite; }
.is-cloudy .scene-cloud-rear { opacity: 0.9; }
.is-cloudy .scene-cloud-front { opacity: 1; }
.is-overcast .scene-cloud-rear,
.is-rain .scene-cloud-rear,
.is-snow .scene-cloud-rear,
.is-mixed .scene-cloud-rear { opacity: 0.94; transform: translate(17px, -1px) scale(1.05); }
.is-overcast .scene-cloud-front,
.is-rain .scene-cloud-front,
.is-snow .scene-cloud-front,
.is-mixed .scene-cloud-front { opacity: 1; transform: translate(-6px, -8px) scale(1.07); }
.is-overcast .scene-cloud path:first-child { fill: url(#weather-cloud-mid); }
.is-rain .scene-cloud path:first-child,
.is-mixed .scene-cloud path:first-child { fill: url(#weather-cloud-dark); }
.is-snow .scene-cloud path:first-child { fill: url(#weather-cloud-mid); }
.is-rain .scene-cloud .cloud-highlight,
.is-mixed .scene-cloud .cloud-highlight { opacity: 0.44; }

.scene-rain,
.scene-snow { opacity: 0; }
.is-rain .scene-rain,
.is-mixed .scene-rain { opacity: var(--rain-opacity, 1); }
.is-snow .scene-snow,
.is-mixed .scene-snow { opacity: var(--snow-opacity, 1); }
.rain-drop { fill: none; stroke: url(#weather-rain); stroke-width: var(--rain-stroke, 3.2px); stroke-linecap: round; animation: weather-rain-fall var(--rain-duration, 1.15s) linear infinite; }
.rain-2 { animation-delay: -0.46s; }
.rain-3 { animation-delay: -0.82s; }
.rain-4 { animation-delay: -0.24s; }
.rain-5 { animation-delay: -0.68s; }
.rain-6 { animation-delay: -0.96s; }
.rain-splash { fill: none; stroke: rgba(159, 214, 255, 0.62); stroke-width: 1.5; opacity: var(--rain-splash-opacity, 0.7); animation: weather-rain-splash 1.25s ease-out infinite; }
.splash-2 { animation-delay: -0.62s; }

.snowflake { fill: none; stroke: rgba(250, 252, 255, 0.96); stroke-width: var(--snow-stroke, 1.35px); stroke-linecap: round; filter: drop-shadow(0 0 4px rgba(226, 241, 255, 0.72)); transform-box: fill-box; transform-origin: center; animation: weather-snow-fall var(--snow-duration, 3.4s) ease-in infinite; }
.snow-2 { animation-delay: -1.3s; animation-duration: var(--snow-duration-2, 4.1s); }
.snow-3 { animation-delay: -2.5s; animation-duration: var(--snow-duration-3, 3.7s); }
.snow-4 { animation-delay: -0.7s; animation-duration: var(--snow-duration-4, 4.4s); }
.snow-5 { animation-delay: -2s; animation-duration: var(--snow-duration-5, 3.9s); }

.is-light-precip .rain-2,
.is-light-precip .rain-4,
.is-light-precip .rain-6,
.is-light-precip .snow-2,
.is-light-precip .snow-4 { display: none; }
.is-heavy-precip .rain-drop { filter: drop-shadow(0 0 2px rgba(136, 204, 255, 0.34)); }
.is-shower .scene-rain { animation: weather-shower-pulse 5.8s ease-in-out infinite; }

.scene-grain { opacity: 0.16; mix-blend-mode: soft-light; pointer-events: none; }
.scene-glass { fill: none; stroke: rgba(255, 237, 221, 0.17); stroke-width: 1; }

@keyframes weather-aura {
  0%, 100% { transform: scale(0.92); opacity: 0.46; }
  50% { transform: scale(1.12); opacity: 0.8; }
}
@keyframes weather-ray-turn { to { transform: rotate(360deg); } }
@keyframes weather-star {
  0%, 100% { opacity: 0.3; transform: scale(0.72); }
  50% { opacity: 1; transform: scale(1.16); }
}
@keyframes weather-cloud-front {
  0%, 100% { translate: var(--cloud-front-start, -2px) 0; }
  50% { translate: var(--cloud-front-end, 3px) -3px; }
}
@keyframes weather-cloud-rear {
  0%, 100% { translate: var(--cloud-rear-start, 1px) 0; }
  50% { translate: var(--cloud-rear-end, -4px) 2px; }
}
@keyframes weather-haze-drift {
  from { transform: translateX(-7px); opacity: var(--haze-min-opacity, 0.35); }
  to { transform: translateX(10px); opacity: var(--haze-max-opacity, 0.62); }
}
@keyframes weather-rain-fall {
  0% { translate: var(--rain-start-x, -7px) -25px; opacity: 0; }
  18% { opacity: 1; }
  82% { opacity: 0.9; }
  100% { translate: var(--rain-end-x, 8px) 25px; opacity: 0; }
}
@keyframes weather-rain-splash {
  0%, 54% { opacity: 0; transform: scaleX(0.25); }
  65% { opacity: var(--rain-splash-opacity, 0.78); }
  100% { opacity: 0; transform: scaleX(1.35); }
}
@keyframes weather-snow-fall {
  0% { translate: var(--snow-start-x, -3px) -25px; rotate: 0deg; opacity: 0; }
  18% { opacity: 0.9; }
  55% { translate: var(--snow-mid-x, 5px) 4px; rotate: 130deg; }
  100% { translate: var(--snow-end-x, -4px) 38px; rotate: 260deg; opacity: 0; }
}
@keyframes weather-shower-pulse {
  0%, 100% { opacity: 0.62; }
  32% { opacity: var(--rain-opacity, 1); }
  68% { opacity: 0.74; }
}

@media (prefers-reduced-motion: reduce) {
  .weather-scene * { animation-duration: 1ms !important; animation-iteration-count: 1 !important; }
}
</style>
