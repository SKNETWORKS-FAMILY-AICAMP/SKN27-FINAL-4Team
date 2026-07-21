const transparentImageCache = new Map();

export function createTransparentCharacterImage(src) {
  if (transparentImageCache.has(src)) return transparentImageCache.get(src);

  const pendingImage = new Promise((resolve) => {
    if (typeof window === "undefined" || !src) {
      resolve(src);
      return;
    }

    const image = new Image();
    image.crossOrigin = "anonymous";

    image.onload = () => {
      try {
        const width = image.naturalWidth || image.width;
        const height = image.naturalHeight || image.height;
        if (!width || !height) {
          resolve(src);
          return;
        }

        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d", { willReadFrequently: true });
        if (!context) {
          resolve(src);
          return;
        }

        canvas.width = width;
        canvas.height = height;
        context.drawImage(image, 0, 0, width, height);

        const imageData = context.getImageData(0, 0, width, height);
        const { data } = imageData;
        const cornerIndexes = [
          3,
          (width - 1) * 4 + 3,
          ((height - 1) * width) * 4 + 3,
          (width * height - 1) * 4 + 3,
        ];

        if (cornerIndexes.every(index => data[index] <= 16)) {
          resolve(src);
          return;
        }

        const visited = new Uint8Array(width * height);
        const queueX = new Int32Array(width * height);
        const queueY = new Int32Array(width * height);
        let queueHead = 0;
        let queueTail = 0;

        const pixelOffset = (x, y) => (y * width + x) * 4;
        const isBackgroundPixel = (x, y) => {
          const offset = pixelOffset(x, y);
          const alpha = data[offset + 3];
          if (alpha <= 16) return true;

          const red = data[offset];
          const green = data[offset + 1];
          const blue = data[offset + 2];
          const brightness = (red + green + blue) / 3;
          const maxDifference = Math.max(
            Math.abs(red - green),
            Math.abs(red - blue),
            Math.abs(green - blue),
          );
          return brightness >= 235 && maxDifference <= 22;
        };

        const enqueue = (x, y) => {
          if (x < 0 || x >= width || y < 0 || y >= height) return;
          const index = y * width + x;
          if (visited[index] || !isBackgroundPixel(x, y)) return;
          visited[index] = 1;
          queueX[queueTail] = x;
          queueY[queueTail] = y;
          queueTail += 1;
        };

        for (let x = 0; x < width; x += 1) {
          enqueue(x, 0);
          enqueue(x, height - 1);
        }
        for (let y = 0; y < height; y += 1) {
          enqueue(0, y);
          enqueue(width - 1, y);
        }

        while (queueHead < queueTail) {
          const x = queueX[queueHead];
          const y = queueY[queueHead];
          queueHead += 1;
          data[pixelOffset(x, y) + 3] = 0;
          enqueue(x + 1, y);
          enqueue(x - 1, y);
          enqueue(x, y + 1);
          enqueue(x, y - 1);
        }

        context.putImageData(imageData, 0, 0);
        resolve(canvas.toDataURL("image/png"));
      } catch {
        resolve(src);
      }
    };

    image.onerror = () => resolve(src);
    image.src = src;
  });

  transparentImageCache.set(src, pendingImage);
  return pendingImage;
}
