import { DISPLAY_CHARACTER_META } from '../config/chat.constants.js'

export function readStoredCharacter() {
  try {
    return JSON.parse(localStorage.getItem('binteumsaiCharacter') || '{}')
  } catch {
    return {}
  }
}

export function normalizeCharacterId(id) {
  if (DISPLAY_CHARACTER_META[id]) return id
  if (id === 'toto') return 'otter'
  if (id === 'kkami') return 'cat'
  if (id === 'pori') return 'redpanda'
  if (id === 'yeoul') return 'bird'
  if (id === 'haeon') return 'otter'
  if (id === 'greung' || id === 'geureung') return 'cat'
  if (id === 'dalkong') return 'redpanda'
  return 'otter'
}
