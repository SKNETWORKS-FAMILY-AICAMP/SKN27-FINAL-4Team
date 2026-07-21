import os
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import SimpleTestCase

from .agent import WeatherWebAgent
from .service.insight_cache_service import get_or_create_weather_insight
from .service.life_index_service import fetch_uv_index
from .services import (
    _request_kma_json,
    fetch_current_weather,
    filter_kma_warnings,
    merge_forecast_rainfall,
    merge_weekly_forecasts,
    parse_kma_warning_rows,
    parse_mid_forecast_items,
    parse_short_forecast_items,
    parse_ultra_short_forecast_items,
    resolve_location,
)


class RainfallMergeTests(SimpleTestCase):
    def test_uses_rainy_forecast_when_observation_is_zero(self):
        forecast = {
            "forecast_precipitation_type": "1",
            "forecast_rainfall_1h": "1.0mm 미만",
        }
        self.assertEqual(merge_forecast_rainfall("0", forecast), "1.0mm 미만")

    def test_keeps_positive_observation_over_forecast(self):
        forecast = {
            "forecast_precipitation_type": "1",
            "forecast_rainfall_1h": "1.0mm 미만",
        }
        self.assertEqual(merge_forecast_rainfall("2.5", forecast), "2.5")

    def test_does_not_apply_dry_forecast_rainfall(self):
        forecast = {
            "forecast_precipitation_type": "0",
            "forecast_rainfall_1h": "강수없음",
        }
        self.assertEqual(merge_forecast_rainfall("0", forecast), "0")


class WeatherInsightCacheServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_reuses_analysis_when_relevant_weather_state_is_unchanged(self):
        weather = {
            "base_date": "20260718",
            "base_time": "1200",
            "condition": "맑음",
            "temperature": 28,
            "location": {"name": "서울"},
            "weekly_forecasts": [],
            "weather_alerts": {"status": "none", "items": []},
        }
        profile = {"hobbies": ["산책"], "today_emotion": "평온"}
        analyzer = Mock(return_value={"weatherAnalysis": "안내", "is_fallback": False})

        first, first_cache_hit = get_or_create_weather_insight(
            weather, 7, profile, analyzer
        )
        second, second_cache_hit = get_or_create_weather_insight(
            weather, 7, profile, analyzer
        )

        self.assertFalse(first_cache_hit)
        self.assertTrue(second_cache_hit)
        self.assertEqual(first, second)
        analyzer.assert_called_once_with(weather, profile)


class WeatherLocationResolutionTests(SimpleTestCase):
    def test_default_location_is_a_plain_serializable_mapping(self):
        location = resolve_location()

        self.assertIsInstance(location, dict)
        self.assertTrue({"name", "lat", "lon"}.issubset(location))

    def test_current_coordinates_are_labeled_with_nearest_supported_region(self):
        location = resolve_location(
            lat=37.5665,
            lon=126.9780,
            region="현재 위치",
        )

        self.assertEqual(location["name"], "서울")
        self.assertTrue(location["is_current_location"])
        self.assertEqual(location["location_resolution"], "nearest_supported_region")


class WeatherExternalProcessingTests(SimpleTestCase):
    def test_only_https_urls_from_allowed_domains_are_exposed(self):
        domains = ['weather.naver.com', 'weatheri.co.kr', 'kweather.co.kr']
        self.assertTrue(
            WeatherWebAgent._is_safe_source_url(
                'https://weather.naver.com/today/example',
                domains,
            )
        )
        self.assertTrue(
            WeatherWebAgent._is_safe_source_url('https://www.weatheri.co.kr/example', domains)
        )
        self.assertFalse(
            WeatherWebAgent._is_safe_source_url('http://weather.naver.com/example', domains)
        )
        self.assertFalse(
            WeatherWebAgent._is_safe_source_url('https://weather.naver.com.evil.example', domains)
        )

    def test_default_tavily_domains_are_the_requested_private_weather_services(self):
        with patch.dict(os.environ, {'TAVILY_INCLUDE_DOMAINS': ''}):
            self.assertEqual(
                WeatherWebAgent._tavily_domains(),
                ['weather.naver.com', 'weatheri.co.kr', 'kweather.co.kr'],
            )

    @patch.dict(os.environ, {'TAVILY_API_KEY': 'test-key', 'TAVILY_INCLUDE_DOMAINS': ''})
    @patch('myweather.agent.cache.set')
    @patch('myweather.agent.cache.get', return_value=None)
    @patch('myweather.agent.requests.post')
    def test_tavily_queries_providers_and_exposes_only_allowed_domains(
        self,
        request_post,
        cache_get,
        cache_set,
    ):
        response = Mock(status_code=200)
        response.json.return_value = {
            'results': [
                {'title': '서울 관광 날씨', 'url': 'https://korean.visitseoul.net/weather', 'content': '제외'},
                {'title': '네이버 날씨', 'url': 'https://weather.naver.com/today', 'content': '생활 날씨'},
                {'title': '케이웨더', 'url': 'https://weather.kweather.co.kr/forecast', 'content': '외출 참고'},
            ]
        }
        request_post.return_value = response

        context = WeatherWebAgent._search_weather_context({'location': {'name': '서울'}})

        payload = request_post.call_args.kwargs['json']
        self.assertNotIn('include_domains', payload)
        self.assertIn('네이버 날씨 웨더아이 케이웨더', payload['query'])
        self.assertEqual(
            [source['url'] for source in context['sources']],
            ['https://weather.naver.com/today', 'https://weather.kweather.co.kr/forecast'],
        )

    def test_openai_prompt_excludes_demographics_and_mbti_values(self):
        weather = {
            'condition': '맑음',
            'temperature': 24,
            'humidity': 50,
            'rainfall_1h': 0,
            'wind_speed': 1,
            'location': {'name': '서울'},
            'weekly_forecasts': [{
                'date': '2026-07-16',
                'day': '7/16(목)',
                'condition': '구름많음',
                'min_temperature': 23,
                'max_temperature': 30,
                'precipitation_probability': 40,
                'source': '기상청 API허브 단기예보',
            }],
        }
        profile = {
            'age': 33,
            'gender': '여',
            'mbti': 'INTJ',
            'hobbies': ['사진'],
            'today_emotion': '평온',
        }
        prompt = WeatherWebAgent._build_prompt(
            weather,
            profile,
            {'answer': '공개 날씨 요약'},
            WeatherWebAgent._calculate_weather_indices(weather),
        )

        self.assertNotIn('33세', prompt)
        self.assertNotIn('INTJ', prompt)
        self.assertNotIn('사용자: 여', prompt)
        self.assertIn('[기상청 API허브 초단기예보]', prompt)
        self.assertIn('[기상청 API허브 주간예보]', prompt)
        self.assertIn('주간예보를 요약', prompt)
        self.assertIn('민간 검색 결과와 다르면 API허브를 우선', prompt)

    def test_indices_use_deterministic_observations_and_explicit_scales(self):
        weather = {
            'base_date': '20260715',
            'base_time': '1200',
            'temperature': 30,
            'humidity': 70,
            'wind_speed': 2,
            'uv_index': {'status': 'available', 'value': 9},
        }
        indices = WeatherWebAgent._calculate_weather_indices(weather)

        self.assertEqual(list(indices), ['불쾌지수', '체감온도', '식중독지수', '자외선지수'])
        self.assertEqual(indices['불쾌지수']['value'], 81.4)
        self.assertEqual(indices['불쾌지수']['gauge_percent'], 71.3)
        self.assertEqual(indices['불쾌지수']['level'], '매우 높음')
        self.assertEqual(indices['불쾌지수']['severity'], 'danger')
        self.assertEqual(
            [band['level'] for band in indices['불쾌지수']['bands']],
            ['낮음', '보통', '높음', '매우 높음'],
        )
        self.assertTrue(indices['체감온도']['derived'])
        self.assertEqual(indices['체감온도']['level'], '관심')
        self.assertEqual(
            [band['level'] for band in indices['체감온도']['bands']],
            ['기준 미만', '관심', '주의', '경고', '위험'],
        )
        self.assertEqual(indices['식중독지수']['value'], 67.7)
        self.assertEqual(indices['식중독지수']['level'], '주의')
        self.assertEqual(indices['자외선지수']['value'], 9.0)
        self.assertEqual(indices['자외선지수']['level'], '매우 높음')
        self.assertFalse(indices['자외선지수']['derived'])
        self.assertIn('getUVIdxV5', indices['자외선지수']['method'])
        self.assertNotIn('습도', indices)
        self.assertNotIn('풍속', indices)
        self.assertNotIn('감기가능지수', indices)

    def test_uv_index_has_no_calculated_or_dummy_fallback(self):
        official = WeatherWebAgent._calculate_weather_indices({
            'uv_index': {'status': 'available', 'value': 6.2},
        })['자외선지수']
        unavailable = WeatherWebAgent._calculate_weather_indices({
            'temperature': 35,
            'humidity': 15,
            'wind_speed': 10,
        })['자외선지수']

        self.assertEqual(official['value'], 6.2)
        self.assertEqual(official['level'], '높음')
        self.assertTrue(official['available'])
        self.assertFalse(unavailable['available'])
        self.assertIsNone(unavailable['value'])
        self.assertEqual(unavailable['severity'], 'unavailable')

    def test_winter_apparent_temperature_uses_official_calculation_boundary(self):
        applicable = WeatherWebAgent._calculate_weather_indices({
            'base_date': '20260115',
            'temperature': 0,
            'humidity': 50,
            'wind_speed': 1.3,
        })['체감온도']
        outside = WeatherWebAgent._calculate_weather_indices({
            'base_date': '20260115',
            'temperature': 0,
            'humidity': 50,
            'wind_speed': 1.29,
        })['체감온도']

        self.assertTrue(applicable['available'])
        self.assertEqual(applicable['level'], '관심')
        self.assertIn('기온·풍속', applicable['method'])
        self.assertFalse(outside['available'])
        self.assertIn('산출 조건 밖', outside['status'])

    def test_recommendations_are_normalized_to_summary_and_actions(self):
        recommendations = WeatherWebAgent._normalize_recommendations([
            {
                'title': '우산 준비',
                'reason': '오후에 비가 옵니다.',
                'howTo': '접이식 우산을 가방에 넣으세요.',
            }
        ])

        self.assertEqual(recommendations[0]['summary'], '오후에 비가 옵니다.')
        self.assertEqual(recommendations[0]['actions'], ['접이식 우산을 가방에 넣으세요.'])
        self.assertNotIn('reason', recommendations[0])
        self.assertNotIn('howTo', recommendations[0])

    def test_general_recommendations_precede_one_hobby_recommendation(self):
        recommendations = WeatherWebAgent._normalize_recommendations(
            [
                {'kind': 'hobby', 'title': '사진 산책', 'summary': '사진을 찍어요.', 'actions': ['카메라 챙기기']},
                {'kind': 'general', 'title': '우산 준비', 'summary': '비에 대비해요.', 'actions': ['우산 챙기기']},
                {'kind': 'general', 'title': '겉옷 준비', 'summary': '기온에 대비해요.', 'actions': ['겉옷 챙기기']},
            ],
            {'condition': '흐림'},
            {'hobbies': ['사진']},
        )

        self.assertEqual([item['kind'] for item in recommendations], ['general', 'general', 'hobby'])
        self.assertEqual([item['title'] for item in recommendations], ['우산 준비', '겉옷 준비', '사진 산책'])

    def test_fallback_does_not_expose_synthetic_recommendations(self):
        result = WeatherWebAgent._fallback(
            {'condition': '맑음', 'temperature': 24, 'humidity': 50},
            WeatherWebAgent._empty_tavily_context(),
            'generation_failed',
            {'hobbies': ['사진']},
        )

        self.assertEqual(result['recommendations'], [])
        self.assertFalse(result['generation']['personalized'])
        self.assertEqual(result['generation']['personalization_fields'], [])

    def test_normalizer_does_not_fill_missing_recommendations_with_dummy_data(self):
        recommendations = WeatherWebAgent._normalize_recommendations(
            [{'kind': 'general', 'title': '제목만 있음'}],
            {'condition': '맑음'},
            {'hobbies': ['사진']},
        )

        self.assertEqual(recommendations, [])

    def test_llm_cannot_replace_index_values(self):
        weather = {
            'base_date': '20260715',
            'base_time': '1200',
            'condition': '맑음',
            'temperature': 30,
            'humidity': 70,
            'wind_speed': 2,
            'hourly_forecasts': [],
        }
        normalized = WeatherWebAgent._normalize(
            {
                'weatherAnalysis': '안내',
                'conditionGuide': [
                    {'label': '식중독지수', 'score': 100, 'level': '위험'}
                ],
                'recommendations': [],
            },
            WeatherWebAgent._empty_tavily_context(),
            weather,
            {},
        )

        self.assertEqual(len(normalized['conditionGuide']), 4)
        self.assertEqual(normalized['conditionGuide'][0]['label'], '불쾌지수')
        self.assertEqual(normalized['conditionGuide'][0]['value'], 81.4)
        self.assertEqual(normalized['conditionGuide'][2]['label'], '식중독지수')
        self.assertEqual(normalized['conditionGuide'][2]['value'], 67.7)

    def test_fallback_preserves_tavily_sources(self):
        context = {
            'available': True,
            'sources': [{'title': '네이버 날씨', 'url': 'https://weather.naver.com/today'}],
            'provider': WeatherWebAgent._tavily_provider_status(),
        }
        result = WeatherWebAgent._fallback({}, context, 'rate_limit')
        self.assertTrue(result['webSearchUsed'])
        self.assertEqual(result['sources'], context['sources'])
        self.assertEqual(result['generation']['status'], 'fallback')


class ForecastTimelineTests(SimpleTestCase):
    @patch('myweather.services.timezone.localtime')
    def test_selects_first_future_forecast_and_excludes_past_cards(self, localtime):
        localtime.return_value = datetime(2026, 7, 15, 10, 40, tzinfo=ZoneInfo('Asia/Seoul'))
        items = []
        for time_value, temperature in [('1000', '27'), ('1100', '28'), ('1200', '29')]:
            for category, value in [
                ('SKY', '1'),
                ('PTY', '0'),
                ('T1H', temperature),
                ('RN1', '강수없음'),
            ]:
                items.append({
                    'category': category,
                    'fcstDate': '20260715',
                    'fcstTime': time_value,
                    'fcstValue': value,
                })

        parsed = parse_ultra_short_forecast_items(items)

        self.assertEqual(parsed['forecast_time']['time'], '1100')
        self.assertEqual([item['time'] for item in parsed['hourly_forecasts']], ['11:00', '12:00'])


class WeeklyForecastTests(SimpleTestCase):
    def test_parses_short_forecast_into_daily_summary(self):
        items = []
        for time_value, temperature, sky, rain_probability in [
            ('0600', '22', '1', '10'),
            ('1500', '31', '4', '70'),
        ]:
            for category, value in [
                ('TMP', temperature),
                ('SKY', sky),
                ('PTY', '0'),
                ('POP', rain_probability),
            ]:
                items.append({
                    'category': category,
                    'fcstDate': '20260716',
                    'fcstTime': time_value,
                    'fcstValue': value,
                })
        items.extend([
            {'category': 'TMN', 'fcstDate': '20260716', 'fcstTime': '0600', 'fcstValue': '21'},
            {'category': 'TMX', 'fcstDate': '20260716', 'fcstTime': '1500', 'fcstValue': '32'},
        ])

        parsed = parse_short_forecast_items(items)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['date'], '2026-07-16')
        self.assertEqual(parsed[0]['min_temperature'], 21.0)
        self.assertEqual(parsed[0]['max_temperature'], 32.0)
        self.assertEqual(parsed[0]['precipitation_probability'], 70.0)

    def test_combines_mid_temperature_and_land_forecast(self):
        temperatures = [{'taMin4': 20, 'taMax4': 29, 'taMin5': 21, 'taMax5': 30}]
        land = [{
            'wf4Am': '구름많음', 'wf4Pm': '흐리고 비', 'rnSt4Am': 30, 'rnSt4Pm': 70,
            'wf5Am': '맑음', 'wf5Pm': '맑음', 'rnSt5Am': 10, 'rnSt5Pm': 10,
        }]

        parsed = parse_mid_forecast_items(temperatures, land, '202607150600')

        self.assertEqual([item['date'] for item in parsed], ['2026-07-19', '2026-07-20'])
        self.assertEqual(parsed[0]['condition'], '구름많음/흐리고 비')
        self.assertEqual(parsed[0]['precipitation_probability'], 70.0)

    def test_weekly_merge_prefers_short_forecast_and_keeps_mid_tail(self):
        short = [{
            'date': '2026-07-19', 'day': '7/19(일)', 'condition': '맑음',
            'min_temperature': 22, 'max_temperature': 31,
            'precipitation_probability': 10, 'source': '단기',
        }]
        mid = [
            {
                'date': '2026-07-19', 'day': '7/19(일)', 'condition': '흐림',
                'min_temperature': 20, 'max_temperature': 29,
                'precipitation_probability': 60, 'source': '중기',
            },
            {
                'date': '2026-07-20', 'day': '7/20(월)', 'condition': '구름많음',
                'min_temperature': 21, 'max_temperature': 30,
                'precipitation_probability': 30, 'source': '중기',
            },
        ]

        merged = merge_weekly_forecasts(short, mid, today=datetime(2026, 7, 15).date())

        self.assertEqual(merged[0]['condition'], '맑음')
        self.assertEqual(merged[1]['date'], '2026-07-20')


class KmaRateLimitTests(SimpleTestCase):
    @patch('myweather.services.KMA_RETRY_COUNT', 1)
    @patch('myweather.services.time.sleep')
    @patch('myweather.services.requests.get')
    def test_honors_short_retry_after_before_retrying(self, request_get, sleep):
        limited = Mock(status_code=429, headers={'Retry-After': '1.5'})
        success = Mock(status_code=200)
        success.json.return_value = {'response': {'header': {'resultCode': '00'}}}
        request_get.side_effect = [limited, success]

        payload = _request_kma_json('https://example.test/weather', {'nx': 60})

        self.assertEqual(payload['response']['header']['resultCode'], '00')
        sleep.assert_called_once_with(1.5)
        self.assertEqual(request_get.call_count, 2)


class KmaApiHubUnificationTests(SimpleTestCase):
    @patch.dict(os.environ, {'KMA_API_HUB_AUTH_KEY': 'hub-key'})
    @patch(
        'myweather.services.fetch_uv_index',
        return_value={'status': 'available', 'value': 5, 'cache_status': 'miss'},
    )
    @patch('myweather.services.fetch_weather_warnings')
    @patch('myweather.services.fetch_weekly_forecast', return_value={'days': []})
    @patch('myweather.services.fetch_sky_forecast', return_value={})
    @patch('myweather.services._cached_payload', return_value=None)
    @patch('myweather.services._request_kma_json')
    def test_observation_and_forecast_use_api_hub_auth_key(
        self,
        request_kma_json,
        cached_payload,
        fetch_sky_forecast,
        fetch_weekly_forecast,
        fetch_weather_warnings,
        fetch_uv_index_mock,
    ):
        request_kma_json.return_value = {
            'response': {
                'header': {'resultCode': '00'},
                'body': {'items': {'item': [
                    {'category': 'T1H', 'obsrValue': '24.4'},
                    {'category': 'REH', 'obsrValue': '70'},
                    {'category': 'WSD', 'obsrValue': '2.1'},
                    {'category': 'PTY', 'obsrValue': '0'},
                    {'category': 'RN1', 'obsrValue': '0'},
                ]}},
            }
        }
        fetch_weather_warnings.return_value = {'status': 'none', 'items': []}

        result = fetch_current_weather(region='서울')

        request_url, request_params = request_kma_json.call_args.args
        self.assertTrue(request_url.startswith('https://apihub.kma.go.kr/'))
        self.assertEqual(request_params['authKey'], 'hub-key')
        self.assertNotIn('serviceKey', request_params)
        fetch_sky_forecast.assert_called_once()
        self.assertEqual(fetch_sky_forecast.call_args.args[0], 'hub-key')
        fetch_weekly_forecast.assert_called_once()
        self.assertEqual(fetch_weekly_forecast.call_args.args[0], 'hub-key')
        fetch_uv_index_mock.assert_called_once()
        self.assertEqual(result['uv_index']['value'], 5)
        self.assertEqual(result['provider'], 'KMA API Hub')


class KmaLifeIndexTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch.dict(os.environ, {'KMA_LIFE_INDEX_SERVICE_KEY': 'life-key'})
    @patch('myweather.service.life_index_service.requests.get')
    def test_fetches_official_uv_index_without_local_calculation(self, request_get):
        response = Mock(status_code=200, content=b'')
        response.json.return_value = {
            'response': {
                'header': {'resultCode': '00'},
                'body': {'items': {'item': {
                    'areaNo': '1100000000',
                    'date': '2026071812',
                    'h0': '8.4',
                }}},
            }
        }
        request_get.return_value = response

        result = fetch_uv_index({'name': '서울'})

        self.assertEqual(result['value'], 8.4)
        self.assertEqual(result['provider'], '기상청 생활기상지수 V5')
        self.assertFalse(result['stale'])
        request_url = request_get.call_args.args[0]
        request_params = request_get.call_args.kwargs['params']
        self.assertEqual(
            request_url,
            'https://apis.data.go.kr/1360000/LivingWthrIdxServiceV5/getUVIdxV5',
        )
        self.assertEqual(request_params['ServiceKey'], 'life-key')
        self.assertEqual(request_params['areaNo'], '1100000000')

    @patch.dict(
        os.environ,
        {'KMA_LIFE_INDEX_SERVICE_KEY': '', 'KMA_API_KEY': ''},
    )
    @patch('myweather.service.life_index_service.requests.get')
    def test_missing_key_returns_unavailable_instead_of_dummy(self, request_get):
        result = fetch_uv_index({'name': '서울'})

        self.assertEqual(result['status'], 'unconfigured')
        self.assertIsNone(result['value'])
        request_get.assert_not_called()


class KmaWarningTests(SimpleTestCase):
    def test_parses_and_filters_current_warnings_by_region(self):
        payload = """# REG_UP,REG_UP_KO-------------------------------,REG_ID,REG_KO----------------------------------,TM_FC,TM_EF,WRN,LVL,CMD,ED_TM
L1021900,동해시,L1021920,동해시산지,202607151000,202607151100,폭염,주의,발표,
L1022000,삼척시,L1022020,삼척시산지,202607151000,202607151100,폭염,주의,변경,
L1022500,강릉시,L1022520,강릉시산지,202607151000,202607151100,폭염,주의,발표,
L1022700,양양군,L1022730,양양군북부산지,202607151000,202607151100,폭염,주의,발표,
L1020000,강원도,L1022600,속초시평지,202607151000,202607151100,강풍,경보,해제,
L1150000,부산광역시,L1150100,부산동부,202607151000,202607151100,호우,경보,발표,
"""

        rows = parse_kma_warning_rows(payload)
        alerts = filter_kma_warnings(rows, '강원')

        self.assertEqual(len(rows), 6)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], '폭염')
        self.assertEqual(alerts[0]['level'], '주의보')
        self.assertEqual(alerts[0]['areas'], ['동해산지', '삼척산지', '강릉산지', '양양북부산지'])
        self.assertEqual(alerts[0]['region'], '강원도(동해산지, 삼척산지, 강릉산지, 양양북부산지)')

    def test_maps_every_supported_region_by_official_land_warning_code(self):
        cases = {
            '서울': 'L1100100', '부산': 'L1150100', '대구': 'L1140100',
            '인천': 'L1110100', '대전': 'L1120100', '울산': 'L1160100',
            '세종': 'L1170100', '전남광주': 'L1050100', '경기': 'L1010100',
            '강원': 'L1020100', '충북': 'L1040100', '충남': 'L1030100',
            '전북': 'L1060100', '경북': 'L1070100', '경남': 'L1080100',
            '제주': 'L1090100',
        }
        for region, reg_id in cases.items():
            with self.subTest(region=region):
                alerts = filter_kma_warnings(
                    [{
                        'REG_UP': reg_id[:4] + '0000',
                        'REG_ID': reg_id,
                        'REG_KO': '세부지역',
                        'WRN': 'H',
                        'LVL': '2',
                        'CMD': '1',
                    }],
                    region,
                )
                self.assertEqual(len(alerts), 1)

    def test_includes_ulleungdo_dokdo_in_gyeongbuk(self):
        alerts = filter_kma_warnings(
            [{
                'REG_UP': 'L1600000',
                'REG_ID': 'L1072100',
                'REG_KO': '울릉도.독도',
                'WRN': '강풍',
                'LVL': '주의',
                'CMD': '발표',
            }],
            '경북',
        )

        self.assertEqual(alerts[0]['region'], '경상북도(울릉도.독도)')

    def test_uses_detail_code_when_parent_and_detail_regions_conflict(self):
        alerts = filter_kma_warnings(
            [{
                'REG_UP': 'L1010000',
                'REG_UP_KO': '경기도',
                'REG_ID': 'L1100100',
                'REG_KO': '서울특별시',
                'WRN': '폭염',
                'LVL': '주의',
                'CMD': '발표',
            }],
            '경기',
        )

        self.assertEqual(alerts, [])

    def test_keeps_gwangju_and_jeonnam_in_integrated_region(self):
        alerts = filter_kma_warnings(
            [
                {
                    'REG_UP': 'L1050000', 'REG_ID': 'L1050100',
                    'REG_KO': '목포시', 'WRN': '폭염', 'LVL': '주의', 'CMD': '발표',
                },
                {
                    'REG_UP': 'L1130000', 'REG_ID': 'L1130100',
                    'REG_KO': '광주광역시', 'WRN': '폭염', 'LVL': '주의', 'CMD': '발표',
                },
            ],
            '전남광주',
        )

        self.assertEqual(alerts[0]['areas'], ['목포', '광주'])
        self.assertEqual(alerts[0]['region'], '전남광주(목포, 광주)')

    def test_returns_none_when_coordinate_region_cannot_be_mapped(self):
        self.assertIsNone(filter_kma_warnings([], '현재 위치'))
