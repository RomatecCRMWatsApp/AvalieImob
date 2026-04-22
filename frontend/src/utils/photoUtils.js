// @module photoUtils — compressão de imagem e geolocalização silenciosa
const MAX_W = 1920;
const MAX_H = 1080;
const JPEG_QUALITY = 0.85;

export function compressFile(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new window.Image();
    img.onload = () => {
      const ratio = Math.min(MAX_W / img.width, MAX_H / img.height, 1);
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * ratio);
      canvas.height = Math.round(img.height * ratio);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob((blob) => {
        const out = new File([blob], file.name.replace(/\.[^.]+$/, '.jpg'), { type: 'image/jpeg' });
        resolve(out);
      }, 'image/jpeg', JPEG_QUALITY);
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

export function getGeoSilent() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve(null),
      { timeout: 5000, maximumAge: 60000 }
    );
  });
}
