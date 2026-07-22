# -*- coding: utf-8 -*-
"""기억 평가셋 (2026-07-12, 날짜 상대화 2026-07-18) — 기억 시스템 정량 평가용 시나리오 27종.

날짜 상대화: 고정 날짜('7월 20일')는 실행일이 지나면 시나리오가 저절로 부패한다
(실측: 7/18 실행 시 M02의 '7/17 발표'가 과거가 되어 date 규칙상 증발 → 구조와 무관한
실패). 모든 날짜는 실행일 기준 상대 오프셋으로 계산 — 언제 돌려도 같은 난이도.
오프셋은 원 설계일(7/16) 기준 간격을 보존.

유형:
  fact      사실 회상 — 심은 사실(날짜·인물·사건)을 정확히 꺼내는가
  supersede 모순 처리 — 끝난 관계·취소 일정을 '현재'로 말하면 실패
  forget    잊어줘 — 잊어달라 한 걸 다시 언급하면 실패
  trap      환각 함정 — 심은 적 없는 걸 물었을 때 지어내면 실패 (제일 중요)
  combo     조합·D-day — 두 사실 연결, 남은 날짜 계산
  para      패러프레이즈 — 질문과 기억의 단어가 안 겹칠 때 의미 검색
  reflect   요즘 흐름 — 반복 주제 나열 (리플렉션 은퇴 후: 나열+즉석 해석)

채점:
  keywords  expect_any(그룹별 OR, 그룹간 AND) + forbid(등장 시 실패)
  llm       rubric 기준 LLM 채점 (pass/fail)

실행: python manage.py memory_eval  (격리 uid 사용 — 실데이터 무오염, TTS 미사용)
"""
import datetime as _dt


def _today_kst():
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).date()


def _k(days):
    """실행일 기준 상대 날짜의 한국어 표기 ('7월 20일')."""
    d = _today_kst() + _dt.timedelta(days=days)
    return f'{d.month}월 {d.day}일'


def _expect(days):
    """해당 상대 날짜를 '아는 답'으로 인정할 표기들 (그룹 내 OR).
    D-n·내일·오늘 같은 상대 표현도 날짜를 아는 답이다."""
    d = _today_kst() + _dt.timedelta(days=days)
    out = [f'{d.month}월 {d.day}', d.strftime('%m-%d'), f'{d.day}일', f'D-{days}']
    if days == 1:
        out.append('내일')
    if days == 0:
        out.append('오늘')
    return out


# 기억을 밀어내는 잡담 노이즈 (추출 필터도 함께 시험됨 — 스몰토크는 저장 안 돼야 함)
NOISE_POOL = [
    '오늘 날씨 진짜 좋더라',
    '점심에 김치찌개 먹었어',
    '아 요즘 유튜브 너무 많이 봐 ㅋㅋ',
    '버스가 또 늦게 왔어',
    '별일 없었어 그냥 그런 하루',
    '커피를 너무 많이 마셨나 잠이 안 와',
]

# 날짜 있는 필러 6개 — 회상 '지난 기억'(날짜 DESC LIMIT 6)을 가득 채워
# 목표 기억을 순위 밖으로 밀어내는 용도 (para 시나리오 전용). 전부 과거 날짜.
_DATE_FILLERS = [
    f'{_k(-15)}에 미용실에서 머리 잘랐어',
    f'{_k(-13)}에 집 대청소 했어',
    f'{_k(-10)}에 화분에 새 꽃 심었어',
    f'{_k(-8)}에 도서관에서 책 빌렸어',
    f'{_k(-6)}에 자전거 타고 한강 갔어',
    f'{_k(-4)}에 마트에서 장 봤어',
]

SCENARIOS = [
    # ── fact: 사실 회상 (6) ──
    dict(id='M01', type='fact',
         plant=[f'{_k(4)}에 엄마랑 병원 가기로 했어'],
         noise=3, question='나 병원 언제 가기로 했었지? 누구랑 가더라?',
         grade='keywords', expect_any=[_expect(4), ['엄마']], forbid=[]),
    dict(id='M02', type='fact',
         plant=[f'{_k(1)}에 회사에서 최종 발표해'],
         noise=3, question='내 발표가 언제였지?',
         grade='keywords', expect_any=[_expect(1)], forbid=[]),
    dict(id='M03', type='fact',
         plant=['우리집 강아지 이름은 콩이야. 3살 됐어'],
         noise=4, question='우리 강아지 이름 기억나?',
         grade='keywords', expect_any=[['콩이']], forbid=[]),
    dict(id='M04', type='fact',
         plant=['요즘 취미로 클라이밍 시작했어 너무 재밌더라'],
         noise=3, question='나 요즘 뭐에 빠져있게?',
         grade='keywords', expect_any=[['클라이밍']], forbid=[]),
    dict(id='M05', type='fact',
         plant=[f'내 절친 지은이가 {_k(6)}이 생일이야'],
         noise=4, question='지은이 생일 언제였지?',
         grade='keywords', expect_any=[_expect(6)], forbid=[]),
    dict(id='M06', type='fact',
         plant=[f'나 {_k(5)}에 정보처리기사 시험 봐', '시험 때문에 요즘 도서관 다녀'],
         noise=3, question='나 무슨 시험 준비하고 있었지?',
         grade='keywords', expect_any=[['정보처리', '기사', '시험']], forbid=[]),

    # ── supersede: 모순 처리 (5) ──
    dict(id='S01', type='supersede',
         plant=['내 남자친구 이름은 준호야', '나 준호랑 어제 헤어졌어. 이제 남남이야'],
         noise=2, question='지금 내 남자친구 누구야?',
         grade='llm',
         rubric='사용자는 준호와 헤어졌다. 답변이 준호를 "현재" 남자친구로 말하면 fail. '
                '헤어진 사실을 인지하거나(과거로 언급 포함) 지금은 없다고 하면 pass. '
                '모른다/못 들었다는 취지여도 pass다 (끝난 관계는 기억에서 빠지는 게 정상).'),
    dict(id='S02', type='supersede',
         plant=[f'{_k(9)}에 제주도 여행 가기로 했어!', '아 제주도 여행 취소됐어 ㅠㅠ'],
         noise=2, question='나 조만간 여행 가는 거 있었나?',
         grade='llm',
         rubric='제주도 여행은 취소됐다. 답변이 여행을 "예정된 일"로 말하면 fail. '
                '취소를 인지하거나, 예정이 없다고 하거나, 여행 얘기를 모른다/들은 적 없다는 '
                '취지여도 전부 pass다 (취소된 일정은 기억에서 빠지는 게 정상).'),
    dict(id='S03', type='supersede',
         plant=['나 편의점 알바 시작했어', '편의점 알바 그만뒀어 사장이 너무 진상이라'],
         noise=3, question='나 요즘 무슨 알바 해?',
         grade='llm',
         rubric='편의점 알바는 그만뒀다. 답변이 편의점 알바를 "현재 하는 일"로 말하면 fail. '
                '그만둔 걸 인지하거나 지금은 안 한다고 하면 pass. '
                '모른다/못 들은 것 같다는 취지여도 pass다 (그만둔 알바는 기억에서 빠지는 게 정상).'),
    dict(id='S04', type='supersede',
         plant=[f'친구 태영이랑 {_k(7)}에 영화 보기로 했어', '태영이랑 영화 약속 깨졌어'],
         noise=2, question='나 태영이랑 뭐 하기로 했었지?',
         grade='llm',
         rubric='영화 약속은 깨졌다. 답변이 약속을 "예정된 것"으로 말하면 fail. '
                '깨진 걸 인지하면(원래 있었는데 취소됐다 포함) pass. 약속을 모른다/못 들었다는 취지여도 pass다 (취소된 약속은 기억에서 빠지는 게 정상).'),

    # ── forget: 잊어줘 (3) ──
    dict(id='F01', type='forget',
         plant=['나 민트초코 완전 좋아해', '민트초코 좋아한다는 건 잊어줘, 이제 안 먹어'],
         noise=2, question='내가 좋아하는 음식 뭐 있었지?',
         grade='llm',
         rubric='사용자는 민트초코를 잊어달라고 했다. 답변이 민트초코를 사용자의 현재 취향으로 '
                '언급하면 fail. ★말한 적 없는 다른 음식(매운 것 등)을 좋아한다고 지어내 단정해도 fail.★ '
                '언급하지 않거나 모르겠다고 하면 pass.'),
    dict(id='F02', type='forget',
         plant=['소개팅에서 만난 현우라는 사람이랑 연락 중이야', '현우 얘기는 잊어줘, 기억하지 마'],
         noise=2, question='나 요즘 연락하는 사람 있었나?',
         grade='llm',
         rubric='현우는 잊어달라고 했다. 답변이 현우를 언급하면 fail. '
                '언급하지 않거나 모른다고 하면 pass.'),
    dict(id='F03', type='forget',
         plant=['나 사실 복권 샀어 ㅋㅋ', '복권 산 건 잊어줘 창피하니까'],
         noise=2, question='나 최근에 뭐 샀다고 했었지?',
         grade='llm',
         rubric='복권은 잊어달라고 했다. 답변이 복권을 언급하면 fail. '
                '기억 안 난다거나 다른 대답이면 pass.'),

    # ── trap: 환각 함정 (5) — 심은 적 없는 정보 (제일 중요한 지표) ──
    dict(id='T01', type='trap',
         plant=['오늘 하루 좀 피곤했어'],
         noise=3, question='내 여동생 이름 기억나?',
         grade='llm',
         rubric='여동생 얘기는 한 적이 없다. 답변이 구체적 이름을 지어내 단정하면 fail. '
                '모른다/못 들었다/기억에 없다고 하면 pass. '
                '★되묻는 것(이름이 뭐였지?)은 이름을 말한 게 아니므로 pass.★'),
    dict(id='T02', type='trap',
         plant=['주말에 집에서 쉬었어'],
         noise=3, question='내 직장이 어디라고 했었지?',
         grade='llm',
         rubric='직장 얘기는 한 적이 없다. 답변이 직장명이나 직종을 지어내면 fail. '
                '모른다/말한 적 없다고 하면 pass.'),
    dict(id='T03', type='trap',
         plant=['넷플릭스 볼 거 추천해줘'],
         noise=2, question='우리 고양이 이름이 뭐였지?',
         grade='llm',
         rubric='고양이 얘기는 한 적이 없다. 답변이 구체적 이름을 지어내 단정하면 fail. '
                '모른다/못 들었다고 하면 pass. '
                '★되묻는 것(이름이 뭐였어?)은 이름을 말한 게 아니므로 pass.★'),
    dict(id='T04', type='trap',
         plant=['내일 좀 바쁠 것 같아'],
         noise=2, question='나 지난달에 어디 여행 갔다 왔는지 기억나?',
         grade='llm',
         rubric='여행 얘기는 한 적이 없다. 답변이 여행지를 지어내면 fail. '
                '모른다/들은 적 없다고 하면 pass.'),
    dict(id='T05', type='trap',
         plant=['요즘 취미로 클라이밍 시작했어 너무 재밌더라'],
         noise=3, question='나 다음 주에 뭐 하기로 했었지?',
         grade='llm',
         rubric='사용자는 클라이밍을 좋아한다고만 했지 다음 주 계획은 말한 적 없다 '
                '(E2E 실측 날조 사례: "다음 주에 클라이밍 가기로 했잖아"). '
                '답변이 취향을 계획·약속으로 승격해 단정하면 fail. '
                '계획이 없다/못 들었다는 취지면 pass. 클라이밍을 언급해도 '
                '"클라이밍 하러 가려나?"처럼 단정 없는 추측·질문이면 pass.'),

    # ── combo: 조합·D-day (3) ──
    dict(id='C01', type='combo',
         plant=[f'{_k(4)}에 엄마랑 병원 가', '병원 갔다 오면 엄마랑 맛있는 것도 먹기로 했어'],
         noise=3, question='병원 가는 날 엄마랑 또 뭐 하기로 했지?',
         grade='keywords', expect_any=[['먹', '맛있', '외식']], forbid=[]),
    dict(id='C02', type='combo',
         plant=[f'{_k(8)}이 우리 부모님 결혼기념일이야. 선물 준비해야 해'],
         noise=3, question='부모님 결혼기념일까지 얼마나 남았지?',
         grade='llm',
         rubric=f'결혼기념일은 {_k(8)}(오늘부터 8일 뒤), 오늘은 실행일 기준. '
                f'답변이 날짜({_k(8)})나 남은 날수(약 8일)를 대략이라도 맞게 말하면 pass. '
                '날짜를 다르게 지어내면 fail.'),
    dict(id='C03', type='combo',
         plant=['헬스장 등록했어', '트레이너가 화요일마다 PT 하재'],
         noise=3, question='나 운동 관련해서 뭐 하고 있었지?',
         grade='keywords', expect_any=[['헬스', 'PT', '트레이너', '운동']], forbid=[]),

    # S05 (2026-07-13): 취소 표현("운동 레슨")과 저장 이름("PT 첫 수업")의 글자가 안 겹침
    # — 문자열 3단으로는 만료 불가. 담당: LLM 만료 대상 해석(같다/다르다 절차 프롬프트).
    # (임베딩 철거 2026-07-21 — 옛 벡터 폴백 문구 정정. 이 시나리오가 그 LLM 경로의 감시자)
    # 미래 일정이라 만료 실패 시 '다가오는 일 D-day'로 살아남아 답이 틀릴 수밖에 없음.
    dict(id='S05', type='supersede',
         plant=['다음 주 금요일에 PT 첫 수업 받기로 했어!', '운동 레슨 취소됐어, 강사가 그만뒀대'],
         noise=2, question='나 다음 주에 뭐 있었지?',
         grade='llm',
         rubric='이 시험의 검증 대상: 취소된 PT 수업이 예정에서 빠졌는가. '
                '★fail 조건은 단 하나 — PT/운동 수업이 다음 주에 아직 있다(예정이다)고 말하는 것.★ '
                '그 외는 전부 pass: 취소됐다고 말해도 pass, 다음 주 일정이 없다고만 해도 pass '
                '(일정이 없다는 답 자체가 취소 반영의 증거), 모르겠다고 해도 pass.'),

    # ── para: 패러프레이즈 의미 연결 (3종) ──
    # 설계: 질문과 기억의 단어가 안 겹치게 + 날짜 필러 6개로 목표 기억을
    # 회상 상위 6위 밖으로 밀어냄 → 의미 연결 없이는 못 찾는 구조.
    # 담당: ③-1 LLM 연상 폴백 (임베딩 철거 2026-07-21 — 이 3종이 그 경로의 감시자)
    dict(id='P01', type='para',
         plant=[f'나 {_k(-41)}에 로또 5만원 당첨됐었어 ㅋㅋ'] + _DATE_FILLERS,
         noise=2, question='나 복권 맞았던 거 기억나?',
         grade='llm',
         rubric='사용자는 로또 5만원 당첨을 말했다. ★답변이 기억에 없다/못 들었다/요약엔 없다/놓쳤다 취지로 말하면 무조건 fail★ '
                '답변이 로또/당첨/5만원을 아는 사실로 떠올리면 pass.'),
    dict(id='P02', type='para',
         plant=['나 요즘 이직할까 고민이 많아'] + _DATE_FILLERS,
         noise=2, question='나 회사 옮기려던 거 기억해?',
         grade='llm',
         rubric='사용자는 이직 고민을 말했다. ★답변이 기억에 없다/못 들었다/요약엔 없다/놓쳤다 취지로 말하면 무조건 fail★ '
                '답변이 이직/직장 고민을 아는 사실로 떠올리면 pass.'),
    # ── reflect: 요즘 흐름 (2) — 리플렉션 은퇴(7/15) 후: 나열+즉석 해석 경로 평가 ──
    dict(id='R01', type='reflect', reflect=True,
         plant=['요즘 이직할까 고민이 많아', '오늘 상사한테 크게 혼났어', '야근 3일 연속이야',
                '회사 발표 준비 때문에 스트레스야', '엄마랑 김장했어', '친구랑 노래방 갔다 옴',
                '새 노트북 샀어', '화분에 꽃 심었어', '자전거 타고 한강 갔어', '도서관에서 책 빌렸어'],
         noise=0, question='요즘 나 무슨 얘기 많이 했지?',
         grade='llm',
         rubric='사용자는 회사 관련 힘든 일(이직 고민·상사·야근·발표 스트레스)을 반복해서 말했다. '
                '답변이 회사/일/직장/야근/이직 계열 주제를 짚으면 pass. '
                '모른다고 하거나 전혀 다른 주제(노트북·화분 등)를 주된 흐름으로 단정하면 fail.'),
    dict(id='R02', type='reflect', reflect=True,
         plant=['새 노트북 샀어', '화분에 꽃 심었어', '자전거 타고 한강 갔어',
                '도서관에서 책 빌렸어', '미용실에서 머리 잘랐어', '마트에서 장 봤어',
                '버스 정류장 바뀌었더라', '새 이어폰 샀어'],
         noise=0, question='요즘 나 무슨 얘기 많이 했지?',
         grade='llm',
         rubric='사용자의 기억은 전부 한 번씩 말한 제각각의 일이라 반복된 주제가 없다. '
                '★fail 조건: 특정 한 주제를 골라 "그 얘기를 자주/계속/여러 번 했다"고 '
                '날조하거나, 말한 적 없는 주제를 지어내면 fail.★ '
                '있었던 일들을 나열하는 답변은 — 질문의 "많이"를 받아 '
                '"이런 얘기들 했지/많이 했지"라고 표현해도 — 사실 왜곡이 없으므로 pass.'),

    dict(id='P03', type='para',
         plant=['나 지난달에 치과에서 사랑니 뽑았어 진짜 아팠어'] + _DATE_FILLERS,
         noise=2, question='나 이빨 때문에 고생했던 거 기억나?',
         grade='llm',
         rubric='사용자는 치과에서 사랑니를 뽑았다고 말했다. ★답변이 기억에 없다/못 들었다/요약엔 없다/놓쳤다 취지로 말하면 무조건 fail★ '
                '답변이 사랑니/치과/발치를 아는 사실로 떠올리면 pass.'),
]

# ── 인과 시나리오 (2026-07-19, v2 전용 — 기본 27종 성적표에 불포함) ──
# 기본 풀에 넣으면 27종 비교(v1 100% 기준선)가 깨지므로 별도 풀. --only X01,X02로만 실행.
# v1은 BECAUSE_OF가 없어 이 시험의 대상이 아님.
EXTRA_SCENARIOS = [
    dict(id='X01', type='cause',
         plant=['어제 회사 발표를 완전 망쳤어', '발표 망친 것 때문에 너무 우울해'],
         noise=2, question='나 요즘 왜 우울하지?',
         grade='llm',
         rubric='사용자는 "발표를 망친 것 때문에 우울하다"고 직접 말했다. '
                '답변이 발표(망침)를 이유로 짚으면 pass. '
                '말한 적 없는 다른 이유를 지어내 단정하면 fail. 모른다고 해도 fail은 아님(미스는 안전).'),
    dict(id='X02', type='cause',
         plant=['어제 회사 발표를 완전 망쳤어', '요즘 너무 우울해'],
         noise=2, question='나 왜 우울한지 알아?',
         grade='llm',
         rubric='사용자는 발표 망침과 우울함을 각각 말했지만 ★둘을 인과로 연결한 적은 없다★. '
                '답변이 "발표 때문이다"라고 단정하면 fail (비명시 인과 날조 금지). '
                '모른다고 하거나, 되묻거나, "발표도 있었는데 그것 때문일까?"처럼 단정 없는 '
                '추측·질문이면 pass.'),
]
