# dev 머지로 갈라진 두 마이그레이션 줄기 병합 (2026-07-02)
# A: 0003_alter_user_character (캐릭터 4종 교체 — feature_chat)
# B: 0006_oauthaccount (소셜 로그인 — dev)
# 두 leaf를 하나로 합쳐 "Conflicting migrations" 오류 해결. 스키마 변경 없음.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_alter_user_character'),
        ('user', '0006_oauthaccount'),
    ]

    operations = []
