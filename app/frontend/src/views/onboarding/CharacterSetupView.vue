<script setup>
import { computed, ref } from "vue";

defineEmits(["navigate"]);

const selectedCharacter = ref("pori");

// 캐릭터 = 성격(분위기). 4종이 밝음/깊음/장난/차분에 1:1로 대응한다.
const characters = [
  {
    id: "pori",
    name: "포리",
    role: "레서판다 · 밝음 · 응원형",
    face: "bright",
    faceLabel: "밝음",
    tone: "작은 빛처럼 곁에서 응원하는 말투",
    line: "오늘 여기까지 온 것만으로 충분해요! 작은 것부터 같이 해봐요!",
    color: "mint"
  },
  {
    id: "kkami",
    name: "까미",
    role: "고양이 · 깊음 · 공감형",
    face: "deep",
    faceLabel: "깊음",
    tone: "긴 말보다 묵직하게 함께 있어주는 말투",
    line: "그랬구나. 말로 다 못 해도 괜찮아. 여기서 같이 들여다보자.",
    color: "lavender"
  },
  {
    id: "toto",
    name: "토토",
    role: "수달 · 장난 · 환기형",
    face: "playful",
    faceLabel: "장난",
    tone: "가벼운 농담으로 부담을 덜어주는 말투",
    line: "너무 무겁게 안 가도 돼. 일단 나랑 한 숨 돌려볼래?",
    color: "sky"
  },
  {
    id: "yeoul",
    name: "여울",
    role: "뱁새 · 차분 · 포근형",
    face: "calm",
    faceLabel: "차분",
    tone: "느린 호흡으로 곁을 지키는 말투",
    line: "천천히 숨 한 번 같이 쉬어볼까요. 급하지 않아도 괜찮아요.",
    color: "sunset"
  }
];

const selected = computed(() => characters.find((character) => character.id === selectedCharacter.value) || characters[0]);
const selectedFace = computed(() => selected.value.face);
const selectedFaceLabel = computed(() => selected.value.faceLabel);
</script>

<template>
  <section class="view-card content-view setup-view character-setup-view">
    <article class="glass-panel content-main-panel">
      <div class="setup-progress" aria-label="첫 로그인 설정 단계">
        <span class="done">로그인</span>
        <span class="active">캐릭터 설정</span>
        <span>사용자 정보</span>
        <span>완료</span>
      </div>

      <div class="content-heading">
        <div>
          <p class="section-kicker">Character persona</p>
          <h2>대화 동행자를 선택해요</h2>
          <p>네 동행자는 각각 차분·밝음·깊음·장난의 성격을 가져요. 첫 로그인 때 한 명을 골라주세요.</p>
        </div>
        <button class="btn secondary small" type="button" @click="$emit('navigate', 'login')">로그인으로</button>
      </div>

      <div class="character-grid" aria-label="캐릭터 선택">
        <button
          v-for="character in characters"
          :key="character.id"
          type="button"
          class="character-card"
          :class="[character.color, { selected: selectedCharacter === character.id }]"
          @click="selectedCharacter = character.id"
        >
          <span class="character-avatar">
            <i></i>
          </span>
          <strong>{{ character.name }}</strong>
          <small>{{ character.role }}</small>
        </button>
      </div>

      <section class="question-card">
        <div class="question-meta">
          <span>선택한 동행자</span>
          <strong>{{ selected.name }} · {{ selectedFaceLabel }}</strong>
        </div>
        <p class="character-summary">{{ selected.tone }}</p>
      </section>
    </article>

    <aside class="glass-panel content-side-panel setup-preview-panel">
      <div class="tiny-mascot large" :class="selectedFace" aria-hidden="true">
        <span class="mascot-face"></span>
      </div>
      <p class="section-kicker">Preview</p>
      <h3>{{ selected.name }}</h3>
      <p>{{ selected.role }} · {{ selected.tone }}</p>
      <div class="preview-bubble">
        {{ selected.line }}
      </div>
      <div class="advice-box">
        <strong>설정 영향</strong>
        <span>선택한 동행자의 성격은 대화 시작 문장, 위로 톤, 추천 질문 스타일에 반영돼요.</span>
      </div>
      <button class="btn primary full" type="button" @click="$emit('navigate', 'userinfo')">다음: 사용자 정보</button>
    </aside>
  </section>
</template>
