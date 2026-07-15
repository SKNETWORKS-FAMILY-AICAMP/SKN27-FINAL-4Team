from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from .agent import (
    BookRecommendationAgent,
    BookRecommendationUnavailable,
    NLK_COVER_PROVIDER_INFO,
    _is_general_book,
    _nlk_items,
    _nlk_search_terms,
    _rank_personalized_books,
    _request_nlk_cover,
    _request_nlk_books,
)
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
        self.assertEqual(request_get.call_args_list[0].kwargs['params']['label'], '사진')
        self.assertNotIn('headers', request_get.call_args_list[0].kwargs.get('params', {}))

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

    @patch('mybook.agent.time.sleep')
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

    @patch.object(BookRecommendationAgent, '_search_nlk_books')
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

    def test_search_terms_keep_specific_words_for_title_search(self):
        self.assertEqual(
            _nlk_search_terms('사진 실용 도서'),
            ['사진 실용 도서', '사진'],
        )

    def test_payload_separates_lod_metadata_and_ai_curation(self):
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
            'description': '국가서지 초록',
            'subjects': ['사진술'],
            'link': 'https://lod.nl.go.kr/resource/BOOK-2',
            'isbn': '9788959710256',
            'general_book_verified': True,
        }

        payload = BookRecommendationAgent._book_payload(theme, book, 'AI 추천 서평', genre='실용서')

        self.assertEqual(payload['source_result']['description'], '국가서지 초록')
        self.assertEqual(payload['source_result']['subjects'], ['사진술'])
        self.assertTrue(payload['source_result']['general_book_verified'])
        self.assertEqual(payload['ai_curation']['review'], 'AI 추천 서평')
        self.assertEqual(payload['source_provider']['id'], 'nlk_national_bibliography_lod')

    @patch.object(BookRecommendationAgent, '_generate_reviews')
    @patch.object(BookRecommendationAgent, '_search_nlk_books')
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
                'reason': '감정 기준', 'keyword_basis': '오늘의 감정',
                'basis_label': '오늘의 감정', 'basis_values': ['슬픔'],
            },
            {
                'id': 'interests', 'name': '관심사', 'keyword': '음악 감상',
                'reason': '관심사 기준', 'keyword_basis': '관심사',
                'basis_label': '관심사', 'basis_values': ['음악'],
            },
            {
                'id': 'hobbies', 'name': '취미', 'keyword': '사진 촬영',
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
            '마음 회복', display=4, basis_values=['슬픔'], theme_id='emotion'
        )
        search_books.assert_any_call(
            '음악 감상', display=4, basis_values=['음악'], theme_id='interests'
        )
        search_books.assert_any_call(
            '사진 촬영', display=4, basis_values=['사진'], theme_id='hobbies'
        )
        self.assertTrue(result['selection_policy']['general_books_only'])
        self.assertEqual(
            result['source_disclosure']['cover_metadata'],
            '국립중앙도서관 ISBN 서지정보 TITLE_URL',
        )


class NationalLibraryCoverTests(SimpleTestCase):
    @patch('mybook.agent.requests.get')
    def test_isbn_api_title_url_is_normalized_as_official_cover(self, request_get):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'PAGE_NO': '1',
            'TOTAL_COUNT': '1',
            'docs': [
                {
                    'EA_ISBN': '9788959710256',
                    'TITLE_URL': 'http://seoji.nl.go.kr/cover/9788959710256.jpg',
                }
            ],
        }
        request_get.return_value = response

        cover_url = _request_nlk_cover('isbn-key', '9788959710256')

        self.assertEqual(
            cover_url,
            'https://seoji.nl.go.kr/cover/9788959710256.jpg',
        )
        self.assertEqual(request_get.call_args.kwargs['params']['isbn'], '9788959710256')
        self.assertEqual(request_get.call_args.kwargs['params']['cert_key'], 'isbn-key')
        self.assertEqual(request_get.call_args.kwargs['timeout'], 3.0)

    @patch.dict('os.environ', {'NLK_ISBN_SERVICE_KEY': 'isbn-key'}, clear=False)
    @patch('mybook.agent._cached_nlk_cover_url')
    def test_final_recommendation_receives_cover_in_both_payload_shapes(self, cover_lookup):
        cover_lookup.return_value = 'https://www.nl.go.kr/cover/book.jpg'
        book = {
            'isbn': '9788959710256',
            'image': '',
            'source_result': {'isbn': '9788959710256', 'image': ''},
        }

        BookRecommendationAgent._enrich_book_covers([book])

        self.assertEqual(book['image'], 'https://www.nl.go.kr/cover/book.jpg')
        self.assertEqual(
            book['source_result']['image'],
            'https://www.nl.go.kr/cover/book.jpg',
        )
        self.assertEqual(book['cover_provider'], NLK_COVER_PROVIDER_INFO)
        self.assertEqual(
            book['source_result']['cover_provider'],
            NLK_COVER_PROVIDER_INFO,
        )

    @patch.dict('os.environ', {'NLK_ISBN_SERVICE_KEY': 'isbn-key'}, clear=False)
    @patch('mybook.agent._cached_nlk_cover_url', side_effect=requests.Timeout('slow'))
    def test_cover_failure_does_not_fail_or_mutate_recommendation(self, cover_lookup):
        book = {
            'isbn': '9788959710256',
            'image': '',
            'source_result': {'isbn': '9788959710256', 'image': ''},
        }

        BookRecommendationAgent._enrich_book_covers([book])

        self.assertEqual(book['image'], '')
        self.assertEqual(book['source_result']['image'], '')


class BookRecommendationViewStabilityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(id=7, is_authenticated=True)
        self.profile = {
            'today_emotion': '평온',
            'interests': ['사진'],
            'hobbies': ['산책'],
        }

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.cache')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_uncached_service_failure_returns_retryable_503(self, recommend, cache, build_profile):
        build_profile.return_value = self.profile
        cache.get.return_value = None
        recommend.side_effect = BookRecommendationUnavailable(
            '서지 서비스 장애',
            code='NLK_SERVICE_UNAVAILABLE',
        )
        request = self.factory.get('/api/mybook/recommendation/')
        force_authenticate(request, user=self.user)

        response = book_recommendation(request)

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.data['retryable'])
        self.assertEqual(response.data['code'], 'NLK_SERVICE_UNAVAILABLE')
        cache.set.assert_not_called()

    @patch('mybook.views._build_user_profile')
    @patch('mybook.views.cache')
    @patch('mybook.views.BookRecommendationAgent.recommend')
    def test_failed_forced_refresh_serves_stale_cache_without_overwriting_it(
        self,
        recommend,
        cache,
        build_profile,
    ):
        build_profile.return_value = self.profile
        cache.get.return_value = {'books': [{'title': '검증된 이전 책'}], 'themes': []}
        recommend.side_effect = BookRecommendationUnavailable(
            '서지 서비스 장애',
            code='NLK_SERVICE_UNAVAILABLE',
        )
        request = self.factory.get('/api/mybook/recommendation/?force=true')
        force_authenticate(request, user=self.user)

        response = book_recommendation(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_stale'])
        self.assertEqual(response.data['service_status']['state'], 'degraded')
        self.assertEqual(response.data['books'][0]['title'], '검증된 이전 책')
        cache.set.assert_not_called()
