# app/ — Django 웹 서비스 애플리케이션 공간

Django 백엔드 API 서버와 Vue 프론트엔드가 위치합니다.

## 폴더 구조

| 폴더 | 역할 |
|---|---|
| `backend/` | Django REST API 서버 — 챗봇 세션, 사용자 인증, 온보딩, 마이페이지, 감정 리포트, 타로 등 앱별 모듈 |
| `frontend/` | Vue 3 + Vite 프론트엔드 — 챗봇 UI, 온보딩, 마이페이지, 캘린더, 마음 리포트 화면 |
| `Dockerfile` | 백엔드 컨테이너 빌드 설정 |
