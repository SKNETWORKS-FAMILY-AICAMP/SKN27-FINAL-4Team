import csv
import re

from myweather.constants import (
    JEJU_WARNING_CITY_PREFIXES,
    KMA_WARNING_EXPECTED_FIELDS,
    KMA_WARNING_LEVEL_PRIORITY,
    KMA_WARNING_REGION_CODE_OVERRIDES,
    METROPOLITAN_WARNING_DISPLAY_NAMES,
    WARNING_LEVEL_LABELS,
    WARNING_RELEASE_COMMANDS,
    WARNING_TYPE_LABELS,
)

from .region_service import (
    KNOWN_LOCATIONS,
    WARNING_REGION_ALIASES,
    WARNING_REGION_CODE_PREFIXES,
    WARNING_REGION_DISPLAY_NAMES,
)


def _warning_line_tokens(line):
    stripped = line.strip().lstrip("#").strip()
    if not stripped:
        return []
    if "," in stripped:
        return [value.strip() for value in next(csv.reader([stripped]))]
    return re.split(r"\s+", stripped)


def parse_kma_warning_rows(text):
    """API허브 help 헤더를 기준으로 CSV와 공백 구분 응답을 모두 해석한다."""
    header = None
    rows = []
    for raw_line in str(text or "").splitlines():
        tokens = _warning_line_tokens(raw_line)
        upper_tokens = [token.upper() for token in tokens]
        if "REG_UP" in upper_tokens and "WRN" in upper_tokens:
            start = upper_tokens.index("REG_UP")
            header = [
                match.group(0) if (match := re.match(r"[A-Z][A-Z0-9_]*", token)) else token
                for token in upper_tokens[start:]
            ]
            continue
        if not tokens or raw_line.lstrip().startswith("#"):
            continue
        if header and len(tokens) >= len(header):
            row = dict(zip(header, tokens[:len(header)]))
        elif len(tokens) == len(KMA_WARNING_EXPECTED_FIELDS):
            row = dict(zip(KMA_WARNING_EXPECTED_FIELDS, tokens))
        else:
            continue
        if row.get("REG_ID") and row.get("WRN"):
            rows.append(row)
    return rows


def warning_region_aliases(location_name):
    name = str(location_name or "").strip()
    if not name or name == "현재 위치":
        return ()
    if name in WARNING_REGION_ALIASES:
        return WARNING_REGION_ALIASES[name]
    resolved = KNOWN_LOCATIONS.get(name)
    if resolved:
        return WARNING_REGION_ALIASES.get(resolved["name"], (resolved["name"],))
    return (name,)


def _warning_region_name(location_name):
    name = str(location_name or "").strip()
    if name in WARNING_REGION_CODE_PREFIXES:
        return name
    resolved = KNOWN_LOCATIONS.get(name)
    if resolved and resolved["name"] in WARNING_REGION_CODE_PREFIXES:
        return resolved["name"]
    return name


def _warning_row_matches_region(row, region_name, aliases):
    reg_id = str(row.get("REG_ID") or "").strip().upper()
    reg_up = str(row.get("REG_UP") or "").strip().upper()
    prefixes = WARNING_REGION_CODE_PREFIXES.get(region_name, ())
    region_text = " ".join((row.get("REG_UP_KO") or "", row.get("REG_KO") or ""))

    # 마이페이지 지역 날씨 카드는 육상 특보만 다룬다. 해상 S 코드를
    # 지역명 문자열로 추정하면 앞바다·먼바다 특보가 육상 카드에 섞인다.
    if reg_id.startswith("S") or reg_up.startswith("S"):
        return False

    # 일부 도서·광역시 하위구역은 REG_ID가 인접 도의 코드 계열을 공유한다.
    # 공식 REG_ID/REG_UP 전체 코드의 정확한 매핑을 접두사 판정보다 우선한다.
    override_region = (
        KMA_WARNING_REGION_CODE_OVERRIDES.get(reg_id)
        or KMA_WARNING_REGION_CODE_OVERRIDES.get(reg_up)
    )
    if override_region:
        return region_name == override_region

    if reg_id.startswith("L") and reg_id != "L1000000":
        return any(reg_id.startswith(prefix) for prefix in prefixes)
    if reg_id == "L1000000" and "전국" in region_text:
        return True
    if reg_up.startswith("L") and reg_up != "L1000000":
        return any(reg_up.startswith(prefix) for prefix in prefixes)
    if reg_up == "L1000000" and "전국" in region_text:
        return True
    return "전국" in region_text or any(alias in region_text for alias in aliases)


def _warning_area_display_name(value):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if text in METROPOLITAN_WARNING_DISPLAY_NAMES:
        return METROPOLITAN_WARNING_DISPLAY_NAMES[text]
    if text.startswith(JEJU_WARNING_CITY_PREFIXES):
        return text
    return re.sub(r"(?<=[가-힣])(시|군)(?=([가-힣]+|$|\())", "", text)


def _format_warning_region(region_name, areas):
    display_name = WARNING_REGION_DISPLAY_NAMES.get(region_name, region_name)
    compact_areas = [area for area in areas if area and area != display_name]
    # 카드 머리글에 이미 조회 기준 상위 지자체가 표시되므로 상세 행에는
    # 중복되는 상위 이름을 붙이지 않고 실제 특보 대상 하위 지역만 노출한다.
    return ", ".join(compact_areas) if compact_areas else display_name


def filter_kma_warnings(rows, location_name):
    aliases = warning_region_aliases(location_name)
    if not aliases:
        return None
    region_name = _warning_region_name(location_name)
    grouped = {}
    for row in rows:
        if str(row.get("CMD") or "").strip() in WARNING_RELEASE_COMMANDS:
            continue
        if not _warning_row_matches_region(row, region_name, aliases):
            continue
        warning_code = str(row.get("WRN") or "").strip().upper()
        level_code = str(row.get("LVL") or "").strip()
        warning_type = WARNING_TYPE_LABELS.get(warning_code, warning_code or "기상특보")
        warning_level = WARNING_LEVEL_LABELS.get(level_code, "특보")
        item = grouped.setdefault((warning_type, warning_level), {
            "type": warning_type,
            "level": warning_level,
            "region_name": WARNING_REGION_DISPLAY_NAMES.get(region_name, region_name),
            "areas": [],
            "issued_times": set(),
            "effective_times": set(),
            "warning_code": warning_code,
            "level_code": level_code,
        })
        area = _warning_area_display_name(row.get("REG_KO") or row.get("REG_UP_KO"))
        if area and area not in item["areas"]:
            item["areas"].append(area)
        if row.get("TM_FC"):
            item["issued_times"].add(row["TM_FC"])
        if row.get("TM_EF"):
            item["effective_times"].add(row["TM_EF"])

    alerts = []
    for item in grouped.values():
        issued_times = item.pop("issued_times")
        effective_times = item.pop("effective_times")
        item["issued_at"] = next(iter(issued_times)) if len(issued_times) == 1 else ""
        item["effective_at"] = next(iter(effective_times)) if len(effective_times) == 1 else ""
        item["region"] = _format_warning_region(region_name, item["areas"])
        alerts.append(item)

    return sorted(
        alerts,
        key=lambda item: (KMA_WARNING_LEVEL_PRIORITY.get(item["level"], 0), item["type"]),
        reverse=True,
    )
