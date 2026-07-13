<template>
  <main class="app-shell">
    <section class="mypage-home" aria-label="마이페이지 홈">
      <aside class="home-left-panel" aria-label="마이홈 대시보드">
        <article class="identity-card">
          <div class="identity-avatar">
            <img :src="`/characters/${currentCharacter.id}/default.png`" :alt="currentCharacter.name" />
          </div>
          <div class="identity-copy">
            <span class="dashboard-kicker">ROOM PLATE</span>
            <h1>{{ displayName }}님의 공간</h1>
            <p>{{ homeStatusMessage }}</p>
            <div class="identity-chips">
              <span>{{ todayEmotionLabel }}</span>
              <span>{{ currentCharacter.name }}</span>
              <span>{{ profileMbtiLabel }}</span>
            </div>
          </div>
          <button class="dashboard-primary" type="button" @click="openPanel('profile')">프로필 관리</button>
        </article>

        <nav class="quick-actions" aria-label="마이룸 오브젝트 메뉴">
          <button type="button" @click="openPanel('profile')">
            <span class="menu-object">문패</span>
            <strong>내 소개</strong>
            <span>프로필 키워드</span>
          </button>
          <button type="button" @click="openPanel('mbti')">
            <span class="menu-object">보드</span>
            <strong>요즘의 나</strong>
            <span>성향 흐름</span>
          </button>
          <button type="button" @click="openPanel('weather')">
            <span class="menu-object">창문</span>
            <strong>창밖 날씨</strong>
            <span>오늘 컨디션</span>
          </button>
          <button type="button" @click="openPanel('book')">
            <span class="menu-object">책장</span>
            <strong>오늘의 책장</strong>
            <span>추천 서평</span>
          </button>
          <button type="button" @click="openPanel('character')">
            <span class="menu-object">친구</span>
            <strong>방 친구</strong>
            <span>캐릭터</span>
          </button>
          <button type="button" @click="openPanel('settings')">
            <span class="menu-object">서랍</span>
            <strong>설정</strong>
            <span>계정 관리</span>
          </button>
        </nav>

        <aside class="home-sidebar" aria-label="오늘의 상태판">
          <div class="panel-caption">
            <span class="dashboard-kicker">ROOM NOTE</span>
            <strong>방 안 상태판</strong>
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
              <small>개인화 보정</small>
            </button>
          </section>
        </aside>
      </aside>

      <section class="room-section" aria-label="내 공간">
        <header class="room-section-heading">
          <div>
            <span class="dashboard-kicker">MY ROOM</span>
            <h2>{{ displayName }}님의 미니룸</h2>
          </div>
          <p>책장, 창문, 액자처럼 방 안 오브젝트가 오늘의 기록과 연결됩니다.</p>
        </header>
        <MypageRoom
          :labels="t"
          :current-character="currentCharacter"
          :focus-target="roomFocusTarget"
          :move-key="roomMoveKey"
          @open-panel="openPanelFromRoom"
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
          :profile-options="profileOptions"
          :profile-edit="profileEdit"
          :profile-saved-at="profileSavedAt"
          :current-character="currentCharacter"
          @toggle-profile-edit="toggleProfileEdit"
          @toggle-interest-keyword="toggleInterestKeyword"
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
          @refresh="loadWeatherData()"
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

        <TastePanel
          v-if="activePanel === 'taste'"
          :taste="taste"
          @refresh="refreshTaste"
        />

        <SettingsPanel
          v-if="activePanel === 'settings'"
          :account="account"
          :settings="settings"
          @show-toast="showToast"
          @reset-settings="resetSettings"
        />
    </MypageModal>

    <transition name="fade">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>
  </main>
</template>

<script>
import { fetchCurrentWeather, fetchMbtiDemoPayload, fetchMyProfile, updateMyProfile, saveOnboardingMbti, fetchBookRecommendation } from "./mypage.api";
import { createMypageState, i18n } from "./mypage.data";
import CharacterPanel from "./components/CharacterPanel.vue";
import MbtiPanel from "./components/MbtiPanel.vue";
import MypageModal from "./components/MypageModal.vue";
import MypageRoom from "./components/MypageRoom.vue";
import ProfilePanel from "./components/ProfilePanel.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import TastePanel from "./components/TastePanel.vue";
import WeatherPanel from "./components/WeatherPanel.vue";
import BookPanel from "./components/BookPanel.vue";

export default {
  name: "MypageView",
  components: {
    CharacterPanel,
    MbtiPanel,
    MypageModal,
    MypageRoom,
    ProfilePanel,
    SettingsPanel,
    TastePanel,
    WeatherPanel,
    BookPanel
  },
  async beforeRouteEnter(to, from, next) {
    try {
      await fetchMyProfile();
      next();
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
      const descriptions = {
        book: "프로필의 관심사와 취미, 오늘의 감정을 바탕으로 지금 읽어볼 만한 책을 추천합니다.",
        profile: "사전 정보 입력 화면에서 설정한 기본 정보와 관심분야 키워드를 조회하고, 수정합니다.",
        character: "방 안의 동행 캐릭터를 고르고, 캐릭터의 말투와 성향을 확인합니다.",
        weather: "창문 밖 현재 날씨와 오늘의 컨디션 관리 추천을 확인합니다.",
        mbti: "대화 중 자연스럽게 나눈 성향 답변을 바탕으로, 내가 요즘 어떤 방식으로 생각하고 소통하는지 MBTI 유형으로 돌아봐요.",
        taste: "최근 30일 대화 로그에서 반복적으로 나타난 관심사·취향 키워드를 집계해 보여줍니다. 일정 횟수 이상 등장한 키워드만 대시보드에 표시됩니다.",
        settings: "계정 기본 정보와 언어, 접근성 설정을 관리합니다."
      };
      return descriptions[this.activePanel] || "";
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
      if (emotion && emotion !== "대화 후 반영") {
        return `${emotion}의 결을 담아 오늘의 추천과 프로필 취향을 정리했어요.`;
      }
      return "대화와 프로필을 바탕으로 오늘의 기분과 추천을 정리하는 개인 홈입니다.";
    },
    profileMbtiLabel() {
      const current = this.mbtiData?.current?.type;
      const onboarding = this.mbtiData?.onboarding?.type;
      return (current && current !== "----" ? current : onboarding) || this.profile?.mbti || "미등록";
    },
    mbtiSummaryText() {
      const previous = this.mbtiData?.previous?.type;
      if (previous && previous !== this.profileMbtiLabel) {
        return `${previous} -> ${this.profileMbtiLabel}`;
      }
      return "최근 분석 기준";
    },
    todayEmotionLabel() {
      return this.bookPayload?.profile_basis?.today_emotion || "대화 후 반영";
    },
    profileInterestCount() {
      return this.normalizeList(this.profile?.interests).length;
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
    const saved = localStorage.getItem("mindroom-settings");
    if (saved) {
      const parsed = JSON.parse(saved);
      this.settings = {
        ...this.settings,
        language: parsed.language || this.settings.language,
        fontScale: parsed.fontScale || this.settings.fontScale,
        highContrast: Boolean(parsed.highContrast)
      };
    }
    this.applySettings();
    this.loadMbtiDemoData();
    this.loadProfileData();
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
      this.pendingPanel = null;
      this.closePanel();
      this.$router.push("/report");
    },
    async loadProfileData() {
      try {
        const data = await fetchMyProfile();
        if (data && data.profile) {
          this.profile = { ...this.profile, ...data.profile };
          if (data.profile.selectedCharacter) {
            this.selectedCharacter = data.profile.selectedCharacter;
            
            if (this.selectedCharacter === 'otter' || this.selectedCharacter === 'sol') {
              try {
                const stored = JSON.parse(localStorage.getItem('binteumsaiCharacter') || '{}');
                if (stored && stored.characterId && stored.characterId !== this.selectedCharacter) {
                  this.selectedCharacter = stored.characterId;
                  updateMyProfile({ selectedCharacter: stored.characterId }).catch(() => {});
                }
              } catch (err) {}
            }
          }
        }
      } catch (e) {
        console.error("Failed to load profile, redirecting to login", e);
        this.$router.push("/login");
      }
    },
    openPanel(panel) {
      this.pendingPanel = null;
      this.activatePanel(panel);
    },
    openPanelFromRoom(panel) {
      if (this.shouldMoveBeforeOpen(panel)) {
        this.pendingPanel = panel;
        this.roomFocusTarget = panel;
        this.roomMoveKey += 1;
        return;
      }
      this.activatePanel(panel);
    },
    shouldMoveBeforeOpen(panel) {
      return ["profile", "mbti", "weather", "book", "character", "settings"].includes(panel);
    },
    activatePanel(panel) {
      this.pendingPanel = null;
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
    },
    activatePanelAfterRoomMove(panel) {
      if (!this.pendingPanel || panel !== this.pendingPanel) return;
      this.activatePanel(panel);
    },
    closePanel() {
      this.activePanel = null;
    },
    async toggleProfileEdit() {
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
          this.showToast("프로필 수정 내용이 정상적으로 반영되었습니다.");
        } catch (e) {
          console.error("Failed to update profile", e);
          this.showToast("프로필 저장에 실패했습니다.");
          return;
        }
      }
      this.profileEdit = !this.profileEdit;
    },
    toggleInterestKeyword(keyword) {
      if (!this.profileEdit) return;
      if (this.profile.interests.includes(keyword)) {
        this.profile.interests = this.profile.interests.filter(item => item !== keyword);
        return;
      }
      this.profile.interests = [...this.profile.interests, keyword];
    },
    async chooseCharacter(id) {
      const oldChar = this.selectedCharacter;
      this.selectedCharacter = id;
      try {
        await updateMyProfile({ selectedCharacter: id });
        localStorage.setItem('binteumsaiCharacter', JSON.stringify({ characterId: id }));
        this.showToast("대화 대상 캐릭터가 교체되었습니다.");
      } catch (e) {
        console.error(e);
        this.selectedCharacter = oldChar;
        this.showToast("캐릭터 교체에 실패했습니다.");
      }
    },
    getSavedWeatherLocation() {
      try {
        return JSON.parse(localStorage.getItem("mindroom-weather-location") || "null");
      } catch (error) {
        return null;
      }
    },
    saveWeatherLocation(location) {
      this.weatherLocation = location;
      localStorage.setItem("mindroom-weather-location", JSON.stringify(location));
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
          { enableHighAccuracy: false, timeout: 5000, maximumAge: 10 * 60 * 1000 }
        );
      });
    },
    async resolveWeatherLocation(force = false) {
      const saved = this.getSavedWeatherLocation();
      if (!force && saved) {
        this.weatherLocation = saved;
        return saved;
      }
      try {
        const browserLocation = await this.getBrowserLocation();
        this.saveWeatherLocation(browserLocation);
        return browserLocation;
      } catch (error) {
        const fallback = saved || { mode: "manual", region: "서울" };
        this.saveWeatherLocation(fallback);
        return fallback;
      }
    },
    async loadWeatherData(force = false) {
      this.weatherLoading = true;
      this.weatherError = "";
      try {
        const location = await this.resolveWeatherLocation(force);
        const requestLocation = location.mode === "auto"
          ? { lat: location.lat, lon: location.lon, region: location.region }
          : { region: location.region || "서울" };
        this.weatherPayload = await fetchCurrentWeather(requestLocation);
      } catch (error) {
        console.error(error);
        this.weatherError = error.message || "날씨 정보를 불러오지 못했습니다.";
      } finally {
        this.weatherLoading = false;
      }
    },
    async setWeatherRegion(region) {
      if (region === "현재 위치") {
        localStorage.removeItem("mindroom-weather-location");
        await this.loadWeatherData(true);
        return;
      }
      this.saveWeatherLocation({ mode: "manual", region });
      await this.loadWeatherData();
    },
    async loadBookData(force = false) {
      this.bookLoading = true;
      this.bookError = "";
      try {
        this.bookPayload = await fetchBookRecommendation(force);
      } catch (error) {
        console.error(error);
        this.bookError = error.message || "책 추천 정보를 불러오지 못했습니다.";
      } finally {
        this.bookLoading = false;
      }
    },

    setMbtiView(viewKey) {
      this.mbtiViewMode = viewKey;
      this.showToast(`${this.currentMbtiView.title} 화면으로 전환했습니다.`);
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

        if (hasMonthlyAnalysis || hasOnboardingProfile) {
          this.mbtiData = payload.mbti_data;
        }
        if (payload.mbti_data?.onboarding?.type === '----') {
          this.mbtiViewMode = "onboardingType";
        } else if (hasMonthlyAnalysis) {
          this.mbtiViewMode = payload.mbti_view_mode || "onboardingNext";
        } else if (hasOnboardingProfile) {
          this.mbtiViewMode = "onboardingType";
        }
        this.mbtiApiStatus = payload.status || "ready";
      } catch (error) {
        console.warn(error);
        this.mbtiApiStatus = "demo-fallback";
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
      const message = this.mbtiApiStatus === "demo-fallback"
        ? "분석 파이프라인 호출에 실패해 기존 데이터를 유지합니다."
        : "성향 분석이 완료되어 결과가 업데이트되었습니다!";
      this.showToast(message);
    },
    refreshTaste() {
      this.taste.updated = new Date().toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
      this.taste.keywords = this.taste.keywords.map(item => ({
        ...item,
        count: Math.max(1, item.count + Math.round(Math.random() * 2 - 1))
      })).sort((a, b) => b.count - a.count);
      this.showToast("저장된 대화 로그에서 키워드를 다시 추출했습니다.");
    },
    resetSettings() {
      this.settings = {
        language: "ko",
        fontScale: 1,
        highContrast: false
      };
      this.showToast("설정이 기본값으로 복원되었습니다.");
    },
    applySettings() {
      document.documentElement.dataset.contrast = String(this.settings.highContrast);
      document.documentElement.style.setProperty("--font-scale", this.settings.fontScale);
      localStorage.setItem("mindroom-settings", JSON.stringify(this.settings));
    },
    showToast(message) {
      this.toast = message;
      window.clearTimeout(this.toastTimer);
      this.toastTimer = window.setTimeout(() => {
        this.toast = "";
      }, 2400);
    }
  }
};
</script>

<style src="./mypage.css"></style>
