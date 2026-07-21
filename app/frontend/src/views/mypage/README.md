# mypage

마이페이지는 `/mypage` 단일 라우트에서 대시보드와 기능별 모달을 제공합니다.

## 주요 구성

- `mypage.vue`: 화면 상태와 기능별 데이터 로딩을 조정하는 컨테이너
- `mypage.api.js`: 기존 import 경로를 유지하는 API 진입점과 기억 보관함 임시 연동
- `services/`: 프로필·MBTI·날씨·도서·기억보관함 도메인별 API 호출
- `state/mypage.state.js`: 화면 초기 상태와 표시 언어 데이터
- `config/mypage.constants.js`: 캐릭터, 패널, 저장소 키, 시간 설정 등 공통 설정
- `config/profile.constants.js`: 프로필 입력 규칙
- `utils/profile.preferences.js`: 관심사·취미 CSV 파싱과 그룹화
- `components/`: 기능별 표시 컴포넌트
- `config/room.config.js`: 방 이동 좌표·장애물·캐릭터 이동 설정
- `config/book.config.js`: 도서 추천 테마와 출처 표시 설정
- `config/mbti.constants.js`: MBTI 선택지와 Q&A 완료 기준
- `config/weather.constants.js`: 날씨 표시 구간과 색상·시간 기준
- `config/memory.constants.js`: 기억 API 경로와 감정·취향 표시 규칙
- `utils/memory.formatters.js`: 기억 응답 정규화와 날짜·그래프 맥락 포맷
- `styles/mypage.css`: 기존 캐스케이드를 유지하는 마이페이지 스타일 진입점
- `styles/sections/`: 화면 영역과 반응형·재정의 순서로 분리한 마이페이지 스타일

## 연결 API

- `GET/PUT /api/myprofile/profile/`
- `GET /api/mbti/monthly-demo/`
- `POST /api/mbti/onboarding/`
- `GET /api/myweather/current/`
- `GET /api/myweather/regions/`
- `GET /api/mybook/recommendation/`
- `GET /api/mymemory/memories/`
- `DELETE /api/mymemory/memories/<memory_id>/`
