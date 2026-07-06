import os
import sys
import django

# Set up Django environment
sys.path.append(r"c:\Dev\project\SKN27-FINAL-4Team\app\backend")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from chat.models import MbtiAnswer
from mbti.models import MbtiQuestionResponse

print("--- MbtiAnswer (chat_mbtianswer) 최근 5건 ---")
for a in MbtiAnswer.objects.all().order_by('-id')[:5]:
    dt = a.created_at.strftime('%m-%d %H:%M:%S')
    print(f"[{dt}] User:{a.user_id} Code:{a.question_code} Answer:{a.answer_text}")

print("--- MbtiQuestionResponse (mbti_mbtiquestionresponse) 최근 5건 ---")
for r in MbtiQuestionResponse.objects.all().order_by('-id')[:5]:
    dt = r.created_at.strftime('%m-%d %H:%M:%S')
    print(f"[{dt}] User:{r.user_id} Axis:{r.target_axis} Answer:{r.answer_text} Period:{r.period_key}")
