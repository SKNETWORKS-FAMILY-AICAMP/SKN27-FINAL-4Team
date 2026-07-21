import { ref } from 'vue'

export function useChatImageAttachment(isTyping) {
  const attachedImage = ref(null)
  const isDragging = ref(false)

  function processImageFile(file) {
    if (!file || !file.type.startsWith('image/')) return
    const reader = new FileReader()
    reader.onload = () => {
      const image = new Image()
      image.onload = () => {
        const maxSize = 1024
        let { width, height } = image
        if (width > maxSize || height > maxSize) {
          const ratio = Math.min(maxSize / width, maxSize / height)
          width = Math.round(width * ratio)
          height = Math.round(height * ratio)
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        canvas.getContext('2d').drawImage(image, 0, 0, width, height)
        attachedImage.value = canvas.toDataURL('image/jpeg', 0.8)
      }
      image.src = reader.result
    }
    reader.readAsDataURL(file)
  }

  function onPickImage(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    processImageFile(file)
  }

  function onDropImage(event) {
    isDragging.value = false
    processImageFile(event.dataTransfer?.files?.[0])
  }

  function onDragOver() {
    if (!isTyping.value) isDragging.value = true
  }

  function onDragLeave(event) {
    if (!event.relatedTarget) isDragging.value = false
  }

  function onPasteImage(event) {
    const item = [...(event.clipboardData?.items || [])]
      .find(clipboardItem => clipboardItem.type.startsWith('image/'))
    if (item) processImageFile(item.getAsFile())
  }

  function clearImage() {
    attachedImage.value = null
  }

  return {
    attachedImage,
    clearImage,
    isDragging,
    onDragLeave,
    onDragOver,
    onDropImage,
    onPasteImage,
    onPickImage,
  }
}
