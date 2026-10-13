export const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const MAX_ORIGINAL_BYTES = 25 * 1024 * 1024; // refuse absurd files before decoding

/**
 * Shrinks a photo to at most `maxEdge` pixels on its long side and re-encodes it as JPEG.
 * The browser applies the phone's rotation flag while decoding. If anything goes wrong,
 * the original file is returned unchanged.
 */
export async function prepareUpload(file: File, maxEdge = 1024, quality = 0.85): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
    const scale = Math.min(1, maxEdge / Math.max(bitmap.width, bitmap.height));
    const width = Math.max(1, Math.round(bitmap.width * scale));
    const height = Math.max(1, Math.round(bitmap.height * scale));

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) {
      bitmap.close();
      return file;
    }

    context.fillStyle = '#ffffff'; // transparent PNG areas become white, not black
    context.fillRect(0, 0, width, height);
    context.drawImage(bitmap, 0, 0, width, height);
    bitmap.close();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', quality),
    );
    if (blob) {
      return blob;
    }
  } catch {
    // fall through and send the original
  }
  return file;
}
