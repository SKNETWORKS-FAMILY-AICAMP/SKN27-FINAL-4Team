import { createMindReportCanvas } from './reportImageSaver.js'

const DEFAULT_TARGET_SELECTOR = '.report-card'
const MAX_PDF_PAGE_EDGE = 841.89
const JPEG_QUALITY = 0.95

/**
 * 화면의 마음 리포트 구성을 한 장의 PDF로 만들어 바로 내려받는다.
 * 페이지 비율을 리포트 비율에 맞추므로 카드 배치가 A4용으로 재배열되지 않는다.
 *
 * @param {object} [options]
 * @param {HTMLElement} [options.element] 저장할 마음 리포트 요소
 * @param {string} [options.targetSelector='.report-card'] 저장할 요소 선택자
 * @param {string} [options.filename] 확장자를 제외한 파일명
 * @param {number} [options.scale] 출력 배율
 * @param {string[]} [options.excludeSelectors] PDF에서 제외할 요소 선택자
 * @returns {Promise<{ blob: Blob, filename: string, width: number, height: number }>}
 */
export async function saveMindReportAsPdf(options = {}) {
  const report = await createMindReportCanvas({
    element: options.element,
    targetSelector: options.targetSelector ?? DEFAULT_TARGET_SELECTOR,
    filename: options.filename,
    scale: options.scale,
    excludeSelectors: options.excludeSelectors,
  })
  const jpegBlob = await canvasToJpegBlob(report.canvas)
  const jpegBytes = new Uint8Array(await jpegBlob.arrayBuffer())
  const page = fitPageToReport(report.width, report.height)
  const pdfBytes = createSingleImagePdf({
    jpegBytes,
    imageWidth: report.width,
    imageHeight: report.height,
    pageWidth: page.width,
    pageHeight: page.height,
  })
  const blob = new Blob([pdfBytes], { type: 'application/pdf' })
  const filename = `${report.filename}.pdf`

  downloadBlob(blob, filename)
  return {
    blob,
    filename,
    width: report.width,
    height: report.height,
  }
}

function fitPageToReport(width, height) {
  const aspectRatio = width / height
  if (aspectRatio >= 1) {
    return {
      width: MAX_PDF_PAGE_EDGE,
      height: MAX_PDF_PAGE_EDGE / aspectRatio,
    }
  }
  return {
    width: MAX_PDF_PAGE_EDGE * aspectRatio,
    height: MAX_PDF_PAGE_EDGE,
  }
}

function createSingleImagePdf({
  jpegBytes,
  imageWidth,
  imageHeight,
  pageWidth,
  pageHeight,
}) {
  const drawImage = encodeAscii(
    `q\n${formatNumber(pageWidth)} 0 0 ${formatNumber(pageHeight)} 0 0 cm\n/Im0 Do\nQ\n`,
  )
  const objects = [
    encodeAscii('<< /Type /Catalog /Pages 2 0 R >>'),
    encodeAscii('<< /Type /Pages /Kids [3 0 R] /Count 1 >>'),
    encodeAscii(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${formatNumber(pageWidth)} ${formatNumber(pageHeight)}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`,
    ),
    joinBytes([
      encodeAscii(
        `<< /Type /XObject /Subtype /Image /Width ${imageWidth} /Height ${imageHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpegBytes.length} >>\nstream\n`,
      ),
      jpegBytes,
      encodeAscii('\nendstream'),
    ]),
    joinBytes([
      encodeAscii(`<< /Length ${drawImage.length} >>\nstream\n`),
      drawImage,
      encodeAscii('endstream'),
    ]),
  ]

  const parts = [encodeAscii('%PDF-1.4\n%1234\n')]
  const offsets = [0]
  let byteOffset = parts[0].length

  objects.forEach((object, index) => {
    offsets.push(byteOffset)
    const block = joinBytes([
      encodeAscii(`${index + 1} 0 obj\n`),
      object,
      encodeAscii('\nendobj\n'),
    ])
    parts.push(block)
    byteOffset += block.length
  })

  const xrefOffset = byteOffset
  const xrefRows = offsets.slice(1)
    .map((offset) => `${String(offset).padStart(10, '0')} 00000 n \n`)
    .join('')
  parts.push(encodeAscii(
    `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${xrefRows}`
    + `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n`
    + `startxref\n${xrefOffset}\n%%EOF`,
  ))

  return joinBytes(parts)
}

function canvasToJpegBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob)
      } else {
        reject(new Error('PDF에 담을 마음 리포트 이미지를 만들지 못했습니다.'))
      }
    }, 'image/jpeg', JPEG_QUALITY)
  })
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function encodeAscii(value) {
  return new TextEncoder().encode(value)
}

function joinBytes(parts) {
  const totalLength = parts.reduce((sum, part) => sum + part.length, 0)
  const joined = new Uint8Array(totalLength)
  let offset = 0
  for (const part of parts) {
    joined.set(part, offset)
    offset += part.length
  }
  return joined
}

function formatNumber(value) {
  return Number(value.toFixed(3)).toString()
}
