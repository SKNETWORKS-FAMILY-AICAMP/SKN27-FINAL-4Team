<script setup>
defineProps({
  uniqueId: {
    type: String,
    default: 'mind-card-drawing-loader',
  },
})

const faces = [
  { key: 'front', animated: true },
  { key: 'back', animated: false },
]
</script>

<template>
  <div class="mind-card-loading__visual" aria-hidden="true">
    <div class="mind-card-loading__halo"></div>

    <div class="mind-card-loading__orbit mind-card-loading__orbit--outer">
      <span class="mind-card-loading__orbit-dot"></span>
    </div>
    <div class="mind-card-loading__orbit mind-card-loading__orbit--inner">
      <span class="mind-card-loading__orbit-dot"></span>
    </div>

    <div class="mind-card-loading__float">
      <div class="mind-card-loading__card-rotator">
        <div
          v-for="face in faces"
          :key="face.key"
          class="mind-card-loading__card-face"
          :class="[
            `mind-card-loading__card-face--${face.key}`,
            { 'mind-card-loading__card-face--static': !face.animated },
          ]"
        >
          <svg
            class="mind-card-svg"
            viewBox="0 0 160 240"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <defs>
              <linearGradient
                :id="`${uniqueId}-${face.key}-stroke`"
                x1="20"
                y1="20"
                x2="140"
                y2="220"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0%" stop-color="#FF9BDD" />
                <stop offset="48%" stop-color="#F05CFF" />
                <stop offset="100%" stop-color="#A584FF" />
              </linearGradient>
              <radialGradient
                :id="`${uniqueId}-${face.key}-surface`"
                cx="50%"
                cy="44%"
                r="70%"
              >
                <stop offset="0%" stop-color="#FFB5E8" stop-opacity=".28" />
                <stop offset="56%" stop-color="#B96CFF" stop-opacity=".13" />
                <stop offset="100%" stop-color="#6E3B87" stop-opacity=".03" />
              </radialGradient>
              <filter
                :id="`${uniqueId}-${face.key}-point-glow`"
                x="-180%"
                y="-180%"
                width="460%"
                height="460%"
              >
                <feGaussianBlur stdDeviation="5" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <rect
              class="mind-card-svg__surface"
              x="18"
              y="12"
              width="124"
              height="216"
              rx="18"
              :fill="`url(#${uniqueId}-${face.key}-surface)`"
            />

            <rect
              class="mind-card-svg__line mind-card-svg__line--frame"
              pathLength="1"
              x="18"
              y="12"
              width="124"
              height="216"
              rx="18"
              :stroke="`url(#${uniqueId}-${face.key}-stroke)`"
              stroke-width="3"
            />
            <rect
              class="mind-card-svg__line mind-card-svg__line--inner-frame"
              pathLength="1"
              x="25"
              y="19"
              width="110"
              height="202"
              rx="14"
              stroke="rgba(255,255,255,.62)"
              stroke-width="1.25"
            />

            <path
              class="mind-card-svg__line mind-card-svg__line--orbit-symbol"
              pathLength="1"
              d="M46 120C46 90 63 68 80 68C97 68 114 90 114 120C114 150 97 172 80 172C63 172 46 150 46 120Z"
              :stroke="`url(#${uniqueId}-${face.key}-stroke)`"
              stroke-width="1.6"
            />
            <path
              class="mind-card-svg__line mind-card-svg__line--orbit-symbol mind-card-svg__line--delay-1"
              pathLength="1"
              d="M56 120C56 96 66 82 80 82C94 82 104 96 104 120C104 144 94 158 80 158C66 158 56 144 56 120Z"
              stroke="rgba(255,255,255,.72)"
              stroke-width="1.2"
            />
            <path
              class="mind-card-svg__line mind-card-svg__line--star"
              pathLength="1"
              d="M80 96L86 114L104 120L86 126L80 144L74 126L56 120L74 114L80 96Z"
              :stroke="`url(#${uniqueId}-${face.key}-stroke)`"
              stroke-width="2"
            />

            <path
              class="mind-card-svg__line mind-card-svg__line--corner mind-card-svg__line--delay-2"
              pathLength="1"
              d="M36 40L39 47L46 50L39 53L36 60L33 53L26 50L33 47L36 40Z"
              stroke="rgba(255,255,255,.84)"
              stroke-width="1.3"
            />
            <path
              class="mind-card-svg__line mind-card-svg__line--corner mind-card-svg__line--delay-3"
              pathLength="1"
              d="M124 40L127 47L134 50L127 53L124 60L121 53L114 50L121 47L124 40Z"
              stroke="rgba(255,255,255,.84)"
              stroke-width="1.3"
            />
            <path
              class="mind-card-svg__line mind-card-svg__line--corner mind-card-svg__line--delay-4"
              pathLength="1"
              d="M36 180L39 187L46 190L39 193L36 200L33 193L26 190L33 187L36 180Z"
              stroke="rgba(255,255,255,.84)"
              stroke-width="1.3"
            />
            <path
              class="mind-card-svg__line mind-card-svg__line--corner mind-card-svg__line--delay-5"
              pathLength="1"
              d="M124 180L127 187L134 190L127 193L124 200L121 193L114 190L121 187L124 180Z"
              stroke="rgba(255,255,255,.84)"
              stroke-width="1.3"
            />

            <path
              v-if="face.animated"
              :id="`${uniqueId}-draw-path`"
              d="M36 12H124C134 12 142 20 142 30V210C142 220 134 228 124 228H36C26 228 18 220 18 210V30C18 20 26 12 36 12Z"
              fill="none"
              stroke="none"
            />
            <circle
              v-if="face.animated"
              class="mind-card-svg__draw-point"
              r="3.6"
              fill="#FFF7FD"
              :filter="`url(#${uniqueId}-${face.key}-point-glow)`"
            >
              <animateMotion
                dur="4.8s"
                repeatCount="indefinite"
                calcMode="linear"
                keyTimes="0;0.1;0.48;1"
                keyPoints="0;0;1;1"
              >
                <mpath :href="`#${uniqueId}-draw-path`" />
              </animateMotion>
              <animate
                attributeName="opacity"
                dur="4.8s"
                repeatCount="indefinite"
                values="0;0;1;1;0;0"
                keyTimes="0;0.08;0.12;0.48;0.53;1"
              />
            </circle>
          </svg>
        </div>
      </div>
    </div>

    <span class="mind-card-loading__spark mind-card-loading__spark--1"></span>
    <span class="mind-card-loading__spark mind-card-loading__spark--2"></span>
    <span class="mind-card-loading__spark mind-card-loading__spark--3"></span>
    <span class="mind-card-loading__spark mind-card-loading__spark--4"></span>
  </div>
</template>

<style scoped>
.mind-card-loading__visual {
  position: relative;
  display: grid;
  width: clamp(190px, 20vw, 220px);
  height: clamp(210px, 22vw, 242px);
  place-items: center;
  perspective: 900px;
  isolation: isolate;
}

.mind-card-loading__halo {
  position: absolute;
  z-index: 0;
  width: 72%;
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 91, 208, .34) 0%, rgba(160, 86, 255, .18) 46%, transparent 72%);
  filter: blur(10px);
  animation: mind-card-halo-pulse 2.4s ease-in-out infinite;
}

.mind-card-loading__orbit {
  --orbit-tilt: 0deg;
  position: absolute;
  left: 50%;
  top: 50%;
  z-index: 1;
  border: 1px solid rgba(255, 139, 225, .42);
  border-radius: 50%;
  filter: drop-shadow(0 0 5px rgba(225, 104, 255, .42));
  pointer-events: none;
}

.mind-card-loading__orbit--outer {
  --orbit-tilt: -14deg;
  width: 98%;
  height: 35%;
  animation: mind-card-orbit-clockwise 6s linear infinite;
}

.mind-card-loading__orbit--inner {
  --orbit-tilt: 20deg;
  width: 76%;
  height: 27%;
  border-color: rgba(167, 132, 255, .38);
  animation: mind-card-orbit-counter 5s linear infinite;
}

.mind-card-loading__orbit-dot {
  position: absolute;
  left: 50%;
  top: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff8fe;
  box-shadow: 0 0 7px #ff9bdd, 0 0 15px rgba(190, 115, 255, .82);
  transform: translateX(-50%);
}

.mind-card-loading__float {
  position: relative;
  z-index: 3;
  animation: mind-card-float 2.6s ease-in-out infinite;
}

.mind-card-loading__card-rotator {
  position: relative;
  width: clamp(92px, 8vw, 104px);
  aspect-ratio: 2 / 3;
  transform-style: preserve-3d;
  transform-origin: center;
  animation: mind-card-rotate-cycle 4.8s ease-in-out infinite;
  will-change: transform;
}

.mind-card-loading__card-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  filter: drop-shadow(0 0 5px rgba(255, 112, 221, .34)) drop-shadow(0 0 10px rgba(160, 92, 255, .24));
  animation: mind-card-complete-glow 4.8s ease-in-out infinite;
}

.mind-card-loading__card-face--front {
  transform: rotateY(0deg);
}

.mind-card-loading__card-face--back {
  transform: rotateY(180deg);
}

.mind-card-svg {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.mind-card-svg__surface {
  opacity: 0;
  animation: mind-card-surface-reveal 4.8s ease-in-out infinite;
}

.mind-card-svg__line {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  stroke-linecap: round;
  stroke-linejoin: round;
  animation: mind-card-line-draw 4.8s cubic-bezier(.65, 0, .35, 1) infinite;
}

.mind-card-svg__line--inner-frame { animation-delay: .08s; }
.mind-card-svg__line--orbit-symbol { animation-delay: .18s; }
.mind-card-svg__line--delay-1 { animation-delay: .26s; }
.mind-card-svg__line--star { animation-delay: .34s; }
.mind-card-svg__line--delay-2 { animation-delay: .42s; }
.mind-card-svg__line--delay-3 { animation-delay: .50s; }
.mind-card-svg__line--delay-4 { animation-delay: .58s; }
.mind-card-svg__line--delay-5 { animation-delay: .66s; }

.mind-card-loading__card-face--static .mind-card-svg__line {
  stroke-dashoffset: 0;
  opacity: 1;
  animation: none;
}

.mind-card-loading__card-face--static .mind-card-svg__surface {
  opacity: 1;
  animation: none;
}

.mind-card-loading__spark {
  position: absolute;
  z-index: 4;
  width: 6px;
  height: 6px;
  background: #fff4fc;
  box-shadow: 0 0 6px rgba(255, 180, 235, .92), 0 0 14px rgba(188, 122, 255, .68);
  transform: rotate(45deg);
  animation: mind-card-spark 2.2s ease-in-out infinite;
}

.mind-card-loading__spark--1 { left: 13%; top: 28%; }
.mind-card-loading__spark--2 { right: 9%; top: 39%; animation-delay: -.65s; }
.mind-card-loading__spark--3 { left: 21%; bottom: 20%; animation-delay: -1.2s; }
.mind-card-loading__spark--4 { right: 18%; bottom: 17%; animation-delay: -1.7s; }

@keyframes mind-card-line-draw {
  0%, 8% { stroke-dashoffset: 1; opacity: 0; }
  12% { opacity: 1; }
  42%, 78% { stroke-dashoffset: 0; opacity: 1; }
  92%, 100% { stroke-dashoffset: 1; opacity: 0; }
}

@keyframes mind-card-surface-reveal {
  0%, 34% { opacity: 0; }
  48%, 86% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes mind-card-rotate-cycle {
  0%, 56% { transform: rotateY(0deg); }
  72% { transform: rotateY(180deg); }
  88%, 100% { transform: rotateY(360deg); }
}

@keyframes mind-card-float {
  0%, 100% { transform: translateY(3px); }
  50% { transform: translateY(-5px); }
}

@keyframes mind-card-complete-glow {
  0%, 38% {
    filter: drop-shadow(0 0 4px rgba(255, 112, 221, .28)) drop-shadow(0 0 8px rgba(160, 92, 255, .2));
  }
  52%, 80% {
    filter: drop-shadow(0 0 9px rgba(255, 112, 221, .82)) drop-shadow(0 0 22px rgba(160, 92, 255, .56));
  }
  100% {
    filter: drop-shadow(0 0 4px rgba(255, 112, 221, .28)) drop-shadow(0 0 8px rgba(160, 92, 255, .2));
  }
}

@keyframes mind-card-orbit-clockwise {
  from { transform: translate(-50%, -50%) rotate(var(--orbit-tilt)) rotateZ(0deg); }
  to { transform: translate(-50%, -50%) rotate(var(--orbit-tilt)) rotateZ(360deg); }
}

@keyframes mind-card-orbit-counter {
  from { transform: translate(-50%, -50%) rotate(var(--orbit-tilt)) rotateZ(360deg); }
  to { transform: translate(-50%, -50%) rotate(var(--orbit-tilt)) rotateZ(0deg); }
}

@keyframes mind-card-halo-pulse {
  0%, 100% { opacity: .58; transform: scale(.92); }
  50% { opacity: 1; transform: scale(1.08); }
}

@keyframes mind-card-spark {
  0%, 100% { opacity: .25; scale: .65; }
  50% { opacity: 1; scale: 1.15; }
}

@media (max-width: 1100px) {
  .mind-card-loading__visual {
    width: clamp(170px, 22vw, 195px);
    height: clamp(190px, 25vw, 218px);
  }

  .mind-card-loading__card-rotator {
    width: clamp(84px, 10vw, 94px);
  }
}

@media (max-width: 720px) {
  .mind-card-loading__visual {
    width: clamp(150px, 45vw, 175px);
    height: clamp(174px, 52vw, 198px);
  }

  .mind-card-loading__card-rotator {
    width: clamp(72px, 22vw, 84px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .mind-card-svg__line,
  .mind-card-svg__surface,
  .mind-card-loading__card-rotator,
  .mind-card-loading__float,
  .mind-card-loading__orbit,
  .mind-card-loading__halo,
  .mind-card-loading__spark,
  .mind-card-loading__card-face {
    animation: none !important;
  }

  .mind-card-svg__line {
    stroke-dashoffset: 0;
    opacity: 1;
  }

  .mind-card-svg__surface {
    opacity: 1;
  }

  .mind-card-svg__draw-point {
    display: none;
  }

  .mind-card-loading__orbit {
    transform: translate(-50%, -50%) rotate(var(--orbit-tilt));
  }

  .mind-card-loading__card-rotator {
    transform: rotateY(10deg);
  }
}
</style>
