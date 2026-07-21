export function getTimeScene(hour = new Date().getHours()) {
  if (hour < 6) return { className: 'time-dawn', label: '별빛이 머무는 새벽' }
  if (hour < 12) return { className: 'time-morning', label: '햇살이 드는 아침' }
  if (hour < 18) return { className: 'time-day', label: '느긋한 오후' }
  return { className: 'time-night', label: '노을이 내려앉은 밤' }
}

export function getMoteStyle(index) {
  const x = (index * 37 + 11) % 96
  const y = (index * 53 + 17) % 78
  const delay = (index % 6) * -0.8
  const duration = 5 + (index % 5) * 1.1
  return {
    left: `${x}%`,
    top: `${y}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
  }
}
