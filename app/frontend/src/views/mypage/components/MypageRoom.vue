<template>
  <section class="room-stage">
    <div class="room-canvas">
      <img class="room-image" src="../../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
      <button
        class="room-character"
        type="button"
        :aria-label="currentCharacter.name"
        :class="{ walking: isWalking, arrived: arrivalPulse }"
        :data-facing="facing"
        :style="characterStyle"
        @click="$emit('open-panel', 'character')"
      >
        <img :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
      </button>
      <button class="hotspot profile" type="button" :aria-label="labels.profile" @click="$emit('open-panel', 'profile')"></button>
      <button class="hotspot weather" type="button" :aria-label="labels.weather" @click="$emit('open-panel', 'weather')"></button>
      <button class="hotspot mbti" type="button" :aria-label="labels.mbti" @click="$emit('open-panel', 'mbti')"></button>
      <button class="hotspot book" type="button" :aria-label="labels.book || '오늘의 책 추천'" @click="$emit('open-panel', 'book')"></button>

      <!-- 취향 분석 hotspot: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button class="hotspot taste" type="button" :aria-label="labels.taste" @click="$emit('open-panel', 'taste')"></button> -->
      <!-- 설정 hotspot: 당장 비활성화. 재활성화 시 아래 버튼 주석 해제 -->
      <!-- <button class="hotspot settings" type="button" :aria-label="labels.settings" @click="$emit('open-panel', 'settings')"></button> -->
    </div>
    <slot />
  </section>
</template>

<script>
export default {
  name: "MypageRoom",
  props: {
    labels: {
      type: Object,
      required: true
    },
    currentCharacter: {
      type: Object,
      required: true
    },
    focusTarget: {
      type: String,
      default: "character"
    },
    moveKey: {
      type: Number,
      default: 0
    }
  },
  emits: ["open-panel", "arrived"],
  data() {
    return {
      characterPosition: { x: 45.2, y: 33.8 },
      activeTarget: "character",
      isWalking: false,
      arrivalPulse: false,
      facing: "right",
      moveTimers: []
    };
  },
  computed: {
    characterStyle() {
      return {
        "--character-x": `${this.characterPosition.x}%`,
        "--character-y": `${this.characterPosition.y}%`
      };
    },
    roomStops() {
      return {
        character: { x: 45.2, y: 33.8 },
        profile: { x: 21.8, y: 20.1 },
        weather: { x: 31.0, y: 16.6 },
        book: { x: 58.2, y: 20.4 },
        mbti: { x: 74.0, y: 20.8 },
        settings: { x: 82.8, y: 60.2 }
      };
    },
    characterFootOffset() {
      return { x: 3.7, y: 16.5 };
    },
    pathGridStep() {
      return 1.5;
    },
    roomObstacles() {
      return [
        { id: "door", x1: 5, y1: 5, x2: 17, y2: 31, padding: 0.8 },
        { id: "window", x1: 28, y1: 9, x2: 42, y2: 29, padding: 0.8 },
        { id: "plant", x1: 45, y1: 12, x2: 54, y2: 36, padding: 1.1 },
        { id: "bookcase", x1: 54, y1: 3, x2: 68.5, y2: 35, padding: 0.8 },
        { id: "mbti-board", x1: 71, y1: 5, x2: 86.5, y2: 31.5, padding: 0.8 },
        { id: "wall-shelf", x1: 87, y1: 14, x2: 97, y2: 34, padding: 1.2 },
        { id: "nightstand", x1: 2, y1: 63, x2: 12, y2: 88, padding: 1.4 },
        { id: "bed", x1: 13, y1: 40, x2: 31, y2: 96, padding: 1.8 },
        { id: "desk", x1: 58.5, y1: 40, x2: 85.5, y2: 65.5, padding: 3.2 },
        { id: "desk-chair", x1: 63.2, y1: 60, x2: 72.2, y2: 80.5, padding: 1.8 },
        { id: "closet", x1: 86.2, y1: 39, x2: 97.5, y2: 76, padding: 1.6 },
        { id: "trash-bin", x1: 77.8, y1: 79, x2: 86.2, y2: 93, padding: 0.8 },
        { id: "heart-box", x1: 86, y1: 78, x2: 97.2, y2: 92, padding: 0.8 }
      ];
    },
    walkableFloorRects() {
      return [
        { id: "wood-floor", x1: 2, y1: 31.8, x2: 98, y2: 96 }
      ];
    }
  },
  watch: {
    moveKey() {
      this.walkTo(this.focusTarget);
    }
  },
  beforeUnmount() {
    this.clearMoveTimers();
  },
  methods: {
    clearMoveTimers() {
      this.moveTimers.forEach(timer => window.clearTimeout(timer));
      this.moveTimers = [];
    },
    walkTo(target) {
      const destination = this.roomStops[target] || this.roomStops.character;
      const start = this.characterPosition;
      const route = this.buildRoute(start, destination, target);

      this.clearMoveTimers();
      this.arrivalPulse = false;

      if (this.prefersReducedMotion() || !route.length || this.samePoint(start, destination)) {
        this.characterPosition = route[route.length - 1] || this.fromFootPoint(this.nearestWalkablePoint(this.toFootPoint(destination)));
        this.activeTarget = target;
        this.$emit("arrived", target);
        return;
      }

      this.isWalking = true;
      let delay = 0;
      let previousPoint = start;
      route.forEach((point) => {
        delay += this.segmentDuration(previousPoint, point);
        previousPoint = point;
        const timer = window.setTimeout(() => {
          this.facing = point.x >= this.characterPosition.x ? "right" : "left";
          this.characterPosition = point;
        }, delay);
        this.moveTimers.push(timer);
      });

      const doneTimer = window.setTimeout(() => {
        this.isWalking = false;
        this.arrivalPulse = true;
        this.activeTarget = target;
        this.$emit("arrived", target);
        const pulseTimer = window.setTimeout(() => {
          this.arrivalPulse = false;
        }, 520);
        this.moveTimers.push(pulseTimer);
      }, delay + 260);
      this.moveTimers.push(doneTimer);
    },
    buildRoute(start, destination) {
      const startFoot = this.nearestWalkablePoint(this.toFootPoint(start));
      const goalFoot = this.nearestWalkablePoint(this.toFootPoint(destination));
      const footRoute = this.findShortestWalkablePath(
        startFoot,
        goalFoot,
      );
      const route = footRoute.map(point => this.fromFootPoint(point));
      const safeDestination = this.fromFootPoint(goalFoot);
      if (!route.length || !this.samePoint(route[route.length - 1], safeDestination)) {
        route.push(safeDestination);
      }
      return this.compactRoute(this.smoothRoute(route));
    },
    compactRoute(route) {
      return route.filter((point, index, list) => {
        const previous = index === 0 ? this.characterPosition : list[index - 1];
        return !this.samePoint(previous, point);
      });
    },
    samePoint(a, b) {
      return Math.abs(a.x - b.x) < 0.3 && Math.abs(a.y - b.y) < 0.3;
    },
    segmentDuration(from, to) {
      const distance = Math.hypot(to.x - from.x, to.y - from.y);
      return Math.min(520, Math.max(220, distance * 18));
    },
    toFootPoint(position) {
      return {
        x: position.x + this.characterFootOffset.x,
        y: position.y + this.characterFootOffset.y
      };
    },
    fromFootPoint(point) {
      return {
        x: point.x - this.characterFootOffset.x,
        y: point.y - this.characterFootOffset.y
      };
    },
    findShortestWalkablePath(start, goal) {
      const startNode = this.snapToGrid(start);
      const goalNode = this.snapToGrid(goal);
      const open = new Map([[this.nodeKey(startNode), { ...startNode, g: 0, f: this.pathHeuristic(startNode, goalNode), parent: null }]]);
      const closed = new Set();
      let bestNode = open.values().next().value;
      const maxIterations = 6400;

      for (let i = 0; open.size && i < maxIterations; i += 1) {
        const current = this.lowestCostNode(open);
        const currentKey = this.nodeKey(current);
        open.delete(currentKey);
        closed.add(currentKey);

        if (this.pathHeuristic(current, goalNode) < this.pathHeuristic(bestNode, goalNode)) {
          bestNode = current;
        }
        if (currentKey === this.nodeKey(goalNode)) {
          return this.reconstructPath(current, start, goal);
        }

        this.neighborNodes(current).forEach((neighbor) => {
          const neighborKey = this.nodeKey(neighbor);
          if (closed.has(neighborKey) || !this.canMoveBetween(current, neighbor, goalNode)) return;

          const moveCost = Math.hypot(neighbor.x - current.x, neighbor.y - current.y);
          const nextG = current.g + moveCost;
          const existing = open.get(neighborKey);
          if (existing && existing.g <= nextG) return;

          open.set(neighborKey, {
            ...neighbor,
            g: nextG,
            f: nextG + this.pathHeuristic(neighbor, goalNode),
            parent: current
          });
        });
      }

      return this.reconstructPath(bestNode, start, goal);
    },
    snapToGrid(point) {
      const step = this.pathGridStep;
      return {
        x: Math.round(point.x / step) * step,
        y: Math.round(point.y / step) * step
      };
    },
    nodeKey(point) {
      return `${point.x}:${point.y}`;
    },
    lowestCostNode(nodes) {
      let winner = null;
      nodes.forEach((node) => {
        if (!winner || node.f < winner.f) winner = node;
      });
      return winner;
    },
    neighborNodes(point) {
      const step = this.pathGridStep;
      const directions = [
        [-1, 0], [1, 0], [0, -1], [0, 1],
        [-1, -1], [1, -1], [-1, 1], [1, 1]
      ];
      return directions.map(([dx, dy]) => ({
        x: point.x + dx * step,
        y: point.y + dy * step
      }));
    },
    isWalkable(point) {
      if (point.x < 2 || point.x > 98 || point.y < 31.8 || point.y > 96) return false;
      if (!this.walkableFloorRects.some(rect => this.pointInsideBox(point, rect))) return false;
      return !this.roomObstacles.some(box => this.pointInsideBox(point, box, box.padding ?? 1.8));
    },
    canMoveBetween(current, neighbor, goal) {
      if (!this.isWalkable(neighbor, goal)) return false;
      const isDiagonal = current.x !== neighbor.x && current.y !== neighbor.y;
      if (!isDiagonal) return true;
      return (
        this.isWalkable({ x: neighbor.x, y: current.y }, goal) &&
        this.isWalkable({ x: current.x, y: neighbor.y }, goal)
      );
    },
    pointInsideBox(point, box, padding = 0) {
      return (
        point.x >= box.x1 - padding &&
        point.x <= box.x2 + padding &&
        point.y >= box.y1 - padding &&
        point.y <= box.y2 + padding
      );
    },
    nearestWalkablePoint(point) {
      if (this.isWalkable(point)) return point;

      const step = 0.75;
      const candidates = [];
      for (let radius = step; radius <= 12; radius += step) {
        for (let dx = -radius; dx <= radius; dx += step) {
          candidates.push({ x: point.x + dx, y: point.y - radius });
          candidates.push({ x: point.x + dx, y: point.y + radius });
        }
        for (let dy = -radius + step; dy <= radius - step; dy += step) {
          candidates.push({ x: point.x - radius, y: point.y + dy });
          candidates.push({ x: point.x + radius, y: point.y + dy });
        }
        const nearest = candidates
          .filter(candidate => this.isWalkable(candidate))
          .sort((a, b) => this.pathHeuristic(point, a) - this.pathHeuristic(point, b))[0];
        if (nearest) return nearest;
      }

      return { x: 48.9, y: 50.3 };
    },
    pathHeuristic(a, b) {
      return Math.hypot(a.x - b.x, a.y - b.y);
    },
    reconstructPath(node, exactStart, exactGoal) {
      if (!node) return [exactGoal];
      const path = [];
      let current = node;
      while (current) {
        path.unshift({ x: current.x, y: current.y });
        current = current.parent;
      }
      path[0] = exactStart;
      path[path.length - 1] = exactGoal;
      return this.smoothFootPath(path);
    },
    smoothFootPath(path) {
      if (path.length <= 2) return path;
      const smoothed = [path[0]];
      let anchorIndex = 0;
      while (anchorIndex < path.length - 1) {
        let nextIndex = path.length - 1;
        while (nextIndex > anchorIndex + 1 && !this.hasWalkableLine(path[anchorIndex], path[nextIndex])) {
          nextIndex -= 1;
        }
        smoothed.push(path[nextIndex]);
        anchorIndex = nextIndex;
      }
      return smoothed;
    },
    smoothRoute(route) {
      if (route.length <= 2) return route;
      const footPath = route.map(point => this.toFootPoint(point));
      return this.smoothFootPath(footPath).map(point => this.fromFootPoint(point));
    },
    hasWalkableLine(a, b) {
      const distance = Math.hypot(b.x - a.x, b.y - a.y);
      const steps = Math.max(1, Math.ceil(distance / 1.5));
      for (let index = 1; index < steps; index += 1) {
        const point = {
          x: a.x + ((b.x - a.x) * index) / steps,
          y: a.y + ((b.y - a.y) * index) / steps
        };
        if (!this.isWalkable(point, b)) return false;
      }
      return true;
    },
    prefersReducedMotion() {
      return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    }
  }
};
</script>
