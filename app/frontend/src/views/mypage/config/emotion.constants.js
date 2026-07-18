export const DEFAULT_ROOM_EXPRESSION = "default";

export const EMOTION_EXPRESSIONS = Object.freeze([
  { id: "joy", label: "기쁨", description: "통통 튀는 밝은 표정" },
  { id: "anger", label: "화남", description: "부들부들 화가 난 표정" },
  { id: "sadness", label: "슬픔", description: "조용히 가라앉은 표정" },
  { id: "anxiety", label: "불안", description: "조금 긴장한 표정" },
  { id: "hurt", label: "상처", description: "마음이 아픈 표정" },
  { id: "panic", label: "당황", description: "깜짝 놀란 표정" },
]);

export const VALID_ROOM_EXPRESSIONS = Object.freeze(
  new Set(EMOTION_EXPRESSIONS.map((expression) => expression.id)),
);

export const EMOTION_ANIMATION_CLASSES = Object.freeze(
  EMOTION_EXPRESSIONS.reduce((classes, expression) => {
    classes[expression.id] = `expression-${expression.id}`;
    return classes;
  }, {}),
);
