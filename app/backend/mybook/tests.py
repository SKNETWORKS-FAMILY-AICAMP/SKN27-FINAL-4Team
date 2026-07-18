from datetime import date
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

import requests
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .agent import (
    BookRecommendationAgent,
    BookRecommendationUnavailable,
    KAKAO_BOOK_PROVIDER_INFO,
    OPEN_LIBRARY_COVER_PROVIDER_INFO,
    _cached_external_book_info,
    _is_general_book,
    _is_recent_book,
    _daum_book_search_url,
    _nlk_items,
    _nlk_probe_page_numbers,
    _rank_personalized_books,
    _request_kakao_book_info,
    _request_nlk_books,
    _semantic_search_terms,
    _without_excluded_books,
)
from .utils import _catalog_search_terms, _nlk_search_terms
from .models import DailyBookRecommendation
from .views import book_recommendation


def _general_book_item(**overrides):
    item = {
        'BIBLIO_ID': 'KMO202600001',
        'DCTERMS_title': '사진을 즐기는 새로운 방법',
        'DC_creator': ['국립 작가'],
        'DC_publisher': '공공 출판사',
        'DCTERMS_abstract': '사진 촬영과 감상을 함께 다룬다.',
        'DCTERMS_subject': ['사진', '촬영'],
        'BIBO_isbn': '9788959710256',
        'DCTERMS_issued': '2025',
        'RDF_type': [
            'http://lod.nl.go.kr/ontology/OfflineMaterial',
            'http://lod.nl.go.kr/ontology/Book',
        ],
        'URI': 'https://lod.nl.go.kr/resource/KMO202600001',
    }
    item.update(overrides)
    return item


class NationalBibliographyBookSearchTests(SimpleTestCase):
    def test_keyword_prompt_requires_an_exact_profile_topic_anchor(self):
        prompt = BookRecommendationAgent._keyword_prompt(
            {},
            {
                'id': 'interests',
                'name': '관심사 기반 추천',
                'basis_label': '프로필 관심사',
            },
            ['패션', '천문학'],
        )

        self.assertIn('selected_basis 원문을 그대로 포함', prompt)
        self.assertIn('원래 주제를 다른 분야', prompt)
        self.assertIn('여러 핵심 값을 억지로', prompt)
        self.assertIn('Kakao Daum 책 검색 API', prompt)
        self.assertIn('"search_terms"', prompt)
        self.assertIn("'헬스'→'근력 운동'", prompt)
        self.assertIn('"selected_basis"', prompt)

    def test_catalog_terms_keep_profile_topic_and_reject_sentence_style(self):
        terms = _catalog_search_terms(
            ['인물 촬영 가이드입니다', '빛과 노출'],
            selected_basis='사진 찍기',
            keyword='사진 찍기 인물 촬영',
        )

        self.assertEqual(terms, ['인물 촬영 가이드입니다', '빛과 노출', '사진'])

    def test_hobby_search_intent_restores_selected_profile_topic_if_llm_omits_it(self):
        keyword, content_terms = BookRecommendationAgent._anchor_profile_topic(
            'hobbies',
            '빛과 구도 실전',
            ['노출 기술', '시각적 스토리텔링'],
            '사진 찍기',
        )

        self.assertEqual(keyword, '사진 찍기 빛과 구도 실전')
        self.assertEqual(content_terms[0], '사진 찍기')

    @patch.object(
        BookRecommendationAgent,
        '_build_search_intent',
        return_value={
            'keyword': '테스트 도서',
            'content_terms': ['테스트 주제', '테스트 관점'],
            'reason': '테스트 추천 이유',
            'keyword_basis': '테스트 기준',
        },
    )
    def test_build_themes_preserves_all_profile_values_for_ai_ranking(
        self,
        build_search_intent,
    ):
        themes = BookRecommendationAgent._build_themes(
            {
                'today_emotion': '기쁨',
                'interests': ['음악', '사진'],
                'hobbies': ['산책', '요리'],
            }
        )

        themes_by_id = {theme['id']: theme for theme in themes}
        self.assertEqual(themes_by_id['emotion']['basis_values'], ['기쁨'])
        self.assertEqual(themes_by_id['interests']['basis_values'], ['음악', '사진'])
        self.assertEqual(themes_by_id['hobbies']['basis_values'], ['산책', '요리'])
        self.assertEqual(build_search_intent.call_count, 3)

    @patch.dict('os.environ', {'NLK_BIBLIO_SERVICE_KEY': 'public-data-key'}, clear=False)
    @patch('mybook.agent.requests.get')
    def test_searches_actual_top_level_contract_and_normalizes_general_book(self, request_get):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'header': {'resultCode': '00', 'resultMsg': 'NORMAL_CODE'},
            'body': {
                'pageNo': 1,
                'numOfRows': 20,
                'totalCount': 1,
                'items': [_general_book_item()],
            },
        }
        request_get.return_value = response

        books = BookRecommendationAgent._search_nlk_books(
            '사진 촬영',
            display=1,
            basis_values=['사진'],
            theme_id='hobbies',
        )

        self.assertEqual(books[0]['title'], '사진을 즐기는 새로운 방법')
        self.assertEqual(books[0]['subjects'], ['사진', '촬영'])
        self.assertEqual(books[0]['isbn'], '9788959710256')
        self.assertTrue(books[0]['general_book_verified'])
        self.assertIn('사진', books[0]['match_terms'])
        self.assertEqual(books[0]['source_provider']['id'], 'nlk_national_bibliography_lod')
        search_url = urlparse(books[0]['link'])
        search_query = parse_qs(search_url.query)
        self.assertEqual(search_url.hostname, 'search.daum.net')
        self.assertEqual(search_query['w'], ['book'])
        self.assertEqual(search_query['q'], ['사진을 즐기는 새로운 방법'])
        self.assertEqual(request_get.call_args_list[0].kwargs['params']['label'], '사진')
        self.assertNotIn('headers', request_get.call_args_list[0].kwargs.get('params', {}))

    def test_daum_book_link_uses_title_without_isbn_or_author(self):
        link = _daum_book_search_url(title='사진책')

        query = parse_qs(urlparse(link).query)
        self.assertEqual(query['q'], ['사진책'])

    @patch.dict('os.environ', {'KAKAO_REST_API_KEY': 'kakao-key'}, clear=False)
    @patch('mybook.agent.requests.get')
    def test_kakao_candidate_search_normalizes_rich_book_metadata(self, request_get):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'meta': {'total_count': 1, 'pageable_count': 1, 'is_end': True},
            'documents': [
                {
                    'title': '<b>근력 운동을 위한 가이드</b>',
                    'contents': '운동 원리와 프로그램 구성을 설명한다.',
                    'url': 'https://search.daum.net/search?w=bookpage&bookId=1234',
                    'isbn': '8959710254 9788959710256',
                    'datetime': '2022-05-12T00:00:00.000+09:00',
                    'authors': ['홍길동'],
                    'publisher': '운동출판사',
                    'translators': ['김번역'],
                    'price': 22000,
                    'sale_price': 19800,
                    'thumbnail': 'https://search1.kakaocdn.net/thumb/R120x174.q85/?fname=book',
                    'status': '정상판매',
                },
                {
                    'title': '근력 운동을 위한 가이드',
                    'contents': '이전 판본',
                    'url': 'https://search.daum.net/search?w=bookpage&bookId=5678',
                    'isbn': '8937460440 9788937460449',
                    'datetime': '2020-01-01T00:00:00.000+09:00',
                    'authors': ['홍길동'],
                    'publisher': '운동출판사',
                    'translators': [],
                    'price': 18000,
                    'sale_price': 16000,
                    'thumbnail': '',
                    'status': '정상판매',
                },
                {
                    'title': '근력 운동을 위한 가이드(체험판)',
                    'contents': '체험판',
                    'url': 'https://search.daum.net/search?w=bookpage&bookId=9999',
                    'isbn': '9788971998557',
                    'datetime': '2022-05-12T00:00:00.000+09:00',
                    'authors': ['홍길동'],
                    'publisher': '운동출판사',
                    'translators': [],
                    'price': 0,
                    'sale_price': 0,
                    'thumbnail': '',
                    'status': '정상판매',
                },
            ],
        }
        request_get.return_value = response

        books = BookRecommendationAgent._search_kakao_books(
            '헬스 근력 운동',
            display=4,
            basis_values=['헬스'],
            content_terms=['근력 운동', '운동 루틴'],
            search_terms=['근력 운동'],
            theme_id='hobbies',
        )

        self.assertEqual(books[0]['title'], '근력 운동을 위한 가이드')
        self.assertEqual(books[0]['authors'], ['홍길동'])
        self.assertEqual(books[0]['translators'], ['김번역'])
        self.assertEqual(books[0]['publisher'], '운동출판사')
        self.assertEqual(books[0]['published_at'][:10], '2022-05-12')
        self.assertEqual(books[0]['price'], 22000)
        self.assertEqual(books[0]['sale_price'], 19800)
        self.assertEqual(books[0]['status'], '정상판매')
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0]['source_provider'], KAKAO_BOOK_PROVIDER_INFO)
        self.assertEqual(request_get.call_args_list[0].kwargs['params']['query'], '근력 운동')
        self.assertNotIn('target', request_get.call_args_list[0].kwargs['params'])

    @patch.dict('os.environ', {'KAKAO_REST_API_KEY': 'kakao-key'}, clear=False)
    @patch('mybook.agent.requests.get')
    def test_kakao_candidate_service_failure_is_retryable(self, request_get):
        response = Mock(status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError('unauthorized')
        request_get.return_value = response

        with self.assertRaises(BookRecommendationUnavailable) as raised:
            BookRecommendationAgent._search_kakao_books(
                '근력 운동',
                display=1,
                search_terms=['근력 운동'],
            )

        self.assertEqual(raised.exception.code, 'KAKAO_SERVICE_UNAVAILABLE')

    def test_previous_recommendation_is_excluded_without_reordering_the_rest(self):
        books = [
            {'title': '책1', 'isbn': '9788959710256'},
            {'title': '책2', 'isbn': '9788937460449'},
            {'title': '책3', 'isbn': '9788971998557'},
        ]

        eligible = _without_excluded_books(books, ['9788959710256'])

        self.assertEqual([book['title'] for book in eligible], ['책2', '책3'])

    def test_exclusion_falls_back_when_it_would_remove_every_candidate(self):
        books = [{'title': '유일한 책', 'isbn': '9788959710256'}]

        self.assertEqual(
            _without_excluded_books(books, ['9788959710256']),
            books,
        )

    def test_rejects_thesis_even_when_it_has_an_isbn(self):
        item = _general_book_item(
            BIBLIO_ID='KDM202600001',
            BIBO_degree='석사',
            DCTERMS_title='사진 교육에 관한 연구',
        )
        book = BookRecommendationAgent._normalize_nlk_book_item(1, item)

        self.assertFalse(_is_general_book(item, book))

    def test_rejects_non_book_and_missing_isbn(self):
        non_book = _general_book_item(RDF_type=['http://lod.nl.go.kr/ontology/Audio'])
        missing_isbn = _general_book_item(BIBO_isbn='')

        self.assertFalse(
            _is_general_book(non_book, BookRecommendationAgent._normalize_nlk_book_item(1, non_book))
        )
        self.assertFalse(
            _is_general_book(missing_isbn, BookRecommendationAgent._normalize_nlk_book_item(1, missing_isbn))
        )

    def test_rejects_books_older_than_ten_years_or_without_a_year(self):
        self.assertTrue(_is_recent_book({'issued_year': 2016}, reference_year=2026))
        self.assertFalse(_is_recent_book({'issued_year': 2015}, reference_year=2026))
        self.assertFalse(_is_recent_book({'issued_year': None}, reference_year=2026))

    def test_personalized_ranking_prefers_basis_match(self):
        books = [
            {
                'title': '일상의 기록', 'subjects': ['에세이'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2025,
            },
            {
                'title': '사진 촬영의 기술', 'subjects': ['사진', '카메라'], 'description': '촬영 실습',
                'isbn': '9788959710256', 'issued_year': 2020,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='사진 입문',
            basis_values=['사진'],
            theme_id='hobbies',
        )

        self.assertEqual(ranked[0]['title'], '사진 촬영의 기술')
        self.assertIn('사진', ranked[0]['match_terms'])

    def test_profile_basis_outweighs_peripheral_search_word(self):
        books = [
            {
                'title': '감상의 심리학', 'subjects': ['감상'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2025,
            },
            {
                'title': '음악을 듣는 시간', 'subjects': ['음악'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2021,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='음악 감상',
            basis_values=['음악'],
            theme_id='interests',
        )

        self.assertEqual(ranked[0]['title'], '음악을 듣는 시간')
        self.assertEqual(len(ranked), 1)

    def test_content_metadata_outweighs_a_title_only_match(self):
        books = [
            {
                'title': '사진과 산책', 'subjects': ['에세이'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2025,
            },
            {
                'title': '장면을 엮는 법', 'subjects': ['시각적 스토리텔링'],
                'description': '사진으로 일상을 관찰하고 서사를 구성하는 방법',
                'isbn': '9788937460449', 'issued_year': 2021,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='사진으로 일상 기록',
            content_terms=['시각적 스토리텔링', '관찰과 서사'],
            basis_values=['사진'],
            theme_id='hobbies',
        )

        self.assertEqual(ranked[0]['title'], '장면을 엮는 법')
        self.assertGreater(ranked[0]['content_match_score'], 0)

    def test_hobby_ranking_prefers_activity_over_academic_context(self):
        books = [
            {
                'title': '사진측량 및 원격탐측', 'subjects': ['사진', '측량'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2021,
            },
            {
                'title': '사진 촬영 스타일링 가이드', 'subjects': ['사진', '촬영'], 'description': '',
                'isbn': '9788959710256', 'issued_year': 2021,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='사진 실용서',
            basis_values=['사진'],
            theme_id='hobbies',
        )

        self.assertEqual(ranked[0]['title'], '사진 촬영 스타일링 가이드')

    def test_hobby_ranking_rejects_incidental_keyword_without_activity_domain(self):
        books = [
            {
                'title': '보정 선생 서화집',
                'subjects': ['한국 회화', '서화'],
                'description': '보정 김정회 작품과 소장 현황을 정리한 작품집',
                'isbn': '9788959710256',
                'issued_year': 2020,
            },
            {
                'title': '카메라로 배우는 빛과 구도',
                'subjects': ['카메라', '촬영'],
                'description': '사진 촬영과 노출 보정 기술을 실습한다.',
                'isbn': '9788937460449',
                'issued_year': 2022,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='사진 촬영 실전 기술',
            content_terms=['노출 보정', '구도'],
            basis_values=['사진 찍기', '산책'],
            theme_id='hobbies',
        )

        self.assertEqual([book['title'] for book in ranked], ['카메라로 배우는 빛과 구도'])
        self.assertIn('카메라', ranked[0]['basis_match_terms'])

    def test_hobby_ranking_follows_the_hobby_selected_by_search_intent(self):
        books = [
            {
                'title': '사진, 빛으로 그린 이야기',
                'subjects': ['사진'],
                'description': '카메라 촬영의 표현을 살펴본다.',
                'isbn': '9788959710256',
                'issued_year': 2022,
            },
            {
                'title': '구도자의 산책',
                'subjects': ['산책'],
                'description': '',
                'isbn': '9788937460449',
                'issued_year': 2025,
            },
        ]

        ranked = _rank_personalized_books(
            books,
            keyword='사진 촬영 기법',
            content_terms=['구도', '노출'],
            basis_values=['사진 찍기', '산책'],
            theme_id='hobbies',
        )

        self.assertEqual(
            [book['title'] for book in ranked],
            ['사진, 빛으로 그린 이야기'],
        )

    @patch('mybook.services.catalog_service.time.sleep')
    @patch('mybook.agent.requests.get')
    def test_transport_timeout_is_retried(self, request_get, sleep):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'header': {'resultCode': '00'},
            'body': {'items': []},
        }
        request_get.side_effect = [requests.Timeout('slow'), response]

        payload = _request_nlk_books('key', '사진', 20)

        self.assertEqual(payload['header']['resultCode'], '00')
        self.assertEqual(request_get.call_count, 2)
        sleep.assert_called_once()

    @patch.object(BookRecommendationAgent, '_search_kakao_books')
    def test_theme_fallback_keeps_profile_basis(self, search_books):
        search_books.side_effect = [[], [{'title': '사진 일반책'}]]
        theme = {
            'id': 'hobbies',
            'keyword': '카메라 실용서',
            'basis_values': ['사진'],
        }

        BookRecommendationAgent._search_theme_candidates(theme)

        self.assertEqual(search_books.call_args_list[1].args[0], '사진 실용')
        self.assertTrue(theme['search_fallback_used'])

    @patch.object(
        BookRecommendationAgent,
        '_generate_single_review',
        side_effect=RuntimeError('llm unavailable'),
    )
    def test_review_failure_does_not_create_dummy_review(self, generate_review):
        theme = {
            'id': 'hobbies',
            'name': '취미 추천',
            'candidates': [{'candidate_id': 'book_1', 'title': '실제 책'}],
        }

        with self.assertRaises(BookRecommendationUnavailable) as raised:
            BookRecommendationAgent._generate_reviews({}, [theme])

        self.assertEqual(raised.exception.code, 'BOOK_REVIEW_GENERATION_FAILED')
        generate_review.assert_called_once()

    @patch.dict('os.environ', {'NLK_BIBLIO_SERVICE_KEY': 'public-data-key'}, clear=False)
    @patch('mybook.agent.requests.get')
    def test_service_failure_is_not_treated_as_empty_result(self, request_get):
        response = Mock(status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError('unauthorized')
        request_get.return_value = response

        with self.assertRaises(BookRecommendationUnavailable) as raised:
            BookRecommendationAgent._search_nlk_books('사진', display=1)

        self.assertEqual(raised.exception.code, 'NLK_SERVICE_UNAVAILABLE')

    def test_no_data_response_is_a_valid_empty_result(self):
        payload = {
            'header': {'resultCode': '03', 'resultMsg': 'NODATA_ERROR'},
            'body': {'pageNo': 1, 'numOfRows': 20, 'totalCount': 0, 'items': []},
        }

        self.assertEqual(_nlk_items(payload), [])

    def test_catalog_probe_checks_latest_page_first(self):
        payload = {
            'body': {'numOfRows': 20, 'totalCount': 100},
        }

        self.assertEqual(_nlk_probe_page_numbers(payload)[0], 4)

    def test_search_terms_keep_specific_words_for_catalog_search(self):
        self.assertEqual(
            _nlk_search_terms('사진 실용 도서'),
            ['사진 실용 도서', '사진'],
        )

    def test_semantic_search_terms_anchor_profile_topic_before_ai_phrases(self):
        terms = _semantic_search_terms(
            '사진으로 일상 기록',
            ['시각적 스토리텔링', '관찰과 서사'],
            ['사진'],
        )

        self.assertEqual(terms[:4], [
            '사진',
            '카메라',
            '시각적 스토리텔링',
            '관찰과 서사',
        ])

    def test_semantic_search_budget_keeps_profile_hobby_core_terms(self):
        terms = _semantic_search_terms(
            '일상 사진 구도와 걷기 기록',
            ['빛과 노출 기술', '시각적 스토리텔링', '렌즈 선택', '야외 관찰'],
            ['사진 찍기', '산책'],
        )

        self.assertEqual(terms[:4], [
            '사진',
            '카메라',
            '빛과 노출 기술',
            '시각적 스토리텔링',
        ])

    def test_fashion_interest_search_uses_catalog_friendly_alias(self):
        terms = _semantic_search_terms(
            '패션 문화비평',
            ['유행 형성', '소비문화', '브랜드 전략', '복식사'],
            ['패션', '팝업스토어', '맛집 탐방'],
        )

        self.assertEqual(terms[:4], [
            '패션',
            '스타일',
            '유행 형성',
            '소비문화',
        ])

    def test_llm_catalog_terms_are_used_before_the_profile_fallback(self):
        terms = _semantic_search_terms(
            '사진 찍기 인물 촬영',
            ['빛과 노출', '구도'],
            ['사진 찍기', '산책'],
            ['인물 촬영', '사진'],
        )

        self.assertEqual(terms[:4], ['인물 촬영', '사진', '카메라', '빛과 노출'])

    def test_metadata_confirmed_topic_beats_title_only_topic_match(self):
        ranked = _rank_personalized_books(
            [
                {
                    'title': '사진으로 만나는 일상',
                    'subjects': [],
                    'description': '',
                    'isbn': '9788959710256',
                    'issued_year': 2025,
                },
                {
                    'title': '빛을 이해하는 시간',
                    'subjects': ['사진', '촬영'],
                    'description': '카메라 노출과 구도를 다룬다.',
                    'isbn': '9788937460449',
                    'issued_year': 2024,
                },
            ],
            keyword='사진 촬영',
            content_terms=['노출', '구도'],
            basis_values=['사진'],
            theme_id='hobbies',
        )

        self.assertEqual([book['title'] for book in ranked], ['빛을 이해하는 시간'])

    def test_fashion_interest_ranking_accepts_style_alias_metadata(self):
        ranked = _rank_personalized_books(
            [
                {
                    'title': '나만의 스타일링 원칙',
                    'subjects': ['퍼스널 스타일'],
                    'description': '옷차림과 이미지 연출 방법을 설명한다.',
                    'isbn': '9788937460449',
                    'issued_year': 2024,
                },
            ],
            keyword='패션 문화비평',
            content_terms=['유행 형성', '소비문화'],
            basis_values=['패션', '팝업스토어', '맛집 탐방'],
            theme_id='interests',
        )

        self.assertEqual([book['title'] for book in ranked], ['나만의 스타일링 원칙'])
        self.assertIn('스타일', ranked[0]['basis_match_terms'])

    def test_payload_separates_kakao_metadata_and_ai_curation(self):
        theme = {
            'id': 'hobbies',
            'name': '취미 기반 추천',
            'reason': '취미를 더 즐기기 위한 추천',
            'keyword': '사진',
            'keyword_basis': '프로필 취미',
            'basis_label': '프로필 취미',
            'basis_values': ['사진'],
        }
        book = {
            'title': '사진책',
            'author': '저자',
            'publisher': '출판사',
            'description': '사진 촬영 방법을 소개하는 책 소개',
            'subjects': [],
            'authors': ['저자'],
            'translators': ['번역자'],
            'published_at': '2025-03-14T00:00:00.000+09:00',
            'price': 20000,
            'sale_price': 18000,
            'status': '정상판매',
            'matched_queries': ['사진 촬영'],
            'link': 'https://search.daum.net/search?w=bookpage&bookId=2',
            'isbn': '9788959710256',
            'general_book_verified': True,
            'source_provider': KAKAO_BOOK_PROVIDER_INFO,
        }

        payload = BookRecommendationAgent._book_payload(theme, book, 'AI 추천 서평', genre='실용서')

        self.assertEqual(payload['source_result']['description'], '사진 촬영 방법을 소개하는 책 소개')
        self.assertEqual(payload['source_result']['translators'], ['번역자'])
        self.assertEqual(payload['source_result']['published_at'][:10], '2025-03-14')
        self.assertEqual(payload['source_result']['sale_price'], 18000)
        self.assertEqual(payload['source_result']['status'], '정상판매')
        self.assertTrue(payload['source_result']['general_book_verified'])
        self.assertEqual(payload['ai_curation']['review'], 'AI 추천 서평')
        self.assertEqual(payload['source_provider']['id'], 'kakao_daum_book_search')

    @patch.object(BookRecommendationAgent, '_generate_reviews')
    @patch.object(BookRecommendationAgent, '_search_kakao_books')
    @patch.object(BookRecommendationAgent, '_build_themes')
    def test_recommendation_passes_each_theme_personalization_into_catalog_ranking(
        self,
        build_themes,
        search_books,
        generate_reviews,
    ):
        build_themes.return_value = [
            {
                'id': 'emotion', 'name': '감정', 'keyword': '마음 회복',
                'content_terms': ['감정 치유', '휴식'],
                'reason': '감정 기준', 'keyword_basis': '오늘의 감정',
                'basis_label': '오늘의 감정', 'basis_values': ['슬픔'],
            },
            {
                'id': 'interests', 'name': '관심사', 'keyword': '음악 감상',
                'content_terms': ['음악사', '장르 비평'],
                'reason': '관심사 기준', 'keyword_basis': '관심사',
                'basis_label': '관심사', 'basis_values': ['음악'],
            },
            {
                'id': 'hobbies', 'name': '취미', 'keyword': '사진 촬영',
                'content_terms': ['구도', '빛 활용'],
                'reason': '취미 기준', 'keyword_basis': '취미',
                'basis_label': '취미', 'basis_values': ['사진'],
            },
        ]
        search_books.return_value = [{'title': '검증된 일반책'}]
        generate_reviews.return_value = [
            {'theme_id': 'emotion'}, {'theme_id': 'interests'}, {'theme_id': 'hobbies'},
        ]

        result = BookRecommendationAgent.recommend({'today_emotion': '슬픔'})

        search_books.assert_any_call(
            '마음 회복', display=8, basis_values=['슬픔'], theme_id='emotion',
            content_terms=['감정 치유', '휴식'],
            excluded_isbns=[],
        )
        search_books.assert_any_call(
            '음악 감상', display=8, basis_values=['음악'], theme_id='interests',
            content_terms=['음악사', '장르 비평'],
            excluded_isbns=[],
        )
        search_books.assert_any_call(
            '사진 촬영', display=8, basis_values=['사진'], theme_id='hobbies',
            content_terms=['구도', '빛 활용'],
            excluded_isbns=[],
        )
        self.assertTrue(result['selection_policy']['general_books_only'])
        self.assertEqual(result['recommendation_engine'], 'kakao_books_v1')
        self.assertEqual(result['selection_policy']['candidate_source'], 'Kakao Daum 책 검색')
        self.assertEqual(
            result['source_disclosure']['cover_metadata'],
            'Kakao Daum 책 검색 표지',
        )


class ExternalBookCoverTests(SimpleTestCase):
    @patch('mybook.agent.requests.get')
    def test_kakao_title_result_supplies_cover_and_title_search_link(self, request_get):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'meta': {'total_count': 2},
            'documents': [
                {
                    'title': '카메라 교본',
                    'authors': ['다른 저자'],
                    'thumbnail': 'https://search1.kakaocdn.net/thumb/wrong',
                    'url': 'https://search.daum.net/search?w=bookpage&bookId=wrong',
                },
                {
                    'title': '카메라 교본',
                    'authors': ['윤관식'],
                    'thumbnail': 'http://search1.kakaocdn.net/thumb/R120x174.q85/?fname=cover',
                    'url': 'http://search.daum.net/search?w=bookpage&bookId=1234',
                }
            ],
        }
        request_get.return_value = response

        book_info = _request_kakao_book_info('kakao-key', '카메라 교본', '윤관식')

        self.assertEqual(
            book_info['image'],
            'https://search1.kakaocdn.net/thumb/R120x174.q85/?fname=cover',
        )
        link_query = parse_qs(urlparse(book_info['link']).query)
        self.assertEqual(link_query['q'], ['카메라 교본'])
        self.assertEqual(request_get.call_args.kwargs['params']['query'], '카메라 교본')
        self.assertEqual(request_get.call_args.kwargs['params']['target'], 'title')
        self.assertEqual(
            request_get.call_args.kwargs['headers']['Authorization'],
            'KakaoAK kakao-key',
        )
        self.assertEqual(request_get.call_args.kwargs['timeout'], 3.0)

    @patch('mybook.agent.cache')
    @patch('mybook.agent._kakao_rest_api_key', return_value='')
    def test_open_library_and_daum_search_are_used_without_kakao_key(self, kakao_key, cache):
        cache.get.return_value = None

        book_info = _cached_external_book_info(
            '사진책',
            author='국립 작가',
            isbn='9788959710256',
        )

        self.assertEqual(
            book_info['image'],
            'https://covers.openlibrary.org/b/isbn/9788959710256-L.jpg?default=false',
        )
        self.assertEqual(book_info['cover_provider'], OPEN_LIBRARY_COVER_PROVIDER_INFO)
        self.assertEqual(book_info['link_provider'], KAKAO_BOOK_PROVIDER_INFO)
        self.assertIn('search.daum.net/search?', book_info['link'])
        self.assertEqual(parse_qs(urlparse(book_info['link']).query)['q'], ['사진책'])
        cache.set.assert_called_once()

    @patch('mybook.agent._cached_external_book_info')
    def test_final_recommendation_receives_kakao_media_in_both_payload_shapes(self, lookup):
        lookup.return_value = {
            'image': 'https://search1.kakaocdn.net/thumb/R120x174.q85/?fname=book',
            'link': 'https://search.daum.net/search?w=bookpage&bookId=1234',
            'cover_provider': KAKAO_BOOK_PROVIDER_INFO,
            'link_provider': KAKAO_BOOK_PROVIDER_INFO,
        }
        book = {
            'isbn': '9788959710256',
            'title': '사진책',
            'author': '국립 작가',
            'image': '',
            'link': '',
            'source_result': {'isbn': '9788959710256', 'image': '', 'link': ''},
        }

        BookRecommendationAgent._enrich_book_covers([book])

        self.assertIn('search1.kakaocdn.net', book['image'])
        self.assertIn('search.daum.net', book['link'])
        self.assertEqual(
            book['source_result']['image'],
            book['image'],
        )
        self.assertEqual(book['source_result']['link'], book['link'])
        self.assertEqual(book['cover_provider'], KAKAO_BOOK_PROVIDER_INFO)
        self.assertEqual(
            book['source_result']['cover_provider'],
            KAKAO_BOOK_PROVIDER_INFO,
        )
        lookup.assert_called_once_with('사진책', '국립 작가', '9788959710256')

    @patch('mybook.agent._cached_external_book_info', side_effect=requests.Timeout('slow'))
    def test_external_lookup_failure_does_not_fail_or_mutate_recommendation(self, lookup):
        book = {
            'isbn': '9788959710256',
            'title': '사진책',
            'author': '국립 작가',
            'image': '',
            'source_result': {'isbn': '9788959710256', 'image': ''},
        }

        BookRecommendationAgent._enrich_book_covers([book])

        self.assertEqual(book['image'], '')
        self.assertEqual(book['source_result']['image'], '')


class BookRecommendationViewStabilityTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            email='daily-book@example.com',
            password='test-password',
            nickname='매일책',
        )
        self.today = date(2026, 7, 16)
        self.profile = {
            'today_emotion': '평온',
            'interests': ['사진'],
            'hobbies': ['산책'],
        }

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_previous_day_isbn_is_excluded_and_today_selection_is_saved(
        self,
        recommend,
        build_profile,
    ):
        build_profile.return_value = self.profile
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=date(2026, 7, 15),
            payload={
                'books': [
                    {
                        'theme_id': 'hobbies',
                        'title': '어제 추천',
                        'isbn': '9788959710256',
                    }
                ],
                'themes': [],
            },
            profile_basis=self.profile,
        )
        recommend.return_value = {
            'books': [
                {
                    'theme_id': 'hobbies',
                    'title': '새 추천',
                    'isbn': '9788937460449',
                }
            ],
            'themes': [],
        }
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            recommend.call_args.kwargs['excluded_isbns'],
            {'hobbies': ['9788959710256']},
        )
        self.assertEqual(
            DailyBookRecommendation.objects.get(
                user=self.user,
                recommendation_date=self.today,
            ).payload['books'][0]['isbn'],
            '9788937460449',
        )

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_same_day_uses_stored_recommendation_when_profile_is_unchanged(
        self,
        recommend,
        build_profile,
    ):
        stored_profile = {
            'today_emotion': '평온',
            'interests': ['사진'],
            'hobbies': ['산책'],
        }
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload={
                'books': [{'theme_id': 'hobbies', 'title': '오늘 고정 책'}],
                'themes': [],
            },
            profile_basis=stored_profile,
        )
        build_profile.return_value = stored_profile
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_cached'])
        self.assertEqual(response.data['books'][0]['title'], '오늘 고정 책')
        self.assertEqual(response.data['profile_basis'], stored_profile)
        build_profile.assert_called_once_with(self.user)
        recommend.assert_not_called()

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_same_day_lod_payload_is_rebuilt_once_with_kakao_engine(
        self,
        recommend,
        build_profile,
    ):
        old_payload = {
            'books': [
                {'theme_id': 'hobbies', 'title': '기존 LOD 책', 'isbn': '9788959710256'},
            ],
            'themes': [],
            'source_disclosure': {'book_metadata': '국립중앙도서관 국가서지 LOD'},
        }
        new_payload = {
            'recommendation_engine': 'kakao_books_v1',
            'books': [
                {'theme_id': 'hobbies', 'title': '새 Kakao 책', 'isbn': '9788937460449'},
            ],
            'themes': [],
        }
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload=old_payload,
            profile_basis=self.profile,
        )
        build_profile.return_value = self.profile
        recommend.return_value = new_payload
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_cached'])
        self.assertEqual(response.data['recommendation_engine'], 'kakao_books_v1')
        self.assertEqual(response.data['books'][0]['title'], '새 Kakao 책')
        self.assertEqual(
            recommend.call_args.kwargs['excluded_isbns'],
            {'hobbies': ['9788959710256']},
        )

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_same_day_interest_change_automatically_refreshes_interest_book(
        self,
        recommend,
        build_profile,
    ):
        old_profile = {
            'today_emotion': '평온',
            'interests': ['사진'],
            'hobbies': ['산책'],
        }
        changed_profile = {
            'today_emotion': '평온',
            'interests': ['천문학'],
            'hobbies': ['산책'],
        }
        old_payload = {
            'books': [
                {'theme_id': 'emotion', 'title': '평온 책', 'isbn': '111'},
                {'theme_id': 'interests', 'title': '사진 책', 'isbn': '222'},
                {'theme_id': 'hobbies', 'title': '산책 책', 'isbn': '333'},
            ],
            'themes': [],
        }
        new_payload = {
            'books': [
                {'theme_id': 'emotion', 'title': '평온 책', 'isbn': '111'},
                {'theme_id': 'interests', 'title': '천문학 책', 'isbn': '444'},
                {'theme_id': 'hobbies', 'title': '산책 책', 'isbn': '333'},
            ],
            'themes': [],
        }
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload=old_payload,
            profile_basis=old_profile,
        )
        build_profile.return_value = changed_profile
        recommend.return_value = new_payload
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_cached'])
        recommend.assert_called_once_with(
            changed_profile,
            force_theme='interests',
            cached_data=old_payload,
            excluded_isbns={'interests': ['222']},
        )
        stored = DailyBookRecommendation.objects.get(
            user=self.user,
            recommendation_date=self.today,
        )
        self.assertEqual(stored.payload, new_payload)
        self.assertEqual(stored.profile_basis, changed_profile)
        self.assertEqual(response.data['books'][1]['title'], '천문학 책')

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_same_day_refresh_uses_changed_profile_and_replaces_stored_books(
        self,
        recommend,
        build_profile,
    ):
        old_profile = {
            'today_emotion': '평온',
            'interests': ['사진'],
            'hobbies': ['산책'],
        }
        changed_profile = {
            'today_emotion': '기쁨',
            'interests': ['음악'],
            'hobbies': ['요리'],
        }
        old_payload = {
            'books': [
                {'theme_id': 'emotion', 'title': '평온 책', 'isbn': '111'},
                {'theme_id': 'interests', 'title': '사진 책', 'isbn': '222'},
                {'theme_id': 'hobbies', 'title': '산책 책', 'isbn': '333'},
            ],
            'themes': [],
        }
        new_payload = {
            'books': [
                {'theme_id': 'emotion', 'title': '기쁨 책', 'isbn': '444'},
                {'theme_id': 'interests', 'title': '음악 책', 'isbn': '555'},
                {'theme_id': 'hobbies', 'title': '요리 책', 'isbn': '666'},
            ],
            'themes': [],
        }
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload=old_payload,
            profile_basis=old_profile,
        )
        build_profile.return_value = changed_profile
        recommend.return_value = new_payload
        request = self.factory.get('/api/mybook/recommendation/?force=true')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        recommend.assert_called_once_with(
            changed_profile,
            force_theme=None,
            cached_data=old_payload,
            excluded_isbns={
                'emotion': ['111'],
                'interests': ['222'],
                'hobbies': ['333'],
            },
        )
        stored = DailyBookRecommendation.objects.get(
            user=self.user,
            recommendation_date=self.today,
        )
        self.assertEqual(stored.payload, new_payload)
        self.assertEqual(stored.profile_basis, changed_profile)
        self.assertEqual(response.data['profile_basis'], changed_profile)
        self.assertEqual(
            [book['title'] for book in response.data['books']],
            ['기쁨 책', '음악 책', '요리 책'],
        )

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_uncached_service_failure_returns_retryable_503(self, recommend, build_profile):
        build_profile.return_value = self.profile
        recommend.side_effect = BookRecommendationUnavailable(
            '서지 서비스 장애',
            code='NLK_SERVICE_UNAVAILABLE',
        )
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.data['retryable'])
        self.assertEqual(response.data['code'], 'NLK_SERVICE_UNAVAILABLE')

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_legacy_dummy_review_is_not_served_as_cached_fallback(
        self,
        recommend,
        build_profile,
    ):
        build_profile.return_value = self.profile
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload={
                'books': [
                    {
                        'theme_id': 'hobbies',
                        'title': '실제 후보였던 책',
                        'review': (
                            '실제 후보였던 책은 지금 펼쳐 들었을 때 부담 없이 '
                            '호흡을 맞추기 좋은 책입니다.'
                        ),
                    }
                ],
                'themes': [],
            },
            profile_basis=self.profile,
        )
        recommend.side_effect = BookRecommendationUnavailable(
            '서평 서비스 장애',
            code='BOOK_REVIEW_GENERATION_FAILED',
        )
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['code'], 'BOOK_REVIEW_GENERATION_FAILED')
        self.assertIsNone(recommend.call_args.kwargs['cached_data'])

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_failed_forced_refresh_serves_stored_result_without_overwriting_it(
        self,
        recommend,
        build_profile,
    ):
        build_profile.return_value = self.profile
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=self.today,
            payload={
                'books': [
                    {
                        'theme_id': 'hobbies',
                        'title': '검증된 오늘 책',
                        'isbn': '9788959710256',
                    }
                ],
                'themes': [],
            },
            profile_basis=self.profile,
        )
        recommend.side_effect = BookRecommendationUnavailable(
            '서지 서비스 장애',
            code='NLK_SERVICE_UNAVAILABLE',
        )
        request = self.factory.get('/api/mybook/recommendation/?force=true')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_stale'])
        self.assertEqual(response.data['service_status']['state'], 'degraded')
        self.assertEqual(response.data['books'][0]['title'], '검증된 오늘 책')
        self.assertEqual(
            recommend.call_args.kwargs['excluded_isbns'],
            {'hobbies': ['9788959710256']},
        )
        self.assertEqual(
            DailyBookRecommendation.objects.get(
                user=self.user,
                recommendation_date=self.today,
            ).payload['books'][0]['title'],
            '검증된 오늘 책',
        )

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_new_day_failure_serves_previous_day_as_stale(
        self,
        recommend,
        build_profile,
    ):
        build_profile.return_value = self.profile
        DailyBookRecommendation.objects.create(
            user=self.user,
            recommendation_date=date(2026, 7, 15),
            payload={'books': [{'title': '어제의 검증된 책'}], 'themes': []},
            profile_basis=self.profile,
        )
        recommend.side_effect = BookRecommendationUnavailable(
            '서지 서비스 장애',
            code='NLK_SERVICE_UNAVAILABLE',
        )
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        with patch('mybook.views.timezone.localdate', return_value=self.today):
            response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_stale'])
        self.assertEqual(response.data['content_date'], '2026-07-15')
        self.assertEqual(response.data['books'][0]['title'], '어제의 검증된 책')
