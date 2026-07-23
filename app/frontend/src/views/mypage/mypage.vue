<template>
  <main class="app-shell">
    <section class="mypage-home" aria-label="마이페이지 홈">
      <aside class="home-left-panel" aria-label="마이홈 대시보드">
        <article class="identity-card">
          <div class="identity-avatar-block">
            <div class="identity-avatar">
              <img :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
            </div>
            <small class="identity-character-name">{{ currentCharacter.name }}</small>
          </div>
          <div class="identity-copy">
            <span class="dashboard-kicker">나의 오늘</span>
            <h1>{{ displayName }}님의 공간</h1>
            <div class="identity-chips" aria-label="나의 관심사와 취미">
              <span class="identity-chip-mbti">{{ profileMbtiLabel }}</span>
              <span v-for="chip in tasteSummaryChips" :key="chip.type" :class="`identity-chip-${chip.type}`">
                <i v-if="chip.icon" class="identity-chip-icon" aria-hidden="true">{{ chip.icon }}</i>
                <b>{{ chip.caption }}</b>{{ chip.label }}
              </span>
            </div>
          </div>
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

        <aside class="home-sidebar" aria-labelledby="home-summary-title">
          <header class="panel-caption memory-dashboard-caption">
            <div>
              <h2 id="home-summary-title">오늘의 기억 요약</h2>
              <small v-if="memoryDashboard.count">많이 언급된 항목 TOP 3</small>
            </div>
            <button type="button" @click="openMemoryPanel()">보관함 열기 <span aria-hidden="true">→</span></button>
          </header>
          <section class="memory-dashboard" aria-label="기억을 구조화한 오늘의 요약">
            <div v-if="memoryLoading && !memoryDashboard.count" class="memory-dashboard-state">기억을 차분히 정리하고 있어요...</div>
            <template v-else>
              <div
                v-if="memoryDashboard.events.length || memoryDashboard.people.length || memoryDashboard.preferences.length"
                class="memory-dashboard-facts"
              >
                <div v-if="memoryDashboard.events.length">
                  <span>사건</span>
                  <div class="memory-dashboard-tags">
                    <strong v-for="event in memoryDashboard.events" :key="event">{{ event }}</strong>
                  </div>
                </div>
                <div v-if="memoryDashboard.people.length">
                  <span>인물</span>
                  <div class="memory-dashboard-tags">
                    <strong v-for="person in memoryDashboard.people" :key="person">{{ person }}</strong>
                  </div>
                </div>
                <div v-if="memoryDashboard.preferences.length">
                  <span>취향</span>
                  <div class="memory-dashboard-tags">
                    <strong v-for="preference in memoryDashboard.preferences" :key="preference">{{ preference }}</strong>
                  </div>
                </div>
              </div>

              <button v-if="memoryDashboard.latest" class="memory-dashboard-latest" type="button" @click="openMemoryPanel(memoryDashboard.latest.id)">
                <span>가장 최근 기억</span>
                <strong>{{ memoryDashboard.latest.title }}</strong>
                <small>{{ memoryDashboard.latest.savedAt || '대화에서 저장됨' }}</small>
              </button>
              <button v-else class="memory-dashboard-empty-action" type="button" @click="goToChat">
                오늘 기억된 내용이 없어요 <br /> 대화하러 가기 <span aria-hidden="true">→</span>
              </button>
            </template>
          </section>
        </aside>
      </aside>

      <section class="room-section" aria-label="내 공간">
        <header class="room-section-heading">
          <div>
            <span class="dashboard-kicker">나의 공간</span>
            <h2>{{ displayName }}님의 미니룸</h2>
          </div>
          <button class="dashboard-primary room-profile-button" type="button" @click="openPanel('profile')">
            프로필 관리
            <span aria-hidden="true">↗</span>
          </button>
        </header>
        <MypageRoom
          :labels="t"
          :current-character="currentCharacter"
          :focus-target="roomFocusTarget"
          :move-key="roomMoveKey"
          @open-panel="openPanelFromRoom"
          @open-chat="goToChat"
          @open-report="goToReport"
          @arrived="activatePanelAfterRoomMove"
          @movement-interrupted="cancelPendingRoomAction"
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

        <MbtiPanel
          v-if="activePanel === 'mbti'"
          :mbti-data="mbtiData"
          :mbti-view-mode="mbtiViewMode"
          :mbti-views="mbtiViews"
          :current-mbti-view="currentMbtiView"
          :analysis-eligibility="mbtiAnalysisEligibility"
          :analysis-polling="mbtiAnalysisPolling"
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
          @refresh="loadWeatherData({ force: true, rotateHobby: true })"
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
          :initial-selected-id="memorySelectedId"
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
import { fetchCurrentWeather, fetchMbtiDemoPayload, requestMbtiMonthlyAnalysis, fetchMyProfile, fetchTodayEmotion, updateMyProfile, saveOnboardingMbti, fetchBookRecommendation, fetchMemoryVault, deleteMemoryVaultItem, fetchWeatherRegions } from "./mypage.api";
import { userApi } from "../../api/user.js";
import { LOCATION_CONSENT_VERSION } from "../../constants/consentVersions";
import { createMypageState, i18n } from "./state/mypage.state";
import {
  DEFAULT_WEATHER_REGION,
  MOVABLE_PANEL_IDS,
  MYPAGE_STORAGE_KEYS,
  MYPAGE_TIMING,
  NAVIGATION_CONFIRM_OPTIONS,
  PANEL_DESCRIPTIONS,
} from "./config/mypage.constants";
import CharacterPanel from "./components/CharacterPanel.vue";
import MbtiPanel from "./components/MbtiPanel.vue";
import MypageModal from "./components/MypageModal.vue";
import MypageRoom from "./components/MypageRoom.vue";
import ProfilePanel from "./components/ProfilePanel.vue";
import WeatherPanel from "./components/WeatherPanel.vue";
import BookPanel from "./components/BookPanel.vue";
import MemoryPanel from "./components/MemoryPanel.vue";
import { buildMemoryDashboard } from "./utils/memory.dashboard";
import { getKeywordIcon } from "../../constants/keywordIcons.js";

export default {
  name: "MypageView",
  components: {
    CharacterPanel,
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
        return "대화에서 저장된 기억을 확인하고 직접 관리할 수 있어요.";
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
      if (this.todayEmotionLoading) return "확인 중";
      if (this.todayEmotionError) return "확인 불가";
      return this.todayEmotionPayload?.representative?.label || "아직 기록 없음";
    },
    tasteSummaryChips() {
      const chips = [
        {
          type: "interest",
          caption: "관심 · ",
          values: this.normalizeList(this.profile?.interests),
        },
        {
          type: "hobby",
          caption: "취미 · ",
          values: this.normalizeList(this.profile?.hobbies),
        },
      ];

      return chips.map((chip) => ({
        ...chip,
        icon: chip.values.length ? getKeywordIcon(chip.values[0], chip.type) : "",
        label: this.previewList(chip.values, "미등록"),
      }));
    },
    memoryDashboard() {
      return buildMemoryDashboard(this.memoryPayload);
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
    this.loadTodayEmotion();
    this.loadMbtiDemoData();
    this.loadMemoryData();
    this.loadWeatherRegions();
    this.weatherRefreshTimer = window.setInterval(() => {
      if (this.activePanel === "weather") this.loadWeatherData();
    }, MYPAGE_TIMING.weatherRefreshIntervalMs);
  },
  beforeUnmount() {
    this.mbtiPollToken += 1;
    if (this.weatherRefreshTimer) window.clearInterval(this.weatherRefreshTimer);
    if (this.toastTimer) window.clearTimeout(this.toastTimer);
  },
  methods: {
    async loadTodayEmotion() {
      this.todayEmotionLoading = true;
      this.todayEmotionError = "";
      try {
        this.todayEmotionPayload = await fetchTodayEmotion();
      } catch (error) {
        console.warn("Failed to load today's emotion:", error);
        this.todayEmotionPayload = null;
        this.todayEmotionError = error.message || "오늘의 감정을 불러오지 못했습니다.";
      } finally {
        this.todayEmotionLoading = false;
      }
    },
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
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = true;
      this.roomFocusTarget = "wardrobe";
      this.roomMoveKey += 1;
    },
    goToChat() {
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
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      this.activatePanel(panel);
    },
    openPanelFromRoom(panel) {
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
    openMemoryPanel(memoryId = "") {
      this.memorySelectedId = memoryId;
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
      this.activatePanel("memory");
    },
    cancelPendingRoomAction() {
      this.pendingPanel = null;
      this.pendingChatNavigation = false;
      this.pendingReportNavigation = false;
    },
    shouldMoveBeforeOpen(panel) {
      return MOVABLE_PANEL_IDS.includes(panel);
    },
    activatePanel(panel) {
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
      this.memorySelectedId = "";
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
        try {
          const updatedUser = await userApi.getCurrentUser();
          window.dispatchEvent(new CustomEvent("binteumsai-auth-changed", { detail: { user: updatedUser } }));
        } catch (authErr) {
          console.warn("Failed to refresh user after character update", authErr);
        }
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
    weatherLocalDateKey() {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, "0");
      const day = String(now.getDate()).padStart(2, "0");
      return `${year}-${month}-${day}`;
    },
    requestWeatherLocationConsent() {
      const consentKey = `mindroom-location-consent-${LOCATION_CONSENT_VERSION}`;
      if (localStorage.getItem(consentKey) === "true") return true;
      const confirmed = window.confirm(
        "현재 위치의 위도·경도를 날씨 조회에 사용합니다. 좌표는 서버에 저장하지 않고 현재 브라우저 탭에서만 보관하며, 기상청 예보 격자 변환에 사용합니다. 계속할까요?"
      );
      if (confirmed) localStorage.setItem(consentKey, "true");
      return confirmed;
    },
    async resolveWeatherLocation(force = false) {
      let saved = this.getSavedWeatherLocation();
      const today = this.weatherLocalDateKey();
      const dailyLocationDate = localStorage.getItem(
        MYPAGE_STORAGE_KEYS.weatherDailyLocationDate
      );
      if (!force && dailyLocationDate !== today) {
        // 하루의 첫 날씨 진입에서는 이전 수동 선택보다 현재 위치를 먼저 시도한다.
        // 거부·실패 후 패널을 다시 열 때마다 권한 창이 반복되지 않도록 시도 날짜를 기록한다.
        localStorage.setItem(MYPAGE_STORAGE_KEYS.weatherDailyLocationDate, today);
        if (this.requestWeatherLocationConsent()) {
          try {
            const browserLocation = await this.getBrowserLocation();
            this.saveWeatherLocation(browserLocation);
            return browserLocation;
          } catch (error) {
            console.warn("Failed to resolve today's browser location:", error);
          }
        }
        sessionStorage.removeItem(MYPAGE_STORAGE_KEYS.weatherAutoLocation);
        saved = this.getSavedWeatherLocation();
      }
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
    async loadWeatherData({ force = false, refreshLocation = false, rotateHobby = false } = {}) {
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
        const payload = await fetchCurrentWeather(requestLocation, { rotateHobby });
        if (requestId !== this.weatherRequestId) return;
        this.weatherPayload = payload;
        this.weatherLastFetchedAt = Date.now();
      } catch (error) {
        if (requestId !== this.weatherRequestId) return;
        console.error(error);
        this.weatherError = error.message || "날씨 정보를 불러오지 못했습니다.";
      } finally {
        if (requestId === this.weatherRequestId) {
          this.weatherLoading = false;
        }
      }
    },
    async setWeatherRegion(region) {
      if (region === "현재 위치") {
        if (!this.requestWeatherLocationConsent()) return;
        localStorage.setItem(
          MYPAGE_STORAGE_KEYS.weatherDailyLocationDate,
          this.weatherLocalDateKey()
        );
        localStorage.removeItem(MYPAGE_STORAGE_KEYS.weatherLocation);
        await this.loadWeatherData({ force: true, refreshLocation: true });
        return;
      }
      localStorage.removeItem(`mindroom-location-consent-${LOCATION_CONSENT_VERSION}`);
      this.saveWeatherLocation({ mode: "manual", region });
      await this.loadWeatherData({ force: true });
    },
    async loadBookData(force = false) {
      let forceBool = false;
      let themeParam = null;
      if (typeof force === "object" && force !== null) {
        forceBool = Boolean(force.force);
        themeParam = force.theme || null;
      } else {
        forceBool = Boolean(force);
      }
      if (!forceBool && this.bookPayload) return;

      this.bookLoading = true;
      this.bookError = "";
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
      try {
        const payload = await fetchMemoryVault(force);
        this.memoryPayload = payload || { memories: [] };
      } catch (error) {
        console.warn(error);
        if (!this.memoryPayload) {
          this.memoryPayload = { memories: [] };
        }
        this.memoryError = error.message || "기억 정보를 불러오지 못했습니다.";
      } finally {
        this.memoryLoading = false;
      }
    },
    async deleteMemoryItems(ids = []) {
      const targetIds = ids.filter(Boolean).map(String);
      if (!targetIds.length) return;
      const previousPayload = this.memoryPayload;
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

      this.memoryNotice = "";
      try {
        await Promise.all(targetIds.map(id => deleteMemoryVaultItem(id)));
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
        const payload = await this.loadMbtiDemoData();
        const savedType = payload?.mbti_data?.onboarding?.type;
        if (savedType && savedType !== "----") {
          this.mbtiViewMode = "onboardingNext";
        }
      } catch (e) {
        console.error(e);
        this.showToast("지원하지 않는 MBTI거나 통신 오류가 발생했습니다.");
      }
    },
    async loadMbtiDemoData(force = false, periodKey = "") {
      try {
        const payload = await fetchMbtiDemoPayload(force, periodKey);
        const hasMonthlyAnalysis = this.hasRenderableMonthlyMbtiData(payload.mbti_data);
        const hasOnboardingProfile = this.hasRenderableOnboardingMbtiData(payload.mbti_data);

        this.mbtiData = payload.mbti_data || null;
        this.mbtiAnalysisEligibility = payload.analysis_eligibility || null;
        if (payload.mbti_data?.onboarding?.type === '----') {
          this.mbtiViewMode = "onboardingType";
        } else if (hasMonthlyAnalysis || hasOnboardingProfile) {
          this.mbtiViewMode = payload.mbti_view_mode
            || "onboardingNext";
        }
        this.mbtiApiStatus = payload.status || "ready";
        return payload;
      } catch (error) {
        console.warn(error);
        this.mbtiApiStatus = "error";
        return null;
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
      if (this.mbtiAnalysisPolling) return;
      this.showToast("성향 분석을 요청하고 있습니다...");
      try {
        const requestPayload = await requestMbtiMonthlyAnalysis();
        const periodKey = requestPayload?.analysis_job?.period_key || "";
        let finalPayload = requestPayload;
        const requestedStatus = requestPayload?.analysis_job?.status;

        if (["pending", "running"].includes(requestedStatus)) {
          this.mbtiAnalysisPolling = true;
          const pollToken = ++this.mbtiPollToken;
          this.showToast("분석 요청이 접수되었습니다. 결과를 만드는 중입니다...");
          finalPayload = await this.pollMbtiAnalysis(periodKey, pollToken) || requestPayload;
        } else {
          finalPayload = await this.loadMbtiDemoData(false, periodKey) || requestPayload;
        }

        const jobStatus = finalPayload?.analysis_job?.status || requestedStatus;
        const message = finalPayload.status === "not_eligible" || requestPayload.status === "not_eligible"
          ? "분석에 필요한 답변이 아직 충분하지 않습니다."
          : jobStatus === "completed"
            ? "성향 분석 결과가 최신 상태입니다."
            : ["failed", "skipped"].includes(jobStatus)
              ? "분석 작업에 실패했습니다. 잠시 후 다시 시도해주세요."
              : "분석이 계속 진행 중입니다. 잠시 후 다시 확인해주세요.";
        this.showToast(message);
      } catch (error) {
        console.warn(error);
        this.mbtiApiStatus = "error";
        this.showToast("분석 요청에 실패했습니다.");
      } finally {
        this.mbtiAnalysisPolling = false;
      }
    },
    async pollMbtiAnalysis(periodKey, pollToken) {
      const maxAttempts = 30;
      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        if (pollToken !== this.mbtiPollToken) return null;

        const payload = await this.loadMbtiDemoData(false, periodKey);
        const jobStatus = payload?.analysis_job?.status;
        if (["completed", "failed", "skipped"].includes(jobStatus)) {
          return payload;
        }
      }
      return this.loadMbtiDemoData(false, periodKey);
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
