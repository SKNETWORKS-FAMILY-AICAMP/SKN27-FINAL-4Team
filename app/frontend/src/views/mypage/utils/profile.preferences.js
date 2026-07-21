function parseCsvLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && next === '"') {
      current += '"';
      index += 1;
      continue;
    }
    if (char === '"') {
      inQuotes = !inQuotes;
      continue;
    }
    if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
      continue;
    }
    current += char;
  }

  result.push(current);
  return result.map((value) => value.trim());
}

function parseKeywordCsv(csvText, type) {
  const lines = csvText.replace(/^\uFEFF/, "").split(/\r?\n/).filter(Boolean);
  const headers = parseCsvLine(lines.shift() || "");

  return lines.map((line) => {
    const values = parseCsvLine(line);
    const raw = Object.fromEntries(headers.map((header, index) => [header, values[index] || ""]));
    const label = type === "hobby"
      ? raw.display_label || raw.label || raw.keyword
      : raw.label || raw.displayLabel || raw.displayText || raw.keyword;

    return {
      label,
      category: raw.category || "기타",
    };
  }).filter((item) => item.label);
}

export function createPreferenceGroups(csvText, type) {
  return parseKeywordCsv(csvText, type).reduce((groups, item) => {
    const categoryItems = groups[item.category] || [];
    if (!categoryItems.some((candidate) => candidate.label === item.label)) {
      categoryItems.push(item);
    }
    groups[item.category] = categoryItems;
    return groups;
  }, {});
}
