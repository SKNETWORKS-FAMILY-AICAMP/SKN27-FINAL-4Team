from django.test import SimpleTestCase

from mbti.services.question_generation import clean_generated_question


class MbtiQuestionGenerationTests(SimpleTestCase):
    def test_missing_question_mark_is_normalized(self):
        cleaned = clean_generated_question(
            '최근에는 계획을 먼저 정하는 편이야, 상황을 보며 정하는 편이야'
        )

        self.assertEqual(
            cleaned,
            '최근에는 계획을 먼저 정하는 편이야, 상황을 보며 정하는 편이야?',
        )

