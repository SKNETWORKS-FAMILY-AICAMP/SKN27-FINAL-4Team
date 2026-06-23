// 전역 시크릿챗 상태 — 켜지면 앱 전체가 밤하늘 톤으로 전환됨
import { ref } from 'vue'

const secret = ref(localStorage.getItem('binteumsai_secret') === 'on')

function setSecret(v) {
  secret.value = !!v
  localStorage.setItem('binteumsai_secret', v ? 'on' : 'off')
}
function toggleSecret() {
  setSecret(!secret.value)
}

export function useSecret() {
  return { secret, setSecret, toggleSecret }
}
