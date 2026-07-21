import {
  DEFAULT_MEMORY_POLARITY,
  MEMORY_DATE_FORMAT,
  MEMORY_DATE_TIME_FORMAT,
  MEMORY_NEGATIVE_POLARITIES,
  MEMORY_NEUTRAL_POLARITIES,
} from "../config/memory.constants";

function parseMemoryDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date;
}

export function formatMemoryDate(value) {
  const date = parseMemoryDate(value);
  return date instanceof Date
    ? date.toLocaleString("ko-KR", MEMORY_DATE_TIME_FORMAT)
    : date;
}

export function formatMemoryDateOnly(value) {
  const date = parseMemoryDate(value);
  return date instanceof Date
    ? date.toLocaleDateString("ko-KR", MEMORY_DATE_FORMAT)
    : date;
}

export function getMemoryCreatedAt(item) {
  const context = item?.context || {};
  const sourceProperties = context.graph?.source?.properties || {};
  const eventCreatedAt = (context.events || [])
    .map((event) => event?.created_at || event?.graph?.node?.properties?.created_at)
    .find(Boolean);
  const edgeCreatedAt = (context.graph?.edges || [])
    .map((edge) => edge?.properties?.created_at || edge?.properties?.valid_from)
    .find(Boolean);

  return (
    item?.saved_at ||
    item?.created_at ||
    item?.updated_at ||
    item?.savedAtRaw ||
    item?.savedAt ||
    context.saved_at ||
    sourceProperties.created_at ||
    eventCreatedAt ||
    edgeCreatedAt ||
    ""
  );
}

export function getMemoryOriginalText(item) {
  return (
    item?.context?.introduction?.original_text ||
    item?.context?.source_text ||
    item?.originalText ||
    ""
  );
}

export function hasMemoryContext(item) {
  const context = item?.context;
  return Boolean(
    context &&
    (
      context.events?.length ||
      context.relations?.length ||
      context.preferences?.length ||
      getMemoryOriginalText(item)
    )
  );
}

export function hasLegacyMemoryContext(item) {
  return Boolean(
    item?.rawDate ||
    item?.rawPeople?.length ||
    item?.rawRelation ||
    item?.rawEvents?.length
  );
}

export function formatMemoryEventDate(event) {
  if (!event) return "";
  if (event.occurs_start) {
    const start = formatMemoryDateOnly(event.occurs_start);
    if (event.occurs_end && event.occurs_end !== event.occurs_start) {
      return `${start} ~ ${formatMemoryDateOnly(event.occurs_end)}`;
    }
    return start;
  }

  const dates = (event.dates || [])
    .map((item) => formatMemoryDateOnly(item.date))
    .filter(Boolean);
  return [...new Set(dates)].join(", ");
}

export function formatMemoryPolarity(value) {
  const polarity = String(value || DEFAULT_MEMORY_POLARITY).toLowerCase();
  if (MEMORY_NEGATIVE_POLARITIES.includes(polarity)) {
    return "좋아하지 않음";
  }
  if (MEMORY_NEUTRAL_POLARITIES.includes(polarity)) return "중립";
  return "좋아함";
}

export function formatMemoryValidity(item) {
  if (item?.valid_to) {
    return `종료 · ${formatMemoryDateOnly(item.valid_to)}`;
  }
  return "현재 유효";
}

export function normalizeMemory(item, index) {
  const id = String(
    item.id || item.memory_id || item.key || `node-temp-${index}`,
  );
  return {
    id,
    title: item.title || item.topic || item.label || `기억 항목 ${index + 1}`,
    content: item.content || item.summary || item.text || item.memory || "",
    savedAt: item.savedAt || formatMemoryDate(getMemoryCreatedAt(item)),
    type: item.type || "",
    rawDate: item.raw_date || "",
    rawPeople: item.raw_people || [],
    rawRelation: item.raw_relation || "",
    rawEvents: item.raw_events || [],
    originalText: item.original_text || item.source_text || "",
    context: item.context || null,
  };
}

export function filterMemories(memories, keyword) {
  const needle = String(keyword || "").trim().toLowerCase();
  if (!needle) return memories;

  return memories.filter((item) => [
    item.title,
    item.content,
    item.id,
    getMemoryOriginalText(item),
  ].join(" ").toLowerCase().includes(needle));
}
