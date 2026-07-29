<template>
  <section class="room-stage">
    <div class="room-interaction-guide" :class="{ 'is-game-guide': isGameSessionActive }">
      <template v-if="gameState === 'idle'">
        <span aria-hidden="true">●</span>
        <p>빛나는 지점을 선택하면 연결된 기능을 열 수 있어요.</p>
        <button class="room-game-start-button" type="button" :disabled="isMovementLocked" @click="startRoomGame">
          <b>GAME START</b>
          <small v-if="gameBestScore">BEST {{ gameBestScore.toLocaleString() }}</small>
        </button>
      </template>
      <template v-else-if="gameState === 'countdown'">
        <span aria-hidden="true">◆</span>
        <p>상대는 자유롭게 돌아다니다 가까워지면 잠깐 쫓아와요. 느낌표가 보이면 거리를 벌리세요.</p>
      </template>
      <template v-else-if="gameState === 'playing'">
        <span aria-hidden="true">◆</span>
        <p><b>WASD</b>로 이동하고 스킬 아이템을 먹은 뒤 <b>Q·E·R</b>로 사용하세요.</p>
        <button class="room-game-exit-button" type="button" @click="exitRoomGame">게임 종료</button>
      </template>
      <template v-else-if="gameState === 'stage-clear'">
        <span aria-hidden="true">★</span>
        <p>스테이지 {{ gameStage }} 클리어! 다음 스테이지에는 상대 캐릭터가 한 명 더 등장해요.</p>
      </template>
      <template v-else>
        <span aria-hidden="true">★</span>
        <p>게임이 끝났어요. 결과를 확인하거나 원래 마이룸으로 돌아갈 수 있어요.</p>
      </template>
    </div>
    <div
      ref="roomCanvas"
      class="room-canvas"
      :class="{
        'is-character-locked': isMovementLocked,
        'is-game-mode': isGameSessionActive,
        'is-game-playing': gameState === 'playing'
      }"
    >
      <img class="room-image" src="../../../assets/UI 신버전4.png" alt="야간 톤 MindRoom 방 일러스트" />
      <button
        class="room-character"
        type="button"
        :aria-label="characterAriaLabel"
        :class="{
          walking: isWalking,
          arrived: arrivalPulse,
          'is-tantrum': isTantrum,
          'is-returning-home': isReturningHome,
          'is-invulnerable': gameIsInvulnerable,
          'is-game-invisible': gameInvisibilityActive,
          'has-speed-boost': gameSpeedBoostActive
        }"
        :data-facing="facing"
        :data-character="currentCharacter.id"
        :disabled="isMovementLocked"
        :style="characterStyle"
        @click="handleCharacterClick"
      >
        <img :key="characterImage" :src="characterImage" :alt="currentCharacter.name" />
        <span
          v-if="isTantrum"
          class="room-character-protest"
          role="status"
          aria-live="assertive"
        >
          나도 좀 쉬자! <span aria-hidden="true">💢</span>
        </span>
      </button>
      <template v-if="!isGameSessionActive">
        <button
          class="hotspot door"
          type="button"
          aria-label="대화하러 가기"
          title="대화하러 가기"
          :disabled="isMovementLocked"
          @mouseenter="showHotspotLabel"
          @mouseleave="hideHotspotLabel"
          @focus="showHotspotLabel"
          @blur="hideHotspotLabel"
          @click="$emit('open-chat')"
        ></button>
        <button class="hotspot profile" type="button" :aria-label="labels.profile" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'profile')"></button>
        <button class="hotspot weather" type="button" :aria-label="labels.weather" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'weather')"></button>
        <button class="hotspot mbti" type="button" :aria-label="labels.mbti" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'mbti')"></button>
        <button class="hotspot book" type="button" :aria-label="labels.book || '오늘의 책 추천'" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'book')"></button>
        <button class="hotspot memory" type="button" :aria-label="labels.memory || '기억 보관함'" title="기억 보관함" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-panel', 'memory')"></button>
        <button class="hotspot wardrobe" type="button" aria-label="마음리포트 보기" title="마음리포트 보기" :disabled="isMovementLocked" @mouseenter="showHotspotLabel" @mouseleave="hideHotspotLabel" @focus="showHotspotLabel" @blur="hideHotspotLabel" @click="$emit('open-report')"></button>
      </template>

      <section v-if="gameState === 'playing'" class="room-game-hud" aria-label="게임 진행 상황">
        <div>
          <span>STAGE</span>
          <strong>{{ gameStage }}/{{ maxGameStage }}</strong>
        </div>
        <div>
          <span>TIME</span>
          <strong :class="{ urgent: gameRemainingSeconds <= 10 }">{{ gameRemainingSeconds }}</strong>
        </div>
        <div>
          <span>LIGHT</span>
          <strong>{{ gameStageCollected }}/{{ currentStageSettings.targetCollectibles }}</strong>
        </div>
        <div>
          <span>SCORE</span>
          <strong>{{ gameScore.toLocaleString() }}</strong>
        </div>
        <b v-if="gameMultiplier > 1" class="room-game-combo">×{{ gameMultiplier }} COMBO</b>
        <small class="room-game-control-hint">WASD · Q/E/R 스킬</small>
        <span class="room-game-lives" :aria-label="`남은 생명 ${gameLives}개`">
          <i v-for="life in gameSettings.initialLives" :key="life" :class="{ lost: life > gameLives }">♥</i>
        </span>
      </section>

      <section v-if="gameState === 'playing'" class="room-game-skillbar" aria-label="보유 스킬">
        <button
          v-for="skill in gameSkillDefinitions"
          :key="skill.id"
          type="button"
          :class="[`is-${skill.id}`, { active: isGameSkillActive(skill.id) }]"
          :disabled="gameSkillCharges[skill.id] <= 0 || isGameSkillActive(skill.id)"
          :aria-label="`${skill.name}, ${gameSkillCharges[skill.id]}회 보유, ${skill.key} 키로 사용`"
          @click="activateGameSkill(skill.id)"
        >
          <img :src="skill.icon" alt="" aria-hidden="true" />
          <kbd>{{ skill.key }}</kbd>
          <span>
            <b>{{ skill.name }}</b>
            <small>{{ isGameSkillActive(skill.id) ? "ACTIVE" : `×${gameSkillCharges[skill.id]}` }}</small>
          </span>
        </button>
      </section>

      <div
        v-for="enemy in gameEnemies"
        v-show="gameState === 'playing'"
        :key="enemy.id"
        class="room-game-enemy"
        :class="{
          'is-stunned': enemy.stunnedUntil > gameLastMovementAt,
          'is-chasing': enemy.mode === 'chase',
          'is-turning': enemy.turningUntil > gameLastMovementAt
        }"
        :data-facing="enemy.facing"
        :style="{ left: `${enemy.x}%`, top: `${enemy.y}%` }"
        :aria-label="enemy.mode === 'chase'
          ? `플레이어를 잠깐 쫓아오는 화가 난 ${enemy.name}`
          : `방 안을 돌아다니는 화가 난 ${enemy.name}`"
      >
        <span v-if="enemy.mode === 'chase'" class="room-game-enemy-alert" aria-hidden="true">!</span>
        <img :src="`/characters/${enemy.characterId}/anger.png`" :alt="`화가 난 ${enemy.name}`" />
      </div>

      <button
        v-for="item in gameItems"
        v-show="gameState === 'playing'"
        :key="item.id"
        class="room-game-item"
        :class="[`is-${item.type}`, { targeted: item.id === gameTargetId }]"
        type="button"
        :style="{ left: `${item.x}%`, top: `${item.y}%` }"
        :disabled="isWalking || Boolean(gameTargetId)"
        :aria-label="gameItemAriaLabel(item)"
        @click="selectGameItem(item)"
      >
        <span class="room-game-item-icon" aria-hidden="true">
          <img
            v-if="gameItemIconSource(item)"
            :src="gameItemIconSource(item)"
            alt=""
          />
          <svg
            v-else
            class="room-game-cloud-icon"
            viewBox="0 0 164 100"
            focusable="false"
          >
            <path d="M24 77c-13 0-23-10-23-23 0-12 9-22 21-23C25 14 40 2 58 2c17 0 31 10 36 25 5-3 11-4 17-4 17 0 31 13 32 30 12 2 20 11 20 23 0 13-10 23-24 23H24Z" />
            <path class="cloud-highlight" d="M19 39c15-8 30-5 41-17C68 13 75 8 84 8c13 0 24 8 29 19-13-5-24-1-31 7-9 11-18 18-34 19-12 1-21-5-29-14Z" />
          </svg>
        </span>
        <small v-if="item.type === 'time'" class="room-game-time-badge" aria-hidden="true">
          +{{ gameSettings.timeBonusMs / 1000 }}s
        </small>
      </button>

      <transition name="room-game-feedback">
        <div
          v-if="gameFeedback"
          :key="gameFeedbackKey"
          class="room-game-score-feedback"
          :class="`is-${gameFeedbackTone}`"
          role="status"
        >
          {{ gameFeedback }}
        </div>
      </transition>

      <div v-if="gameState === 'countdown'" class="room-game-countdown" role="status" aria-live="assertive">
        <span>마음빛 수집</span>
        <strong>{{ gameCountdown }}</strong>
        <p>3개 스테이지 · 상대 캐릭터와 닿지 않게 조심하세요!</p>
      </div>

      <div v-if="gameState === 'stage-clear'" class="room-game-stage-clear" role="status" aria-live="polite">
        <span>STAGE {{ gameStage }}</span>
        <strong>CLEAR!</strong>
        <p>다음 스테이지 준비 중</p>
      </div>

      <section v-if="gameState === 'result'" class="room-game-result" role="dialog" aria-modal="true" aria-label="게임 결과">
        <div class="room-game-result-card">
          <span class="room-game-result-badge">
            {{ gameWon ? "MISSION CLEAR" : gameResultReason === "lives" ? "GAME OVER" : "TIME OVER" }}
          </span>
          <h3>{{ gameResultTitle }}</h3>
          <p>{{ gameCollected }}개의 마음빛 · {{ gameScore.toLocaleString() }}점</p>
          <dl>
            <div>
              <dt>이번 점수</dt>
              <dd>{{ gameScore.toLocaleString() }}</dd>
            </div>
            <div>
              <dt>도달 스테이지</dt>
              <dd>{{ gameStage }} / {{ maxGameStage }}</dd>
            </div>
          </dl>
          <div class="room-game-result-actions">
            <button type="button" class="retry" @click="startRoomGame">다시 하기</button>
            <button type="button" @click="exitRoomGame">마이룸으로</button>
          </div>
        </div>
      </section>

      <div
        v-if="activeHotspotLabel && !isGameSessionActive"
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
  ROOM_GAME_ENEMY_CHARACTERS,
  ROOM_GAME_SETTINGS,
  ROOM_OBSTACLES,
  ROOM_STOPS,
  ROOM_TANTRUM_SETTINGS,
  WALKABLE_FLOOR_RECTS,
} from "../config/room.config";
import { createTransparentCharacterImage } from "../utils/character-image";
import gameHeartIcon from "../../../assets/report/heart.png";
import gameTimeIcon from "../../../assets/icons/calendar-record.png";
import invisibilitySkillIcon from "../../../assets/report/bubble-heart.png";
import timeStopSkillIcon from "../../../assets/report/sidebar-moon.png";
import speedSkillIcon from "../../../assets/report/feather.png";

const ROOM_GAME_SKILL_DEFINITIONS = Object.freeze([
  Object.freeze({
    id: "invisibility",
    key: "Q",
    name: "투명화",
    itemName: "투명 구슬",
    icon: invisibilitySkillIcon,
  }),
  Object.freeze({
    id: "time-stop",
    key: "E",
    name: "시간정지",
    itemName: "고요한 달",
    icon: timeStopSkillIcon,
  }),
  Object.freeze({
    id: "speed",
    key: "R",
    name: "바람가속",
    itemName: "바람 깃털",
    icon: speedSkillIcon,
  }),
]);

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
  emits: ["open-panel", "open-chat", "open-report", "arrived", "movement-interrupted"],
  data() {
    return {
      characterPosition: { ...DEFAULT_CHARACTER_POSITION },
      activeTarget: "character",
      isWalking: false,
      isTantrum: false,
      isReturningHome: false,
      redirectTimestamps: [],
      arrivalPulse: false,
      facing: "right",
      activeWalkCycleMs: null,
      resolvedCharacterImage: "",
      characterImageRequestId: 0,
      moveTimers: [],
      moveFrameId: null,
      activeHotspotLabel: "",
      hotspotTooltipStyle: { left: "0px", top: "0px" },
      activeHotspotElement: null,
      gameState: "idle",
      gameCountdown: ROOM_GAME_SETTINGS.startCountdown,
      gameRemainingMs: ROOM_GAME_SETTINGS.stages[0].durationMs,
      gameScore: 0,
      gameBestScore: 0,
      gameCollected: 0,
      gameStageCollected: 0,
      gameStage: 1,
      gameLives: ROOM_GAME_SETTINGS.initialLives,
      gameCombo: 0,
      gameLastCollectedAt: 0,
      gameItems: [],
      gameTargetId: "",
      gameItemSequence: 0,
      gameDeadline: 0,
      gameTimerIds: [],
      gameFeedback: "",
      gameFeedbackTone: "positive",
      gameFeedbackKey: 0,
      gameFeedbackTimer: null,
      gameReactionPose: "",
      gameReactionTimer: null,
      gameWon: false,
      gamePressedKeys: new Set(),
      gameMovementFrameId: null,
      gameLastMovementAt: 0,
      gameEnemies: [],
      gameEnemySequence: 0,
      gameIsInvulnerable: false,
      gameInvulnerabilityTimer: null,
      gameSkillCharges: {
        invisibility: 0,
        "time-stop": 0,
        speed: 0,
      },
      gameInvisibilityActive: false,
      gameInvisibilityTimer: null,
      gameTimeStopActive: false,
      gameTimeStopStartedAt: 0,
      gameTimeStopTimer: null,
      gameSpeedBoostActive: false,
      gameSpeedBoostTimer: null,
      gameResultReason: "time"
    };
  },
  computed: {
    isMovementLocked() {
      return this.isTantrum || this.isReturningHome;
    },
    characterAriaLabel() {
      if (this.isTantrum) {
        return `${this.currentCharacter.name}가 화가 나서 잠시 멈췄어요`;
      }
      if (this.isReturningHome) {
        return `${this.currentCharacter.name}가 원래 자리로 돌아가는 중이에요`;
      }
      return this.currentCharacter.name;
    },
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
    characterPose() {
      if (this.isTantrum) return "anger";
      if (this.isReturningHome) return "default";
      if (this.gameReactionPose) return this.gameReactionPose;
      if (!this.isWalking && this.activeTarget === "mbti") return "search";
      return "default";
    },
    characterImageSource() {
      return `/characters/${this.currentCharacter.id}/${this.characterPose}.png`;
    },
    characterImage() {
      return this.resolvedCharacterImage || this.characterImageSource;
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
    },
    gameSettings() {
      return ROOM_GAME_SETTINGS;
    },
    isGameSessionActive() {
      return this.gameState !== "idle";
    },
    gameRemainingSeconds() {
      return Math.max(0, Math.ceil(this.gameRemainingMs / 1000));
    },
    gameMultiplier() {
      return Math.min(3, 1 + Math.floor(Math.max(0, this.gameCombo - 1) / 2));
    },
    maxGameStage() {
      return ROOM_GAME_SETTINGS.stages.length;
    },
    currentStageSettings() {
      return ROOM_GAME_SETTINGS.stages[this.gameStage - 1]
        || ROOM_GAME_SETTINGS.stages[ROOM_GAME_SETTINGS.stages.length - 1];
    },
    gameResultTitle() {
      if (this.gameWon) return "모든 스테이지의 마음빛을 모았어요!";
      if (this.gameResultReason === "lives") return "상대 캐릭터에게 붙잡혔어요";
      return `스테이지 ${this.gameStage}에서 시간이 끝났어요`;
    },
    gameSkillDefinitions() {
      return ROOM_GAME_SKILL_DEFINITIONS;
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
    this.restoreGameBestScore();
    window.addEventListener("resize", this.repositionHotspotLabel);
    window.addEventListener("keydown", this.handleGameKeyDown, { passive: false });
    window.addEventListener("keyup", this.handleGameKeyUp);
    window.addEventListener("blur", this.clearGamePressedKeys);
  },
  beforeUnmount() {
    this.clearMoveTimers();
    this.clearGameTimers();
    this.stopGameMovementLoop();
    window.clearTimeout(this.gameFeedbackTimer);
    window.clearTimeout(this.gameReactionTimer);
    window.clearTimeout(this.gameInvulnerabilityTimer);
    window.clearTimeout(this.gameInvisibilityTimer);
    window.clearTimeout(this.gameTimeStopTimer);
    window.clearTimeout(this.gameSpeedBoostTimer);
    window.removeEventListener("resize", this.repositionHotspotLabel);
    window.removeEventListener("keydown", this.handleGameKeyDown);
    window.removeEventListener("keyup", this.handleGameKeyUp);
    window.removeEventListener("blur", this.clearGamePressedKeys);
  },
  methods: {
    handleCharacterClick() {
      if (this.isGameSessionActive) return;
      this.$emit("open-panel", "character");
    },
    normalizeGameKey(key) {
      const normalized = String(key || "").toLowerCase();
      return {
        w: "up",
        arrowup: "up",
        s: "down",
        arrowdown: "down",
        a: "left",
        arrowleft: "left",
        d: "right",
        arrowright: "right",
      }[normalized] || "";
    },
    shouldIgnoreGameKeyEvent(event) {
      if (event.ctrlKey || event.metaKey || event.altKey) return true;
      const target = event.target;
      return Boolean(
        target?.isContentEditable
        || ["INPUT", "TEXTAREA", "SELECT"].includes(target?.tagName),
      );
    },
    handleGameKeyDown(event) {
      if (this.gameState !== "playing" || this.shouldIgnoreGameKeyEvent(event)) return;
      const skillId = {
        q: "invisibility",
        e: "time-stop",
        r: "speed",
      }[String(event.key || "").toLowerCase()];
      if (skillId) {
        event.preventDefault();
        if (!event.repeat) this.activateGameSkill(skillId);
        return;
      }
      const direction = this.normalizeGameKey(event.key);
      if (!direction) return;
      event.preventDefault();
      this.gamePressedKeys.add(direction);

      if (this.moveFrameId !== null || this.gameTargetId) {
        this.clearMoveTimers();
        this.gameTargetId = "";
        this.isWalking = false;
      }
    },
    handleGameKeyUp(event) {
      const direction = this.normalizeGameKey(event.key);
      if (!direction) return;
      if (this.gameState === "playing") event.preventDefault();
      this.gamePressedKeys.delete(direction);
    },
    clearGamePressedKeys() {
      this.gamePressedKeys.clear();
      if (this.moveFrameId === null) this.isWalking = false;
    },
    startGameMovementLoop() {
      this.stopGameMovementLoop();
      this.gameLastMovementAt = performance.now();
      const step = (now) => {
        this.gameMovementFrameId = null;
        if (this.gameState !== "playing") return;
        const deltaSeconds = Math.min(0.05, Math.max(0, (now - this.gameLastMovementAt) / 1000));
        this.gameLastMovementAt = now;
        this.updateManualGameMovement(deltaSeconds);
        this.updateGameEnemies(deltaSeconds, now);
        this.checkGameEnemyCollision();
        this.gameMovementFrameId = window.requestAnimationFrame(step);
      };
      this.gameMovementFrameId = window.requestAnimationFrame(step);
    },
    stopGameMovementLoop() {
      if (this.gameMovementFrameId !== null) {
        window.cancelAnimationFrame(this.gameMovementFrameId);
        this.gameMovementFrameId = null;
      }
      this.gamePressedKeys.clear();
      this.gameLastMovementAt = 0;
    },
    updateManualGameMovement(deltaSeconds) {
      let dx = 0;
      let dy = 0;
      if (this.gamePressedKeys.has("left")) dx -= 1;
      if (this.gamePressedKeys.has("right")) dx += 1;
      if (this.gamePressedKeys.has("up")) dy -= 1;
      if (this.gamePressedKeys.has("down")) dy += 1;

      if (!dx && !dy) {
        if (this.moveFrameId === null) this.isWalking = false;
        return;
      }

      const magnitude = Math.hypot(dx, dy) || 1;
      const boostMultiplier = this.gameSpeedBoostActive
        ? ROOM_GAME_SETTINGS.speedBoostMultiplier
        : 1;
      const speed = (
        ROOM_GAME_SETTINGS.manualSpeedPerSecond * boostMultiplier
      ) / Math.max(0.72, this.currentMovementProfile.speedFactor);
      const movement = {
        x: (dx / magnitude) * speed * deltaSeconds,
        y: (dy / magnitude) * speed * deltaSeconds,
      };
      const previous = this.characterPosition;
      const next = this.resolveManualGamePosition(previous, movement);

      if (Math.abs(next.x - previous.x) > 0.001) {
        this.facing = next.x > previous.x ? "right" : "left";
      }
      const moved = this.pathHeuristic(previous, next) > 0.001;
      this.characterPosition = next;
      this.isWalking = moved;
      this.activeTarget = "game-manual";
      if (moved) this.checkGameItemCollisions();
    },
    resolveManualGamePosition(position, movement) {
      const direct = {
        x: position.x + movement.x,
        y: position.y + movement.y,
      };
      if (this.hasWalkableLine(this.toFootPoint(position), this.toFootPoint(direct))) {
        return direct;
      }

      let resolved = position;
      const horizontal = { x: position.x + movement.x, y: position.y };
      if (
        movement.x
        && this.hasWalkableLine(this.toFootPoint(position), this.toFootPoint(horizontal))
      ) {
        resolved = horizontal;
      }
      const vertical = { x: resolved.x, y: resolved.y + movement.y };
      if (
        movement.y
        && this.hasWalkableLine(this.toFootPoint(resolved), this.toFootPoint(vertical))
      ) {
        resolved = vertical;
      }
      return resolved;
    },
    checkGameItemCollisions() {
      if (this.gameState !== "playing") return;
      const foot = this.toFootPoint(this.characterPosition);
      const item = this.gameItems.find(candidate => (
        this.pathHeuristic(foot, candidate) <= ROOM_GAME_SETTINGS.collectionRadius
      ));
      if (item) this.resolveGameItem(item);
    },
    setupGameEnemies() {
      const candidates = ROOM_GAME_ENEMY_CHARACTERS
        .filter(character => character.id !== this.currentCharacter.id)
        .slice(0, this.currentStageSettings.enemyCount);
      this.gameEnemies = [];

      candidates.forEach((character, index) => {
        const now = performance.now();
        const foot = this.findEnemySpawnPoint();
        const position = this.fromFootPoint(foot);
        this.gameEnemySequence += 1;
        this.gameEnemies.push({
          id: `room-enemy-${this.gameEnemySequence}`,
          characterId: character.id,
          name: character.name,
          mode: "roam",
          x: position.x,
          y: position.y,
          targetX: foot.x,
          targetY: foot.y,
          speed: this.currentStageSettings.enemySpeedPerSecond * (0.94 + index * 0.05),
          facing: index % 2 ? "left" : "right",
          route: [],
          stunnedUntil: 0,
          chaseUntil: 0,
          chaseCooldownUntil: now + 1600 + index * 400,
          nextSenseAt: now + 700 + index * 180,
          nextChaseRouteAt: 0,
          lastMoveX: index % 2 ? -1 : 1,
          lastMoveY: 0,
          turningUntil: 0,
          obstacleHitCount: 0,
          lastObstacleHitAt: 0,
          obstacleAnchorX: foot.x,
          obstacleAnchorY: foot.y,
          clearTravelAfterObstacle: 0,
          avoidanceUntil: 0,
          lastEscapeTargetX: null,
          lastEscapeTargetY: null,
        });
      });
    },
    findEnemySpawnPoint() {
      const playerFoot = this.toFootPoint(this.characterPosition);
      for (let attempt = 0; attempt < 160; attempt += 1) {
        const point = {
          x: 7 + Math.random() * 86,
          y: 38 + Math.random() * 52,
        };
        const farFromPlayer = this.pathHeuristic(playerFoot, point) >= 20;
        const farFromEnemies = this.gameEnemies.every(enemy => (
          this.pathHeuristic(this.toFootPoint(enemy), point) >= 14
        ));
        if (farFromPlayer && farFromEnemies && this.isWalkable(point)) return point;
      }
      return this.nearestWalkablePoint({ x: 88, y: 88 });
    },
    randomEnemyTarget(enemy = null) {
      const enemyFoot = enemy ? this.toFootPoint(enemy) : null;
      for (let attempt = 0; attempt < 140; attempt += 1) {
        const point = {
          x: 7 + Math.random() * 86,
          y: 38 + Math.random() * 52,
        };
        const crossesRoom = !enemyFoot || this.pathHeuristic(enemyFoot, point) >= 30;
        if (crossesRoom && this.isWalkable(point)) return point;
      }
      return this.nearestWalkablePoint({ x: 50, y: 78 });
    },
    setGameEnemyRoute(enemy, destination) {
      const enemyFoot = this.nearestWalkablePoint(this.toFootPoint(enemy));
      const route = this.findShortestWalkablePath(enemyFoot, destination);
      const nextRoute = route.filter(point => this.pathHeuristic(enemyFoot, point) > 0.8);
      const target = nextRoute[nextRoute.length - 1] || destination;
      enemy.targetX = target.x;
      enemy.targetY = target.y;
      enemy.route = nextRoute;
    },
    retargetGameEnemy(enemy) {
      this.setGameEnemyRoute(enemy, this.randomEnemyTarget(enemy));
    },
    retargetChasingEnemy(enemy, now) {
      this.setGameEnemyRoute(
        enemy,
        this.nearestWalkablePoint(this.toFootPoint(this.characterPosition)),
      );
      enemy.nextChaseRouteAt = now + this.currentStageSettings.enemyChaseRefreshMs;
    },
    updateEnemyAwareness(enemy, now) {
      const settings = this.currentStageSettings;
      if (now < enemy.avoidanceUntil) return;
      if (this.gameInvisibilityActive) {
        if (enemy.mode === "chase") {
          enemy.mode = "roam";
          enemy.route = [];
          enemy.chaseUntil = 0;
          enemy.chaseCooldownUntil = Math.max(enemy.chaseCooldownUntil, now + 900);
          enemy.nextSenseAt = enemy.chaseCooldownUntil;
        }
        return;
      }
      if (enemy.mode === "chase") {
        if (now >= enemy.chaseUntil) {
          enemy.mode = "roam";
          enemy.route = [];
          enemy.chaseCooldownUntil = now + settings.enemyChaseCooldownMs;
          enemy.nextSenseAt = enemy.chaseCooldownUntil;
          return;
        }
        if (now >= enemy.nextChaseRouteAt) this.retargetChasingEnemy(enemy, now);
        return;
      }

      if (now < enemy.nextSenseAt) return;
      enemy.nextSenseAt = now + settings.enemySenseIntervalMs * (0.85 + Math.random() * 0.3);
      if (now < enemy.chaseCooldownUntil) return;

      const activeChasers = this.gameEnemies.filter(candidate => (
        candidate.mode === "chase"
      )).length;
      if (activeChasers >= settings.maxActiveChasers) return;

      const distanceToPlayer = this.pathHeuristic(
        this.toFootPoint(enemy),
        this.toFootPoint(this.characterPosition),
      );
      if (
        distanceToPlayer > settings.enemyAwarenessRadius
        || Math.random() > settings.enemyChaseChance
      ) return;

      enemy.mode = "chase";
      enemy.chaseUntil = now + settings.enemyChaseDurationMs;
      enemy.nextChaseRouteAt = 0;
      enemy.route = [];
    },
    findEnemyRetreatPoint(enemy) {
      const foot = this.toFootPoint(enemy);
      const magnitude = Math.hypot(enemy.lastMoveX, enemy.lastMoveY) || 1;
      const reverse = {
        x: -enemy.lastMoveX / magnitude,
        y: -enemy.lastMoveY / magnitude,
      };
      const angles = [0, Math.PI / 6, -Math.PI / 6, Math.PI / 3, -Math.PI / 3, Math.PI / 2, -Math.PI / 2];
      const distances = [10, 7, 4];

      for (const distance of distances) {
        for (const angle of angles) {
          const direction = {
            x: reverse.x * Math.cos(angle) - reverse.y * Math.sin(angle),
            y: reverse.x * Math.sin(angle) + reverse.y * Math.cos(angle),
          };
          const candidate = {
            x: foot.x + direction.x * distance,
            y: foot.y + direction.y * distance,
          };
          if (
            this.isWalkable(candidate)
            && this.hasWalkableLine(foot, candidate)
          ) return candidate;
        }
      }
      return this.randomEnemyTarget(enemy);
    },
    registerEnemyObstacleHit(enemy, now) {
      const foot = this.toFootPoint(enemy);
      const isSameTrap = (
        now - enemy.lastObstacleHitAt <= 1600
        && enemy.clearTravelAfterObstacle < 14
        && this.pathHeuristic(
          foot,
          { x: enemy.obstacleAnchorX, y: enemy.obstacleAnchorY },
        ) < 18
      );

      if (isSameTrap) {
        enemy.obstacleHitCount += 1;
      } else {
        enemy.obstacleHitCount = 1;
        enemy.obstacleAnchorX = foot.x;
        enemy.obstacleAnchorY = foot.y;
      }
      enemy.lastObstacleHitAt = now;
      enemy.clearTravelAfterObstacle = 0;
      return enemy.obstacleHitCount >= 2;
    },
    enemyEscapeOpenness(point) {
      const directions = 12;
      const radii = [4, 8, 12];
      let score = 0;
      radii.forEach((radius, radiusIndex) => {
        for (let index = 0; index < directions; index += 1) {
          const angle = (Math.PI * 2 * index) / directions;
          const edge = {
            x: point.x + Math.cos(angle) * radius,
            y: point.y + Math.sin(angle) * radius,
          };
          if (this.hasWalkableLine(point, edge)) score += radiusIndex + 1;
        }
      });
      return score;
    },
    findEnemyOpenEscapePoint(enemy) {
      const foot = this.toFootPoint(enemy);
      const anchor = {
        x: enemy.obstacleAnchorX,
        y: enemy.obstacleAnchorY,
      };
      const playerFoot = this.toFootPoint(this.characterPosition);
      const fixedCandidates = [
        { x: 8, y: 38 },
        { x: 45, y: 38 },
        { x: 92, y: 38 },
        { x: 40, y: 58 },
        { x: 50, y: 76 },
        { x: 38, y: 90 },
        { x: 58, y: 90 },
        { x: 92, y: 90 },
      ];
      const randomCandidates = Array.from({ length: 28 }, () => ({
        x: 6 + Math.random() * 88,
        y: 35 + Math.random() * 58,
      }));
      let best = null;

      const rankedCandidates = [...fixedCandidates, ...randomCandidates]
        .filter(candidate => this.isWalkable(candidate))
        .map((candidate) => {
          const distanceFromFoot = this.pathHeuristic(foot, candidate);
          const distanceFromAnchor = this.pathHeuristic(anchor, candidate);
          if (distanceFromFoot < 20 || distanceFromAnchor < 22) return null;
          const playerDistance = this.pathHeuristic(playerFoot, candidate);
          const previousTargetDistance = (
            Number.isFinite(enemy.lastEscapeTargetX)
            && Number.isFinite(enemy.lastEscapeTargetY)
          ) ? this.pathHeuristic(candidate, {
              x: enemy.lastEscapeTargetX,
              y: enemy.lastEscapeTargetY,
            })
            : 30;
          const preliminaryScore = (
            this.enemyEscapeOpenness(candidate) * 1.8
            + Math.min(45, distanceFromAnchor) * 0.45
            + Math.min(35, previousTargetDistance) * 0.3
            + Math.min(24, playerDistance) * 0.18
          );
          return { point: candidate, preliminaryScore };
        })
        .filter(Boolean)
        .sort((a, b) => b.preliminaryScore - a.preliminaryScore)
        .slice(0, 8);

      rankedCandidates.forEach((candidate) => {
        const route = this.findShortestWalkablePath(foot, candidate.point);
        if (route.length < 2) return;
        const routeDistance = route.slice(1).reduce((total, point, index) => (
          total + this.pathHeuristic(route[index], point)
        ), 0);
        const score = candidate.preliminaryScore - routeDistance * 0.08;
        if (!best || score > best.score) best = { point: candidate.point, score };
      });

      return best?.point || this.randomEnemyTarget(enemy);
    },
    turnEnemyAwayFromObstacle(enemy, now) {
      const foot = this.toFootPoint(enemy);
      const isRepeatedHit = this.registerEnemyObstacleHit(enemy, now);
      const retreat = isRepeatedHit
        ? this.findEnemyOpenEscapePoint(enemy)
        : this.findEnemyRetreatPoint(enemy);
      const retreatX = retreat.x - foot.x;
      enemy.mode = "roam";
      enemy.chaseUntil = 0;
      enemy.avoidanceUntil = now + (isRepeatedHit ? 2800 : 1300);
      enemy.chaseCooldownUntil = Math.max(
        enemy.chaseCooldownUntil,
        enemy.avoidanceUntil + 500,
      );
      enemy.nextSenseAt = enemy.chaseCooldownUntil;
      enemy.nextChaseRouteAt = 0;
      enemy.route = [];
      enemy.turningUntil = now + (isRepeatedHit ? 560 : 420);
      enemy.lastEscapeTargetX = retreat.x;
      enemy.lastEscapeTargetY = retreat.y;
      if (Math.abs(retreatX) > 0.01) {
        enemy.facing = retreatX > 0 ? "right" : "left";
      }
      this.setGameEnemyRoute(enemy, retreat);
    },
    updateGameEnemies(deltaSeconds, now) {
      if (this.gameState !== "playing") return;
      this.gameEnemies.forEach((enemy) => {
        if (now < enemy.stunnedUntil) return;
        this.updateEnemyAwareness(enemy, now);
        if (!enemy.route.length) {
          if (enemy.mode === "chase") this.retargetChasingEnemy(enemy, now);
          else this.retargetGameEnemy(enemy);
        }

        const foot = this.toFootPoint(enemy);
        let target = enemy.route[0] || { x: enemy.targetX, y: enemy.targetY };
        if (this.pathHeuristic(foot, target) < 1.15 && enemy.route.length) {
          enemy.route.shift();
          target = enemy.route[0] || { x: enemy.targetX, y: enemy.targetY };
        }
        const distance = this.pathHeuristic(foot, target);
        if (distance < 0.35) {
          if (enemy.mode === "chase") this.retargetChasingEnemy(enemy, now);
          else this.retargetGameEnemy(enemy);
          return;
        }

        const movement = {
          x: ((target.x - foot.x) / distance) * enemy.speed * deltaSeconds,
          y: ((target.y - foot.y) / distance) * enemy.speed * deltaSeconds,
        };
        const previous = { x: enemy.x, y: enemy.y };
        const direct = {
          x: previous.x + movement.x,
          y: previous.y + movement.y,
        };
        if (!this.hasWalkableLine(this.toFootPoint(previous), this.toFootPoint(direct))) {
          this.turnEnemyAwayFromObstacle(enemy, now);
          return;
        }
        const next = this.resolveManualGamePosition(previous, movement);
        const movedDistance = this.pathHeuristic(previous, next);
        if (movedDistance <= 0.001) {
          this.turnEnemyAwayFromObstacle(enemy, now);
          return;
        }
        enemy.lastMoveX = (next.x - previous.x) / movedDistance;
        enemy.lastMoveY = (next.y - previous.y) / movedDistance;
        if (enemy.lastObstacleHitAt > 0) {
          enemy.clearTravelAfterObstacle += movedDistance;
          if (
            enemy.clearTravelAfterObstacle >= 18
            && now - enemy.lastObstacleHitAt >= 650
          ) {
            enemy.obstacleHitCount = 0;
            enemy.lastObstacleHitAt = 0;
            enemy.clearTravelAfterObstacle = 0;
          }
        }
        if (Math.abs(next.x - previous.x) > 0.001) {
          enemy.facing = next.x > previous.x ? "right" : "left";
        }
        enemy.x = next.x;
        enemy.y = next.y;
      });
    },
    checkGameEnemyCollision() {
      if (
        this.gameState !== "playing"
        || this.gameIsInvulnerable
        || this.gameInvisibilityActive
      ) return;
      const playerFoot = this.toFootPoint(this.characterPosition);
      const enemy = this.gameEnemies.find(candidate => (
        this.pathHeuristic(playerFoot, this.toFootPoint(candidate))
          <= ROOM_GAME_SETTINGS.enemyCollisionRadius
      ));
      if (!enemy) return;
      this.handleGameEnemyHit(enemy);
    },
    handleGameEnemyHit(enemy) {
      if (this.gameIsInvulnerable || this.gameState !== "playing") return;
      this.clearMoveTimers();
      this.gamePressedKeys.clear();
      this.gameTargetId = "";
      this.isWalking = false;
      this.gameCombo = 0;
      this.gameLives = Math.max(0, this.gameLives - 1);
      this.gameScore = Math.max(0, this.gameScore - ROOM_GAME_SETTINGS.enemyHitScorePenalty);
      this.gameIsInvulnerable = true;
      this.characterPosition = this.findSafePlayerRespawn();
      this.setGameReaction("sadness", ROOM_GAME_SETTINGS.hitInvulnerabilityMs);
      this.showGameFeedback(
        `${enemy.name}와 충돌! ♥ -1 · -${ROOM_GAME_SETTINGS.enemyHitScorePenalty}점`,
        "danger",
      );

      if (this.gameLives <= 0) {
        this.finishRoomGame(false, "lives");
        return;
      }

      window.clearTimeout(this.gameInvulnerabilityTimer);
      this.gameInvulnerabilityTimer = window.setTimeout(() => {
        this.gameIsInvulnerable = false;
      }, ROOM_GAME_SETTINGS.hitInvulnerabilityMs);
    },
    isGameSkillActive(skillId) {
      return {
        invisibility: this.gameInvisibilityActive,
        "time-stop": this.gameTimeStopActive,
        speed: this.gameSpeedBoostActive,
      }[skillId] || false;
    },
    activateGameSkill(skillId) {
      if (
        this.gameState !== "playing"
        || !ROOM_GAME_SKILL_DEFINITIONS.some(skill => skill.id === skillId)
        || this.gameSkillCharges[skillId] <= 0
        || this.isGameSkillActive(skillId)
      ) return;

      this.gameSkillCharges = {
        ...this.gameSkillCharges,
        [skillId]: this.gameSkillCharges[skillId] - 1,
      };

      if (skillId === "invisibility") {
        const now = performance.now();
        this.gameInvisibilityActive = true;
        this.gameEnemies.forEach((enemy) => {
          enemy.mode = "roam";
          enemy.route = [];
          enemy.chaseUntil = 0;
          enemy.chaseCooldownUntil = Math.max(
            enemy.chaseCooldownUntil,
            now + ROOM_GAME_SETTINGS.invisibilityDurationMs + 900,
          );
          enemy.nextSenseAt = enemy.chaseCooldownUntil;
        });
        window.clearTimeout(this.gameInvisibilityTimer);
        this.gameInvisibilityTimer = window.setTimeout(() => {
          this.gameInvisibilityActive = false;
        }, ROOM_GAME_SETTINGS.invisibilityDurationMs);
        this.showGameFeedback("투명화! 4초간 적에게 보이지 않아요", "time");
        return;
      }

      if (skillId === "time-stop") {
        const now = performance.now();
        const freezeUntil = now + ROOM_GAME_SETTINGS.timeStopDurationMs;
        this.gameTimeStopActive = true;
        this.gameTimeStopStartedAt = Date.now();
        this.gameEnemies.forEach((enemy) => {
          enemy.mode = "roam";
          enemy.route = [];
          enemy.stunnedUntil = Math.max(enemy.stunnedUntil, freezeUntil);
          enemy.chaseUntil = 0;
          enemy.chaseCooldownUntil = Math.max(enemy.chaseCooldownUntil, freezeUntil + 1500);
          enemy.nextSenseAt = enemy.chaseCooldownUntil;
        });
        window.clearTimeout(this.gameTimeStopTimer);
        this.gameTimeStopTimer = window.setTimeout(() => {
          if (!this.gameTimeStopActive) return;
          const frozenDuration = Math.max(0, Date.now() - this.gameTimeStopStartedAt);
          this.gameDeadline += frozenDuration;
          this.gameTimeStopActive = false;
          this.gameTimeStopStartedAt = 0;
          this.gameRemainingMs = Math.max(0, this.gameDeadline - Date.now());
        }, ROOM_GAME_SETTINGS.timeStopDurationMs);
        this.showGameFeedback("시간정지! 적과 제한시간이 2.4초간 멈춰요", "time");
        return;
      }

      this.gameSpeedBoostActive = true;
      window.clearTimeout(this.gameSpeedBoostTimer);
      this.gameSpeedBoostTimer = window.setTimeout(() => {
        this.gameSpeedBoostActive = false;
      }, ROOM_GAME_SETTINGS.speedBoostDurationMs);
      this.showGameFeedback("바람가속! 4.5초간 더 빨라져요", "time");
    },
    clearGameSkillEffects() {
      window.clearTimeout(this.gameInvisibilityTimer);
      window.clearTimeout(this.gameTimeStopTimer);
      window.clearTimeout(this.gameSpeedBoostTimer);
      this.gameInvisibilityActive = false;
      this.gameTimeStopActive = false;
      this.gameTimeStopStartedAt = 0;
      this.gameSpeedBoostActive = false;
    },
    findSafePlayerRespawn() {
      const preferred = this.toFootPoint(DEFAULT_CHARACTER_POSITION);
      const isSafe = point => (
        this.isWalkable(point)
        && this.gameEnemies.every(enemy => (
          this.pathHeuristic(point, this.toFootPoint(enemy)) >= 18
        ))
      );
      if (isSafe(preferred)) return { ...DEFAULT_CHARACTER_POSITION };

      for (let attempt = 0; attempt < 160; attempt += 1) {
        const point = {
          x: 8 + Math.random() * 84,
          y: 40 + Math.random() * 48,
        };
        if (isSafe(point)) return this.fromFootPoint(point);
      }
      return this.fromFootPoint(this.nearestWalkablePoint(preferred));
    },
    restoreGameBestScore() {
      try {
        const saved = Number(localStorage.getItem(ROOM_GAME_SETTINGS.bestScoreStorageKey));
        this.gameBestScore = Number.isFinite(saved) && saved > 0 ? Math.floor(saved) : 0;
      } catch (error) {
        this.gameBestScore = 0;
      }
    },
    saveGameBestScore() {
      try {
        localStorage.setItem(
          ROOM_GAME_SETTINGS.bestScoreStorageKey,
          String(this.gameBestScore),
        );
      } catch (error) {
        console.warn("Failed to save room game score:", error);
      }
    },
    startRoomGame() {
      if (this.isMovementLocked && this.gameState === "idle") return;
      this.clearMoveTimers();
      this.clearGameTimers();
      this.stopGameMovementLoop();
      window.clearTimeout(this.gameFeedbackTimer);
      window.clearTimeout(this.gameReactionTimer);
      window.clearTimeout(this.gameInvulnerabilityTimer);
      this.clearGameSkillEffects();
      this.hideHotspotLabel();
      this.isWalking = false;
      this.isTantrum = false;
      this.isReturningHome = false;
      this.arrivalPulse = false;
      this.gameState = "countdown";
      this.gameCountdown = ROOM_GAME_SETTINGS.startCountdown;
      this.gameStage = 1;
      this.gameRemainingMs = ROOM_GAME_SETTINGS.stages[0].durationMs;
      this.gameScore = 0;
      this.gameCollected = 0;
      this.gameStageCollected = 0;
      this.gameLives = ROOM_GAME_SETTINGS.initialLives;
      this.gameCombo = 0;
      this.gameLastCollectedAt = 0;
      this.gameItems = [];
      this.gameEnemies = [];
      this.gameTargetId = "";
      this.gameFeedback = "";
      this.gameReactionPose = "";
      this.gameIsInvulnerable = false;
      this.gameSkillCharges = {
        invisibility: 0,
        "time-stop": 0,
        speed: 0,
      };
      this.gameWon = false;
      this.gameResultReason = "time";

      const countdownId = window.setInterval(() => {
        this.gameCountdown -= 1;
        if (this.gameCountdown > 0) return;
        window.clearInterval(countdownId);
        this.beginRoomGame();
      }, 850);
      this.gameTimerIds.push(countdownId);
    },
    beginRoomGame() {
      this.gameStage = 1;
      this.startCurrentGameStage();
    },
    startCurrentGameStage() {
      this.clearGameTimers();
      this.stopGameMovementLoop();
      this.clearMoveTimers();
      this.clearGameSkillEffects();
      this.gameState = "playing";
      this.gameStageCollected = 0;
      this.gameCombo = 0;
      this.gameLastCollectedAt = 0;
      window.clearTimeout(this.gameInvulnerabilityTimer);
      this.gameIsInvulnerable = false;
      this.gameItems = [];
      this.gameTargetId = "";
      this.gameDeadline = Date.now() + this.currentStageSettings.durationMs;
      this.gameRemainingMs = this.currentStageSettings.durationMs;
      this.setupGameEnemies();
      this.ensureGameLightAvailable();
      while (this.gameItems.length < this.currentStageSettings.visibleItemCount) {
        this.spawnGameItem();
      }
      this.spawnGameItem(this.randomGameSkillItemType());

      const clockId = window.setInterval(this.tickGameClock, 100);
      this.gameTimerIds.push(clockId);
      this.startGameMovementLoop();
    },
    tickGameClock() {
      if (this.gameState !== "playing") return;
      if (this.gameTimeStopActive) return;
      this.gameRemainingMs = Math.max(0, this.gameDeadline - Date.now());
      if (this.gameRemainingMs <= 0) this.finishRoomGame(false, "time");
    },
    clearCurrentGameStage() {
      if (this.gameState !== "playing") return;
      this.clearMoveTimers();
      this.clearGameTimers();
      this.stopGameMovementLoop();
      this.isWalking = false;
      this.gameTargetId = "";
      this.gameItems = [];
      this.gameEnemies = [];
      this.gameScore += this.gameStage * 300;
      this.gameState = "stage-clear";
      this.setGameReaction("joy", ROOM_GAME_SETTINGS.stageTransitionMs);

      const transitionId = window.setTimeout(() => {
        this.gameTimerIds = this.gameTimerIds.filter(timer => timer !== transitionId);
        if (this.gameState !== "stage-clear") return;
        this.gameStage += 1;
        this.startCurrentGameStage();
      }, ROOM_GAME_SETTINGS.stageTransitionMs);
      this.gameTimerIds.push(transitionId);
    },
    finishRoomGame(won, reason = "time") {
      if (!["playing", "countdown", "stage-clear"].includes(this.gameState)) return;
      this.clearMoveTimers();
      this.clearGameTimers();
      this.stopGameMovementLoop();
      window.clearTimeout(this.gameInvulnerabilityTimer);
      this.clearGameSkillEffects();
      this.isWalking = false;
      this.gameTargetId = "";
      this.gameWon = Boolean(won);
      this.gameResultReason = reason;
      this.gameIsInvulnerable = false;
      this.gameState = "result";
      this.gameItems = [];
      this.gameEnemies = [];
      if (this.gameScore > this.gameBestScore) {
        this.gameBestScore = this.gameScore;
        this.saveGameBestScore();
      }
      this.setGameReaction(won ? "joy" : "sadness", 2200);
    },
    exitRoomGame() {
      if (this.gameState === "idle") return;
      this.clearMoveTimers();
      this.clearGameTimers();
      this.stopGameMovementLoop();
      window.clearTimeout(this.gameFeedbackTimer);
      window.clearTimeout(this.gameInvulnerabilityTimer);
      this.clearGameSkillEffects();
      this.gameState = "idle";
      this.gameItems = [];
      this.gameEnemies = [];
      this.gameTargetId = "";
      this.gameFeedback = "";
      this.gameReactionPose = "";
      this.gameIsInvulnerable = false;
      this.isWalking = false;
      this.isReturningHome = true;
      this.faceDefaultPosition();
      this.walkTo("character", { force: true });
    },
    clearGameTimers() {
      this.gameTimerIds.forEach(timer => {
        window.clearInterval(timer);
        window.clearTimeout(timer);
      });
      this.gameTimerIds = [];
    },
    spawnGameItem(forcedType = "") {
      if (this.gameState !== "playing") return;
      const type = forcedType || this.randomGameItemType();
      const point = this.randomWalkableGamePoint();
      this.gameItemSequence += 1;
      this.gameItems.push({
        id: `room-item-${this.gameItemSequence}`,
        type,
        x: point.x,
        y: point.y,
      });
    },
    ensureGameLightAvailable() {
      if (
        this.gameState === "playing"
        && !this.gameItems.some(item => item.type === "light")
      ) {
        this.spawnGameItem("light");
      }
    },
    queueGameItemSpawn() {
      const settings = this.currentStageSettings;
      const delay = settings.itemRespawnMinMs
        + Math.random() * (settings.itemRespawnMaxMs - settings.itemRespawnMinMs);
      const spawnId = window.setTimeout(() => {
        this.gameTimerIds = this.gameTimerIds.filter(timer => timer !== spawnId);
        if (this.gameState !== "playing") return;
        this.ensureGameLightAvailable();
        while (this.gameItems.length < this.currentStageSettings.visibleItemCount) {
          this.spawnGameItem();
        }
      }, delay);
      this.gameTimerIds.push(spawnId);
    },
    randomGameItemType() {
      const roll = Math.random();
      if (roll < this.currentStageSettings.shadowChance) return "shadow";
      if (
        roll
        < this.currentStageSettings.shadowChance + this.currentStageSettings.timeChance
      ) return "time";
      if (
        roll
        < this.currentStageSettings.shadowChance
          + this.currentStageSettings.timeChance
          + this.currentStageSettings.skillChance
      ) return this.randomGameSkillItemType();
      return "light";
    },
    randomGameSkillItemType() {
      const available = ROOM_GAME_SKILL_DEFINITIONS.filter(skill => (
        this.gameSkillCharges[skill.id] < ROOM_GAME_SETTINGS.skillMaxCharges
      ));
      const candidates = available.length ? available : ROOM_GAME_SKILL_DEFINITIONS;
      const skill = candidates[Math.floor(Math.random() * candidates.length)];
      return `skill-${skill.id}`;
    },
    randomWalkableGamePoint() {
      const occupied = this.gameItems.map(item => ({ x: item.x, y: item.y }));
      for (let attempt = 0; attempt < 180; attempt += 1) {
        const point = {
          x: 7 + Math.random() * 86,
          y: 37 + Math.random() * 54,
        };
        const hasSpacing = occupied.every(item => this.pathHeuristic(item, point) >= 9);
        const farFromEnemies = this.gameEnemies.every(enemy => (
          this.pathHeuristic(this.toFootPoint(enemy), point) >= 10
        ));
        if (hasSpacing && farFromEnemies && this.isWalkable(point)) return point;
      }
      return this.nearestWalkablePoint({
        x: 38 + Math.random() * 30,
        y: 62 + Math.random() * 22,
      });
    },
    selectGameItem(item) {
      if (this.gameState !== "playing" || this.isWalking || this.gameTargetId) return;
      if (!this.gameItems.some(candidate => candidate.id === item.id)) return;
      this.gameTargetId = item.id;
      const destination = this.fromFootPoint({ x: item.x, y: item.y });
      this.walkTo(`game:${item.id}`, {
        force: true,
        destinationOverride: destination,
      });
    },
    handleGameArrival(target) {
      if (!target.startsWith("game:") || this.gameState !== "playing") return;
      const itemId = target.slice("game:".length);
      const item = this.gameItems.find(candidate => candidate.id === itemId);
      this.gameTargetId = "";
      if (!item) return;
      this.resolveGameItem(item);
    },
    resolveGameItem(item) {
      if (this.gameState !== "playing") return;
      if (!this.gameItems.some(candidate => candidate.id === item.id)) return;
      if (this.gameTargetId === item.id) this.gameTargetId = "";
      this.gameItems = this.gameItems.filter(candidate => candidate.id !== item.id);

      if (item.type.startsWith("skill-")) {
        this.collectGameSkillItem(item.type.slice("skill-".length));
        this.queueGameItemSpawn();
        return;
      }

      if (item.type === "shadow") {
        this.gameCombo = 0;
        this.gameScore = Math.max(0, this.gameScore - ROOM_GAME_SETTINGS.shadowScorePenalty);
        this.gameDeadline -= ROOM_GAME_SETTINGS.shadowPenaltyMs;
        this.gameRemainingMs = this.gameTimeStopActive
          ? Math.max(0, this.gameRemainingMs - ROOM_GAME_SETTINGS.shadowPenaltyMs)
          : Math.max(0, this.gameDeadline - Date.now());
        this.setGameReaction("hurt");
        this.showGameFeedback(
          `그림자! -${ROOM_GAME_SETTINGS.shadowPenaltyMs / 1000}초`,
          "danger",
        );
        if (this.gameRemainingMs <= 0) {
          this.finishRoomGame(false);
          return;
        }
        this.queueGameItemSpawn();
        return;
      }

      const now = Date.now();
      this.gameCombo = now - this.gameLastCollectedAt <= ROOM_GAME_SETTINGS.comboWindowMs
        ? this.gameCombo + 1
        : 1;
      this.gameLastCollectedAt = now;
      const baseScore = item.type === "time" ? 140 : 100;
      const gainedScore = baseScore * this.gameMultiplier;
      this.gameScore += gainedScore;
      this.setGameReaction("joy");

      if (item.type === "time") {
        this.gameDeadline += ROOM_GAME_SETTINGS.timeBonusMs;
        this.gameRemainingMs = this.gameTimeStopActive
          ? this.gameRemainingMs + ROOM_GAME_SETTINGS.timeBonusMs
          : Math.max(0, this.gameDeadline - Date.now());
        this.showGameFeedback(
          `+${gainedScore} · +${ROOM_GAME_SETTINGS.timeBonusMs / 1000}초`,
          "time",
        );
        this.queueGameItemSpawn();
        return;
      }

      this.gameCollected += 1;
      this.gameStageCollected += 1;
      this.showGameFeedback(
        `마음빛 +1 · +${gainedScore}${this.gameMultiplier > 1 ? ` ×${this.gameMultiplier}` : ""}`,
        "positive",
      );

      if (this.gameStageCollected >= this.currentStageSettings.targetCollectibles) {
        if (this.gameStage >= this.maxGameStage) {
          this.gameScore += this.gameStage * 300;
          this.finishRoomGame(true, "clear");
        } else {
          this.clearCurrentGameStage();
        }
        return;
      }
      this.queueGameItemSpawn();
    },
    collectGameSkillItem(skillId) {
      const skill = ROOM_GAME_SKILL_DEFINITIONS.find(candidate => candidate.id === skillId);
      if (!skill) return;
      const currentCharges = this.gameSkillCharges[skillId] || 0;
      if (currentCharges >= ROOM_GAME_SETTINGS.skillMaxCharges) {
        this.gameScore += 50;
        this.showGameFeedback(`${skill.name} 충전이 가득 찼어요 · +50`, "positive");
        return;
      }
      this.gameSkillCharges = {
        ...this.gameSkillCharges,
        [skillId]: currentCharges + 1,
      };
      this.setGameReaction("joy");
      this.showGameFeedback(
        `${skill.name} 충전! ${skill.key} 키로 사용하세요`,
        "time",
      );
    },
    gameItemIconSource(item) {
      if (item.type === "light") return gameHeartIcon;
      if (item.type === "time") return gameTimeIcon;
      if (item.type.startsWith("skill-")) {
        const skillId = item.type.slice("skill-".length);
        return ROOM_GAME_SKILL_DEFINITIONS.find(skill => skill.id === skillId)?.icon || "";
      }
      return "";
    },
    gameItemAriaLabel(item) {
      if (item.type === "shadow") return "위험한 그림자, 피하세요";
      if (item.type === "time") return "시간을 늘려주는 빛 조각";
      if (item.type.startsWith("skill-")) {
        const skillId = item.type.slice("skill-".length);
        const skill = ROOM_GAME_SKILL_DEFINITIONS.find(candidate => candidate.id === skillId);
        return skill ? `${skill.itemName}, ${skill.name} 스킬 충전` : "스킬 충전 아이템";
      }
      return "수집할 마음빛";
    },
    showGameFeedback(message, tone = "positive") {
      window.clearTimeout(this.gameFeedbackTimer);
      this.gameFeedbackKey += 1;
      this.gameFeedback = message;
      this.gameFeedbackTone = tone;
      this.gameFeedbackTimer = window.setTimeout(() => {
        this.gameFeedback = "";
      }, 950);
    },
    setGameReaction(pose, duration = 760) {
      window.clearTimeout(this.gameReactionTimer);
      this.gameReactionPose = pose;
      this.gameReactionTimer = window.setTimeout(() => {
        this.gameReactionPose = "";
      }, duration);
    },
    notifyArrival(target) {
      if (target.startsWith("game:")) {
        this.handleGameArrival(target);
        return;
      }
      this.$emit("arrived", target);
    },
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
    walkTo(target, { force = false, destinationOverride = null } = {}) {
      if (this.isMovementLocked && !force) return;
      if (!force && this.registerRapidRedirect(target)) {
        this.startTantrum();
        return;
      }

      const destination = destinationOverride
        || this.roomStops[target]
        || this.roomStops.character;
      const start = this.characterPosition;
      const route = this.buildRoute(start, destination, target);

      this.clearMoveTimers();
      this.arrivalPulse = false;
      this.activeTarget = target;

      if (!route.length) {
        this.isWalking = false;
        this.activeTarget = target;
        this.finishForcedReturn(target);
        this.resetRedirectHistory();
        this.notifyArrival(target);
        return;
      }

      if (this.prefersReducedMotion() || this.samePoint(start, destination)) {
        this.characterPosition = route[route.length - 1] || this.fromFootPoint(this.nearestWalkablePoint(this.toFootPoint(destination)));
        this.activeTarget = target;
        this.finishForcedReturn(target);
        this.resetRedirectHistory();
        this.notifyArrival(target);
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
        this.finishForcedReturn(target);
        this.resetRedirectHistory();
        this.notifyArrival(target);
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
    registerRapidRedirect(target) {
      if (!this.isWalking || target === this.activeTarget) return false;

      const now = Date.now();
      const windowStart = now - ROOM_TANTRUM_SETTINGS.redirectWindowMs;
      this.redirectTimestamps = this.redirectTimestamps
        .filter(timestamp => timestamp >= windowStart);
      this.redirectTimestamps.push(now);
      return this.redirectTimestamps.length >= ROOM_TANTRUM_SETTINGS.redirectLimit;
    },
    resetRedirectHistory() {
      this.redirectTimestamps = [];
    },
    startTantrum() {
      this.clearMoveTimers();
      this.isWalking = false;
      this.arrivalPulse = false;
      this.isTantrum = true;
      this.resetRedirectHistory();
      this.hideHotspotLabel();
      this.$emit("movement-interrupted");

      const tantrumTimer = window.setTimeout(() => {
        this.isTantrum = false;
        this.isReturningHome = true;
        this.faceDefaultPosition();

        const returnTimer = window.setTimeout(() => {
          this.walkTo("character", { force: true });
        }, ROOM_TANTRUM_SETTINGS.returnLeadInMs);
        this.moveTimers.push(returnTimer);
      }, ROOM_TANTRUM_SETTINGS.pauseMs);
      this.moveTimers.push(tantrumTimer);
    },
    faceDefaultPosition() {
      const home = this.roomStops.character;
      const horizontalDelta = home.x - this.characterPosition.x;
      if (Math.abs(horizontalDelta) > 0.015) {
        this.facing = horizontalDelta > 0 ? "right" : "left";
      }
    },
    finishForcedReturn(target) {
      if (this.isReturningHome && target === "character") {
        this.isReturningHome = false;
      }
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
      const returnSpeedFactor = this.isReturningHome
        ? ROOM_TANTRUM_SETTINGS.returnSpeedFactor
        : 1;
      const gameSpeedFactor = this.gameState === "playing" && this.gameSpeedBoostActive
        ? 1 / ROOM_GAME_SETTINGS.speedBoostMultiplier
        : 1;
      const minimumDuration = gameSpeedFactor < 1 ? 520 : 850;
      return Math.round(Math.min(3200, Math.max(minimumDuration,
        baseDuration
          * this.currentMovementProfile.speedFactor
          * returnSpeedFactor
          * gameSpeedFactor
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
