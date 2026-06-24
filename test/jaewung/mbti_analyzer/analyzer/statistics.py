from __future__ import annotations

from collections import defaultdict

from test.jaewung.mbti_analyzer.analyzer.schemas import AxisScore, MbtiEvidenceRecord, MbtiPeriodResult


class MbtiStatisticsEngine:
    """
    LLM 결과를 점수화하지 않는다.
    저장된 evidence record를 deterministic하게 count하고 ratio를 계산한다.
    """

    AXIS_SELECTION_RULES = {
        "IE": ("I", "E"),
        "SN": ("N", "S"),
        "TF": ("F", "T"),
        "JP": ("J", "P"),
    }

    AXIS_ORDER = ["IE", "SN", "TF", "JP"]

    def aggregate(
        self,
        *,
        user_id: int,
        period_type: str,
        period_key: str,
        source_message_count: int,
        evidence_records: list[MbtiEvidenceRecord],
    ) -> MbtiPeriodResult:
        unique_records = self._dedupe(evidence_records)

        counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for record in unique_records:
            counts[record.axis][record.pole] += 1

        axis_scores: dict[str, AxisScore] = {}

        for axis in self.AXIS_ORDER:
            first_pole, second_pole = self.AXIS_SELECTION_RULES[axis]

            first_count = counts[axis][first_pole]
            second_count = counts[axis][second_pole]
            total = first_count + second_count

            if total == 0:
                selected = None
                first_ratio = 0.0
                second_ratio = 0.0
            else:
                first_ratio = round(first_count / total * 100, 2)
                second_ratio = round(second_count / total * 100, 2)

                # 문서의 otherwise 규칙을 따른다.
                # IE: I > E면 I, 아니면 E
                # SN: N > S면 N, 아니면 S
                # TF: F > T면 F, 아니면 T
                # JP: J > P면 J, 아니면 P
                selected = first_pole if first_ratio > second_ratio else second_pole

            axis_scores[axis] = AxisScore(
                selected=selected,
                ratios={
                    first_pole: first_ratio,
                    second_pole: second_ratio,
                },
                counts={
                    first_pole: first_count,
                    second_pole: second_count,
                },
            )

        estimated_type = self._build_estimated_type(axis_scores)

        coded_message_count = len(
            {
                record.message_id
                for record in unique_records
                if record.coding_status == "coded"
            }
        )

        return MbtiPeriodResult(
            user_id=user_id,
            period_type=period_type,
            period_key=period_key,
            source_message_count=source_message_count,
            coded_message_count=coded_message_count,
            axis_scores=axis_scores,
            estimated_type=estimated_type,
        )

    def _dedupe(
        self,
        records: list[MbtiEvidenceRecord],
    ) -> list[MbtiEvidenceRecord]:
        seen: set[tuple[str, str, str, str]] = set()
        unique_records: list[MbtiEvidenceRecord] = []

        for record in records:
            key = (
                record.message_id,
                record.axis,
                record.pole,
                record.normalized_keyword,
            )

            if key in seen:
                continue

            seen.add(key)
            unique_records.append(record)

        return unique_records

    def _build_estimated_type(
        self,
        axis_scores: dict[str, AxisScore],
    ) -> str:
        letters: list[str] = []

        for axis in self.AXIS_ORDER:
            selected = axis_scores[axis].selected
            letters.append(selected if selected else "?")

        return "".join(letters)