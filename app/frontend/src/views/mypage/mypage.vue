<template>
  <main class="app-shell">
    <section class="mypage-home" aria-label="마이페이지 홈">
      <aside class="home-left-panel" aria-label="마이홈 대시보드">
        <article class="identity-card">
          <div class="identity-avatar">
            <img :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
          </div>
          <div class="identity-copy">
            <span class="dashboard-kicker">나의 오늘</span>
            <h1>{{ displayName }}님의 공간</h1>
            <p>{{ homeStatusMessage }}</p>
            <div class="identity-chips">
              <span>{{ todayEmotionLabel }}</span>
              <span>{{ currentCharacter.name }}</span>
              <span>{{ profileMbtiLabel }}</span>
            </div>
          </div>
          <button class="dashboard-primary" type="button" @click="openPanel('profile')">
            프로필 관리
            <span aria-hidden="true">↗</span>
          </button>
        </article>

        <nav class="quick-actions" aria-label="마이룸 기능 메뉴">
          <div class="quick-actions-heading">
            <div>
              <span class="dashboard-kicker">내 공간 살펴보기</span>
              <strong>마이룸 기능</strong>
            </div>
            <span class="quick-actions-count">5</span>
          </div>
          <button type="button" @click="openPanel('mbti')">
            <span class="menu-index">01</span>
            <span class="menu-object" aria-hidden="true">◑</span>
            <span class="menu-copy"><strong>MBTI 분석</strong><small>월간 성향과 변화 확인</small></span>
            <span class="menu-arrow" aria-hidden="true">→</span>
          </button>
          <button type="button" @click="openPanel('weather')">
            <span class="menu-index">02</span>
            <span class="menu-object" aria-hidden="true">⌑</span>
            <span class="menu-copy"><strong>날씨 정보</strong><small>현재 날씨와 활동 제안</small></span>
            <span class="menu-arrow" aria-hidden="true">→</span>
          </button>
          <button type="button" @click="openPanel('book')">
            <span class="menu-index">03</span>
            <span class="menu-object" aria-hidden="true">▤</span>
            <span class="menu-copy"><strong>오늘의 책 추천</strong><small>프로필 기반 추천 도서</small></span>
            <span class="menu-arrow" aria-hidden="true">→</span>
          </button>
          <button class="memory-action" type="button" @click="openPanel('memory')">
            <span class="menu-index">04</span>
            <span class="menu-object" aria-hidden="true">◇</span>
            <span class="menu-copy"><strong>기억 보관함</strong><small>저장된 대화 기억 관리</small></span>
            <span class="menu-arrow" aria-hidden="true">→</span>
          </button>
          <button class="character-action" type="button" @click="openPanel('character')">
            <span class="menu-index">05</span>
            <span class="menu-object" aria-hidden="true">●</span>
            <span class="menu-copy"><strong>캐릭터 정보</strong><small>캐릭터 선택 및 정보 확인</small></span>
            <span class="menu-arrow" aria-hidden="true">→</span>
          </button>
        </nav>

        <aside class="home-sidebar" aria-label="오늘의 상태판">
          <div class="panel-caption">
            <span class="dashboard-kicker">오늘의 요약</span>
            <strong>내 상태 한눈에 보기</strong>
          </div>
          <section class="summary-grid" aria-label="내 상태 요약">
            <button class="summary-card" type="button" @click="goToReport">
              <span>오늘 기분</span>
              <strong>{{ todayEmotionLabel }}</strong>
              <small>마음 리포트에서 확인</small>
            </button>
            <button class="summary-card" type="button" @click="openPanel('mbti')">
              <span>MBTI</span>
              <strong>{{ profileMbtiLabel }}</strong>
              <small>{{ mbtiSummaryText }}</small>
            </button>
            <button class="summary-card" type="button" @click="openPanel('profile')">
              <span>관심사</span>
              <strong>{{ interestPreview }}</strong>
              <small>프로필 기준</small>
            </button>
            <button class="summary-card" type="button" @click="openPanel('profile')">
              <span>취미</span>
              <strong>{{ hobbyPreview }}</strong>
              <small>프로필 기준</small>
            </button>
          </section>
        </aside>
      </aside>

      <section class="room-section" aria-label="내 공간">
        <header class="room-section-heading">
          <div>
            <span class="dashboard-kicker">나의 공간</span>
            <h2>{{ displayName }}님의 미니룸</h2>
          </div>
          <p>표시된 방 안 오브젝트를 선택하면 연결된 기능을 열 수 있어요.</p>
        </header>
        <MypageRoom
          :labels="t"
          :current-character="currentCharacter"
          :focus-target="roomFocusTarget"
          :move-key="roomMoveKey"
          :room-expression="activeRoomExpression"
          @open-panel="openPanelFromRoom"
          @open-chat="goToChat"
          @open-report="goToReport"
          @arrived="activatePanelAfterRoomMove"
        />
      </section>
    </section>

    <MypageModal
        :active-panel="activePanel"
        :title="currentPanelTitle"
        :description="currentPanelDescription"
        @close="closePanel"
      >
        <ProfilePanel
          v-if="activePanel === 'profile'"
          :profile="profile"
          :profile-edit="profileEdit"
          :profile-saved-at="profileSavedAt"
          :current-character="currentCharacter"
          @toggle-profile-edit="toggleProfileEdit"
          @cancel-profile-edit="cancelProfileEdit"
          @update-profile-keywords="updateProfileKeywords"
        />

        <CharacterPanel
          v-if="activePanel === 'character'"
          :selected-character="selectedCharacter"
          :current-character="currentCharacter"
          :characters="characters"
          @choose-character="chooseCharacter"
        />

        <EmotionPanel
          v-if="activePanel === 'emotion'"
          :current-character="currentCharacter"
          :active-expression="activeRoomExpression"
          @apply-expression="applyRoomExpression"
          @cancel="closePanel"
        />

        <MbtiPanel
          v-if="activePanel === 'mbti'"
          :mbti-data="mbtiData"
          :mbti-view-mode="mbtiViewMode"
          :mbti-views="mbtiViews"
          :current-mbti-view="currentMbtiView"
          @refresh="refreshMbtiDemoData"
          @set-view="setMbtiView"
          @save-mbti="saveMbti"
        />

        <WeatherPanel
          v-if="activePanel === 'weather'"
          :payload="weatherPayload"
          :loading="weatherLoading"
          :error="weatherError"
          :location="weatherLocation"
          :regions="weatherRegions"
          @refresh="loadWeatherData({ force: true })"
          @change-region="setWeatherRegion"
          @close="closePanel"
        />

        <BookPanel
          v-if="activePanel === 'book'"
          :payload="bookPayload"
          :loading="bookLoading"
          :error="bookError"
          @refresh="loadBookData"
          @close="closePanel"
        />

        <MemoryPanel
          v-if="activePanel === 'memory'"
          :payload="memoryPayload"
          :loading="memoryLoading"
          :error="memoryError"
          :notice="memoryNotice"
          @refresh="loadMemoryData(true)"
          @delete-memory="deleteMemoryItems([$event])"
          @delete-selected="deleteMemoryItems"
        />

    </MypageModal>

    <transition name="fade">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>

    <section
      v-if="navigationConfirm"
      class="navigation-confirm-backdrop"
      role="presentation"
      @click.self="cancelNavigationConfirm"
    >
      <article class="navigation-confirm" role="dialog" aria-modal="true" :aria-label="navigationConfirm.title">
        <h2>{{ navigationConfirm.title }}</h2>
        <p>{{ navigationConfirm.message }}</p>
        <div class="navigation-confirm-actions">
          <button class="navigation-cancel-button" type="button" @click="cancelNavigationConfirm">취소</button>
          <button class="navigation-confirm-button" type="button" @click="confirmNavigation">
            이동하기
          </button>
        </div>
      </article>
    </section>
  </main>
</template>

<script>
import { MEMORY_API_ENABLED, fetchCurrentWeather, fetchMbtiDemoPayload, fetchMyProfile, updateMyProfile, saveOnboardingMbti, fetchBookRecommendation, fetchMemoryVault, deleteMemoryVaultItem, fetchWeatherRegions } from "./mypage.api";
import { LOCATION_CONSENT_VERSION } from "../../constants/consentVersions";
import { createMypageState, i18n } from "./state/mypage.state";
import { DEFAULT_ROOM_EXPRESSION, VALID_ROOM_EXPRESSIONS } from "./config/emotion.constants";
import {
  DEFAULT_WEATHER_REGION,
  MOVABLE_PANEL_IDS,
  MYPAGE_STORAGE_KEYS,
  MYPAGE_TIMING,
  NAVIGATION_CONFIRM_OPTIONS,
  PANEL_DESCRIPTIONS,
} from "./config/mypage.constants";
import CharacterPanel from "./components/CharacterPanel.vue";
import EmotionPanel from "./components/EmotionPanel.vue";
import MbtiPanel from "./components/MbtiPanel.vue";
import MypageModal from "./components/MypageModal.vue";
import MypageRoom from "./components/MypageRoom.vue";
import ProfilePanel from "./components/ProfilePanel.vue";
import WeatherPanel from "./components/WeatherPanel.vue";
import BookPanel from "./components/BookPanel.vue";
import MemoryPanel from "./components/MemoryPanel.vue";

export default {
  name: "MypageView",
  components: {
    CharacterPanel,
    EmotionPanel,
    MbtiPanel,
    MypageModal,
    MypageRoom,
    ProfilePanel,
    WeatherPanel,
    BookPanel,
    MemoryPanel
  },
  async beforeRouteEnter(to, from, next) {
    try {
      const profilePayload = await fetchMyProfile();
      next((view) => view.applyProfilePayload(profilePayload));
    } catch (e) {
      next("/login");
    }
  },
  data() {
    return createMypageState();
  },
  computed: {
    t() {
      return i18n[this.settings.language];
    },
    currentMbtiView() {
      return this.mbtiViews.find(view => view.key === this.mbtiViewMode) || this.mbtiViews[0];
    },
    currentPanelTitle() {
      if (!this.activePanel) return "";
      return this.t[this.activePanel];
    },
    currentPanelDescription() {
      if (this.activePanel === "memory") {
        return MEMORY_API_ENABLED
          ? "대화에서 저장된 기억을 확인하고 직접 관리할 수 있어요."
          : "예시 화면에서 기억 검색·상세 보기·숨기기 흐름을 미리 체험할 수 있어요.";
      }
      return PANEL_DESCRIPTIONS[this.activePanel] || "";
    },
    currentCharacter() {
      const found = this.characters.find(character => character.id === this.selectedCharacter);
      return found || this.characters[0];
    },
    displayName() {
      return this.profile?.name || this.profile?.nickname || "사용자";
    },
    homeStatusMessage() {
      const emotion = this.todayEmotionLabel;
      if (emotion && emotion !== "아직 기록 없음") {
        return `${emotion}의 결을 담아 오늘의 추천과 프로필 취향을 정리했어요.`;
      }
      return "대화와 프로필을 바탕으로 오늘의 기분과 추천을 정리하는 개인 홈입니다.";
    },
    profileMbtiLabel() {
      const current = this.mbtiData?.current?.type;
      const onboarding = this.mbtiData?.onboarding?.type;
      const profileType = this.profile?.mbti;
      return [current, onboarding, profileType].find(type => type && type !== "----") || "미등록";
    },
    mbtiSummaryText() {
      const previous = this.mbtiData?.previous?.type;
      if (this.profileMbtiLabel === "미등록") return "설정 필요";
      if (previous && previous !== "----" && previous !== this.profileMbtiLabel) {
        return `${previous} -> ${this.profileMbtiLabel}`;
      }
      return this.mbtiData?.current?.type && this.mbtiData.current.type !== "----"
        ? "최근 월간 분석 기준"
        : "온보딩 기준";
    },
    todayEmotionLabel() {
      return this.bookPayload?.profile_basis?.today_emotion || "아직 기록 없음";
    },
    interestPreview() {
      return this.previewList(this.profile?.interests, "관심사 미등록");
    },
    hobbyPreview() {
      return this.previewList(this.profile?.hobbies, "취미 미등록");
    },
  },
  watch: {
    settings: {
      deep: true,
      handler() {
        this.applySettings();
      }
    }
  },
  mounted() {
    try {
      const saved = localStorage.getItem(MYPAGE_STORAGE_KEYS.settings);
      if (saved) {
        const parsed = JSON.parse(saved);
        this.settings = {
          ...this.settings,
          language: parsed.language || this.settings.language,
          fontScale: parsed.fontScale || this.settings.fontScale,
          highContrast: Boolean(parsed.highContrast)
        };
      }
    } catch (error) {
      console.warn("Failed to restore mypage settings:", error);
    }
    this.applySettings();
    this.loadMbtiDemoData();
    this.loadWeatherRegions();
    this.weatherRefreshTimer = window.setInterval(() => {
      if (this.activePanel === "weather") this.loadWeatherData();
    }, MYPAGE_TIMING.weatherRefreshIntervalMs);
  },
  beforeUnmount() {
    if (this.weatherRefreshTimer) window.clearInterval(this.weatherRefreshTimer);
    if (this.toastTimer) window.clearTimeout(this.toastTimer);
  },
  methods: {
    normalizeList(value) {
      if (Array.isArray(value)) return value.filter(Boolean);
      if (!value) return [];
      return String(value)
        .split(",")
        .map(item => item.trim())
        .filter(Boolean);
    },
    previewList(value, fallback) {
      const list = this.normalizeList(value);
      if (!list.length) return fallback;
      const visible = list.slice(0, 2).join(", ");
      return list.length > 2 ? `${visible} 외 ${list.length - 2}` : visible;
    },
    goToReport() {
      this.resetRoomExpression();
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = true;
      this.roomFocusTarget = "wardrobe";
      this.roomMoveKey += 1;
    },
    goToChat() {
      this.resetRoomExpression();
      this.pendingPanel = null;
      this.pendingReportNavigation = false;
      this.pendingChatNavigation = true;
      this.roomFocusTarget = "door";
      this.roomMoveKey += 1;
    },
    completeReportNavigation() {
      this.pendingPanel = null;
      this.pendingReportNavigation = false;
      this.closePanel();
      this.requestNavigationConfirm("report");
    },
    completeChatNavigation() {
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      this.closePanel();
      this.requestNavigationConfirm("chat");
    },
    requestNavigationConfirm(type) {
      this.navigationConfirm = NAVIGATION_CONFIRM_OPTIONS[type] || null;
    },
    cancelNavigationConfirm() {
      this.navigationConfirm = null;
    },
    confirmNavigation() {
      if (!this.navigationConfirm?.path) return;
      const path = this.navigationConfirm.path;
      this.navigationConfirm = null;
      this.$router.push(path);
    },
    async loadWeatherRegions() {
      try {
        const regions = await fetchWeatherRegions();
        if (Array.isArray(regions) && regions.length > 0) {
          this.weatherRegions = regions;
        }
      } catch (error) {
        console.error("Failed to load weather regions:", error);
      }
    },
    applyProfilePayload(data) {
      if (!data?.profile) return;
      this.profile = { ...this.profile, ...data.profile };
      if (data.profile.selectedCharacter) {
        this.selectedCharacter = data.profile.selectedCharacter;
      }
    },
    openPanel(panel) {
      this.resetRoomExpression();
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      this.activatePanel(panel);
    },
    openPanelFromRoom(panel) {
      if (panel !== "emotion") this.resetRoomExpression();
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      if (this.shouldMoveBeforeOpen(panel)) {
        this.pendingPanel = panel;
        this.roomFocusTarget = panel;
        this.roomMoveKey += 1;
        return;
      }
      this.activatePanel(panel);
    },
    shouldMoveBeforeOpen(panel) {
      return MOVABLE_PANEL_IDS.includes(panel);
    },
    activatePanel(panel) {
      if (panel !== "emotion") this.resetRoomExpression();
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      this.activePanel = panel;
      if (panel === "mbti") {
        this.loadMbtiDemoData();
      }
      if (panel === "weather") {
        this.loadWeatherData();
      }
      if (panel === "book") {
        this.loadBookData();
      }
      if (panel === "memory") {
        this.loadMemoryData();
      }
    },
    activatePanelAfterRoomMove(panel) {
      if (this.pendingChatNavigation && panel === "door") {
        this.completeChatNavigation();
        return;
      }
      if (this.pendingReportNavigation && panel === "wardrobe") {
        this.completeReportNavigation();
        return;
      }
      if (!this.pendingPanel || panel !== this.pendingPanel) return;
      this.activatePanel(panel);
    },
    closePanel() {
      if (this.activePanel === "profile" && this.profileEdit) {
        this.cancelProfileEdit();
      }
      this.activePanel = null;
    },
    applyRoomExpression(expressionId) {
      if (!VALID_ROOM_EXPRESSIONS.has(expressionId)) return;
      this.activeRoomExpression = expressionId;
      this.closePanel();
    },
    resetRoomExpression() {
      this.activeRoomExpression = DEFAULT_ROOM_EXPRESSION;
    },
    async toggleProfileEdit() {
      if (!this.profileEdit) {
        this.profileSnapshot = JSON.parse(JSON.stringify(this.profile));
        this.profileEdit = true;
        return;
      }
      if (this.profileEdit) {
        try {
          const res = await updateMyProfile({
            ...this.profile,
            selectedCharacter: this.selectedCharacter
          });
          if (res && res.profile) {
            this.profile = { ...this.profile, ...res.profile };
            if (res.profile.selectedCharacter) {
              this.selectedCharacter = res.profile.selectedCharacter;
            }
          }
          this.profileSavedAt = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
          this.bookPayload = null;
          this.showToast("프로필 수정 내용이 정상적으로 반영되었습니다.");
          this.profileSnapshot = null;
        } catch (e) {
          console.error("Failed to update profile", e);
          this.showToast("프로필 저장에 실패했습니다.");
          return;
        }
      }
      this.profileEdit = false;
    },
    cancelProfileEdit() {
      if (this.profileSnapshot) {
        this.profile = JSON.parse(JSON.stringify(this.profileSnapshot));
      }
      this.profileSnapshot = null;
      this.profileEdit = false;
    },
    updateProfileKeywords({ type, values }) {
      if (!this.profileEdit) return;
      if (type === 'hobby') {
        this.profile.hobbies = values;
      } else if (type === 'interest') {
        this.profile.interests = values;
      }
    },
    async chooseCharacter(id) {
      const oldChar = this.selectedCharacter;
      this.selectedCharacter = id;
      try {
        await updateMyProfile({ selectedCharacter: id });
        localStorage.setItem(MYPAGE_STORAGE_KEYS.character, JSON.stringify({ characterId: id }));
        this.showToast("대화 대상 캐릭터가 교체되었습니다.");
      } catch (e) {
        console.error(e);
        this.selectedCharacter = oldChar;
        this.showToast("캐릭터 교체에 실패했습니다.");
      }
    },
    getSavedWeatherLocation() {
      try {
        const sessionLocation = JSON.parse(
          sessionStorage.getItem(MYPAGE_STORAGE_KEYS.weatherAutoLocation) || "null"
        );
        if (sessionLocation?.mode === "auto") return sessionLocation;
        const saved = JSON.parse(
          localStorage.getItem(MYPAGE_STORAGE_KEYS.weatherLocation) || "null"
        );
        return saved;
      } catch (error) {
        return null;
      }
    },
    saveWeatherLocation(location) {
      this.weatherLocation = location;
      if (location?.mode === "auto") {
        sessionStorage.setItem(MYPAGE_STORAGE_KEYS.weatherAutoLocation, JSON.stringify(location));
        localStorage.removeItem(MYPAGE_STORAGE_KEYS.weatherLocation);
        return;
      }
      sessionStorage.removeItem(MYPAGE_STORAGE_KEYS.weatherAutoLocation);
      localStorage.setItem(MYPAGE_STORAGE_KEYS.weatherLocation, JSON.stringify(location));
    },
    getBrowserLocation() {
      return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
          reject(new Error("geolocation unavailable"));
          return;
        }
        navigator.geolocation.getCurrentPosition(
          (position) => resolve({
            mode: "auto",
            region: "현재 위치",
            lat: position.coords.latitude,
            lon: position.coords.longitude
          }),
          reject,
          {
            enableHighAccuracy: false,
            timeout: MYPAGE_TIMING.geolocationTimeoutMs,
            maximumAge: MYPAGE_TIMING.geolocationMaximumAgeMs
          }
        );
      });
    },
    async resolveWeatherLocation(force = false) {
      const saved = this.getSavedWeatherLocation();
      if (!force && saved) {
        this.weatherLocation = saved;
        return saved;
      }
      if (!force) {
        const fallback = { mode: "manual", region: DEFAULT_WEATHER_REGION };
        this.saveWeatherLocation(fallback);
        return fallback;
      }
      try {
        const browserLocation = await this.getBrowserLocation();
        this.saveWeatherLocation(browserLocation);
        return browserLocation;
      } catch (error) {
        const fallback = saved || { mode: "manual", region: DEFAULT_WEATHER_REGION };
        this.saveWeatherLocation(fallback);
        return fallback;
      }
    },
    async loadWeatherData({ force = false, refreshLocation = false } = {}) {
      const hasFreshPayload = this.weatherPayload
        && Date.now() - this.weatherLastFetchedAt < MYPAGE_TIMING.weatherFreshnessMs;
      if (!force && (hasFreshPayload || this.weatherLoading)) return;

      const requestId = ++this.weatherRequestId;
      this.weatherLoading = true;
      this.weatherError = "";
      try {
        const location = await this.resolveWeatherLocation(refreshLocation);
        const requestLocation = location.mode === "auto"
          ? { lat: location.lat, lon: location.lon, region: location.region }
          : { region: location.region || DEFAULT_WEATHER_REGION };
        const payload = await fetchCurrentWeather(requestLocation);
        if (requestId !== this.weatherRequestId) return;
        this.weatherPayload = payload;
        this.weatherLastFetchedAt = Date.now();
      } catch (error) {
        if (requestId !== this.weatherRequestId) return;
        console.error(error);
        this.weatherError = error.message || "날씨 정보를 불러오지 못했습니다.";
      } finally {
        if (requestId === this.weatherRequestId) this.weatherLoading = false;
      }
    },
    async setWeatherRegion(region) {
      if (region === "현재 위치") {
        const consentKey = `mindroom-location-consent-${LOCATION_CONSENT_VERSION}`;
        const hasConsent = localStorage.getItem(consentKey) === "true";
        if (!hasConsent) {
          const confirmed = window.confirm(
            "현재 위치의 위도·경도를 날씨 조회에 사용합니다. 좌표는 서버에 저장하지 않고 현재 브라우저 탭에서만 보관하며, 기상청 예보 격자 변환에 사용합니다. 계속할까요?"
          );
          if (!confirmed) return;
          localStorage.setItem(consentKey, "true");
        }
        localStorage.removeItem(MYPAGE_STORAGE_KEYS.weatherLocation);
        await this.loadWeatherData({ force: true, refreshLocation: true });
        return;
      }
      localStorage.removeItem(`mindroom-location-consent-${LOCATION_CONSENT_VERSION}`);
      this.saveWeatherLocation({ mode: "manual", region });
      await this.loadWeatherData({ force: true });
    },
    async loadBookData(force = false) {
      this.bookLoading = true;
      this.bookError = "";
      let forceBool = false;
      let themeParam = null;
      if (typeof force === "object" && force !== null) {
        forceBool = Boolean(force.force);
        themeParam = force.theme || null;
      } else {
        forceBool = Boolean(force);
      }
      try {
        this.bookPayload = await fetchBookRecommendation(forceBool, themeParam);
      } catch (error) {
        console.error(error);
        this.bookError = error.message || "책 추천 정보를 불러오지 못했습니다.";
      } finally {
        this.bookLoading = false;
      }
    },
    async loadMemoryData(force = false) {
      this.memoryLoading = true;
      this.memoryError = "";
      this.memoryNotice = "";
      if (!MEMORY_API_ENABLED) {
        this.memoryPayload = this.createMemoryPreviewPayload();
        this.memoryLoading = false;
        return;
      }
      try {
        this.memoryPayload = await fetchMemoryVault(force);
      } catch (error) {
        console.warn(error);
        if (!this.memoryPayload) {
          this.memoryPayload = this.createMemoryPreviewPayload();
        }
        this.memoryNotice = "기억 API 연결 전이라 미리보기 데이터로 표시합니다.";
      } finally {
        this.memoryLoading = false;
      }
    },
    createMemoryPreviewPayload() {
      return {
        source: "preview",
        preview_label: "기능 미리보기",
        memories: [
          {
            id: "preview-career-worry",
            title: "커리어 전환 고민",
            content: "최근 대화에서 직무 전환과 준비 방향에 대한 고민이 반복적으로 언급되었습니다.",
            saved_at: "2026-07-01T09:00:00+09:00",
            last_used_at: "2026-07-01T09:00:00+09:00",
            is_preview: true
          },
          {
            id: "preview-relationship",
            title: "관계에서 느끼는 부담",
            content: "가까운 관계에서 기대와 거리감 사이를 조절하고 싶다는 이야기가 있었습니다.",
            saved_at: "2026-07-05T14:30:00+09:00",
            last_used_at: "",
            is_preview: true
          },
          {
            id: "preview-routine",
            title: "혼자 정리하는 습관",
            content: "기분이 복잡할 때 산책, 기록, 음악으로 생각을 정리하는 경향이 있습니다.",
            saved_at: "2026-07-10T21:10:00+09:00",
            last_used_at: "2026-07-10T21:10:00+09:00",
            is_preview: true
          },
          {
            id: "preview-first-meeting",
            title: "첫 만남",
            content: "AI와 처음 대화를 나누며 앞으로 어떤 이야기를 기록할지 천천히 살펴보았습니다.",
            saved_at: "2026-07-11T18:20:00+09:00",
            last_used_at: "",
            is_preview: true
          },
          {
            id: "preview-rainy-afternoon",
            title: "비 오는 오후",
            content: "비 내리는 창밖을 떠올리며 복잡했던 마음을 차분하게 정리했습니다.",
            saved_at: "2026-07-12T16:40:00+09:00",
            last_used_at: "",
            is_preview: true
          },
          {
            id: "preview-new-goal",
            title: "새로운 목표",
            content: "부담을 줄이고 매일 조금씩 실천할 수 있는 작은 계획을 세웠습니다.",
            saved_at: "2026-07-13T10:15:00+09:00",
            last_used_at: "",
            is_preview: true
          },
          {
            id: "preview-old-dream",
            title: "잊고 있던 꿈",
            content: "한동안 미뤄두었던 관심사를 다시 시작해 보고 싶은 마음을 이야기했습니다.",
            saved_at: "2026-07-14T20:05:00+09:00",
            last_used_at: "",
            is_preview: true
          },
          {
            id: "preview-evening-walk",
            title: "저녁 산책",
            content: "짧은 산책과 음악으로 하루의 긴장을 풀어내는 나만의 루틴을 정리했습니다.",
            saved_at: "2026-07-15T19:30:00+09:00",
            last_used_at: "",
            is_preview: true
          }
        ]
      };
    },
    async deleteMemoryItems(ids = []) {
      const targetIds = ids.filter(Boolean).map(String);
      if (!targetIds.length) return;
      const previousPayload = this.memoryPayload;
      const isPreview = this.memoryPayload?.source === "preview";
      const idSet = new Set(targetIds);
      const currentMemories = Array.isArray(this.memoryPayload)
        ? this.memoryPayload
        : this.memoryPayload?.memories || this.memoryPayload?.items || [];

      if (Array.isArray(this.memoryPayload)) {
        this.memoryPayload = currentMemories.filter(item => !idSet.has(String(item.id || item.memory_id || item.key)));
      } else {
        this.memoryPayload = {
          ...(this.memoryPayload || {}),
          memories: currentMemories.filter(item => !idSet.has(String(item.id || item.memory_id || item.key)))
        };
      }

      if (isPreview) {
        this.showToast("예시 기억을 목록에서 숨겼습니다. 새로고침하면 다시 표시됩니다.");
        return;
      }

      this.memoryNotice = "";
      try {
        const realIds = targetIds.filter(id => !id.startsWith("preview-"));
        await Promise.all(realIds.map(id => deleteMemoryVaultItem(id)));
        this.showToast(`${targetIds.length}개의 기억을 삭제했습니다.`);
      } catch (error) {
        console.warn(error);
        this.memoryPayload = previousPayload;
        this.memoryError = "삭제 API 호출에 실패했습니다. 잠시 후 다시 시도해주세요.";
      }
    },

    setMbtiView(viewKey) {
      this.mbtiViewMode = viewKey;
    },
    async saveMbti(mbtiType) {
      try {
        await saveOnboardingMbti(mbtiType);
        this.showToast("초기 MBTI가 성공적으로 저장되었습니다.");
        await this.loadMbtiDemoData();
      } catch (e) {
        console.error(e);
        this.showToast("지원하지 않는 MBTI거나 통신 오류가 발생했습니다.");
      }
    },
    async loadMbtiDemoData(force = false) {
      try {
        const payload = await fetchMbtiDemoPayload(force);
        const hasMonthlyAnalysis = this.hasRenderableMonthlyMbtiData(payload.mbti_data);
        const hasOnboardingProfile = this.hasRenderableOnboardingMbtiData(payload.mbti_data);

        this.mbtiData = payload.mbti_data || null;
        if (payload.mbti_data?.onboarding?.type === '----') {
          this.mbtiViewMode = "onboardingType";
        } else if (hasMonthlyAnalysis) {
          this.mbtiViewMode = payload.mbti_view_mode
            || "onboardingNext";
        } else if (hasOnboardingProfile) {
          this.mbtiViewMode = "onboardingType";
        }
        this.mbtiApiStatus = payload.status || "ready";
      } catch (error) {
        console.warn(error);
        this.mbtiApiStatus = "error";
      }
    },
    hasRenderableOnboardingMbtiData(data) {
      return Boolean(
        data &&
        data.onboarding?.type &&
        Array.isArray(data.onboarding.report) &&
        data.onboarding.report.length > 0
      );
    },
    hasRenderableMonthlyMbtiData(data) {
      return Boolean(
        data &&
        data.onboarding?.type &&
        data.previous?.type &&
        data.current?.type &&
        Array.isArray(data.current.axes) &&
        data.current.axes.length > 0 &&
        Array.isArray(data.report) &&
        data.report.length > 0
      );
    },
    async refreshMbtiDemoData() {
      this.showToast("데이터베이스 기반으로 성향 분석을 시작합니다...");
      await this.loadMbtiDemoData(true);
      const message = this.mbtiApiStatus === "error"
        ? "분석 파이프라인 호출에 실패했습니다."
        : this.mbtiApiStatus === "preparing"
          ? "아직 확정된 월간 분석 결과가 없습니다."
          : "성향 분석이 완료되어 결과가 업데이트되었습니다!";
      this.showToast(message);
    },
    applySettings() {
      document.documentElement.dataset.contrast = String(this.settings.highContrast);
      document.documentElement.style.setProperty("--font-scale", this.settings.fontScale);
      localStorage.setItem(MYPAGE_STORAGE_KEYS.settings, JSON.stringify(this.settings));
    },
    showToast(message) {
      this.toast = message;
      window.clearTimeout(this.toastTimer);
      this.toastTimer = window.setTimeout(() => {
        this.toast = "";
      }, MYPAGE_TIMING.toastDurationMs);
    }
  }
};
</script>

<style src="./styles/mypage.css"></style>
