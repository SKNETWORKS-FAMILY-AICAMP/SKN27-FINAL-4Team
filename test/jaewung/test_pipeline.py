import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from mbti.models import MbtiQuestionResponse

responses = MbtiQuestionResponse.objects.filter(user_id=3)
for r in responses:
    print(f"[{r.target_axis}] Q: {r.question_text[:50]} | A: {r.answer_text[:50]}")
