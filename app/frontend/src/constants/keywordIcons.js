export function getKeywordIcon(label, type) {
  const text = String(label || "");
  if (/음악|K-POP|발라드|재즈|콘서트|악기|연주/.test(text)) return "🎧";
  if (/산책|러닝|운동|헬스|요가|등산|스포츠/.test(text)) return "🚶";
  if (/카페|커피|차|맛집|요리|베이킹/.test(text)) return "☕";
  if (/영화|드라마|웹툰|예능|애니|콘텐츠|유튜브/.test(text)) return "🎬";
  if (/게임|디지털|트렌드/.test(text)) return "🎮";
  if (/독서|글쓰기|자기계발|학습|심리/.test(text)) return "📚";
  if (/사진|전시|문화|공연|창작|드로잉|표현/.test(text)) return "🖼️";
  if (/반려|동물|식물|가드닝|자연/.test(text)) return "🐾";
  if (/여행|외출|공간|팝업|캠핑/.test(text)) return "🧭";
  if (/패션|뷰티|인테리어|쇼핑/.test(text)) return "✨";
  return type === "hobby" ? "💫" : "🔖";
}
