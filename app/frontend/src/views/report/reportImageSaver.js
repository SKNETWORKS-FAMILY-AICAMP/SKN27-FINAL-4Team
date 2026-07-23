const DEFAULT_TARGET_SELECTOR = '.report-card'
const DEFAULT_EXCLUDED_SELECTORS = [
  '.report-actions',
]

const INVALID_FILENAME_CHARACTERS = /[\\/:*?"<>|\u0000-\u001f]/g
const MAX_CANVAS_EDGE = 16384

/**
 * 화면의 마음 리포트를 PDF 출력에 사용할 Canvas로 렌더링한다.
 *
 * @param {object} [options]
 * @returns {Promise<{ canvas: HTMLCanvasElement, filename: string, width: number, height: number }>}
 */
export async function createMindReportCanvas(options = {}) {
  assertBrowserEnvironment()

  const target = options.element ?? document.querySelector(
    options.targetSelector ?? DEFAULT_TARGET_SELECTOR,
  )

  if (!(target instanceof HTMLElement)) {
    throw new Error('저장할 마음 리포트를 찾지 못했습니다.')
  }

  await waitForDocumentAssets(target)

  const scale = normalizeScale(options.scale)
  const excludeSelectors = options.excludeSelectors ?? DEFAULT_EXCLUDED_SELECTORS
  const { width, height } = getCaptureSize(target, excludeSelectors)
  const safeScale = fitScaleToCanvas(width, height, scale)
  const canvas = await renderReportToCanvas(target, {
    width,
    height,
    scale: safeScale,
    excludeSelectors,
  })

  return {
    canvas,
    filename: sanitizeFilename(options.filename ?? buildReportFilename(target)),
    width: canvas.width,
    height: canvas.height,
  }
}

function getCaptureSize(target, excludeSelectors) {
  const rect = target.getBoundingClientRect()
  const width = Math.ceil(Math.max(rect.width, target.scrollWidth))
  const rootStyle = window.getComputedStyle(target)
  const minimumHeight = Number.parseFloat(rootStyle.minHeight) || 0
  const paddingBottom = Number.parseFloat(rootStyle.paddingBottom) || 0
  let contentBottom = Number.parseFloat(rootStyle.paddingTop) || 0

  target.querySelectorAll('*').forEach((element) => {
    if (isExcluded(element, excludeSelectors)) return
    const style = window.getComputedStyle(element)
    if (style.display === 'none' || style.visibility === 'hidden') return

    for (const elementRect of element.getClientRects()) {
      contentBottom = Math.max(contentBottom, elementRect.bottom - rect.top + target.scrollTop)
    }
  })

  const height = Math.ceil(Math.max(minimumHeight, contentBottom + paddingBottom))

  if (width <= 0 || height <= 0) {
    throw new Error('마음 리포트의 이미지 크기를 계산할 수 없습니다.')
  }

  return { width, height }
}

async function renderReportToCanvas(target, { width, height, scale, excludeSelectors }) {
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(width * scale)
  canvas.height = Math.round(height * scale)

  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('이미지 변환을 위한 Canvas를 사용할 수 없습니다.')
  }

  context.setTransform(scale, 0, 0, scale, 0, 0)
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'

  const origin = target.getBoundingClientRect()
  await drawElement(context, target, {
    origin,
    excludeSelectors,
    inheritedOpacity: 1,
  })

  return canvas
}

async function drawElement(context, element, options) {
  if (element !== options.root && isExcluded(element, options.excludeSelectors)) return

  const style = window.getComputedStyle(element)
  if (style.display === 'none' || style.visibility === 'hidden') return

  const opacity = options.inheritedOpacity * (Number.parseFloat(style.opacity) || 1)
  const rect = element.getBoundingClientRect()
  const box = {
    x: rect.left - options.origin.left,
    y: rect.top - options.origin.top,
    width: rect.width,
    height: rect.height,
  }

  context.save()
  context.globalAlpha = opacity
  drawElementBackground(context, box, style)
  drawElementBorder(context, box, style)
  context.restore()

  if (element instanceof HTMLImageElement) {
    drawImageElement(context, element, box, style, opacity)
    return
  }

  if (element instanceof SVGElement && element.tagName.toLowerCase() === 'svg') {
    await drawSvgElement(context, element, box, opacity)
    return
  }

  for (const node of element.childNodes) {
    if (node instanceof Element) {
      await drawElement(context, node, {
        ...options,
        inheritedOpacity: opacity,
        root: options.root ?? element,
      })
    } else if (node instanceof Text) {
      drawTextNode(context, node, style, options.origin, opacity)
    }
  }
}

function drawImageElement(context, image, box, style, opacity) {
  if (!image.complete || image.naturalWidth <= 0 || image.naturalHeight <= 0) return
  if (box.width <= 0 || box.height <= 0) return

  const objectFit = style.objectFit || 'fill'
  const imageRatio = image.naturalWidth / image.naturalHeight
  const boxRatio = box.width / box.height
  let width = box.width
  let height = box.height

  if (objectFit === 'contain' || objectFit === 'scale-down') {
    if (imageRatio > boxRatio) {
      height = width / imageRatio
    } else {
      width = height * imageRatio
    }
    if (objectFit === 'scale-down') {
      width = Math.min(width, image.naturalWidth)
      height = Math.min(height, image.naturalHeight)
    }
  } else if (objectFit === 'cover') {
    if (imageRatio > boxRatio) {
      width = height * imageRatio
    } else {
      height = width / imageRatio
    }
  } else if (objectFit === 'none') {
    width = image.naturalWidth
    height = image.naturalHeight
  }

  const x = box.x + (box.width - width) / 2
  const y = box.y + (box.height - height) / 2
  const radius = Math.max(
    Number.parseFloat(style.borderTopLeftRadius) || 0,
    Number.parseFloat(style.borderTopRightRadius) || 0,
    Number.parseFloat(style.borderBottomRightRadius) || 0,
    Number.parseFloat(style.borderBottomLeftRadius) || 0,
  )

  context.save()
  context.globalAlpha = opacity
  roundedRectPath(context, box.x, box.y, box.width, box.height, radius)
  context.clip()
  context.drawImage(image, x, y, width, height)
  context.restore()
}

async function drawSvgElement(context, svg, box, opacity) {
  if (box.width <= 0 || box.height <= 0) return

  const clone = svg.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clone.setAttribute('width', String(box.width))
  clone.setAttribute('height', String(box.height))
  inlineSvgComputedStyles(svg, clone)

  const markup = new XMLSerializer().serializeToString(clone)
  const blob = new Blob([markup], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(blob)

  try {
    const image = await loadImage(url)
    context.save()
    context.globalAlpha = opacity
    context.drawImage(image, box.x, box.y, box.width, box.height)
    context.restore()
  } finally {
    URL.revokeObjectURL(url)
  }
}

function inlineSvgComputedStyles(source, clone) {
  const sourceElements = [source, ...source.querySelectorAll('*')]
  const cloneElements = [clone, ...clone.querySelectorAll('*')]
  const properties = [
    'fill',
    'fill-opacity',
    'stroke',
    'stroke-width',
    'stroke-opacity',
    'stroke-dasharray',
    'stroke-linecap',
    'stroke-linejoin',
    'opacity',
    'stop-color',
    'stop-opacity',
    'color',
    'font-family',
    'font-size',
    'font-weight',
  ]

  sourceElements.forEach((sourceElement, index) => {
    const cloneElement = cloneElements[index]
    if (!cloneElement) return
    const computed = window.getComputedStyle(sourceElement)
    for (const property of properties) {
      const value = computed.getPropertyValue(property)
      if (value) cloneElement.style.setProperty(property, value)
    }
  })
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('그래프를 이미지에 그리지 못했습니다.'))
    image.src = source
  })
}

function drawElementBackground(context, box, style) {
  if (box.width <= 0 || box.height <= 0) return

  const radius = Math.max(
    Number.parseFloat(style.borderTopLeftRadius) || 0,
    Number.parseFloat(style.borderTopRightRadius) || 0,
    Number.parseFloat(style.borderBottomRightRadius) || 0,
    Number.parseFloat(style.borderBottomLeftRadius) || 0,
  )
  const gradient = createCanvasGradient(context, style.backgroundImage, box)
  const background = gradient ?? normalizePaintColor(style.backgroundColor)

  if (!background) return
  roundedRectPath(context, box.x, box.y, box.width, box.height, radius)
  context.fillStyle = background
  context.fill()
}

function drawElementBorder(context, box, style) {
  const sides = [
    ['Top', box.x, box.y, box.x + box.width, box.y],
    ['Right', box.x + box.width, box.y, box.x + box.width, box.y + box.height],
    ['Bottom', box.x + box.width, box.y + box.height, box.x, box.y + box.height],
    ['Left', box.x, box.y + box.height, box.x, box.y],
  ]

  for (const [side, x1, y1, x2, y2] of sides) {
    const width = Number.parseFloat(style[`border${side}Width`]) || 0
    const borderStyle = style[`border${side}Style`]
    const color = normalizePaintColor(style[`border${side}Color`])
    if (width <= 0 || borderStyle === 'none' || !color) continue

    context.beginPath()
    context.moveTo(x1, y1)
    context.lineTo(x2, y2)
    context.lineWidth = width
    context.strokeStyle = color
    if (borderStyle === 'dashed') context.setLineDash([width * 3, width * 2])
    if (borderStyle === 'dotted') context.setLineDash([width, width * 1.5])
    context.stroke()
    context.setLineDash([])
  }
}

function drawTextNode(context, textNode, style, origin, opacity) {
  const text = textNode.textContent ?? ''
  if (!text.trim()) return

  const color = normalizePaintColor(style.webkitTextFillColor || style.color)
  const fontSize = Number.parseFloat(style.fontSize) || 16
  if (!color || fontSize <= 0) return

  context.save()
  context.globalAlpha = opacity
  context.fillStyle = color
  context.font = [style.fontStyle, style.fontWeight, `${fontSize}px`, style.fontFamily]
    .filter(Boolean)
    .join(' ')
  context.textBaseline = 'top'

  const range = document.createRange()
  for (const { segment, index } of segmentText(text)) {
    if (/^[\r\n]+$/.test(segment)) continue

    range.setStart(textNode, index)
    range.setEnd(textNode, index + segment.length)
    const rect = range.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) continue

    const x = rect.left - origin.left
    const y = rect.top - origin.top + Math.max(0, (rect.height - fontSize) / 2)
    context.fillText(applyTextTransform(segment, style.textTransform), x, y)
  }

  range.detach()
  context.restore()
}

function segmentText(text) {
  if (typeof Intl?.Segmenter === 'function') {
    return new Intl.Segmenter('ko', { granularity: 'grapheme' }).segment(text)
  }

  let index = 0
  return Array.from(text, (segment) => {
    const value = { segment, index }
    index += segment.length
    return value
  })
}

function applyTextTransform(text, transform) {
  if (transform === 'uppercase') return text.toUpperCase()
  if (transform === 'lowercase') return text.toLowerCase()
  if (transform === 'capitalize') return text.replace(/^\p{L}/u, (letter) => letter.toUpperCase())
  return text
}

function createCanvasGradient(context, backgroundImage, box) {
  const match = /^linear-gradient\((.*)\)$/i.exec(backgroundImage ?? '')
  if (!match) return null

  const parts = splitCssArguments(match[1])
  let angle = 180
  if (/^-?[\d.]+deg$/i.test(parts[0])) {
    angle = Number.parseFloat(parts.shift())
  }
  if (parts.length < 2) return null

  const radians = angle * Math.PI / 180
  const directionX = Math.sin(radians)
  const directionY = -Math.cos(radians)
  const length = Math.abs(box.width * directionX) + Math.abs(box.height * directionY)
  const centerX = box.x + box.width / 2
  const centerY = box.y + box.height / 2
  const gradient = context.createLinearGradient(
    centerX - directionX * length / 2,
    centerY - directionY * length / 2,
    centerX + directionX * length / 2,
    centerY + directionY * length / 2,
  )

  const stops = parts.map(parseColorStop).filter(Boolean)
  if (stops.length < 2) return null

  stops.forEach((stop, index) => {
    const fallbackOffset = stops.length === 1 ? 0 : index / (stops.length - 1)
    gradient.addColorStop(stop.offset ?? fallbackOffset, stop.color)
  })
  return gradient
}

function splitCssArguments(value) {
  const parts = []
  let depth = 0
  let start = 0

  for (let index = 0; index < value.length; index += 1) {
    if (value[index] === '(') depth += 1
    if (value[index] === ')') depth -= 1
    if (value[index] === ',' && depth === 0) {
      parts.push(value.slice(start, index).trim())
      start = index + 1
    }
  }
  parts.push(value.slice(start).trim())
  return parts
}

function parseColorStop(value) {
  const match = /^(rgba?\([^)]*\)|hsla?\([^)]*\)|#[\da-f]+|[a-z]+)(?:\s+(-?[\d.]+)%?)?/i.exec(value)
  if (!match) return null
  const rawOffset = match[2] === undefined ? null : Number.parseFloat(match[2]) / 100
  return {
    color: match[1],
    offset: rawOffset === null ? null : Math.min(1, Math.max(0, rawOffset)),
  }
}

function normalizePaintColor(color) {
  if (!color || color === 'transparent' || /rgba\([^)]*,\s*0\s*\)$/i.test(color)) return null
  return color
}

function roundedRectPath(context, x, y, width, height, radius) {
  const safeRadius = Math.min(Math.max(radius, 0), width / 2, height / 2)
  context.beginPath()
  if (typeof context.roundRect === 'function') {
    context.roundRect(x, y, width, height, safeRadius)
    return
  }
  context.rect(x, y, width, height)
}

function isExcluded(element, selectors) {
  return selectors.some((selector) => element.matches(selector) || element.closest(selector))
}

function buildReportFilename(target) {
  const period = target.querySelector('.eyebrow')?.textContent?.trim() ?? ''
  const title = target.querySelector('h1')?.textContent?.trim() ?? '마음리포트'
  return ['마음리포트', period, title].filter(Boolean).join('_')
}

function sanitizeFilename(filename) {
  const safeName = String(filename)
    .replace(INVALID_FILENAME_CHARACTERS, '-')
    .replace(/\s+/g, ' ')
    .replace(/[. ]+$/g, '')
    .trim()
    .slice(0, 120)

  return safeName || '마음리포트'
}

function normalizeScale(scale) {
  const defaultScale = Math.min(window.devicePixelRatio || 1, 2)
  const parsedScale = Number(scale ?? defaultScale)
  return Number.isFinite(parsedScale) ? Math.min(Math.max(parsedScale, 1), 3) : defaultScale
}

function fitScaleToCanvas(width, height, requestedScale) {
  const edgeScale = Math.min(MAX_CANVAS_EDGE / width, MAX_CANVAS_EDGE / height)
  return Math.max(0.1, Math.min(requestedScale, edgeScale))
}

async function waitForDocumentAssets(target) {
  if (document.fonts?.ready) {
    await settleWithin(document.fonts.ready, 3000)
  }

  const pendingImages = [...target.querySelectorAll('img')]
    .filter((image) => !image.complete)
    .map((image) => new Promise((resolve) => {
      image.addEventListener('load', resolve, { once: true })
      image.addEventListener('error', resolve, { once: true })
    }))

  await settleWithin(Promise.all(pendingImages), 3000)
  await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
}

function settleWithin(promise, milliseconds) {
  return Promise.race([
    promise,
    new Promise((resolve) => setTimeout(resolve, milliseconds)),
  ])
}

function assertBrowserEnvironment() {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    throw new Error('마음 리포트 PDF 렌더링은 브라우저에서만 사용할 수 있습니다.')
  }
}
