<template>
  <div class="panel-body">
    <div class="actions mbti-refresh-actions">
      <button class="secondary-button" type="button" @click="$emit('refresh')">
        분석 결과 새로고침
      </button>
    </div>

    <template v-if="mbtiViewMode === 'onboardingType'">
      <div class="mbti-dashboard mbti-dashboard-single">
        <section class="mbti-result-board mbti-onboarding-board">
          <div>
            <span class="mbti-kicker">온보딩 MBTI 유형</span>
            <template v-if="mbtiData.onboarding.type === '----'">
              <div class="mbti-input-area" style="margin-top: 16px; margin-bottom: 12px; display: flex; flex-direction: column; align-items: center; gap: 16px;">
                <div class="mbti-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; width: 100%; max-width: 320px;">
                  <button v-for="type in mbtiOptions" :key="type" type="button"
                          :style="{ padding: '8px 4px', borderRadius: '10px', border: newMbti === type ? '2px solid #f84f9b' : '1px solid rgba(255,255,255,0.15)', background: newMbti === type ? 'rgba(248,79,155,0.15)' : 'rgba(255,255,255,0.05)', color: newMbti === type ? '#fff' : 'rgba(255,255,255,0.7)', fontWeight: 'bold', fontSize: '15px', cursor: 'pointer', transition: 'all 0.2s' }"
                          @click="newMbti = type">
                    {{ type }}
                  </button>
                </div>
                <button class="primary-button" @click="saveMbti" type="button" :disabled="!newMbti" :style="{ padding: '0 24px', borderRadius: '10px', minHeight: '42px', opacity: newMbti ? '1' : '0.5', cursor: newMbti ? 'pointer' : 'not-allowed' }">선택 완료</button>
              </div>
            </template>
            <template v-else>
              <div class="mbti-type">{{ mbtiData.onboarding.type }}</div>
            </template>
            <div class="mbti-confidence">{{ mbtiData.onboarding.period }}</div>
          </div>
        </section>
        <section class="card report-panel mbti-type-description">
          <h3>온보딩 MBTI 유형 설명</h3>
          <p>{{ mbtiData.onboarding.description }}</p>
          <ol class="report-lines compact-report">
            <li v-for="line in mbtiData.onboarding.report" :key="line">{{ line }}</li>
          </ol>
        </section>
      </div>
    </template>

    <template v-else-if="mbtiViewMode === 'onboardingNext'">
      <section class="card mbti-combined-card" :class="{ 'is-preparing': isMonthlyPreparing }">
        <div v-if="isMonthlyPreparing" class="mbti-preparing-banner" role="status">
          <strong>월간 MBTI 분석을 준비하고 있어요.</strong>
          <span>대화 기반 응답이 충분히 저장되면 이 화면에서 성향 그래프와 근거 리포트를 보여드릴게요.</span>
        </div>

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
              <strong>{{ mbtiData.previous.type }}</strong>
              <small>{{ mbtiData.previous.monthLabel }}</small>
            </article>
          </div>

          <article class="mbti-current-graph">
            <div class="mbti-combined-head">
              <div>
                <h3>{{ isMonthlyPreparing ? 'MBTI 선호성향 그래프 준비 중' : '현재 MBTI 선호성향 그래프' }}</h3>
                <p v-if="isMonthlyPreparing">아직 확정된 월간 점수가 없어 기본 상태로 표시됩니다.</p>
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
            <h3>{{ isMonthlyPreparing ? '준비 중 안내' : '근거 리포트' }}</h3>
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
            <div v-for="(count, axis) in mockData.counts" :key="axis" class="progress-pill" :class="{ 'is-complete': count >= 5 }">
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

    <div v-if="mbtiData.onboarding.type !== '----'" class="actions mbti-switch-actions" aria-label="MBTI 화면 전환">
      <button
        v-for="view in mbtiViews"
        :key="view.key"
        class="secondary-button"
        :class="{ active: mbtiViewMode === view.key }"
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

export default {
  name: "MbtiPanel",
  props: {
    mbtiData: { type: Object, required: true },
    mbtiViewMode: { type: String, required: true },
    mbtiViews: { type: Array, required: true },
    currentMbtiView: { type: Object, required: true }
  },
  emits: ["refresh", "set-view", "save-mbti"],
  data() {
    return {
      newMbti: "",
      mbtiOptions: [
        'INTJ', 'INTP', 'ENTJ', 'ENTP',
        'INFJ', 'INFP', 'ENFJ', 'ENFP',
        'ISTJ', 'ISTP', 'ESTJ', 'ESTP',
        'ISFJ', 'ISFP', 'ESFJ', 'ESFP'
      ],
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
    canFinishMock() {
      if (!this.mockData.counts) return false;
      const axes = Object.keys(this.mockData.counts);
      return axes.length >= 4 && Object.values(this.mockData.counts).every(count => count >= 5);
    },
    isMonthlyPreparing() {
      return this.mbtiData.current?.type === "----";
    },
    currentTypeLetters() {
      return Array.from(this.mbtiData.current?.type || "----");
    }
  },
  methods: {
    isMbtiTypeLetterChanged(letter, index) {
      if (this.isMonthlyPreparing || letter === "-") return false;
      return this.mbtiData.previous?.type?.[index] !== letter;
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
  background: linear-gradient(145deg, rgba(30,30,35,0.8) 0%, rgba(20,20,25,0.95) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
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
  background: rgba(248, 79, 155, 0.15);
  color: #f84f9b;
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
  color: #fff;
}

.qna-subtitle {
  margin: 0;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
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
  background: rgba(255, 255, 255, 0.03);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.4);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.qna-draw-button {
  display: flex;
  align-items: center;
  padding: 14px 28px;
  background: linear-gradient(135deg, #f84f9b 0%, #ff8c42 100%);
  color: #fff;
  font-weight: 600;
  font-size: 16px;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(248, 79, 155, 0.3);
}

.qna-draw-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(248, 79, 155, 0.4);
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
  background: linear-gradient(135deg, #2a2a35 0%, #1f1f26 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.axis-tag {
  font-size: 13px;
  font-weight: 800;
  background: -webkit-linear-gradient(#f84f9b, #ffcf5a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.chatbot-message {
  background: rgba(255, 255, 255, 0.06);
  padding: 18px 22px;
  border-radius: 4px 20px 20px 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 15px;
  line-height: 1.6;
  color: #eaeaea;
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
  background: rgba(0, 0, 0, 0.2);
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.qna-textarea {
  width: 100%;
  min-height: 120px;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  outline: none;
  padding: 4px;
}

.qna-textarea::placeholder {
  color: rgba(255, 255, 255, 0.3);
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
  color: rgba(255, 255, 255, 0.4);
}

.qna-submit-button {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: #f84f9b;
  color: #fff;
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
  background: #ff5eaa;
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
  background: rgba(0,0,0,0.3);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  border: 1px solid rgba(255,255,255,0.05);
  transition: all 0.3s ease;
}

.progress-pill.is-complete {
  background: rgba(248, 79, 155, 0.2);
  border-color: rgba(248, 79, 155, 0.5);
  box-shadow: 0 0 10px rgba(248, 79, 155, 0.2);
}

.progress-pill .axis-name {
  font-weight: 700;
  color: #ffcf5a;
}

.progress-pill .axis-count {
  color: rgba(255,255,255,0.8);
  font-weight: 600;
}

.progress-pill.is-complete .axis-name {
  color: #f84f9b;
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
