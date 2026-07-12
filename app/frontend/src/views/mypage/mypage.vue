<template>
  <main class="app-shell">
    <MypageRoom :labels="t" :current-character="currentCharacter" @open-panel="openPanel">
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

        <WardrobePanel
          v-if="activePanel === 'wardrobe'"
          :payload="wardrobePayload"
          :loading="wardrobeLoading"
          :error="wardrobeError"
          @refresh="loadWardrobeData"
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
    </MypageRoom>

    <transition name="fade">
      <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    </transition>
  </main>
</template>

<script>
import { fetchCurrentWeather, fetchMbtiDemoPayload, fetchMyProfile, fetchWardrobeRecommendation, updateMyProfile, saveOnboardingMbti } from "./mypage.api";
import { createMypageState, i18n } from "./mypage.data";
import CharacterPanel from "./components/CharacterPanel.vue";
import MbtiPanel from "./components/MbtiPanel.vue";
import MypageModal from "./components/MypageModal.vue";
import MypageRoom from "./components/MypageRoom.vue";
import ProfilePanel from "./components/ProfilePanel.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import TastePanel from "./components/TastePanel.vue";
import WeatherPanel from "./components/WeatherPanel.vue";
import WardrobePanel from "./components/WardrobePanel.vue";

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
    WardrobePanel
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
      if (this.activePanel === "wardrobe") {
        return "최근 대화의 감정 흐름과 프로필 취향을 바탕으로 오늘 입기 편한 옷차림을 추천합니다.";
      }
      const descriptions = {
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
    }
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
      this.activePanel = panel;
      if (panel === "mbti") {
        this.loadMbtiDemoData();
      }
      if (panel === "weather") {
        this.loadWeatherData();
      }
      if (panel === "wardrobe") {
        this.loadWardrobeData();
      }
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
    async loadWardrobeData() {
      this.wardrobeLoading = true;
      this.wardrobeError = "";
      try {
        this.wardrobePayload = await fetchWardrobeRecommendation();
      } catch (error) {
        console.error(error);
        this.wardrobeError = error.message || "옷장 추천을 불러오지 못했습니다.";
      } finally {
        this.wardrobeLoading = false;
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
