<template>
  <main class="app-shell">
    <MypageRoom :labels="t" @open-panel="openPanel">
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
          :selected-character="selectedCharacter"
          :current-character="currentCharacter"
          :characters="characters"
          :show-character-picker="showCharacterPicker"
          @open-character-picker="showCharacterPicker = true"
          @close-character-picker="showCharacterPicker = false"
          @toggle-profile-edit="toggleProfileEdit"
          @toggle-interest-keyword="toggleInterestKeyword"
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
import { fetchMbtiDemoPayload } from "./mypage.api";
import { createMypageState, i18n } from "./mypage.data";
import MbtiPanel from "./components/MbtiPanel.vue";
import MypageModal from "./components/MypageModal.vue";
import MypageRoom from "./components/MypageRoom.vue";
import ProfilePanel from "./components/ProfilePanel.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import TastePanel from "./components/TastePanel.vue";

export default {
  name: "MypageView",
  components: {
    MbtiPanel,
    MypageModal,
    MypageRoom,
    ProfilePanel,
    SettingsPanel,
    TastePanel
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
        profile: "사전 정보 입력 화면에서 설정한 기본 정보와 관심분야 키워드를 조회하고, 수정합니다.",
        mbti: "지난 한 달간 저장된 MBTI 질문·답변을 바탕으로 이번 달 추정 MBTI, 4개 선호 지표 비율, 전월 대비 변화 경향과 근거 리포트를 보여줍니다. 공식 성격 검사가 아닌 보조 분석 결과입니다.",
        taste: "최근 30일 대화 로그에서 반복적으로 나타난 관심사·취향 키워드를 집계해 보여줍니다. 일정 횟수 이상 등장한 키워드만 대시보드에 표시됩니다.",
        settings: "계정 기본 정보와 언어, 접근성 설정을 관리합니다."
      };
      return descriptions[this.activePanel] || "";
    },
    currentCharacter() {
      return this.characters.find(character => character.id === this.selectedCharacter);
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
  },
  methods: {
    openPanel(panel) {
      this.activePanel = panel;
      this.showCharacterPicker = false;
      if (panel === "mbti") {
        this.loadMbtiDemoData();
      }
    },
    closePanel() {
      this.activePanel = null;
      this.showCharacterPicker = false;
    },
    toggleProfileEdit() {
      if (this.profileEdit) {
        this.profileSavedAt = new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });
        this.showToast("프로필 수정 내용이 저장된 것처럼 반영되었습니다.");
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
    chooseCharacter(id) {
      this.selectedCharacter = id;
      this.showCharacterPicker = false;
      this.showToast("대화 대상 캐릭터가 교체되었습니다.");
    },
    setMbtiView(viewKey) {
      this.mbtiViewMode = viewKey;
      this.showToast(`예시 화면: ${this.currentMbtiView.title} 화면으로 전환했습니다.`);
    },
    async loadMbtiDemoData() {
      try {
        const payload = await fetchMbtiDemoPayload();
        const hasMonthlyAnalysis = this.hasRenderableMonthlyMbtiData(payload.mbti_data);
        const hasOnboardingProfile = this.hasRenderableOnboardingMbtiData(payload.mbti_data);

        if (hasMonthlyAnalysis || hasOnboardingProfile) {
          this.mbtiData = payload.mbti_data;
        }
        if (hasMonthlyAnalysis) {
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
      await this.loadMbtiDemoData();
      const message = this.mbtiApiStatus === "demo-fallback"
        ? "데모 결과 API를 불러오지 못해 기존 예시를 유지합니다."
        : "데모 결과를 다시 불러왔습니다.";
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
