export const DEFAULT_CHARACTER_POSITION = Object.freeze({ x: 45.2, y: 33.8 });

export const CHARACTER_MOVEMENT_PROFILES = Object.freeze({
  otter: { speedFactor: 1.05, transitionMs: 440, walkCycleMs: 480, arrivalMs: 620 },
  cat: { speedFactor: 0.92, transitionMs: 400, walkCycleMs: 520, arrivalMs: 480 },
  redpanda: { speedFactor: 0.8, transitionMs: 350, walkCycleMs: 380, arrivalMs: 560 },
  bird: { speedFactor: 1.18, transitionMs: 480, walkCycleMs: 430, arrivalMs: 540 },
});

export const ROOM_TANTRUM_SETTINGS = Object.freeze({
  redirectLimit: 10,
  redirectWindowMs: 6500,
  pauseMs: 1800,
  returnLeadInMs: 320,
  returnSpeedFactor: 1.12,
});

export const ROOM_GAME_SETTINGS = Object.freeze({
  startCountdown: 3,
  initialLives: 3,
  timeBonusMs: 2 * 1000,
  shadowPenaltyMs: 3 * 1000,
  shadowScorePenalty: 75,
  enemyHitScorePenalty: 100,
  hitInvulnerabilityMs: 1500,
  skillMaxCharges: 2,
  invisibilityDurationMs: 4000,
  timeStopDurationMs: 2400,
  speedBoostDurationMs: 4500,
  speedBoostMultiplier: 1.65,
  enemyCollisionRadius: 5.3,
  comboWindowMs: 6 * 1000,
  manualSpeedPerSecond: 23,
  collectionRadius: 3.8,
  stageTransitionMs: 1700,
  stages: Object.freeze([
    Object.freeze({
      stage: 1,
      durationMs: 30 * 1000,
      targetCollectibles: 5,
      visibleItemCount: 3,
      enemyCount: 1,
      enemySpeedPerSecond: 8.2,
      enemyAwarenessRadius: 24,
      enemyChaseChance: 0.25,
      enemyChaseDurationMs: 1200,
      enemyChaseCooldownMs: 4500,
      enemySenseIntervalMs: 900,
      enemyChaseRefreshMs: 560,
      maxActiveChasers: 1,
      skillChance: 0.08,
      shadowChance: 0.22,
      timeChance: 0.1,
      itemRespawnMinMs: 580,
      itemRespawnMaxMs: 900,
    }),
    Object.freeze({
      stage: 2,
      durationMs: 28 * 1000,
      targetCollectibles: 7,
      visibleItemCount: 3,
      enemyCount: 2,
      enemySpeedPerSecond: 9.8,
      enemyAwarenessRadius: 32,
      enemyChaseChance: 0.35,
      enemyChaseDurationMs: 1500,
      enemyChaseCooldownMs: 3800,
      enemySenseIntervalMs: 700,
      enemyChaseRefreshMs: 480,
      maxActiveChasers: 1,
      skillChance: 0.1,
      shadowChance: 0.3,
      timeChance: 0.08,
      itemRespawnMinMs: 720,
      itemRespawnMaxMs: 1100,
    }),
    Object.freeze({
      stage: 3,
      durationMs: 26 * 1000,
      targetCollectibles: 9,
      visibleItemCount: 2,
      enemyCount: 3,
      enemySpeedPerSecond: 11.2,
      enemyAwarenessRadius: 40,
      enemyChaseChance: 0.45,
      enemyChaseDurationMs: 1800,
      enemyChaseCooldownMs: 3200,
      enemySenseIntervalMs: 550,
      enemyChaseRefreshMs: 420,
      maxActiveChasers: 2,
      skillChance: 0.12,
      shadowChance: 0.38,
      timeChance: 0.06,
      itemRespawnMinMs: 850,
      itemRespawnMaxMs: 1300,
    }),
  ]),
  bestScoreStorageKey: "binteumsai-room-game-best-score",
});

export const ROOM_GAME_ENEMY_CHARACTERS = Object.freeze([
  Object.freeze({ id: "otter", name: "토토" }),
  Object.freeze({ id: "cat", name: "까미" }),
  Object.freeze({ id: "redpanda", name: "포리" }),
  Object.freeze({ id: "bird", name: "여울" }),
]);

export const ROOM_STOPS = Object.freeze({
  character: { x: 45.2, y: 33.8 },
  door: { x: 10.8, y: 17.0 },
  profile: { x: 21.8, y: 20.1 },
  weather: { x: 31.0, y: 16.6 },
  book: { x: 50.0, y: 26.4 },
  mbti: { x: 74.0, y: 20.8 },
  memory: { x: 50.0, y: 53.5 },
  wardrobe: { x: 88.0, y: 66.3 },
});

export const CHARACTER_FOOT_OFFSET = Object.freeze({ x: 3.7, y: 16.5 });
export const CHARACTER_FLOOR_CLEARANCE = Object.freeze({ x: 3.4, y: 1.5 });
export const PATH_GRID_STEP = 1;

export const ROOM_OBSTACLES = Object.freeze([
  { id: "nightstand", x1: 2.3, y1: 62.7, x2: 11.7, y2: 88.4, padding: 0.8 },
  { id: "bed", x1: 13.3, y1: 39.2, x2: 30.7, y2: 95.8, padding: 0.9 },
  { id: "desk", x1: 58.3, y1: 39.8, x2: 85.1, y2: 69.5, padding: 0.8 },
  { id: "desk-chair", x1: 63.1, y1: 59.6, x2: 72.4, y2: 80.7, padding: 0.7 },
  { id: "closet", x1: 85.7, y1: 39.3, x2: 96.8, y2: 72.2, padding: 0.8 },
  { id: "trash-bin", x1: 77.5, y1: 75.2, x2: 83.7, y2: 88.2, padding: 0.6 },
]);

export const WALKABLE_FLOOR_RECTS = Object.freeze([
  { id: "wood-floor", x1: 2, y1: 31.8, x2: 98, y2: 96 },
]);
