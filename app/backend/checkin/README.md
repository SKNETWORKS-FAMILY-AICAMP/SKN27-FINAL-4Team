# 오늘의 나 찾기

## 운영 데이터 import

기본 개발용 최소 데이터는 다음 명령으로 넣습니다.

```powershell
python manage.py migrate
python manage.py import_checkin_content
```

운영 번들 JSON, CSV 폴더, ZIP도 같은 명령으로 가져올 수 있습니다.

```powershell
python manage.py import_checkin_content --source path/to/checkin_content_bundle.json
python manage.py import_checkin_content --source path/to/content-folder
python manage.py import_checkin_content --source path/to/content-bundle.zip
```

## API

- `GET /api/checkin/bootstrap/`
- `POST /api/checkin/`
- `PATCH /api/checkin/{id}/reflection/`
- `PATCH /api/checkin/{id}/cause/`
- `PATCH /api/checkin/{id}/need/`
- `POST /api/checkin/{id}/recommendations/`
- `POST /api/checkin/{id}/complete/`
- `POST /api/checkin/{id}/feedback/`
- `GET /api/checkin/today/`
- `GET /api/insights/weekly/current/`

모든 체크인 데이터는 로그인한 사용자 본인 기록만 조회·수정할 수 있으며, 날짜별로 하나의 체크인만 생성됩니다.
