import { getMemoryCreatedAt, normalizeMemory } from "./memory.formatters";

const NEGATIVE_PREFERENCES = new Set([
  "불호",
  "싫음",
  "오",
  "negative",
  "dislike",
  "-1",
]);

function sourceItems(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.memories || payload?.items || [];
}

function cleanValues(values) {
  return [...new Set(
    values.map(value => String(value || "").trim()).filter(Boolean),
  )];
}

function rankMentions(memories, selectValues, limit = 3) {
  const mentions = new Map();
  let firstSeen = 0;

  memories.forEach((memory) => {
    cleanValues(selectValues(memory)).forEach((value) => {
      const current = mentions.get(value);
      if (current) {
        current.count += 1;
        return;
      }
      mentions.set(value, { value, count: 1, firstSeen: firstSeen++ });
    });
  });

  return [...mentions.values()]
    .sort((a, b) => b.count - a.count || a.firstSeen - b.firstSeen)
    .slice(0, limit)
    .map(item => item.value);
}

function eventMentions(memory) {
  return [
    ...(memory.context?.events || []).map(event => event.name),
    ...(memory.rawEvents || []),
  ];
}

function personMentions(memory) {
  const events = memory.context?.events || [];
  return [
    ...events.flatMap(event => (event.people || []).map(person => person.name)),
    ...(memory.context?.relations || []).map(relation => relation.name),
    ...(memory.rawPeople || []).map(person => person.name || person),
  ];
}

function preferenceMentions(memory) {
  return (memory.context?.preferences || [])
    .filter(preference => !preference.valid_to)
    .map((preference) => {
      const topic = String(preference.topic || "").trim();
      const isNegative = NEGATIVE_PREFERENCES.has(
        String(preference.polarity || "호").toLowerCase(),
      );
      return topic && isNegative ? `${topic} · 비선호` : topic;
    });
}

function dateKey(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function memorySavedAt(memory) {
  return getMemoryCreatedAt(memory);
}

export function buildMemoryDashboard(payload, today = new Date()) {
  const todayKey = dateKey(today);
  const rawMemories = sourceItems(payload).filter(memory => (
    dateKey(memorySavedAt(memory)) === todayKey
  ));
  const memories = rawMemories.map((item, index) => normalizeMemory(item, index));
  const events = rankMentions(memories, eventMentions);
  const people = rankMentions(memories, personMentions);
  const preferences = rankMentions(memories, preferenceMentions);
  const latest = memories[0] || null;

  return {
    count: memories.length,
    events,
    people,
    preferences,
    latest,
  };
}
