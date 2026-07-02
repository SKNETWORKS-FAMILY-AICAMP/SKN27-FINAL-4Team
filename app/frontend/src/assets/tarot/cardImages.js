const imageModules = import.meta.glob('./*.{png,jpg}', {
  eager: true,
  import: 'default',
});

export const tarotCardImages = Object.entries(imageModules).reduce((images, [path, imageUrl]) => {
  const match = path.match(/\/(\d+)_/);
  if (match) {
    images[Number(match[1])] = imageUrl;
  }
  return images;
}, {});

export function getTarotCardImage(cardNumber) {
  return tarotCardImages[Number(cardNumber)] || '';
}
