from django.db import migrations, models


# 6대 감정별 힐링 차 초기 데이터
TEA_SEED = [
    {
        'emotion':  'anger',
        'name':     '페퍼민트 티',
        'name_en':  'Peppermint Tea',
        'emoji':    '🌿',
        'reason':   '강한 박하 향이 쌓인 분노와 긴장을 시원하게 씻어내줘요.',
        'effect':   '긴장 완화, 소화 촉진, 두통 경감',
        'brew_tip': '95°C 물에 2~3분 우리기 (너무 오래 우리면 쓴맛)',
        'caffeine': False,
    },
    {
        'emotion':  'sadness',
        'name':     '로즈 히비스커스 티',
        'name_en':  'Rose Hibiscus Tea',
        'emoji':    '🌹',
        'reason':   '선명한 붉은빛과 달콤한 꽃향이 울적한 마음에 따뜻한 위로를 건네줘요.',
        'effect':   '항산화, 기분 전환, 비타민 C 보충',
        'brew_tip': '85°C 물에 3~5분, 꿀 한 티스푼 추가 추천',
        'caffeine': False,
    },
    {
        'emotion':  'anxiety',
        'name':     '캐모마일 라벤더 티',
        'name_en':  'Chamomile Lavender Tea',
        'emoji':    '🌼',
        'reason':   '캐모마일과 라벤더의 은은한 향이 초조함을 가라앉히고 마음을 안정시켜줘요.',
        'effect':   '수면 유도, 항불안, 근육 이완',
        'brew_tip': '90°C 물에 5분, 뚜껑을 덮어 향이 날아가지 않게',
        'caffeine': False,
    },
    {
        'emotion':  'hurt',
        'name':     '루이보스 바닐라 티',
        'name_en':  'Rooibos Vanilla Tea',
        'emoji':    '🍂',
        'reason':   '부드럽고 달콤한 바닐라 향이 상처받은 마음을 감싸안듯 포근하게 달래줘요.',
        'effect':   '항산화, 심신 안정, 카페인 없이 따뜻한 온기',
        'brew_tip': '95°C 물에 5~7분, 우유를 살짝 더하면 더욱 부드러움',
        'caffeine': False,
    },
    {
        'emotion':  'fluster',
        'name':     '레몬밤 티',
        'name_en':  'Lemon Balm Tea',
        'emoji':    '🍋',
        'reason':   '레몬밤의 상큼한 향기가 혼란스러운 정신을 맑게 가다듬어 줘요.',
        'effect':   '인지 기능 지원, 심박 안정, 집중력 회복',
        'brew_tip': '80°C 물에 3~4분, 과하게 우리면 쓴맛',
        'caffeine': False,
    },
    {
        'emotion':  'joy',
        'name':     '얼그레이 티',
        'name_en':  'Earl Grey Tea',
        'emoji':    '☕',
        'reason':   '베르가못의 상쾌한 향이 기쁜 기분을 한층 더 풍성하게 채워줘요.',
        'effect':   '기분 향상, 집중력 강화, 소화 촉진',
        'brew_tip': '95°C 물에 3~4분, 밀크티로 즐겨도 좋아요',
        'caffeine': True,
    },
]

# 6대 감정별 BGM 초기 데이터 (감정당 3곡)
BGM_SEED = [
    # 분노 — 차분히 가라앉히는 음악
    {'emotion': 'anger', 'title': 'Clair de Lune', 'artist': 'Claude Debussy', 'mood': '달빛처럼 부드럽고 잔잔하게 마음을 식혀주는 피아노', 'youtube_query': 'Debussy Clair de Lune piano', 'genre': '클래식'},
    {'emotion': 'anger', 'title': 'River Flows in You', 'artist': 'Yiruma', 'mood': '잔잔한 물처럼 흐르며 화난 감정을 부드럽게 흘려보내줘요', 'youtube_query': 'Yiruma River Flows in You piano', 'genre': '뉴에이지'},
    {'emotion': 'anger', 'title': 'Comptine d\'un autre été', 'artist': 'Yann Tiersen', 'mood': '영화 아멜리에의 서정적인 선율로 분노를 무력화시켜요', 'youtube_query': 'Yann Tiersen Comptine piano', 'genre': '영화음악'},

    # 슬픔 — 공감하며 위로하는 음악
    {'emotion': 'sadness', 'title': 'Gymnopédie No.1', 'artist': 'Erik Satie', 'mood': '고요하고 몽환적인 선율이 슬픔을 조용히 어루만져줘요', 'youtube_query': 'Satie Gymnopedie No 1 piano', 'genre': '클래식'},
    {'emotion': 'sadness', 'title': 'The Night', 'artist': 'Ludovico Einaudi', 'mood': '밤처럼 깊고 따뜻한 피아노가 눈물과 함께 흘러가요', 'youtube_query': 'Einaudi The Night piano', 'genre': '뉴에이지'},
    {'emotion': 'sadness', 'title': 'Experience', 'artist': 'Ludovico Einaudi', 'mood': '가슴 저미는 현악과 피아노로 슬픔을 온전히 느끼게 해줘요', 'youtube_query': 'Einaudi Experience strings', 'genre': '뉴에이지'},

    # 불안 — 호흡을 가라앉히는 음악
    {'emotion': 'anxiety', 'title': 'Weightless', 'artist': 'Marconi Union', 'mood': '과학적으로 불안을 65% 낮춰주는 것으로 알려진 ambient 트랙', 'youtube_query': 'Marconi Union Weightless anxiety reduction', 'genre': '앰비언트'},
    {'emotion': 'anxiety', 'title': 'Aqua', 'artist': 'ERA', 'mood': '물처럼 투명하고 흐르는 소리가 긴장을 녹여줘요', 'youtube_query': 'ERA Aqua relaxing ambient', 'genre': '앰비언트'},
    {'emotion': 'anxiety', 'title': 'Pure Shores', 'artist': 'All Saints', 'mood': '파도 소리와 청명한 보컬로 마음의 해안으로 데려다줘요', 'youtube_query': 'All Saints Pure Shores relaxing', 'genre': '팝'},

    # 상처 — 포근하게 감싸주는 음악
    {'emotion': 'hurt', 'title': 'Skinny Love', 'artist': 'Bon Iver', 'mood': '허스키하고 진실된 목소리가 상처받은 마음에 공감해줘요', 'youtube_query': 'Bon Iver Skinny Love acoustic', 'genre': '인디 포크'},
    {'emotion': 'hurt', 'title': 'The Scientist', 'artist': 'Coldplay', 'mood': '잔잔한 피아노와 진솔한 가사가 상처를 다독여줘요', 'youtube_query': 'Coldplay The Scientist acoustic', 'genre': '팝 록'},
    {'emotion': 'hurt', 'title': 'Healing', 'artist': 'Tom Odell', 'mood': '마음의 평온을 향해 천천히 걸어가는 듯한 따뜻한 선율', 'youtube_query': 'Tom Odell healing piano ballad', 'genre': '인디 팝'},

    # 당황 — 안정감을 주는 음악
    {'emotion': 'fluster', 'title': 'Canon in D', 'artist': 'Johann Pachelbel', 'mood': '예측 가능한 반복 선율이 혼란스러운 마음에 질서를 줘요', 'youtube_query': 'Pachelbel Canon in D relaxing', 'genre': '클래식'},
    {'emotion': 'fluster', 'title': 'Morning Mood', 'artist': 'Edvard Grieg', 'mood': '아침 햇살처럼 밝고 차분한 오케스트라가 정신을 맑게 해줘요', 'youtube_query': 'Grieg Morning Mood Peer Gynt', 'genre': '클래식'},
    {'emotion': 'fluster', 'title': 'Coffee', 'artist': 'beabadoobee', 'mood': '느긋하고 아늑한 기타 팝이 당황한 마음을 편안하게 해줘요', 'youtube_query': 'beabadoobee Coffee acoustic', 'genre': '인디 팝'},

    # 기쁨 — 기쁨을 함께 즐기는 음악
    {'emotion': 'joy', 'title': 'Happy', 'artist': 'Pharrell Williams', 'mood': '세상에서 가장 신나는 팝으로 기쁜 에너지를 두 배로 만들어줘요', 'youtube_query': 'Pharrell Williams Happy official', 'genre': '팝'},
    {'emotion': 'joy', 'title': 'Good Day Sunshine', 'artist': 'The Beatles', 'mood': '햇살처럼 밝고 활기찬 비틀즈의 클래식으로 기분이 절로 업돼요', 'youtube_query': 'Beatles Good Day Sunshine', 'genre': '팝 록'},
    {'emotion': 'joy', 'title': 'Levitating', 'artist': 'Dua Lipa', 'mood': '둥둥 떠오르는 듯한 리듬감이 기쁜 순간을 더욱 찬란하게 해줘요', 'youtube_query': 'Dua Lipa Levitating official', 'genre': '팝'},
]


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0004_chatmessage_emotion6'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeaRecommendation',
            fields=[
                ('id',       models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emotion',  models.CharField(choices=[('anger','분노'),('sadness','슬픔'),('anxiety','불안'),('hurt','상처'),('fluster','당황'),('joy','기쁨')], max_length=10, unique=True, verbose_name='감정 코드')),
                ('name',     models.CharField(max_length=60, verbose_name='차 이름')),
                ('name_en',  models.CharField(blank=True, max_length=60, verbose_name='차 이름 (영문)')),
                ('emoji',    models.CharField(max_length=8, verbose_name='이모지')),
                ('reason',   models.TextField(verbose_name='추천 이유 (1~2문장)')),
                ('effect',   models.CharField(max_length=120, verbose_name='주요 효능')),
                ('brew_tip', models.CharField(blank=True, max_length=200, verbose_name='우리는 법 팁')),
                ('caffeine', models.BooleanField(default=False, verbose_name='카페인 함유 여부')),
            ],
            options={'db_table': 'tea_recommendations', 'verbose_name': '힐링 차 추천', 'verbose_name_plural': '힐링 차 추천 목록'},
        ),
        migrations.CreateModel(
            name='BgmRecommendation',
            fields=[
                ('id',            models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emotion',       models.CharField(choices=[('anger','분노'),('sadness','슬픔'),('anxiety','불안'),('hurt','상처'),('fluster','당황'),('joy','기쁨')], max_length=10, verbose_name='감정 코드')),
                ('title',         models.CharField(max_length=120, verbose_name='곡 제목')),
                ('artist',        models.CharField(max_length=120, verbose_name='아티스트')),
                ('mood',          models.CharField(max_length=200, verbose_name='분위기 설명 (1문장)')),
                ('youtube_query', models.CharField(max_length=200, verbose_name='유튜브 검색어')),
                ('genre',         models.CharField(blank=True, max_length=60, verbose_name='장르')),
                ('is_active',     models.BooleanField(default=True, verbose_name='활성화 여부')),
            ],
            options={'db_table': 'bgm_recommendations', 'verbose_name': 'BGM 추천', 'verbose_name_plural': 'BGM 추천 목록'},
        ),
        # 초기 시드 데이터 삽입 — 6대 감정 차 1:1 + BGM 감정당 3곡
        migrations.RunPython(
            lambda apps, schema_editor: _seed(apps),
            migrations.RunPython.noop,
        ),
    ]


def _seed(apps):
    Tea = apps.get_model('chat', 'TeaRecommendation')
    Bgm = apps.get_model('chat', 'BgmRecommendation')
    for row in TEA_SEED:
        Tea.objects.get_or_create(emotion=row['emotion'], defaults=row)
    for row in BGM_SEED:
        Bgm.objects.create(**row)
