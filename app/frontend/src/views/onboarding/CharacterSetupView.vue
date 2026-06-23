<script setup>
import { computed, ref } from "vue";

defineEmits(["navigate"]);

const selectedCharacter = ref("haeon");
const selectedFace = ref("calm");

const characters = [
  {
    id: "haeon",
    name: "해온이",
    role: "위로형 동행자",
    tone: "다정하고 천천히 묻는 말투",
    line: "오늘 마음은 내가 옆에서 같이 정리해볼게요.",
    color: "sunset"
  },
  {
    id: "dalkong",
    name: "달콩이",
    role: "코치형 동행자",
    tone: "가볍게 제안하고 실행을 돕는 말투",
    line: "작은 행동 하나만 골라서 같이 시작해봐요.",
    color: "mint"
  },
  {
    id: "geureung",
    name: "그릉이",
    role: "직면형 동행자",
    tone: "솔직하지만 안전하게 짚어주는 말투",
    line: "피하고 싶은 마음까지 천천히 살펴볼까요?",
    color: "lavender"
  }
];

const faces = [
  { id: "calm", label: "차분", desc: "느린 호흡과 안정감" },
  { id: "bright", label: "밝음", desc: "상냥한 응원과 활기" },
  { id: "deep", label: "깊음", desc: "긴 문장보다 조용한 공감" },
  { id: "playful", label: "장난", desc: "부담을 낮추는 작은 농담" }
];

const selected = computed(() => characters.find((character) => character.id === selectedCharacter.value) || characters[0]);
const selectedFaceLabel = computed(() => faces.find((face) => face.id === selectedFace.value)?.label || "차분");
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
          <p>사용자와 대화할 마음 동행자의 기본 성격, 표정, 말투를 첫 로그인 때만 설정하는 화면이에요.</p>
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
          <span>표정 미리보기</span>
          <strong>{{ selected.name }} · {{ selectedFaceLabel }}</strong>
        </div>
        <div class="face-options">
          <button
            v-for="face in faces"
            :key="face.id"
            type="button"
            :class="{ selected: selectedFace === face.id }"
            @click="selectedFace = face.id"
          >
            <strong>{{ face.label }}</strong>
            <small>{{ face.desc }}</small>
          </button>
        </div>
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
        <span>선택한 캐릭터와 표정은 대화 시작 문장, 위로 톤, 추천 질문 스타일에 반영돼요.</span>
      </div>
      <button class="btn primary full" type="button" @click="$emit('navigate', 'userinfo')">다음: 사용자 정보</button>
    </aside>
  </section>
</template>
