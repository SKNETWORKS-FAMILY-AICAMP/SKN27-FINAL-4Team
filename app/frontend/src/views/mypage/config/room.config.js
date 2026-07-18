export const DEFAULT_CHARACTER_POSITION = Object.freeze({ x: 45.2, y: 33.8 });

export const CHARACTER_MOVEMENT_PROFILES = Object.freeze({
  otter: { speedFactor: 1.05, transitionMs: 440, walkCycleMs: 480, arrivalMs: 620 },
  cat: { speedFactor: 0.92, transitionMs: 400, walkCycleMs: 520, arrivalMs: 480 },
  redpanda: { speedFactor: 0.8, transitionMs: 350, walkCycleMs: 380, arrivalMs: 560 },
  bird: { speedFactor: 1.18, transitionMs: 480, walkCycleMs: 430, arrivalMs: 540 },
});

export const ROOM_STOPS = Object.freeze({
  character: { x: 45.2, y: 33.8 },
  door: { x: 10.8, y: 17.0 },
  profile: { x: 21.8, y: 20.1 },
  weather: { x: 31.0, y: 16.6 },
  book: { x: 50.0, y: 26.4 },
  mbti: { x: 74.0, y: 20.8 },
  memory: { x: 50.0, y: 53.5 },
  emotion: { x: 43.0, y: 65.0 },
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
