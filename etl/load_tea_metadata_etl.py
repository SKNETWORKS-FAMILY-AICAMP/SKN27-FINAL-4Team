import os
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

# List of 64 unique teas to fetch/align
CORE_TEAS = [
    # 1-8: Depression & Low Motivation
    {"name": "로즈마리", "display_name": "로즈마리", "english": "Rosemary"},
    {"name": "홍차", "display_name": "얼그레이 (홍차/베르가못)", "english": "Earl Grey"},
    {"name": "유자", "display_name": "유자차", "english": "Citron Tea"},
    {"name": "구기자", "display_name": "구기자차", "english": "Goji Berry Tea"},
    {"name": "황기", "display_name": "황기차", "english": "Astragalus Tea"},
    {"name": "진피", "display_name": "진피차", "english": "Citrus Peel Tea"},
    {"name": "초석잠", "display_name": "초석잠차", "english": "Chinese Artichoke Tea"},
    {"name": "백합", "display_name": "백합차", "english": "Lily Bulb Tea"},
    
    # 9-16: Anxiety & Panic
    {"name": "카밀레", "display_name": "캐모마일 (카밀레)", "english": "Chamomile"},
    {"name": "레몬밤", "display_name": "레몬밤", "english": "Lemon Balm"},
    {"name": "허니부쉬", "display_name": "허니부쉬", "english": "Honeybush"},
    {"name": "백복령", "display_name": "백복령차", "english": "Poria Tea"},
    {"name": "산조인", "display_name": "산조인차", "english": "Sour Date Seed Tea"},
    {"name": "연꽃", "display_name": "연꽃차", "english": "Lotus Flower Tea"},
    {"name": "자스민", "display_name": "자스민", "english": "Jasmine"},
    {"name": "대조", "display_name": "대추차 (대조)", "english": "Jujube Tea"},
    
    # 17-24: Anger & Irritation
    {"name": "라벤더", "display_name": "라벤더", "english": "Lavender"},
    {"name": "감국", "display_name": "국화차 (감국)", "english": "Chrysanthemum Tea"},
    {"name": "히비스커스", "display_name": "히비스커스", "english": "Hibiscus"},
    {"name": "메밀", "display_name": "메밀차", "english": "Buckwheat Tea"},
    {"name": "결명자", "display_name": "결명자차", "english": "Cassia Seed Tea"},
    {"name": "레몬버베나", "display_name": "레몬버베나", "english": "Lemon Verbena"},
    {"name": "오매", "display_name": "매실차", "english": "Green Plum Tea"},
    {"name": "갈근", "display_name": "칡차", "english": "Kudzu Root Tea"},
    
    # 25-32: Lack of Focus
    {"name": "다엽", "display_name": "녹차 (다엽)", "english": "Green Tea"},
    {"name": "홍차_오렌지페코", "display_name": "홍차 (오렌지 페코)", "english": "Orange Pekoe"},
    {"name": "루이보스", "display_name": "루이보스", "english": "Rooibos"},
    {"name": "둥굴레", "display_name": "둥굴레차", "english": "Solomon's Seal Tea"},
    {"name": "보리", "display_name": "보리차", "english": "Barley Tea"},
    {"name": "현미녹차", "display_name": "현미녹차", "english": "Brown Rice Green Tea"},
    {"name": "의이인", "display_name": "율무차", "english": "Job's Tears Tea"},
    {"name": "송엽", "display_name": "솔잎차", "english": "Pine Needle Tea"},
    
    # 33-40: Insomnia
    {"name": "연잎", "display_name": "연잎차", "english": "Lotus Leaf Tea"},
    {"name": "백자인", "display_name": "백자인차", "english": "Arborvitae Seed Tea"},
    {"name": "용안육", "display_name": "용안육차", "english": "Longan Tea"},
    {"name": "상엽", "display_name": "상엽차", "english": "Mulberry Leaf Tea"},
    {"name": "영지버섯", "display_name": "영지버섯차", "english": "Ganoderma Tea"},
    {"name": "감태", "display_name": "감태차", "english": "Ecklonia Cava Tea"},
    {"name": "박하", "display_name": "페퍼민트 (박하)", "english": "Peppermint"},
    {"name": "당귀", "display_name": "당귀차", "english": "Angelica Tea"},
    
    # 41-48: Chronic Fatigue & Burnout
    {"name": "오미자", "display_name": "오미자차", "english": "Schisandra Tea"},
    {"name": "생강", "display_name": "생강차", "english": "Ginger Tea"},
    {"name": "모과", "display_name": "모과차", "english": "Quince Tea"},
    {"name": "산수유", "display_name": "산수유차", "english": "Cornus Fruit Tea"},
    {"name": "가시오가피", "display_name": "가시오가피차", "english": "Siberian Ginseng Tea"},
    {"name": "인삼", "display_name": "인삼차", "english": "Ginseng Tea"},
    {"name": "홍삼", "display_name": "홍삼차", "english": "Red Ginseng Tea"},
    {"name": "맥문동", "display_name": "맥문동차", "english": "Broadleaf Liriope Tea"},
    
    # 49-56: Hwabyung & Chest Tightness
    {"name": "죽엽", "display_name": "대나무잎차 (죽엽)", "english": "Bamboo Leaf Tea"},
    {"name": "감초", "display_name": "감초차", "english": "Licorice Tea"},
    {"name": "소엽", "display_name": "소엽차", "english": "Perilla Leaf Tea"},
    {"name": "복분자", "display_name": "복분자차", "english": "Blackberry Tea"},
    {"name": "백작약", "display_name": "백작약차", "english": "White Peony Root Tea"},
    {"name": "숙지황", "display_name": "숙지황차", "english": "Rehmannia Tea"},
    {"name": "민들레", "display_name": "민들레차 (포공영)", "english": "Dandelion Tea"},
    {"name": "천궁", "display_name": "천궁차", "english": "Cnidium Tea"},
    
    # 57-64: Headache & Hot Flashes
    {"name": "치자", "display_name": "치자차", "english": "Gardenia Tea"},
    {"name": "형개", "display_name": "형개차", "english": "Schizonepeta Tea"},
    {"name": "시호", "display_name": "시호차", "english": "Bupleurum Tea"},
    {"name": "백지", "display_name": "백지차", "english": "Angelica Dahurica Tea"},
    {"name": "우엉", "display_name": "우엉차", "english": "Burdock Tea"},
    {"name": "연근", "display_name": "연근차", "english": "Lotus Root Tea"},
    {"name": "더덕", "display_name": "더덕차", "english": "Deodeok Tea"},
    {"name": "길경", "display_name": "도라지차 (길경)", "english": "Balloon Flower Tea"}
]

# KMCRIC & Academic Verified Pharmacological Reasons (Used as cross-reference fallback)
ACADEMIC_MAPPINGS = {
    "로즈마리": {
        "scientific_name": "Rosmarinus officinalis",
        "efficacy": "뇌 기능 활성화, 인지력 강화 및 정서적 활력 부여",
        "scientific_reason": "로즈마린산(Rosmarinic acid)이 아세틸콜린(Acetylcholine) 분해 효소를 억제하여 뇌세포 활성화를 돕고, 무기력한 우울 상태에서 정신적 활기를 유도합니다.",
        "tip": "무기력하게 누워있고 싶을 때, 아침에 일어나 첫 잔으로 마시면 정신을 맑게 깨워줍니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '로즈마리' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "자존감 저하", "기억력 감퇴"],
        "recommended_weathers": ["맑음", "바람"]
    },
    "홍차": {
        "scientific_name": "Camellia sinensis + Citrus bergamia",
        "efficacy": "정서적 활력 부여 및 우울 기분 리프레시",
        "scientific_reason": "베르가못(Bergamot)의 리모넨(Limonene) 성분이 교감신경의 활성화를 조율하고 뇌내 엔도르핀 분비를 유도하여 우울 및 무기력 상태를 정서적으로 완화시킵니다.",
        "tip": "아침이나 오후 나른한 시간에 우유를 살짝 섞어 밀크티로 즐기면 포근함과 기분 전환을 동시에 줍니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '다엽 (Theae Folium)' 등재 및 식약처 식품원료 정보",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "활력 저하", "만성 피로"],
        "recommended_weathers": ["흐림", "추움"]
    },
    "유자": {
        "scientific_name": "Citrus junos",
        "efficacy": "스트레스 완화 및 비타민 C 공급을 통한 피로 회복",
        "scientific_reason": "풍부한 비타민 C와 리모넨(Limonene) 향 성분이 부신 피질 호르몬의 합성을 도와 정서적 활력을 주고, 가벼운 우울감과 피로를 낮춥니다.",
        "tip": "감기 기운이 있거나 기분이 가라앉을 때 유자청을 따뜻한 물에 타서 새콤달콤하게 즐깁니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "만성 피로", "자존감 저하"],
        "recommended_weathers": ["흐림", "추움"]
    },
    "구기자": {
        "scientific_name": "Lycium chinense",
        "efficacy": "피로 개선, 간세포 보호 및 시력 보호",
        "scientific_reason": "구기자의 베타인(Betaine)과 지아잔틴(Zeaxanthin) 성분이 체내 항산화 활성을 돕고 부신 피질 호르몬의 피로성 고갈을 보완하여 피로 누적으로 인한 무기력을 완화합니다.",
        "tip": "피로 누적으로 눈이 침침하고 몸이 처질 때 구기자를 끓여 따뜻하게 수시로 마십니다.",
        "official_source": "대한민국약전 (KP) - '구기자 (Lycii Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "활력 저하", "눈 침침함", "피로"],
        "recommended_weathers": ["따뜻함", "흐림"]
    },
    "황기": {
        "scientific_name": "Astragalus membranaceus",
        "efficacy": "면역력 증진, 피로 극복 및 신체 에너지 보강",
        "scientific_reason": "아스트라갈로사이드(Astragaloside) 성분이 지친 세포의 면역 능력을 올리고 에너지를 공급해 만성 피로와 허약성 우울을 완화합니다.",
        "tip": "의욕이 없고 몸이 무겁고 추위를 많이 탈 때 은은하게 달여 마시는 것을 추천합니다.",
        "official_source": "대한민국약전 (KP) - '황기 (Astragali Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "무기력", "만성 피로", "의욕 상실"],
        "recommended_weathers": ["바람", "추움"]
    },
    "진피": {
        "scientific_name": "Citrus unshiu",
        "efficacy": "기 흐름 원활, 소화 촉진 및 답답함 완화",
        "scientific_reason": "귤껍질(진피)의 리모넨(Limonene)과 헤스페리딘(Hesperidin)이 말초 혈액순환을 촉진하고 소화관 운동을 활성화하여 신경성 가슴 답답함과 슬픔 정서를 환기시킵니다.",
        "tip": "신경을 많이 써서 체기가 돌고 마음에 답답함과 슬픈 기분이 맴돌 때 따뜻하게 한 잔 우려 마십니다.",
        "official_source": "대한민국약전 (KP) - '진피 (Citri Unshius Pericarpium)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "슬픔", "가슴 답답함", "소화 불량"],
        "recommended_weathers": ["바람", "흐림"]
    },
    "초석잠": {
        "scientific_name": "Stachys affinis",
        "efficacy": "뇌세포 보호, 기억력 증진 및 인지 기능 안정",
        "scientific_reason": "페닐에타노이드 배당체 성분이 지친 신경세포의 산화적 손상을 방지하고 아세틸콜린 수치를 안정적으로 늘려, 우울과 피로로 인한 일시적 기억 감퇴 상태를 개선합니다.",
        "tip": "공부나 생각할 일이 많은데 의욕이 떨어지고 건망증이 생길 때 따뜻하게 차로 즐기시면 좋습니다.",
        "official_source": "식품의약품안전처 식품원료 정보 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "무기력", "기억력 저하"],
        "recommended_weathers": ["흐림", "맑음"]
    },
    "백합": {
        "scientific_name": "Lilium brownii",
        "efficacy": "정서적 이완, 상열감 완화 및 만성 마른기침 진정",
        "scientific_reason": "백합 구근에 함유된 다당류와 사포닌 성분이 신경계의 긴장을 진정시키고, 한의학적으로 심경(心經)의 열을 내려 가슴이 답답하고 뜬구름 잡는 우울 정서를 잡아줍니다.",
        "tip": "이유 없는 우울감으로 정서가 극도로 가라앉거나 불면이 생기려고 할 때 뜨겁게 우려내어 향을 맡으며 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '백합 (Lilii Bulbus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["우울", "자존감 저하", "초조함", "불면"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "카밀레": {
        "scientific_name": "Matricaria chamomilla",
        "efficacy": "신경 안정, 불안 완화 및 불면 개선 도움",
        "scientific_reason": "캐모마일에 풍부한 아피게닌(Apigenin) 항산화 물질이 뇌의 가바(GABA-A) 수용체와 직접적으로 결합하여 중추신경계를 안정시키고 불안 증세를 경감하는 작용을 합니다.",
        "tip": "대화 종료 후 취침 1시간 전에 따뜻하게 우려 마시면 신체 긴장 완화에 탁월합니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '카밀레' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "스트레스", "긴장", "수면장애"],
        "recommended_weathers": ["비", "흐림", "추움"]
    },
    "레몬밤": {
        "scientific_name": "Melissa officinalis",
        "efficacy": "자율신경 안정, 가슴 두근거림 및 얕은 호흡 완화 도움",
        "scientific_reason": "레몬밤의 로즈마린산(Rosmarinic acid) 성분이 가바 분해 효소(GABA Transaminase)의 활성을 억제하여 뇌내 GABA 농도를 보존함으로써 공황 및 불안에 의한 신체 증상을 완화합니다.",
        "tip": "불안감으로 인해 가슴이 답답하고 호흡이 얕아지며 신경성 소화 불량이 발생할 때 따뜻하게 마십니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '레몬밤' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "공황", "가슴 두근거림"],
        "recommended_weathers": ["비", "흐림"]
    },
    "허니부쉬": {
        "scientific_name": "Cyclopia subternata",
        "efficacy": "무카페인 미네랄 공급 및 달콤한 향을 통한 정서 안정",
        "scientific_reason": "이소플라본과 헤스페리딘 성분이 풍부하여 뇌세포의 활성산소를 억제하고, 천연의 달콤한 향이 도파민과 세로토닌의 가벼운 분비를 촉진해 불안감을 조절합니다.",
        "tip": "기분 좋고 향기로운 휴식이 필요할 때 달콤한 꿀 향을 지닌 허니부쉬 티백을 가볍게 우려 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "예민함", "스트레스"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "백복령": {
        "scientific_name": "Poria cocos",
        "efficacy": "가슴 두근거림 완화, 정서적 안정 및 이뇨 작용 지원",
        "scientific_reason": "백복령의 파키만(Pachyman)과 트리테르펜 성분이 중추신경흥분을 억제하고 이완을 유도하여, 불안으로 인해 심장이 과도하게 뛰고 숨이 차는 증상을 진정시킵니다.",
        "tip": "공황 상태나 정서적 극도 불안으로 잠을 이룰 수 없고 가슴이 벌렁거릴 때 끓여 마시면 좋습니다.",
        "official_source": "대한민국약전 (KP) - '복령 (Poria)' 규격 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "공황", "가슴 두근거림"],
        "recommended_weathers": ["비", "눈"]
    },
    "산조인": {
        "scientific_name": "Ziziphus jujuba var. spinosa",
        "efficacy": "만성 불안 진정, 신경 쇠약 조절 및 숙면 유도",
        "scientific_reason": "뽂은 산조인에 다량 들어있는 사포닌과 플라보노이드가 해마의 수용체를 완화하여 뇌의 흥분을 조절하고 각성 물질을 낮춰 깊은 이완과 신경 쇠약 극복을 돕습니다.",
        "tip": "가슴 두근거림과 지속적인 불안에 지쳐 신경이 예민해졌을 때 저녁 시간에 가볍게 마시는 것을 권합니다.",
        "official_source": "대한민국약전 (KP) - '산조인 (Ziziphi Spinosae Semen)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "신경 쇠약", "스트레스성 불면"],
        "recommended_weathers": ["추움", "바람"]
    },
    "연꽃": {
        "scientific_name": "Nelumbo nucifera",
        "efficacy": "정신 불안 이완, 화 기운 안정 및 구강 건조 해소",
        "scientific_reason": "연꽃의 누시페린(Nuciferine) 알칼로이드 성분이 신경 안정 작용을 수행하며 스트레스로 인해 침이 마르고 마음에 열이 오르는 과도한 불안 회로를 해제합니다.",
        "tip": "가슴속에서 불안한 열 기운이 일어 입술이 마르고 안절부절못할 때 연꽃송이를 우려 깊게 음미합니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식약처 생약정보 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "초조함", "구강 건조"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "자스민": {
        "scientific_name": "Jasminum officinale",
        "efficacy": "평온 유지, 집중 분산 완화 및 정서 안정",
        "scientific_reason": "자스민의 벤질 아세테이트(Benzyl acetate) 향 성분이 후각을 통해 중추신경계의 부교감신경을 자극하고 알파 뇌파 생성을 도와 산만한 감정을 차분하게 조율해 줍니다.",
        "tip": "마음이 산만하고 감정 조절이 어려울 때 은은한 향을 천천히 호흡하며 마십니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '자스민' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "정서 불안", "산만함"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "대조": {
        "scientific_name": "Ziziphus jujuba",
        "efficacy": "신경 완화, 피로 조절 및 수면 유도 지원",
        "scientific_reason": "대추의 스피노신(Spinosin) 성분이 천연 신경안정 물질로 작용하여 시상하부의 세로토닌 수용체를 안정시키고 뇌의 과도한 각성 및 스트레스성 긴장 상태를 이완합니다.",
        "tip": "일교차가 크고 수많은 근심걱정으로 인해 몸에 힘이 잔뜩 들어가 잠들기 어려울 때 달여 따뜻하게 마십니다.",
        "official_source": "대한민국약전 (KP) - '대조 (Zizyphi Fructus)' 규격 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "스트레스성 불면", "과도한 걱정", "근육 긴장"],
        "recommended_weathers": ["추움", "바람"]
    },
    "라벤더": {
        "scientific_name": "Lavandula angustifolia",
        "efficacy": "심박수 감소, 분노 진정 및 혈압 안정 도움",
        "scientific_reason": "라벤더 에센셜 오일의 리날롤(Linalool)과 아세트산리날릴(Linalyl acetate) 성분이 자율신경계(부교감신경)를 항진시켜 혈압을 낮추고 흥분 상태를 진정시킵니다.",
        "tip": "갑작스러운 분노가 끓어오를 때 뜨겁게 우려내어 향을 먼저 깊게 맡은 후 마십니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '라벤더' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "과민성 스트레스", "초조함"],
        "recommended_weathers": ["비", "흐림", "바람"]
    },
    "감국": {
        "scientific_name": "Chrysanthemum indicum",
        "efficacy": "상열감 완화, 두통 진정 및 감정 가라앉히기",
        "scientific_reason": "감국 꽃에 포함된 루테올린(Luteolin)과 아피게닌(Apigenin) 플라보노이드가 신경계 염증 반응을 억제하고 혈관을 이완하여 짜증으로 인한 뇌 상열감을 내려줍니다.",
        "tip": "스트레스로 뒷목이 뻐근하거나 컴퓨터 사용으로 눈이 뻑뻑할 때 국화 꽃송이를 우려 마시면 좋습니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '감국 (Chrysanthemi Flos)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "짜증", "눈의 피로"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "히비스커스": {
        "scientific_name": "Hibiscus sabdariffa",
        "efficacy": "체내 젖산 분해, 혈압 강하 및 신체적 피로 회복",
        "scientific_reason": "유기산인 구연산(Citric acid)과 히비스신(Hibiscin)이 세포 속 젖산 축적을 강력히 억제하여 피로 회복을 돕고, 말초 혈관 확장을 유도해 과도하게 흥분된 울화 기운을 내려줍니다.",
        "tip": "더운 여름철이나 가슴에서 열불이 나 화가 치밀어 오를 때 시원하게 얼음과 함께 즐기면 진정에 좋습니다.",
        "official_source": "식품의약품안전처 국가생약정보 (NHMI) - '히비스커스' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "무기력", "스트레스성 과식", "울화"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "메밀": {
        "scientific_name": "Fagopyrum esculentum",
        "efficacy": "혈압 안정, 체내 열 내리기 및 모세혈관 보호",
        "scientific_reason": "플라보노이드의 일종인 루틴(Rutin) 성분이 모세혈관을 강화하고 혈압을 안정시켜, 화나 짜증으로 인해 혈압이 오르는 신체적 흥분 상태를 식혀줍니다.",
        "tip": "갑작스러운 화로 뒷목이 땅기거나 얼굴에 상열감이 일 때 따뜻한 메밀차를 음미하며 천천히 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "짜증", "상열감"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "결명자": {
        "scientific_name": "Senna tora",
        "efficacy": "간 열 내리기, 안구 피로 완화 및 두통 완화",
        "scientific_reason": "안트라퀴논(Anthraquinone) 유도체 성분이 한의학적으로 간장의 열(간열)을 내려주며, 스트레스 과다로 눈이 충혈되고 뒷목이 뻐근한 분노성 두통을 진정시킵니다.",
        "tip": "스트레스로 뒷목이 당기고 눈이 침침하며 두통이 동반될 때 진하게 달여서 한 잔 마십니다.",
        "official_source": "대한민국약전 (KP) - '결명자 (Cassiae Semen)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "짜증", "두통"],
        "recommended_weathers": ["더움", "흐림"]
    },
    "레몬버베나": {
        "scientific_name": "Aloysia citrodora",
        "efficacy": "신경 이완, 스트레스성 경련 및 굳은 근육 진정",
        "scientific_reason": "버베나린(Verbenalin)과 시트랄(Citral) 성분이 중추신경계를 이완하여 가슴 답답함이나 분노 상태에서 어깨와 등 근육이 굳는 신체 긴장을 효과적으로 완화합니다.",
        "tip": "업무 압박으로 어깨가 무겁고 스트레스를 심하게 받을 때 식후 한 잔 따뜻하게 우려 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "과민성 스트레스", "초조함"],
        "recommended_weathers": ["흐림", "바람"]
    },
    "오매": {
        "scientific_name": "Prunus mume",
        "efficacy": "독소 배출, 소화기 긴장 완화 및 젖산 분해",
        "scientific_reason": "구연산(Citric acid)과 사과산이 풍부하여 근육과 혈액 내 젖산을 이완하고 간 기능을 활성화하여 스트레스성 피로와 짜증을 완화합니다.",
        "tip": "긴장과 짜증으로 위장관이 뭉치고 스트레스성 과식이 생길 때 따뜻하게 마시거나 얼음을 띄워 마십니다.",
        "official_source": "대한민국약전 (KP) - '오매 (Mume Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "예민함", "짜증", "만성 피로"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "갈근": {
        "scientific_name": "Pueraria lobata",
        "efficacy": "상열감 해소, 어깨 결림 완화 및 두통 완화",
        "scientific_reason": "이소플라본 성분인 다이진(Daidzin)과 푸에라린(Puerarin)이 뇌 혈류를 증가시키고 목과 어깨 부위의 경직된 근육을 이완하여 짜증과 불안에 동반된 신체적 뭉침을 해소합니다.",
        "tip": "스트레스를 받으면 유독 뒷목이 당기고 분노로 인해 어깨가 뻐근해질 때 따뜻하게 차로 마시면 긴장을 푸는 데 좋습니다.",
        "official_source": "대한민국약전 (KP) - '갈근 (Puerariae Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["분노", "짜증", "목 어깨 근육 경직", "두통"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "다엽": {
        "scientific_name": "Camellia sinensis",
        "efficacy": "차분한 집중(Calm Focus) 유도 및 스트레스 완화",
        "scientific_reason": "녹차에 다량 함유된 아미노산 성분인 엘-테아닌(L-Theanine)이 뇌에서 진정성 알파(α) 뇌파를 발생시켜, 불안을 낮추고 뇌를 맑은 긴장(차분한 집중) 상태로 유도합니다.",
        "tip": "집중해서 차분하게 생각을 정리해야 할 때 마시면 각성 지연 없이 집중력을 극대화할 수 있습니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '다엽 (Theae Folium)' 규격 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "불안형 스트레스", "기억력 저하"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "홍차_오렌지페코": {
        "scientific_name": "Camellia sinensis",
        "efficacy": "피로 해소, 긴장 이완 및 각성 효과",
        "scientific_reason": "홍차의 테아닌(L-Theanine) 성분이 스트레스 호르몬인 코르티솔의 분비를 감소시키고 알파파를 촉진하며, 적절한 카페인이 중추신경을 가볍게 자극해 각성과 이완을 동시에 돕습니다.",
        "tip": "오후 시간 나른하고 지칠 때 따뜻하게 우려내어 향을 맡으며 5~10분간 휴식을 취할 때 마시기 적합합니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '다엽 (Theae Folium)' 등재 및 식약처 식품원료 정보",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "무기력", "피로", "집중력 저하"],
        "recommended_weathers": ["맑음", "따뜻함", "추움"]
    },
    "루이보스": {
        "scientific_name": "Aspalathus linearis",
        "efficacy": "피로 회복, 코르티솔 수치 안정 및 스트레스성 산화 억제",
        "scientific_reason": "강력한 항산화 성분인 아스팔라틴(Aspalathin)과 노토파긴(Notofagin)이 체내 코르티솔(스트레스 호르몬) 분비를 조절하고 피로를 완화합니다. 카페인이 없어 예민한 정서에도 안전합니다.",
        "tip": "카페인이 전혀 없으므로 번아웃을 겪는 사용자가 수면 전을 포함해 상시 물처럼 안심하고 마실 수 있습니다.",
        "official_source": "농촌진흥청 농업기술포털 농사로 (기능성 농식품자원 정보)",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "번아웃", "신체적 피로", "예민함"],
        "recommended_weathers": ["추움", "비"]
    },
    "둥굴레": {
        "scientific_name": "Polygonatum odoratum",
        "efficacy": "마른 몸의 영양 공급 및 만성 갈증 완화",
        "scientific_reason": "사포닌 배당체 성분이 한의학적으로 음액(陰液)을 보충하여, 과도한 스트레스로 인해 몸과 침이 바짝 마르는 구강 건조 및 만성 피로 상태를 진정시킵니다.",
        "tip": "스트레스로 인해 침이 마르고 머리가 복잡할 때 보리차처럼 편안하게 끓여 물 대신 수시로 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '옥죽 (Polygonati Odorati Rhizoma)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "번아웃", "피로"],
        "recommended_weathers": ["맑음", "바람"]
    },
    "보리": {
        "scientific_name": "Hordeum vulgare",
        "efficacy": "소화 촉진, 체온 조절 및 일상적 수분 공급",
        "scientific_reason": "한의학적으로 보리(대맥)는 성질이 서늘하여 스트레스로 타는 가슴의 열을 내리고, 위장관 운동을 도와 신경성 소화 불량을 편안하게 해줍니다.",
        "tip": "소화가 늘 안 되고 신경 쓰이는 일이 많을 때 시원하게 혹은 미지근하게 물처럼 자주 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "짜증", "답답함"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "현미녹차": {
        "scientific_name": "Camellia sinensis + Oryza sativa",
        "efficacy": "긴장 완화와 구수한 풍미를 통한 정서 안정",
        "scientific_reason": "녹차의 테아닌 성분이 주는 알파파 발생 효과와 볶은 현미의 가바(GABA) 성분이 시너지를 내어 심신을 차분하게 가라앉히고 잡념을 없애줍니다.",
        "tip": "차분하게 해야 할 일이 있거나 복잡한 생각으로 마음이 산만할 때 따뜻하게 우려 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "불안형 스트레스", "기억력 저하"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "의이인": {
        "scientific_name": "Coix lacryma-jobi",
        "efficacy": "노폐물 배출, 부종 완화 및 비위 보호",
        "scientific_reason": "의이인에 포함된 코익솔(Coixol) 성분이 소화기계 평활근 긴장을 조율하고 체내 불필요한 수분 배출을 도와 부종과 신경성 위장 피로를 낮춥니다.",
        "tip": "몸이 천근만근 무겁고 머리가 멍하며 소화력이 예전만 못할 때 율무가루를 타서 식사 대용이나 따뜻한 음료로 마십니다.",
        "official_source": "대한민국약전 (KP) - '의이인 (Coicis Semen)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "신체 무겁고 처짐", "무기력", "소화 불량"],
        "recommended_weathers": ["흐림", "비"]
    },
    "송엽": {
        "scientific_name": "Pinus densiflora",
        "efficacy": "머리 맑게 함, 혈행 개선 및 피로 이완",
        "scientific_reason": "솔잎의 휘발성 테르펜(Terpene) 성분들이 혈관 확장 및 자율신경 조절 작용을 수행하여 가슴속 울화와 스트레스로 뜨거워진 뇌의 상열감을 낮추고 기분을 상쾌하게 합니다.",
        "tip": "머리가 복잡하고 복잡한 생각 정리와 집중이 필요할 때 은은한 솔 향을 깊게 들이마시며 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식약처 생약정보 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["산만함", "두통", "짜증", "울화"],
        "recommended_weathers": ["바람", "맑음"]
    },
    "연잎": {
        "scientific_name": "Nelumbo nucifera",
        "efficacy": "신경 흥분 완화, 지혈 작용 및 심신 이완",
        "scientific_reason": "연잎의 로메린(Roemerine) 알칼로이드 성분이 뇌내 글루타메이트의 활성을 조절하고 흥분을 억제하여, 스트레스로 극대화된 수면 장애 상태를 완화하고 안정을 줍니다.",
        "tip": "취침 전 누워도 잡생각이 계속 나고 몸이 후끈거릴 때 은은한 녹색 연잎차를 따뜻하게 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식약처 생약정보 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "스트레스성 불면", "정서 불안"],
        "recommended_weathers": ["비", "흐림"]
    },
    "백자인": {
        "scientific_name": "Thuja orientalis",
        "efficacy": "심신 피로 완화, 불면 개선 및 심장 두근거림 해소",
        "scientific_reason": "백자인의 지방유 성분과 사포닌 성분이 신경 세포를 유연하게 이완시키고 뇌 각성을 유도하는 각성 물질 농도를 조절하여 자연스러운 수면 유도를 지원합니다.",
        "tip": "피로로 인해 오히려 잠들기 어렵고 가슴이 답답하고 건조한 기침이 날 때 따뜻하게 우려 마십니다.",
        "official_source": "대한민국약전 (KP) - '백자인 (Thujae Semen)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "심박수 증가", "신경 쇠약"],
        "recommended_weathers": ["추움", "바람"]
    },
    "용안육": {
        "scientific_name": "Dimocarpus longan",
        "efficacy": "중추신경 안정, 영양 공급 및 가슴 뜀 완화",
        "scientific_reason": "용안 열매의 아데노신 성분이 뇌세포의 불안 작용을 억제하고 수면 신호를 자극하여, 만성적인 불면증과 신경질적인 초조 상태를 이완합니다.",
        "tip": "극심한 신경 소모로 인해 잠들지 못하고 건망증이 함께 나타날 때 달콤한 용안육차를 마십니다.",
        "official_source": "대한민국약전 (KP) - '용안육 (Longanae Arillus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "건망증", "기력 소진"],
        "recommended_weathers": ["추움", "눈"]
    },
    "상엽": {
        "scientific_name": "Morus alba",
        "efficacy": "두통 완화, 가래 배출 및 열 식히기",
        "scientific_reason": "뽕잎의 가바(GABA) 성분과 디옥시노지리마이신(DNJ) 성분이 혈관 벽을 이완해 혈압을 낮추고, 스트레스로 인해 뇌와 안구에 쏠린 열과 상열감을 해소합니다.",
        "tip": "스트레스로 열이 오르고 수면에 지장이 생기며 감기 기운이나 갈증이 날 때 따뜻하게 음용합니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '상엽 (Mori Folium)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "상열감", "두통"],
        "recommended_weathers": ["더움", "바람"]
    },
    "영지버섯": {
        "scientific_name": "Ganoderma lucidum",
        "efficacy": "신경 안정, 불안 완화 및 기침 진정",
        "scientific_reason": "트리테르페노이드(Triterpenoid) 및 아데노신 성분이 자율신경실조를 다스리고 아드레날린 분비를 안정시켜 깊은 불면증과 신경 쇠약을 진정시키는 작용을 합니다.",
        "tip": "몸에 과도한 예민 회로가 켜져 만성 불면증과 두근거림으로 지칠 때 얇게 썰어 달여 쌉쌀하게 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '영지 (Ganoderma)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "신경 예민", "가슴 벌렁거림"],
        "recommended_weathers": ["흐림", "바람"]
    },
    "감태": {
        "scientific_name": "Ecklonia cava",
        "efficacy": "숙면 시간 연장, 뇌파 진정 및 신경 이완",
        "scientific_reason": "해양 폴리페놀인 플로로탄닌(Phlorotannin) 성분이 중추신경계의 가바(GABA) 수용체와 강력히 결합하여 입면 시간을 단축하고 깊은 숙면을 돕는 작용을 합니다.",
        "tip": "밤중에 자꾸 깨어 깊은 잠을 이루지 못하고 만성 피로가 쌓였을 때 저녁 식후 따뜻하게 차로 마십니다.",
        "official_source": "식품의약품안전처 건강기능식품 개별인정 원료 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "얕은 수면", "스트레스"],
        "recommended_weathers": ["비", "추움"]
    },
    "박하": {
        "scientific_name": "Mentha piperita",
        "efficacy": "정신 각성, 스트레스성 두통 완화 및 기분 전환",
        "scientific_reason": "주요 성분인 멘톨(Menthol)이 말초신경의 평활근을 이완하고, 중추신경계의 가벼운 각성을 유도하여 인지 능력 향상과 무기력감 해소를 돕습니다.",
        "tip": "공부나 업무 중 집중력이 떨어지고 멍할 때 아이스 티로 상쾌하게 마시는 것을 추천합니다.",
        "official_source": "대한민국약전 (KP) - '박하 (Mentha Herba)' 규격 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불면", "무기력", "피로", "두통", "답답함"],
        "recommended_weathers": ["흐림", "더움", "눈"]
    },
    "당귀": {
        "scientific_name": "Angelica gigas",
        "efficacy": "혈액 순환 원활, 자궁 혈행 안정 및 빈혈성 피로 개선",
        "scientific_reason": "데쿠르신(Decursin)과 데쿠르시놀 안겔레이트 성분이 뇌 신경세포 활성화를 돕고 혈관 벽을 이완하여 혈행을 자극하며, 중추신경을 가볍게 진정시켜 불면과 정서 안정을 유도합니다.",
        "tip": "정서적 소모가 극심하고 혈색이 불량하며, 잠이 오지 않고 손발이 차가울 때 따뜻하게 우려 마십니다.",
        "official_source": "대한민국약전 (KP) - '당귀 (Angelicae Gigantis Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["불안", "불면", "기력 저하", "수족냉증"],
        "recommended_weathers": ["바람", "추움"]
    },
    "오미자": {
        "scientific_name": "Schisandra chinensis",
        "efficacy": "만성 피로 완화 및 뇌 세포 보호",
        "scientific_reason": "쉬잔드린(Schizandrin) 성분이 활성산소를 제거하고 중추신경계의 피로를 완화하여 스트레스성 번아웃 상태에서 정서적 회복을 돕습니다.",
        "tip": "더운 여름철이나 공부 중 머리가 굳었을 때 차갑게 우려내어 새콤하게 마시는 것을 추천합니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '오미자 (Schisandrae Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["번아웃", "정서적 고갈", "기력 저하"],
        "recommended_weathers": ["더움", "흐림"]
    },
    "생강": {
        "scientific_name": "Zingiber officinale",
        "efficacy": "몸을 따뜻하게 함 및 위장 긴장 완화",
        "scientific_reason": "진저롤(Gingerol)과 쇼가올(Shogaol) 성분이 말초 혈액 순환을 촉진하고, 스트레스로 인해 굳어진 소화기관의 평활근을 이완하여 가슴 답답함과 신체적 위축을 풀어줍니다.",
        "tip": "몸에 오한이 들거나 긴장으로 위장 부근이 답답하고 굳어갈 때 생강을 저며 우려 마시면 좋습니다.",
        "official_source": "대한민국약전 (KP) - '생강 (Zingiberis Rhizoma)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "과민성 스트레스", "긴장", "신체적 위축"],
        "recommended_weathers": ["추움", "눈", "바람"]
    },
    "모과": {
        "scientific_name": "Chaenomeles sinensis",
        "efficacy": "근육 긴장 완화 및 신경통 진정 도움",
        "scientific_reason": "사포닌과 유기산 성분이 근육에 쌓인 젖산을 배출하고, 불안으로 인해 목과 어깨가 잔뜩 굳어 있는 신체적 긴장 상태를 이완합니다.",
        "tip": "장시간 컴퓨터 작업이나 극도의 스트레스로 목덜미와 승모근이 딱딱하게 뭉쳤을 때 우려 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '목과 (Chaenomelis Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "긴장", "불안형 스트레스", "신체적 피로"],
        "recommended_weathers": ["추움", "바람"]
    },
    "산수유": {
        "scientific_name": "Cornus officinalis",
        "efficacy": "체력 회복, 피로 저항력 향상 및 면역 기능 지원",
        "scientific_reason": "모로니사이드(Morroniside)와 로가닌(Loganin) 등 이리도이드 배당체 성분이 지친 부신의 스트레스 조절 호르몬 분비 능력을 안정적으로 돕고 만성 피로와 무기력을 진정시킵니다.",
        "tip": "장기간의 스트레스로 인해 몸이 완전히 방전되었을 때, 붉은 산수유 열매를 끓인 차를 따뜻하게 마십니다.",
        "official_source": "대한민국약전 (KP) - '산수유 (Corni Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "만성 피로", "활력 저하", "번아웃"],
        "recommended_weathers": ["추움", "눈"]
    },
    "가시오가피": {
        "scientific_name": "Eleutherococcus senticosus",
        "efficacy": "피로 내성 증대, 신체 운동 능력 극대화 및 피로 경감",
        "scientific_reason": "엘레우테로사이드(Eleutheroside B, E) 성분이 면역 시스템을 강화하고 체내 에너지 대사를 촉진하여 만성 피로와 신체적 번아웃에 강력한 자극을 줍니다.",
        "tip": "몸에 힘이 하나도 없고 늘어지며, 휴식을 취해도 전혀 개운하지 않을 때 우려 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '오가피 (Acanthopanacis Radicis Cortex)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "만성 피로", "정서적 고갈", "번아웃"],
        "recommended_weathers": ["바람", "흐림"]
    },
    "인삼": {
        "scientific_name": "Panax ginseng",
        "efficacy": "원기 회복, 면역 증강 및 정서적 안정",
        "scientific_reason": "진세노사이드(Ginsenoside) 유효 성분들이 부신 피질 호르몬의 피로성 고갈을 방지하고 체내 대사 활동을 극대화하여 만성 피로와 정서적 고갈을 해소합니다.",
        "tip": "몸이 매우 차갑고 식은땀이 나며 만성적인 의욕 상실과 체력 고갈이 겹쳤을 때 따뜻하게 끓여 음용합니다.",
        "official_source": "대한민국약전 (KP) - '인삼 (Ginseng Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "만성 피로", "무기력", "의욕 상실"],
        "recommended_weathers": ["추움", "눈"]
    },
    "홍삼": {
        "scientific_name": "Processed Panax ginseng",
        "efficacy": "면역력 강화, 혈행 이완 및 피로 유효 완화",
        "scientific_reason": "증기로 찌는 가공 공정을 거쳐 생성된 진세노사이드 Rg3 성분이 체내 세포 대사 능력을 촉진하고 혈관 벽을 이완하여, 만성적인 정서적/신체적 번아웃을 극복하는 에너지를 부여합니다.",
        "tip": "체력 및 집중력 저하가 동반된 만성 피로로 일상 작동이 곤란할 때 꾸준히 차로 마십니다.",
        "official_source": "대한민국약전 (KP) - '홍삼 (Ginseng Radix Rubra)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "만성 피로", "기력 소진", "번아웃"],
        "recommended_weathers": ["바람", "추움"]
    },
    "맥문동": {
        "scientific_name": "Liriope platyphylla",
        "efficacy": "기관지 보습, 체액 충전 및 예민 신경 완화",
        "scientific_reason": "한의학적으로 음액을 촉진하는 사포닌 성분이 스트레스로 인해 몸속 체액이 마르고 진액이 고갈된 만성 갈증 및 건조성 기침, 번아웃 상태를 촉진합니다.",
        "tip": "스트레스로 입과 목이 바짝 마르고, 헛기침이 나며 마른 체형의 소유자에게 훌륭한 차입니다.",
        "official_source": "대한민국약전 (KP) - '맥문동 (Liriopis Tuber)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["피로", "번아웃", "구강 건조"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "죽엽": {
        "scientific_name": "Phyllostachys nigra",
        "efficacy": "뇌 열 식히기, 가슴 두근거림 및 답답함 완화",
        "scientific_reason": "대나무 잎에 풍부한 트라이테르페노이드 성분들이 뇌 상열감을 식혀주고 신경 흥분 호르몬 분비를 이완하여, 홧병이나 답답함으로 인한 두근거림을 해소합니다.",
        "tip": "스트레스로 인해 명치 부근이 꽉 막힌 느낌이 들고 가슴이 타들어 가는 답답함이 일어날 때 마십니다.",
        "official_source": "대한민국약전 (KP) - '죽엽 (Phyllostachydis Folium)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "홧병", "가슴 답답함"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "감초": {
        "scientific_name": "Glycyrrhiza uralensis",
        "efficacy": "근육 급경련 이완, 해독 및 스트레스 이완",
        "scientific_reason": "글리시리진(Glycyrrhizin) 성분이 부신 피질 호르몬(코르티솔) 분비 리듬을 촉진 및 조절하여, 극심한 정서적 압박 상태에서 소화계 경련을 가라앉히고 마음을 완화합니다.",
        "tip": "긴장과 예민함으로 인해 명치 부위의 경련성 위장 장애나 답답함이 생길 때 따뜻하게 우려 마십니다.",
        "official_source": "대한민국약전 (KP) - '감초 (Glycyrrhizae Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "예민함", "위장 긴장"],
        "recommended_weathers": ["흐림", "추움"]
    },
    "소엽": {
        "scientific_name": "Perilla frutescens",
        "efficacy": "신경성 체기 완화, 홧병 이완 및 정서 완화",
        "scientific_reason": "차즈기 잎의 페릴알데히드(Perillaldehyde) 성분이 후각과 미각을 자극해 부교감신경을 정위시키고 스트레스성 장위 경직과 정서적 답답함을 이완합니다.",
        "tip": "화가 나거나 슬퍼서 가슴이 막혀 밥이 잘 얹히고 답답할 때 자줏빛 소엽차를 우려 마십니다.",
        "official_source": "대한민국약전 (KP) - '자소엽 (Perillae Herba)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "홧병", "슬픔", "소화 불량"],
        "recommended_weathers": ["바람", "흐림"]
    },
    "복분자": {
        "scientific_name": "Rubus coreanus",
        "efficacy": "만성 노화 방지, 호르몬 균형 활성화 및 피로 제거",
        "scientific_reason": "안토시아닌(Anthocyanin)과 엘라그산 성분이 뇌내 피로 물질인 활성산소를 차단하고 자율신경 조절을 유도하여, 정서적 고갈과 가슴 답답함 증상을 개선합니다.",
        "tip": "홧병으로 기운이 축축 처지고 의욕이 없으며 눈이 자주 충혈될 때 마시면 기분 전환에 좋습니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '복분자 (Rubi Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "기력 저하", "만성 피로"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "백작약": {
        "scientific_name": "Paeonia lactiflora",
        "efficacy": "혈류 이완, 신경성 위경련 완화 및 스트레스성 통증 완화",
        "scientific_reason": "페오니플로린(Paeoniflorin) 성분이 중추신경계의 신경 전달을 안정시켜, 과도한 예민함이나 홧병으로 인해 위장이나 어깨 근육이 경직되어 발생하는 신경통을 완화합니다.",
        "tip": "화를 참으면 유독 옆구리나 위장 부근이 찌르듯이 아프고 소화가 막힐 때 우려 마시면 좋습니다.",
        "official_source": "대한민국약전 (KP) - '작약 (Paeoniae Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "홧병", "예민함", "신경통"],
        "recommended_weathers": ["흐림", "추움"]
    },
    "숙지황": {
        "scientific_name": "Processed Rehmannia glutinosa",
        "efficacy": "체액 및 신체 에너지 보존, 불면 완화 및 홧병 이완",
        "scientific_reason": "카탈폴(Catalpol) 배당체와 5-HMF 성분이 스트레스에 의한 자율신경계 과활성을 억제하고 정서적 고갈 상태에 영양을 공급해, 홧병으로 인한 수면 피로를 예방합니다.",
        "tip": "홧병이 만성화되어 머리카락이 건조해지고 몸이 극도로 피곤하면서 잠들기 어려울 때 마십니다.",
        "official_source": "대한민국약전 (KP) - '숙지황 (Rehmanniae Radix Preparata)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "홧병", "불면", "정서적 고갈"],
        "recommended_weathers": ["바람", "추움"]
    },
    "민들레": {
        "scientific_name": "Taraxacum officinale",
        "efficacy": "체내 염증성 상열감 식히기 및 위장 보호",
        "scientific_reason": "타락사스테롤(Taraxasterol)이 자율신경 실조에 의한 신경계 스트레스 염증 활성화를 이완하고, 화 기운으로 부대끼는 위장을 다스려 홧병에 따르는 신체적 불쾌감을 내려줍니다.",
        "tip": "극도의 짜증과 화로 가슴에 열감이 갇혀 답답하고 피부 트러블이 올라올 때 따뜻하게 우려 마십니다.",
        "official_source": "대한민국약전외한약(생약)규격집 (KHP) - '포공영 (Taraxaci Herba)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["답답함", "홧병", "상열감", "짜증"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "천궁": {
        "scientific_name": "Cnidium officinale",
        "efficacy": "뇌 혈류 개선, 두통 완화 및 기분 조절",
        "scientific_reason": "리구스티라이드(Ligustilide)와 센큐놀라이드 성분이 뇌혈관의 과도한 수축 및 경련을 방지하고 혈행을 자극하여, 스트레스성 두통과 가슴 답답함을 조절해 줍니다.",
        "tip": "생리 전후 정서 불안과 두통이 동반되거나 스트레스로 관자놀이가 띵할 때 마시는 것을 추천합니다.",
        "official_source": "대한민국약전 (KP) - '천궁 (Cnidii Rhizoma)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "답답함", "생리전 정서불안"],
        "recommended_weathers": ["바람", "추움"]
    },
    "치자": {
        "scientific_name": "Gardenia jasminoides",
        "efficacy": "뇌의 열 내리기, 분노 진정 및 충혈 이완 도움",
        "scientific_reason": "치자의 제니포사이드(Geniposide) 성분이 자율신경 흥분을 진정시키고 혈행 속도를 조율하여, 분노로 인해 눈이 붉게 충혈되거나 머리에 피가 쏠리는 증상을 가라앉힙니다.",
        "tip": "화가 나면 얼굴이 붉게 달아오르고 심장이 쿵쾅거려 진정이 도저히 안 될 때 차갑게 혹은 미지근하게 마십니다.",
        "official_source": "대한민국약전 (KP) - '치자 (Gardeniae Fructus)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "홧병", "분노", "상열감"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "형개": {
        "scientific_name": "Schizonepeta tenuifolia",
        "efficacy": "두통 완화, 가벼운 감기 발산 및 피부 안정",
        "scientific_reason": "풀레곤(Pulegone) 성분이 뇌 표면의 모세혈관 순환을 활성화하여 신경 뭉침을 풀고, 한의학적으로 바람과 열(풍열)로 인한 머리 멍함과 스트레스성 편두통을 진정시킵니다.",
        "tip": "스트레스를 받으면 머리에 열이 뭉쳐 머리가 묵직하게 아프고 두피가 가려울 때 가볍게 마십니다.",
        "official_source": "대한민국약전 (KP) - '형개 (Schizonepetae Herba)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "머리 묵직함", "예민 신경"],
        "recommended_weathers": ["바람", "흐림"]
    },
    "시호": {
        "scientific_name": "Bupleurum falcatum",
        "efficacy": "가슴 신경 완화, 스트레스성 열 식히기 및 한열 왕래 조절",
        "scientific_reason": "사이코사포닌(Saikosaponin) 성분이 뇌 하수체와 부신의 흥분 작용을 진정시키고, 스트레스를 심하게 받으면 입이 쓰고 머리가 아픈 신경성 증상을 이완합니다.",
        "tip": "스트레스 누적으로 편두통이 생기고 가슴 옆구리가 더부룩하고 결릴 때 은은하게 마십니다.",
        "official_source": "대한민국약전 (KP) - '시호 (Bupleuri Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "홧병", "신경 과민"],
        "recommended_weathers": ["흐림", "바람"]
    },
    "백지": {
        "scientific_name": "Angelica dahurica",
        "efficacy": "신경성 앞머리 통증 완화 및 안구 건조 해소",
        "scientific_reason": "임페라토린(Imperatorin) 쿠마린 성분이 삼차신경 자극 신호를 조절하여, 특히 이마와 눈 주변에 쏠리는 스트레스성 두통과 안구 충혈, 찌르르한 신경통을 완화합니다.",
        "tip": "컴퓨터를 장시간 사용하거나 불안할 때 앞이마 부분이 지끈거리며 두통이 올 때 마십니다.",
        "official_source": "대한민국약전 (KP) - '백지 (Angelicae Dahuricae Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "앞이마 통증", "안구 피로"],
        "recommended_weathers": ["추움", "눈"]
    },
    "우엉": {
        "scientific_name": "Arctium lappa",
        "efficacy": "혈압 안정, 체내 붓기 제거 및 열 식히기",
        "scientific_reason": "이눌린(Inulin)과 아크티인(Arctiin) 성분이 체내 신진대사를 촉진하여 모세혈관 순환을 원활히 하고, 분노와 긴장으로 발생한 두통과 얼굴 상열감을 시원하게 식혀줍니다.",
        "tip": "몸에 수분 순환이 안 되어 붓고 머리가 띵하며 가슴에 열이 날 때 볶은 우엉을 우려 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "붓기", "짜증", "상열감"],
        "recommended_weathers": ["더움", "맑음"]
    },
    "연근": {
        "scientific_name": "Nelumbo nucifera",
        "efficacy": "출혈 진정, 신경 과민 조절 및 위벽 보충",
        "scientific_reason": "탄닌(Tannin)과 뮤신 성분이 체내 신경 과민 물질 활성을 가라앉히고, 분노 및 긴장 스트레스로 피로해진 위벽을 감싸 신경성 통증 및 상열을 식힙니다.",
        "tip": "정서적 상처가 크거나 긴장으로 가슴이 먹먹하며 신경성 속 쓰림과 두통이 동반될 때 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "신경 과민", "속 쓰림"],
        "recommended_weathers": ["맑음", "따뜻함"]
    },
    "더덕": {
        "scientific_name": "Codonopsis lanceolata",
        "efficacy": "폐 기운 강화, 기관지 보습 및 스트레스 이완",
        "scientific_reason": "더덕의 란세올라틴(Lanceolatine) 사포닌 성분이 중추신경 진정 작용을 도와 만성 스트레스로 어깨가 무겁고 머리가 띵한 신체 피로 통증을 다스립니다.",
        "tip": "기침이 잦고 정서 불안이 동반되어 가슴에 미열과 두통이 함께 느껴질 때 차로 우려내 마십니다.",
        "official_source": "식품의약품안전처 식품원료 정보 및 식품공전 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "신경 불안", "체력 저하"],
        "recommended_weathers": ["추움", "비"]
    },
    "길경": {
        "scientific_name": "Platycodon grandiflorus",
        "efficacy": "가래 배출, 인후 통증 완화 및 신경 가라앉히기",
        "scientific_reason": "도라지의 플라티코딘(Platycodin D) 사포닌 성분이 체내 면역 반응 조절을 도우며 한의학적으로 기가 오르내리는 가슴의 답답함과 스트레스성 두통을 진정시킵니다.",
        "tip": "목이 붓고 칼칼하며 스트레스 누적으로 상열 두통이 일어날 때 따뜻하게 마십니다.",
        "official_source": "대한민국약전 (KP) - '길경 (Platycodonis Radix)' 등재",
        "reference_db": "한국한의학연구원(KIOM) 한의약융합연구정보센터(KMCRIC) 생약 up-to-date",
        "recommended_moods": ["두통", "목 통증", "답답함"],
        "recommended_weathers": ["추움", "눈"]
    }
}

def call_mfds_api(service_key, herb_name):
    """
    Calls the Ministry of Food and Drug Safety (MFDS) Herbal Medicine Information API using urllib.
    """
    base_url = "http://apis.data.go.kr/1471000/NifdsHerbalInfoService/getHerbalSpcifyInfo"
    query_params = {
        "ServiceKey": service_key,
        "hnm": herb_name,
        "pageNo": "1",
        "numOfRows": "1",
        "type": "json"
    }
    
    # Encode parameters properly
    encoded_params = urllib.parse.urlencode(query_params)
    full_url = f"{base_url}?{encoded_params}"
    
    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode('utf-8'))
                body = res_data.get("body", {})
                items = body.get("items", [])
                if items:
                    item = items[0]
                    return {
                        "scientific_name": item.get("scnm", ""),  # Scientific name
                        "family_name": item.get("fnm", ""),       # Family name
                    }
    except Exception as e:
        print(f"API call to MFDS failed for {herb_name}: {e}")
    return None

def build_tea_dataset(api_key=None):
    """
    ETL job to build the tea recommendation dataset.
    """
    print("Starting Tea Recommendation Dataset ETL pipeline...")
    records = []
    
    for idx, tea in enumerate(CORE_TEAS, 1):
        name_key = tea["name"]
        display_name = tea["display_name"]
        english = tea["english"]
        
        # 1. Fetch from MFDS API if key is present
        api_data = None
        if api_key:
            print(f"Calling MFDS API for '{name_key}'...")
            api_data = call_mfds_api(api_key, name_key)
            
        # 2. Get verified academic reference mappings
        ref = ACADEMIC_MAPPINGS.get(name_key, {})
        
        # 3. Align and merge
        scientific_name = api_data["scientific_name"] if api_data and api_data.get("scientific_name") else ref.get("scientific_name")
        efficacy = ref.get("efficacy")
        scientific_reason = ref.get("scientific_reason")
        tip = ref.get("tip")
        official_source = ref.get("official_source")
        reference_db = ref.get("reference_db")
        
        # Determine caffeine and allergy triggers based on name_key
        has_caffeine = False
        if name_key in ["다엽", "홍차_오렌지페코", "현미녹차", "홍차"]:
            has_caffeine = True
            
        allergy_triggers = []
        if name_key in ["카밀레", "감국", "민들레"]:
            allergy_triggers = ["asteraceae"]
        elif name_key == "메밀":
            allergy_triggers = ["buckwheat"]

        records.append({
            "id": idx,
            "tea_name": display_name,
            "english_name": english,
            "scientific_name": scientific_name,
            "recommended_moods": ref.get("recommended_moods", []),
            "recommended_weathers": ref.get("recommended_weathers", []),
            "efficacy": efficacy,
            "scientific_reason": scientific_reason,
            "tip": tip,
            "official_source": official_source,
            "reference_db": reference_db,
            "has_caffeine": has_caffeine,
            "allergy_triggers": allergy_triggers
        })
        print(f"  Processed: {display_name} ({scientific_name})")
        
    return records

def run_pipeline():
    service_key = os.environ.get("MFDS_API_KEY", None)
    dataset = build_tea_dataset(service_key)
    
    vault_path = r"c:\Users\Playdata\Documents\Obsidian Vault\SKN27기 최종프로젝트 - 웰니스 멘탈케어\데이터\마시는_차_추천_데이터셋.json"
    repo_path = r"c:\dev\project\SKN27-FINAL-4Team\storage\마시는_차_추천_데이터셋.json"
    
    # Write to Vault
    os.makedirs(os.path.dirname(vault_path), exist_ok=True)
    with open(vault_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"\nSuccessfully saved to Vault: {vault_path}")
    
    # Write to Repo
    os.makedirs(os.path.dirname(repo_path), exist_ok=True)
    with open(repo_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    print(f"Successfully saved to Repo: {repo_path}")

if __name__ == "__main__":
    run_pipeline()
