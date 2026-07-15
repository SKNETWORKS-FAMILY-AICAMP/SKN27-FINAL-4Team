import os
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from .agent import WeatherWebAgent
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
            'temperature': 30,
            'humidity': 70,
            'wind_speed': 2,
        }
        indices = WeatherWebAgent._calculate_weather_indices(weather)

        self.assertEqual(list(indices), ['불쾌지수', '체감온도'])
        self.assertEqual(indices['불쾌지수']['value'], 81.4)
        self.assertEqual(indices['불쾌지수']['gauge_percent'], 69.0)
        self.assertTrue(indices['체감온도']['derived'])
        self.assertNotIn('습도', indices)
        self.assertNotIn('풍속', indices)
        self.assertNotIn('식중독지수', indices)
        self.assertNotIn('감기가능지수', indices)

    def test_llm_cannot_replace_index_values(self):
        weather = {
            'base_date': '20260715',
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

        self.assertEqual(normalized['conditionGuide'][0]['label'], '불쾌지수')
        self.assertEqual(normalized['conditionGuide'][0]['value'], 81.4)
        self.assertNotIn('식중독지수', [item['label'] for item in normalized['conditionGuide']])

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
        self.assertEqual(result['provider'], 'KMA API Hub')


class KmaWarningTests(SimpleTestCase):
    def test_parses_and_filters_current_warnings_by_region(self):
        payload = """# REG_UP,REG_UP_KO,REG_ID,REG_KO,TM_FC,TM_EF,WRN,LVL,CMD
L1000000,서울특별시,L1010000,서울 전역,202607151000,202607151100,H,2,1
L1000000,서울특별시,L1020000,서울 동부,202607150900,202607151000,W,3,3
L2000000,부산광역시,L2010000,부산 전역,202607151000,202607151100,R,3,1
"""

        rows = parse_kma_warning_rows(payload)
        alerts = filter_kma_warnings(rows, '서울')

        self.assertEqual(len(rows), 3)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['type'], '폭염')
        self.assertEqual(alerts[0]['level'], '주의보')
        self.assertEqual(alerts[0]['region'], '서울 전역')

    def test_returns_none_when_coordinate_region_cannot_be_mapped(self):
        self.assertIsNone(filter_kma_warnings([], '현재 위치'))
