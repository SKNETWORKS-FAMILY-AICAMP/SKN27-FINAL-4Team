export const CHARACTER_META = {
  pori: {
    name: '포리', color: '#5EEAD4', bg: 'rgba(94,234,212,0.18)',
    faces: {
      default: '^‿^',
      joy: '◕‿◕✨',
      sadness: '；_；',
      anger: '＞﹏＜',
      normal: '^‿^',
    },
  },
  kkami: {
    name: '까미', color: '#C4B5FD', bg: 'rgba(196,181,253,0.18)',
    faces: {
      default: '•_•',
      joy: '•‿•',
      sadness: '•︵•',
      anger: '•益•',
      normal: '•_•',
    },
  },
  toto: {
    name: '토토', color: '#7DD3FC', bg: 'rgba(125,211,252,0.18)',
    faces: {
      default: '◕‿↼',
      joy: '(ᵔᴗᵔ)/',
      sadness: '；ω；',
      anger: '｀皿´',
      normal: '◕‿↼',
    },
  },
  yeoul: {
    name: '여울', color: '#FBBF77', bg: 'rgba(251,191,119,0.18)',
    faces: {
      default: '◠‿◠',
      joy: '◠‿◠♡',
      sadness: '◠︵◠',
      anger: '◠ᗨ◠',
      normal: '◠‿◠',
    },
  },
}

export const DISPLAY_CHARACTER_META = {
  otter: {
    name: '수달',
    color: '#7DD3FC',
    bg: 'rgba(125,211,252,0.18)',
    backendCharacter: 'toto',
  },
  cat: {
    name: '까미',
    color: '#C4B5FD',
    bg: 'rgba(196,181,253,0.18)',
    backendCharacter: 'kkami',
  },
  redpanda: {
    name: '포리',
    color: '#5EEAD4',
    bg: 'rgba(94,234,212,0.18)',
    backendCharacter: 'pori',
  },
  bird: {
    name: '여울',
    color: '#FBBF77',
    bg: 'rgba(251,191,119,0.18)',
    backendCharacter: 'yeoul',
  },
}

export const EXPRESSION_LABELS = {
  default: '평온',
  joy: '기쁨',
  anger: '화남',
  sadness: '슬픔',
  anxiety: '불안',
  hurt: '상처',
  panic: '당황',
}

export const EMOTION_TO_EXPRESSION = {
  joy: 'joy',
  sadness: 'sadness',
  anger: 'anger',
  normal: null,
  default: null,
}

export const EXPRESSION_ANIMATION = {
  joy: 'anim-joy',
  anger: 'anim-anger',
  sadness: 'anim-sadness',
  anxiety: 'anim-anxiety',
  hurt: 'anim-hurt',
  panic: 'anim-panic',
}

export const ACTIONS_BY_EMOTION = {
  default: [
    { label: '오늘 있었던 일부터 말한다', message: '오늘 있었던 일부터 천천히 이야기해볼게.' },
    { label: '지금 마음을 솔직하게 보여준다', message: '지금 내 마음이 어떤지 솔직하게 말해보고 싶어.' },
    { label: '말 대신 사진을 건넨다', type: 'photo' },
  ],
  normal: [
    { label: '오늘 가장 기억나는 순간을 꺼낸다', message: '오늘 있었던 일 중에 가장 기억나는 순간부터 말해볼게.' },
    { label: '친구의 하루를 먼저 묻는다', message: '내 이야기 전에, 너는 오늘 어떻게 지냈어?' },
    { label: '말 대신 사진을 건넨다', type: 'photo' },
  ],
  joy: [
    { label: '좋았던 순간을 더 들려준다', message: '그때 정말 좋았어. 조금 더 자세히 이야기해도 돼?' },
    { label: '이 기분을 함께 기억해 달라고 한다', message: '오늘의 이 기분, 우리 같이 기억해두자.' },
    { label: '함께 기뻐해 달라고 한다', message: '나랑 조금만 더 같이 기뻐해줘!' },
  ],
  sadness: [
    { label: '조금 더 솔직하게 털어놓는다', message: '사실은 괜찮은 척했어. 조금 더 솔직하게 말해볼게.' },
    { label: '잠깐 말없이 곁에 있어 달라고 한다', message: '지금은 해결책보다 그냥 잠깐 곁에 있어줬으면 좋겠어.' },
    { label: '천천히 다른 이야기로 넘어간다', message: '이 이야기는 잠깐 내려놓고, 조금 가벼운 얘기를 해볼까?' },
  ],
  anger: [
    { label: '무엇이 화났는지 정확히 말한다', message: '내가 정확히 어떤 부분에서 화가 났는지 말해볼게.' },
    { label: '내 편이 되어 달라고 한다', message: '지금만큼은 판단하지 말고 내 편이 되어줬으면 좋겠어.' },
    { label: '숨을 고르고 다시 이야기한다', message: '잠깐 숨을 고르고, 처음부터 차근차근 다시 말해볼게.' },
  ],
}

export const OPENER_MSG = {
  pori: isSecret => isSecret
    ? '여긴 비밀이니까 마음 편히 다 풀어놔! 무슨 일 있어?'
    : '안녕! 오늘 작은 좋은 일이라도 있었어? 같이 이야기해봐!',
  kkami: isSecret => isSecret
    ? '여긴 아무것도 안 남아. 천천히 말해도 돼'
    : '왔구나. 오늘 마음에 제일 걸린 게 뭐였어?',
  toto: isSecret => isSecret
    ? '쉿, 여긴 우리 둘만의 비밀이거든? 뭐든 풀어놔도 돼'
    : '안녕! 오늘 일진은 좀 어땠어? 무거우면 같이 털어볼래?',
  yeoul: isSecret => isSecret
    ? '여긴 아무 기록도 안 남아. 천천히, 편하게 말해도 괜찮아'
    : '안녕. 오늘 하루는 어땠어? 천천히 말해줘도 괜찮아',
}
