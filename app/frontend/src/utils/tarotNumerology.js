export function sumDigits(value) {
  const raw = value instanceof Date ? getKSTDateString(value) : String(value ?? '')
  return raw
    .replace(/\D/g, '')
    .split('')
    .filter(Boolean)
    .reduce((sum, digit) => sum + Number(digit), 0)
}

export function reduceToMajorArcanaNumber(num) {
  let result = Number(num) || 0

  while (result > 22) {
    result = String(result)
      .split('')
      .reduce((sum, digit) => sum + Number(digit), 0)
  }

  return result || 1
}

export function numerologyNumberToCardNumber(num) {
  return Number(num) === 22 ? 0 : Number(num)
}

export function getDailyMajorCardNumber(birthDate, targetDate = getTodayKSTString()) {
  const birthNumber = reduceToMajorArcanaNumber(sumDigits(birthDate))
  const dateNumber = reduceToMajorArcanaNumber(sumDigits(targetDate))
  const dailyNumber = reduceToMajorArcanaNumber(birthNumber + dateNumber)
  const cardNumber = numerologyNumberToCardNumber(dailyNumber)

  return {
    birthNumber,
    dateNumber,
    dailyNumber,
    cardNumber,
  }
}

export function getDailyMajorTarotCard(birthDate, targetDate, tarotCards) {
  const result = getDailyMajorCardNumber(birthDate, targetDate)
  const card = tarotCards.find((item) => {
    return Number(item.cardNumber) === result.cardNumber && String(item.arcana).toLowerCase().includes('major')
  })

  if (!card) {
    throw new Error(`Daily major tarot card not found: card_number=${result.cardNumber}`)
  }

  return {
    ...result,
    card,
  }
}

export function getTodayKSTString() {
  return getKSTDateString(new Date())
}

function getKSTDateString(date) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}
