<template>
  <div class="panel-body">
    <div v-if="mbtiViewMode === 'onboardingNext' && !isMonthlyPreparing" class="actions mbti-refresh-actions">
      <button class="secondary-button" type="button" @click="$emit('refresh')">
        분석 결과 새로고침
      </button>
    </div>

    <aside class="mbti-disclaimer" role="note">
      MBTI는 대화와 사용자가 입력한 정보를 바탕으로 살펴본 성향입니다. 전문적인 심리검사나 진단 결과가 아니며, 상황에 따라 달라질 수 있어요.
    </aside>

    <template v-if="mbtiViewMode === 'onboardingType'">
      <div class="mbti-dashboard mbti-dashboard-single">
        <section class="mbti-result-board mbti-onboarding-board">
          <div>
            <span class="mbti-kicker">온보딩 MBTI 유형</span>
            <template v-if="!onboardingData || onboardingData.type === '----'">
              <div class="mbti-input-area">
                <div class="mbti-grid">
                  <button
                    v-for="type in mbtiOptions"
                    :key="type"
                    class="mbti-option-button"
                    :class="{ active: newMbti === type }"
                    type="button"
                    @click="newMbti = type"
                  >
                    {{ type }}
                  </button>
                </div>
                <button class="primary-button mbti-save-button" @click="saveMbti" type="button" :disabled="!newMbti">선택 완료</button>
              </div>
            </template>
            <template v-else>
              <div class="mbti-type">{{ onboardingData.type }}</div>
            </template>
            <div v-if="onboardingData" class="mbti-confidence">{{ onboardingData.period }}</div>
          </div>
        </section>
        <section v-if="onboardingData" class="card report-panel mbti-type-description">
          <h3>온보딩 MBTI 유형 설명</h3>
          <p>{{ onboardingData.description }}</p>
          <ol class="report-lines compact-report">
            <li v-for="line in onboardingData.report" :key="line">{{ line }}</li>
          </ol>
        </section>
      </div>
    </template>

    <template v-else-if="mbtiViewMode === 'onboardingNext'">
      <section v-if="isMonthlyPreparing" class="card mbti-empty-state" role="status">
        <span class="mbti-kicker">월간 분석</span>
        <h3>아직 월간 성향을 보여드릴 만큼 대화가 쌓이지 않았어요.</h3>
        <p>대화 기반 응답이 충분해지면 네 가지 선호 지표와 변화 이유를 이 화면에서 확인할 수 있어요.</p>
        <div class="mbti-empty-baseline">
          <span>현재 참고 기준</span>
          <strong>{{ onboardingData?.type || '미등록' }}</strong>
          <small>{{ onboardingData ? '온보딩에서 직접 입력한 유형' : '온보딩 MBTI를 먼저 등록해주세요.' }}</small>
        </div>
      </section>

      <section v-else class="card mbti-combined-card">

        <div class="mbti-combined-grid">
          <div class="mbti-type-stack">
            <article class="mbti-type-panel current">
              <span>현재 기준 MBTI</span>
              <strong class="mbti-letter-row">
                <span
                  v-for="(letter, index) in currentTypeLetters"
                  :key="letter + index"
                  class="mbti-type-letter"
                  :style="{ color: isMbtiTypeLetterChanged(letter, index) ? '#ffcf5a' : 'inherit' }"
                >{{ letter }}</span>
              </strong>
              <small>{{ mbtiData.current.monthLabel }}</small>
            </article>
            <article class="mbti-type-panel previous">
              <span>이전 기준 MBTI</span>
              <strong>{{ mbtiData.previous?.type || '기준 없음' }}</strong>
              <small>{{ mbtiData.previous?.monthLabel || '' }}</small>
            </article>
          </div>

          <article class="mbti-current-graph">
            <div class="mbti-combined-head">
              <div>
                <h3>현재 MBTI 선호성향 그래프</h3>
              </div>
              <div class="mbti-type mbti-type-current mbti-letter-row">
                <span
                  v-for="(letter, index) in currentTypeLetters"
                  :key="'header-' + letter + index"
                  class="mbti-type-letter"
                  :style="{ color: isMbtiTypeLetterChanged(letter, index) ? '#ffcf5a' : 'inherit' }"
                >{{ letter }}</span>
              </div>
            </div>
            <div class="axis-list graph-only-list">
              <div
                class="axis-item"
                v-for="axis in mbtiData.current.axes"
                :key="axis.pair"
              >
                <div class="axis-head graph-axis-head">
                  <span class="graph-axis-label">
                    <strong>{{ axis.pair }}</strong>
                    <small>{{ axis.label }} 경향</small>
                  </span>
                  <span>{{ axis.score }}%</span>
                </div>
                <div
                  class="meter"
                  :aria-label="axis.pair + ' 중 ' + axis.label + ' 경향 ' + axis.score + '%'"
                >
                  <span :style="{ width: axis.score + '%' }"></span>
                </div>
              </div>
            </div>
          </article>

          <article class="mbti-evidence-report">
            <h3>근거 리포트</h3>
            <ol class="report-lines compact-report">
              <li v-for="line in mbtiData.report" :key="line">{{ line }}</li>
            </ol>
          </article>
        </div>
      </section>
    </template>

    <template v-else-if="mbtiViewMode === 'mockQna'">
      <section class="card report-panel premium-qna-panel">
        <header class="qna-header">
          <div class="qna-badge">MBTI Q&A</div>
          <h3 class="qna-title">챗봇과 대화하기</h3>
          <p class="qna-subtitle">무작위 질문에 답하며 나만의 성향 데이터를 쌓아보세요.</p>
          
          <div class="qna-progress-bar" v-if="mockData.counts">
            <div v-for="(count, axis) in mockData.counts" :key="axis" class="progress-pill" :class="{ 'is-complete': count >= requiredAnswersPerAxis }">
              <span class="axis-name">{{ axis }}</span>
              <span class="axis-count">{{ count }}/5</span>
            </div>
          </div>
          <div v-if="mockData.counts" class="qna-reset-action">
            <button @click="resetMockData" class="qna-reset-button" type="button" title="현재 작성된 질문 내역을 모두 초기화합니다">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path></svg>
              처음부터 다시하기
            </button>
          </div>
        </header>

        <div v-if="canFinishMock" class="qna-finish-action">
          <button @click="$emit('refresh')" class="qna-finish-button">
            ✨ 최소 요건 달성! 분석 결과 새로고침
          </button>
        </div>
        
        <div v-if="!mockData.question && !isLoadingQuestion" class="qna-empty-state">
          <div class="qna-icon-wrap">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          </div>
          <button type="button" @click="selectMockAxis()" class="qna-draw-button">
            첫 질문 받아보기
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left: 6px;"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </button>
        </div>

        <div v-else class="qna-active-state">
          <div v-if="isLoadingQuestion" class="qna-chatbot-bubble">
            <div class="chatbot-avatar">...</div>
            <div class="chatbot-message">질문을 생성하는 중입니다...</div>
          </div>
          <div v-else class="qna-chatbot-bubble">
            <div class="chatbot-avatar">
              <span class="axis-tag">{{ mockData.axis }}</span>
            </div>
            <div class="chatbot-message">
              <p>{{ mockData.question }}</p>
            </div>
          </div>

          <div class="qna-user-input">
            <textarea v-model="mockData.answer" placeholder="답변을 자유롭게 입력해주세요..." 
                      class="qna-textarea"
                      @keydown.ctrl.enter="submitMockAnswer"></textarea>
            <div class="qna-input-footer">
              <span class="qna-hint">Ctrl + Enter로 전송</span>
              <button class="qna-submit-button" @click="submitMockAnswer" type="button" :disabled="!mockData.answer.trim() || isLoadingQuestion">
                답변 전송하기
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-left: 4px;"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>

    <div v-if="onboardingData?.type && onboardingData.type !== '----'" class="actions mbti-switch-actions" aria-label="MBTI 화면 전환">
      <button
        v-for="view in mbtiViews"
        :key="view.key"
        class="secondary-button"
        :class="{ active: mbtiViewMode === view.key }"
        :aria-pressed="mbtiViewMode === view.key"
        type="button"
        @click="$emit('set-view', view.key)"
      >
        {{ view.buttonLabel || view.shortLabel }}
      </button>
    </div>
  </div>
</template>

<script>
import { fetchMockQuestion, saveMockAnswer, resetMockQna } from "../mypage.api";
import {
  MBTI_AXIS_COUNT,
  MBTI_OPTIONS,
  MBTI_REQUIRED_ANSWERS_PER_AXIS,
} from "../config/mbti.constants";

export default {
  name: "MbtiPanel",
  props: {
    mbtiData: { type: Object, default: null },
    mbtiViewMode: { type: String, required: true },
    mbtiViews: { type: Array, required: true },
    currentMbtiView: { type: Object, required: true }
  },
  emits: ["refresh", "set-view", "save-mbti"],
  data() {
    return {
      newMbti: "",
      mbtiOptions: MBTI_OPTIONS,
      requiredAnswersPerAxis: MBTI_REQUIRED_ANSWERS_PER_AXIS,
      mockData: {
        axis: "",
        question: "",
        answer: "",
        counts: null
      },
      isLoadingQuestion: false
    };
  },
  computed: {
    onboardingData() {
      return this.mbtiData?.onboarding || null;
    },
    canFinishMock() {
      if (!this.mockData.counts) return false;
      const axes = Object.keys(this.mockData.counts);
      return axes.length >= MBTI_AXIS_COUNT
        && Object.values(this.mockData.counts).every(
          (count) => count >= MBTI_REQUIRED_ANSWERS_PER_AXIS
        );
    },
    isMonthlyPreparing() {
      const currentType = this.mbtiData?.current?.type;
      return !currentType || currentType === "----";
    },
    currentTypeLetters() {
      return this.isMonthlyPreparing
        ? []
        : Array.from(this.mbtiData.current.type);
    }
  },
  methods: {
    isMbtiTypeLetterChanged(letter, index) {
      if (this.isMonthlyPreparing || letter === "-") return false;
      return this.mbtiData?.previous?.type?.[index] !== letter;
    },
    saveMbti() {
      const type = this.newMbti.trim().toUpperCase();
      if (type.length === 4) {
        this.$emit('save-mbti', type);
      }
    },
    async selectMockAxis(axis = "") {
      this.mockData.question = "";
      this.mockData.answer = "";
      this.mockData.axis = "";
      this.isLoadingQuestion = true;
      try {
        const res = await fetchMockQuestion(axis);
        this.mockData.question = res.question?.text || res.question;
        this.mockData.axis = res.question?.axis || "";
        if (res.axis_counts && !this.mockData.counts) {
          this.mockData.counts = res.axis_counts;
        }
      } catch(e) {
        alert("질문을 불러오지 못했습니다.");
      } finally {
        this.isLoadingQuestion = false;
      }
    },
    async submitMockAnswer() {
      if (!this.mockData.answer.trim()) return;
      try {
        const res = await saveMockAnswer({
          target_axis: this.mockData.axis,
          question_text: this.mockData.question,
          answer_text: this.mockData.answer
        });
        if (res.axis_counts) this.mockData.counts = res.axis_counts;
        this.mockData.answer = "";
        await this.selectMockAxis();
      } catch(e) {
        alert("저장에 실패했습니다.");
      }
    },
    async resetMockData() {
      if (!confirm("정말 처음부터 다시 진행하시겠습니까?\n이번 달에 작성한 Q&A 데이터가 모두 삭제됩니다.")) return;
      this.isLoadingQuestion = true;
      try {
        const res = await resetMockQna();
        this.mockData.counts = res.axis_counts;
        this.mockData.question = "";
        this.mockData.answer = "";
        this.mockData.axis = "";
        alert("초기화가 완료되었습니다. 첫 질문을 다시 받아보세요!");
      } catch(e) {
        alert("초기화에 실패했습니다.");
      } finally {
        this.isLoadingQuestion = false;
      }
    }
  }
};
</script>

<style scoped>
.premium-qna-panel {
  padding: 32px 24px;
  max-width: 640px;
  margin: 0 auto;
  background: linear-gradient(145deg, var(--mbti-surface-soft) 0%, var(--mbti-surface-deep) 100%);
  border: 1px solid var(--mbti-line);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  backdrop-filter: blur(20px);
}

.qna-header {
  text-align: center;
  margin-bottom: 32px;
}

.qna-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(229, 155, 95, 0.12);
  color: #efb789;
  border: 1px solid rgba(229, 155, 95, 0.22);
  font-size: 12px;
  font-weight: 700;
  border-radius: 20px;
  margin-bottom: 12px;
  letter-spacing: 0.5px;
}

.qna-title {
  margin: 0 0 8px 0;
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
}

.qna-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--muted);
}

.qna-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
  gap: 24px;
}

.qna-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(229, 155, 95, 0.07);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d4b49f;
  box-shadow: inset 0 0 0 1px var(--mbti-line);
}

.qna-draw-button {
  display: flex;
  align-items: center;
  padding: 14px 28px;
  background: linear-gradient(135deg, #e59b5f 0%, #8794a4 100%);
  color: #21142b;
  font-weight: 600;
  font-size: 16px;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(10, 7, 24, 0.28);
}

.qna-draw-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(229, 155, 95, 0.22);
}

.qna-active-state {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeIn 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.qna-chatbot-bubble {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.chatbot-avatar {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, #4a304d 0%, #292033 100%);
  border: 1px solid var(--mbti-line-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.axis-tag {
  font-size: 13px;
  font-weight: 800;
  background: -webkit-linear-gradient(#efb789, #9ba8b8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.chatbot-message {
  background: rgba(62, 38, 65, 0.72);
  padding: 18px 22px;
  border-radius: 4px 20px 20px 20px;
  border: 1px solid var(--mbti-line-soft);
  font-size: 15px;
  line-height: 1.6;
  color: var(--text);
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  position: relative;
  max-width: 100%;
}

.chatbot-message p {
  margin: 0;
}

.qna-user-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(27, 17, 36, 0.68);
  padding: 16px;
  border-radius: 20px;
  border: 1px solid var(--mbti-line-soft);
}

.qna-textarea {
  width: 100%;
  min-height: 120px;
  background: transparent;
  border: none;
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  outline: none;
  padding: 4px;
}

.qna-textarea::placeholder {
  color: rgba(199, 179, 188, 0.62);
}

.qna-input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.qna-hint {
  font-size: 12px;
  color: var(--muted);
}

.qna-submit-button {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: #e59b5f;
  color: #21142b;
  font-weight: 600;
  font-size: 14px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.qna-submit-button:disabled {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.3);
  cursor: not-allowed;
}

.qna-submit-button:not(:disabled):hover {
  background: #efb078;
  transform: translateY(-1px);
}

.qna-progress-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

.progress-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(27, 17, 36, 0.66);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  border: 1px solid var(--mbti-line-soft);
  transition: all 0.3s ease;
}

.progress-pill.is-complete {
  background: rgba(229, 155, 95, 0.14);
  border-color: rgba(229, 155, 95, 0.38);
  box-shadow: 0 0 10px rgba(229, 155, 95, 0.12);
}

.progress-pill .axis-name {
  font-weight: 700;
  color: #aeb8c4;
}

.progress-pill .axis-count {
  color: rgba(255,255,255,0.8);
  font-weight: 600;
}

.progress-pill.is-complete .axis-name {
  color: #efb789;
}

.progress-pill.is-complete .axis-count {
  color: #fff;
}

.qna-reset-action {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.qna-reset-button {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.6);
  border-radius: 12px;
  padding: 6px 14px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.qna-reset-button:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  border-color: rgba(255, 255, 255, 0.4);
}

.qna-finish-action {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
  animation: fadeIn 0.4s ease-out;
}

.qna-finish-button {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 700;
  font-size: 15px;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
  transition: all 0.2s ease;
}

.qna-finish-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
}
</style>
