<template>
  <section class="room-stage">
    <p class="room-interaction-guide">
      <span aria-hidden="true">●</span>
      빛나는 지점을 선택하면 연결된 기능을 열 수 있어요.
    </p>
    <div ref="roomCanvas" class="room-canvas">
      <img class="room-image" src="../../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
      <button
        class="room-character"
        type="button"
        :aria-label="currentCharacter.name"
        :class="[{ walking: isWalking, arrived: arrivalPulse }, expressionAnimationClass]"
        :data-facing="facing"
        :data-character="currentCharacter.id"
        :style="characterStyle"
        @click="$emit('open-panel', 'character')"
      >
        <img :key="characterImage" :src="characterImage" :alt="currentCharacter.name" />
      </button>
      <button
        class="hotspot door"
        type="button"
        aria-label="대화하러 가기"
        title="대화하러 가기"
        @mouseenter="showHotspotLabel"
        @mouseleave="hideHotspotLabel"
        @focus="showHotspotLabel"
        @blur="hideHotspotLabel"
        @click="$emit('open-chat')"
      ></button>
      <button class="hotspot profile" type="button" :aria-label="labels.profile" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'profile')"></button>
      <button class="hotspot weather" type="button" :aria-label="labels.weather" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'weather')"></button>
      <button class="hotspot mbti" type="button" :aria-label="labels.mbti" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'mbti')"></button>
      <button class="hotspot book" type="button" :aria-label="labels.book || '오늘의 책 추천'" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'book')"></button>
      <button class="hotspot memory" type="button" :aria-label="labels.memory || '기억 보관함'" title="기억 보관함" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'memory')"></button>
      <button
        class="hotspot emotion"
        type="button"
        :aria-label="labels.emotion || '오늘의 표정'"
        title="오늘의 표정"
        @mouseenter="showHotspotLabel"
        @mouseleave="hideHotspotLabel"
        @focus="showHotspotLabel"
        @blur="hideHotspotLabel"
        @click="$emit('open-panel', 'emotion')"
      >
        <svg
          class="emotion-hotspot-frame"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          <path
            class="emotion-hotspot-shape"
            d="M98.3 42.3 C98.6 44.8 99.3 47.5 99.2 50.1 C99.2 52.6 98.1 55 97.8 57.8 C97.6 60.6 98.3 63.9 97.8 66.9 C97.3 69.9 96.4 73.2 94.9 75.9 C93.5 78.7 91.3 81.4 88.9 83.6 C86.5 85.7 83.7 88.2 80.3 88.9 C77 89.7 72.1 86.8 68.8 87.8 C65.6 88.9 63.9 93.7 60.8 95.3 C57.7 97 53.9 97.6 50.4 97.7 C46.9 97.8 43.2 97.1 39.9 96.1 C36.6 95.1 33.4 93.2 30.5 91.5 C27.7 89.7 25.7 86.9 22.6 85.6 C19.6 84.3 15.1 84.9 12 83.6 C8.9 82.2 5.8 80 3.9 77.4 C2.1 74.8 1.4 71.2 0.8 68.1 C0.3 64.9 0.8 61.6 0.6 58.6 C0.5 55.7 -0.4 53 -0.1 50.3 C0.2 47.6 2.4 45 2.6 42.3 C2.7 39.7 0.4 36.9 0.8 34.4 C1.1 31.9 3.5 29.7 4.6 27.3 C5.8 24.9 5.8 22 7.5 20 C9.2 18 12.6 16.9 15.1 15.6 C17.6 14.3 19.9 13.1 22.4 12.3 C24.9 11.4 27.7 11.3 29.9 10.3 C32.1 9.3 33.7 7.7 35.8 6.2 C37.9 4.7 40 2.4 42.4 1.4 C44.8 0.4 47.8 -0.1 50.4 0 C53.1 0.1 55.9 1 58.3 2.2 C60.7 3.3 62.7 5.4 64.8 6.9 C66.8 8.4 68.5 9.8 70.5 11 C72.5 12.2 74 13.4 76.8 14 C79.6 14.6 84.3 13.6 87.1 14.6 C89.9 15.6 91.8 17.9 93.4 20 C94.9 22.1 95.5 24.8 96.2 27.3 C96.9 29.8 97.2 32.3 97.6 34.8 C97.9 37.3 98 39.8 98.3 42.3 Z"
          />
        </svg>
      </button>
      <button class="hotspot wardrobe" type="button" aria-label="마음리포트 보기" title="마음리포트 보기" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-report')"></button>

      <div
        v-if="activeHotspotLabel"
        ref="hotspotTooltip"
        class="room-hotspot-tooltip"
        :style="hotspotTooltipStyle"
        role="tooltip"
      >
        {{ activeHotspotLabel }}
      </div>
    </div>
    <slot />
  </section>
</template>

<script>
import {
  CHARACTER_FLOOR_CLEARANCE,
  CHARACTER_FOOT_OFFSET,
  CHARACTER_MOVEMENT_PROFILES,
  DEFAULT_CHARACTER_POSITION,
  PATH_GRID_STEP,
  ROOM_OBSTACLES,
  ROOM_STOPS,
  WALKABLE_FLOOR_RECTS,
} from "../config/room.config";
import {
  DEFAULT_ROOM_EXPRESSION,
  EMOTION_ANIMATION_CLASSES,
  VALID_ROOM_EXPRESSIONS,
} from "../config/emotion.constants";
import { createTransparentCharacterImage } from "../utils/character-image";

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
    },
    roomExpression: {
      type: String,
      default: DEFAULT_ROOM_EXPRESSION
    }
  },
  emits: ["open-panel", "open-chat", "open-report", "arrived"],
  data() {
    return {
      characterPosition: { ...DEFAULT_CHARACTER_POSITION },
      activeTarget: "character",
      isWalking: false,
      arrivalPulse: false,
      facing: "right",
      activeWalkCycleMs: null,
      resolvedCharacterImage: "",
      characterImageRequestId: 0,
      moveTimers: [],
      moveFrameId: null,
      activeHotspotLabel: "",
      hotspotTooltipStyle: { left: "0px", top: "0px" },
      activeHotspotElement: null
    };
  },
  computed: {
    characterStyle() {
      const profile = this.currentMovementProfile;
      return {
        "--character-x": `${this.characterPosition.x}%`,
        "--character-y": `${this.characterPosition.y}%`,
        "--character-move-duration": `${profile.transitionMs}ms`,
        "--character-walk-cycle": `${this.activeWalkCycleMs || profile.walkCycleMs}ms`,
        "--character-arrival-duration": `${profile.arrivalMs}ms`
      };
    },
    displayExpression() {
      if (
        this.isWalking
        || this.activeTarget !== "emotion"
        || !VALID_ROOM_EXPRESSIONS.has(this.roomExpression)
      ) {
        return DEFAULT_ROOM_EXPRESSION;
      }
      return this.roomExpression;
    },
    characterPose() {
      if (!this.isWalking && this.activeTarget === "mbti") return "search";
      return this.displayExpression;
    },
    characterImageSource() {
      return `/characters/${this.currentCharacter.id}/${this.characterPose}.png`;
    },
    characterImage() {
      return this.resolvedCharacterImage || this.characterImageSource;
    },
    expressionAnimationClass() {
      return EMOTION_ANIMATION_CLASSES[this.displayExpression] || "";
    },
    currentMovementProfile() {
      return CHARACTER_MOVEMENT_PROFILES[this.currentCharacter.id]
        || CHARACTER_MOVEMENT_PROFILES.otter;
    },
    roomStops() {
      return ROOM_STOPS;
    },
    characterFootOffset() {
      return CHARACTER_FOOT_OFFSET;
    },
    characterFloorClearance() {
      return CHARACTER_FLOOR_CLEARANCE;
    },
    pathGridStep() {
      return PATH_GRID_STEP;
    },
    roomObstacles() {
      return ROOM_OBSTACLES;
    },
    walkableFloorRects() {
      return WALKABLE_FLOOR_RECTS;
    }
  },
  watch: {
    moveKey() {
      this.walkTo(this.focusTarget);
    },
    characterImageSource: {
      immediate: true,
      async handler(src) {
        const requestId = this.characterImageRequestId + 1;
        this.characterImageRequestId = requestId;

        if (!src.endsWith("/search.png")) {
          this.resolvedCharacterImage = src;
          return;
        }

        const transparentImage = await createTransparentCharacterImage(src);
        if (requestId !== this.characterImageRequestId) return;
        this.resolvedCharacterImage = transparentImage || src;
      }
    }
  },
  mounted() {
    window.addEventListener("resize", this.repositionHotspotLabel);
  },
  beforeUnmount() {
    this.clearMoveTimers();
    window.removeEventListener("resize", this.repositionHotspotLabel);
  },
  methods: {
    showHotspotLabel(event) {
      this.activeHotspotElement = event.currentTarget;
      this.activeHotspotLabel = event.currentTarget.getAttribute("aria-label") || "";
      this.$nextTick(this.repositionHotspotLabel);
    },
    hideHotspotLabel() {
      this.activeHotspotElement = null;
      this.activeHotspotLabel = "";
    },
    repositionHotspotLabel() {
      const canvas = this.$refs.roomCanvas;
      const tooltip = this.$refs.hotspotTooltip;
      const target = this.activeHotspotElement;
      if (!canvas || !tooltip || !target?.isConnected) return;

      const canvasRect = canvas.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const tooltipRect = tooltip.getBoundingClientRect();
      const padding = 8;
      const gap = 8;
      const desiredLeft = targetRect.left - canvasRect.left + targetRect.width / 2 - tooltipRect.width / 2;
      const desiredTop = targetRect.top - canvasRect.top - tooltipRect.height - gap;
      const maxLeft = Math.max(padding, canvasRect.width - tooltipRect.width - padding);
      const maxTop = Math.max(padding, canvasRect.height - tooltipRect.height - padding);

      this.hotspotTooltipStyle = {
        left: `${Math.min(Math.max(desiredLeft, padding), maxLeft)}px`,
        top: `${Math.min(Math.max(desiredTop, padding), maxTop)}px`
      };
    },
    clearMoveTimers() {
      this.moveTimers.forEach(timer => window.clearTimeout(timer));
      this.moveTimers = [];
      if (this.moveFrameId !== null) {
        window.cancelAnimationFrame(this.moveFrameId);
        this.moveFrameId = null;
      }
    },
    walkTo(target) {
      const destination = this.roomStops[target] || this.roomStops.character;
      const start = this.characterPosition;
      const route = this.buildRoute(start, destination, target);

      this.clearMoveTimers();
      this.arrivalPulse = false;
      this.activeTarget = target;

      if (!route.length) {
        this.isWalking = false;
        this.activeTarget = target;
        this.$emit("arrived", target);
        return;
      }

      if (this.prefersReducedMotion() || this.samePoint(start, destination)) {
        this.characterPosition = route[route.length - 1] || this.fromFootPoint(this.nearestWalkablePoint(this.toFootPoint(destination)));
        this.activeTarget = target;
        this.$emit("arrived", target);
        return;
      }

      this.isWalking = true;
      const points = [start, ...route];
      const segments = [];
      let totalDistance = 0;
      for (let index = 1; index < points.length; index += 1) {
        const from = points[index - 1];
        const to = points[index];
        const distance = Math.hypot(to.x - from.x, to.y - from.y);
        if (distance <= 0.01) continue;
        segments.push({ from, to, distance, startDistance: totalDistance });
        totalDistance += distance;
      }

      const duration = this.routeDuration(totalDistance);
      const halfCycle = this.currentMovementProfile.walkCycleMs / 2;
      const estimatedSteps = Math.max(2, Math.round(duration / halfCycle));
      const stepCount = Math.max(2, Math.round(estimatedSteps / 2) * 2);
      this.activeWalkCycleMs = (duration / stepCount) * 2;
      const startedAt = performance.now();
      const finishWalk = () => {
        this.moveFrameId = null;
        this.characterPosition = route[route.length - 1];
        this.isWalking = false;
        this.arrivalPulse = true;
        this.activeTarget = target;
        this.$emit("arrived", target);
        const pulseTimer = window.setTimeout(() => {
          this.arrivalPulse = false;
        }, this.currentMovementProfile.arrivalMs);
        this.moveTimers.push(pulseTimer);
      };

      const animate = (now) => {
        const elapsedRatio = Math.min(1, (now - startedAt) / duration);
        const steppedRatio = this.steppedTravelProgress(elapsedRatio, stepCount);
        const travelRatio = this.smoothTravelProgress(steppedRatio);
        const traveledDistance = totalDistance * travelRatio;
        const segment = segments.find(item => (
          traveledDistance <= item.startDistance + item.distance
        )) || segments[segments.length - 1];

        if (!segment) {
          finishWalk();
          return;
        }

        const segmentRatio = Math.min(1, Math.max(0,
          (traveledDistance - segment.startDistance) / segment.distance
        ));
        const nextPosition = {
          x: segment.from.x + (segment.to.x - segment.from.x) * segmentRatio,
          y: segment.from.y + (segment.to.y - segment.from.y) * segmentRatio
        };
        const horizontalDelta = nextPosition.x - this.characterPosition.x;
        if (Math.abs(horizontalDelta) > 0.015) {
          this.facing = horizontalDelta > 0 ? "right" : "left";
        }
        this.characterPosition = nextPosition;

        if (elapsedRatio >= 1) {
          finishWalk();
          return;
        }
        this.moveFrameId = window.requestAnimationFrame(animate);
      };

      this.moveFrameId = window.requestAnimationFrame(animate);
    },
    buildRoute(start, destination) {
      const startFoot = this.nearestWalkablePoint(this.toFootPoint(start));
      const goalFoot = this.nearestWalkablePoint(this.toFootPoint(destination));
      const footRoute = this.findShortestWalkablePath(
        startFoot,
        goalFoot,
      );
      if (!footRoute.length) return [];
      const route = footRoute.map(point => this.fromFootPoint(point));
      const safeDestination = this.fromFootPoint(goalFoot);
      if (!route.length || !this.samePoint(route[route.length - 1], safeDestination)) {
        route.push(safeDestination);
      }
      const directRoute = this.compactRoute(route);
      const optimizedRoute = this.compactRoute(this.smoothRoute(directRoute));
      if (this.isCharacterRouteWalkable(optimizedRoute)) return optimizedRoute;
      if (this.isCharacterRouteWalkable(directRoute)) return directRoute;
      return [];
    },
    isCharacterRouteWalkable(route) {
      if (!route.length) return false;
      const footPath = [this.characterPosition, ...route].map(point => this.toFootPoint(point));
      return footPath.slice(1).every((point, index) => (
        this.hasWalkableLine(footPath[index], point)
      ));
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
    routeDuration(distance) {
      const baseDuration = distance * 32;
      return Math.round(Math.min(3200, Math.max(850,
        baseDuration * this.currentMovementProfile.speedFactor
      )));
    },
    smoothTravelProgress(progress) {
      return progress * progress * (3 - 2 * progress);
    },
    steppedTravelProgress(progress, stepCount) {
      if (progress >= 1) return 1;
      const exactStep = progress * stepCount;
      const stepIndex = Math.floor(exactStep);
      const phase = exactStep - stepIndex;
      const localProgress = phase - 0.085 * Math.sin(Math.PI * 2 * phase);
      return (stepIndex + localProgress) / stepCount;
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
      const visibilityPath = this.findVisibilityPath(start, goal);
      if (visibilityPath.length) return visibilityPath;
      return this.findGridPath(start, goal);
    },
    findVisibilityPath(start, goal) {
      if (this.hasWalkableLine(start, goal)) return [start, goal];

      const nodes = [start, goal, ...this.obstacleCornerNodes()];
      const distances = nodes.map(() => Number.POSITIVE_INFINITY);
      const previous = nodes.map(() => -1);
      const visited = new Set();
      distances[0] = 0;

      while (visited.size < nodes.length) {
        let current = -1;
        for (let index = 0; index < nodes.length; index += 1) {
          if (visited.has(index)) continue;
          if (current === -1 || distances[index] < distances[current]) current = index;
        }
        if (current === -1 || !Number.isFinite(distances[current])) break;
        if (current === 1) break;
        visited.add(current);

        for (let next = 0; next < nodes.length; next += 1) {
          if (next === current || visited.has(next)) continue;
          if (!this.hasWalkableLine(nodes[current], nodes[next])) continue;
          const nextDistance = distances[current] + this.pathHeuristic(nodes[current], nodes[next]);
          if (nextDistance >= distances[next]) continue;
          distances[next] = nextDistance;
          previous[next] = current;
        }
      }

      if (!Number.isFinite(distances[1])) return [];
      const route = [];
      for (let index = 1; index !== -1; index = previous[index]) {
        route.unshift(nodes[index]);
      }
      return route;
    },
    obstacleCornerNodes() {
      const clearance = this.characterFloorClearance;
      const epsilon = 0.12;
      const corners = this.roomObstacles.flatMap((box) => {
        const padding = box.padding ?? 1.8;
        const x1 = box.x1 - padding - clearance.x - epsilon;
        const x2 = box.x2 + padding + clearance.x + epsilon;
        const y1 = box.y1 - padding - clearance.y - epsilon;
        const y2 = box.y2 + padding + clearance.y + epsilon;
        return [
          { x: x1, y: y1 }, { x: x2, y: y1 },
          { x: x1, y: y2 }, { x: x2, y: y2 }
        ];
      });
      const unique = new Map();
      corners.filter(point => this.isWalkable(point)).forEach((point) => {
        unique.set(`${point.x.toFixed(2)}:${point.y.toFixed(2)}`, point);
      });
      return [...unique.values()];
    },
    findGridPath(start, goal) {
      const startNode = this.snapToWalkableGrid(start);
      const goalNode = this.snapToWalkableGrid(goal);
      const open = new Map([[this.nodeKey(startNode), { ...startNode, g: 0, f: this.pathHeuristic(startNode, goalNode), parent: null }]]);
      const closed = new Set();
      const maxIterations = 12000;

      for (let i = 0; open.size && i < maxIterations; i += 1) {
        const current = this.lowestCostNode(open);
        const currentKey = this.nodeKey(current);
        open.delete(currentKey);
        closed.add(currentKey);

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

      return [];
    },
    snapToWalkableGrid(point) {
      const snapped = this.snapToGrid(point);
      if (this.isWalkable(snapped)) return snapped;
      const step = this.pathGridStep;
      for (let radius = step; radius <= 6; radius += step) {
        const candidates = [];
        for (let offset = -radius; offset <= radius; offset += step) {
          candidates.push({ x: snapped.x + offset, y: snapped.y - radius });
          candidates.push({ x: snapped.x + offset, y: snapped.y + radius });
          candidates.push({ x: snapped.x - radius, y: snapped.y + offset });
          candidates.push({ x: snapped.x + radius, y: snapped.y + offset });
        }
        const nearest = candidates
          .filter(candidate => this.isWalkable(candidate))
          .sort((a, b) => this.pathHeuristic(point, a) - this.pathHeuristic(point, b))[0];
        if (nearest) return nearest;
      }
      return snapped;
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
      const clearance = this.characterFloorClearance;
      if (
        point.x < 2 + clearance.x ||
        point.x > 98 - clearance.x ||
        point.y < 31.8 ||
        point.y > 96
      ) return false;
      if (!this.walkableFloorRects.some(rect => this.pointInsideBox(point, rect))) return false;
      return !this.roomObstacles.some(box => this.pointInsideObstacleClearance(
        point,
        box,
        box.padding ?? 1.8
      ));
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
    pointInsideObstacleClearance(point, box, padding = 0) {
      const clearance = this.characterFloorClearance;
      return (
        point.x >= box.x1 - padding - clearance.x &&
        point.x <= box.x2 + padding + clearance.x &&
        point.y >= box.y1 - padding - clearance.y &&
        point.y <= box.y2 + padding + clearance.y
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
      if (!node) return [];
      const path = [];
      let current = node;
      while (current) {
        path.unshift({ x: current.x, y: current.y });
        current = current.parent;
      }
      if (path.length === 1 || this.hasWalkableLine(exactStart, path[1])) {
        path[0] = exactStart;
      }
      const finalNode = path[path.length - 1];
      if (this.hasWalkableLine(finalNode, exactGoal)) {
        if (this.samePoint(finalNode, exactGoal)) path[path.length - 1] = exactGoal;
        else path.push(exactGoal);
      }
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
      if (!this.isWalkable(a) || !this.isWalkable(b)) return false;
      const distance = Math.hypot(b.x - a.x, b.y - a.y);
      const steps = Math.max(1, Math.ceil(distance / 0.25));
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
