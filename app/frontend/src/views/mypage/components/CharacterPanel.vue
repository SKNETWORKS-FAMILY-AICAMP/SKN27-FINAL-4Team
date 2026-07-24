<template>
  <div class="panel-body character-panel-body">
    <section class="character-panel-layout">
      <div class="character-showcase" aria-label="선택 캐릭터 미리보기">
        <div class="character-stage">
          <img :src="characterImage(draftCharacter)" :alt="draftCharacter.name" />
        </div>
        <div class="character-switcher" aria-label="캐릭터 선택">
          <button
            v-for="character in characters"
            :key="character.id"
            type="button"
            class="character-choice"
            :class="{ active: character.id === draftCharacterId }"
            :aria-label="character.name"
            :aria-pressed="character.id === draftCharacterId"
            @click="draftCharacterId = character.id"
          >
            <img :src="characterImage(character)" alt="" aria-hidden="true" />
            <span>{{ character.name }}</span>
          </button>
        </div>
      </div>

      <aside class="character-detail" aria-label="캐릭터 설명">
        <div class="character-heading">
          <span>내 방의 동행 캐릭터</span>
          <h3>{{ draftCharacter.name }}</h3>
          <p>{{ draftCharacter.role }}</p>
        </div>

        <blockquote>{{ draftCharacter.line }}</blockquote>

        <dl class="character-meta">
          <div>
            <dt>말투</dt>
            <dd>{{ draftCharacter.tone }}</dd>
          </div>
          <div>
            <dt>키워드</dt>
            <dd>
              <span v-for="tag in draftCharacter.tags" :key="tag">{{ tag }}</span>
            </dd>
          </div>
        </dl>

        <div class="character-actions">
          <button
            class="primary-button"
            type="button"
            :disabled="isCurrentSelection"
            @click="$emit('choose-character', draftCharacterId)"
          >
            {{ isCurrentSelection ? "현재 적용 중" : "이 캐릭터로 변경" }}
          </button>
        </div>
      </aside>
    </section>
  </div>
</template>

<script>
export default {
  name: "CharacterPanel",
  props: {
    selectedCharacter: { type: String, required: true },
    currentCharacter: { type: Object, required: true },
    characters: { type: Array, required: true }
  },
  emits: ["choose-character"],
  data() {
    return {
      draftCharacterId: this.characters.some((character) => character.id === this.selectedCharacter)
        ? this.selectedCharacter
        : this.currentCharacter.id
    };
  },
  computed: {
    draftCharacter() {
      return this.characters.find((character) => character.id === this.draftCharacterId) || this.currentCharacter;
    },
    isCurrentSelection() {
      return this.draftCharacter.id === this.currentCharacter.id;
    }
  },
  watch: {
    selectedCharacter(value) {
      this.draftCharacterId = this.characters.some((character) => character.id === value)
        ? value
        : this.currentCharacter.id;
    }
  },
  methods: {
    characterImage(character) {
      return `/characters/${character.id}/default.png`;
    }
  }
};
</script>
