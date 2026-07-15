<template>
  <section class="room-stage">
    <div ref="roomCanvas" class="room-canvas">
      <img class="room-image" src="../../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
      <button
        class="room-character"
        type="button"
        :aria-label="currentCharacter.name"
        :class="{ walking: isWalking, arrived: arrivalPulse }"
        :data-facing="facing"
        :data-character="currentCharacter.id"
        :style="characterStyle"
        @click="$emit('open-panel', 'character')"
      >
        <img :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
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
      <button class="hotspot image-vault" type="button" :aria-label="labels.imageVault || '이미지 보관함'" title="이미지 보관함" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'imageVault')"></button>
      <button class="hotspot profile" type="button" :aria-label="labels.profile" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'profile')"></button>
      <button class="hotspot weather" type="button" :aria-label="labels.weather" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'weather')"></button>
      <button class="hotspot mbti" type="button" :aria-label="labels.mbti" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'mbti')"></button>
      <button class="hotspot book" type="button" :aria-label="labels.book || '오늘의 책 추천'" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'book')"></button>
      <button class="hotspot memory" type="button" :aria-label="labels.memory || '기억 보관함'" title="기억 보관함" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'memory')"></button>
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
  emits: ["open-panel", "open-chat", "open-report", "arrived"],
  data() {
    return {
      characterPosition: { x: 45.2, y: 33.8 },
      activeTarget: "character",
      isWalking: false,
      arrivalPulse: false,
      facing: "right",
      activeWalkCycleMs: null,
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
    currentMovementProfile() {
      const profiles = {
        otter: {
          speedFactor: 1.05,
          transitionMs: 440,
          walkCycleMs: 480,
          arrivalMs: 620
        },
        cat: {
          speedFactor: 0.92,
          transitionMs: 400,
          walkCycleMs: 520,
          arrivalMs: 480
        },
        redpanda: {
          speedFactor: 0.8,
          transitionMs: 350,
          walkCycleMs: 380,
          arrivalMs: 560
        },
        bird: {
          speedFactor: 1.18,
          transitionMs: 480,
          walkCycleMs: 430,
          arrivalMs: 540
        }
      };
      return profiles[this.currentCharacter.id] || profiles.otter;
    },
    roomStops() {
      return {
        character: { x: 45.2, y: 33.8 },
        door: { x: 10.8, y: 17.0 },
        imageVault: { x: 19.8, y: 17.2 },
        profile: { x: 21.8, y: 20.1 },
        weather: { x: 31.0, y: 16.6 },
        book: { x: 58.1, y: 26.4 },
        mbti: { x: 74.0, y: 20.8 },
        memory: { x: 73.0, y: 53.5 },
        wardrobe: { x: 84.8, y: 58.0 },
        settings: { x: 82.8, y: 60.2 }
      };
    },
    characterFootOffset() {
      return { x: 3.7, y: 16.5 };
    },
    characterFloorClearance() {
      return { x: 3.4, y: 1.5 };
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

      if (this.prefersReducedMotion() || !route.length || this.samePoint(start, destination)) {
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
      const steps = Math.max(1, Math.ceil(distance / 0.6));
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
