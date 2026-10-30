/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 DAVE contributors. See the repository LICENSE.
 * Original native-canvas exporter. Canvas2Image is retained as a compatibility API.
 */
(function (root) {
  'use strict';
  function resized(source, width, height) {
    if (!source || typeof source.toDataURL !== 'function' || !source.width || !source.height) return null;
    if (width == null || height == null) return source;
    width = Math.floor(Number(width));
    height = Math.floor(Number(height));
    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null;
    const target = document.createElement('canvas');
    target.width = width;
    target.height = height;
    target.getContext('2d').drawImage(source, 0, 0, width, height);
    return target;
  }

  function bitmap(canvas) {
    // Windows BITMAPINFOHEADER, 24-bit BGR rows, bottom-up with 4-byte alignment.
    const stride = Math.ceil(canvas.width * 3 / 4) * 4;
    const length = 54 + stride * canvas.height;
    if (length > 0xffffffff) return null;
    const bytes = new Uint8Array(length);
    const header = new DataView(bytes.buffer);
    bytes[0] = 0x42;
    bytes[1] = 0x4d;
    header.setUint32(2, length, true);
    header.setUint32(10, 54, true);
    header.setUint32(14, 40, true);
    header.setInt32(18, canvas.width, true);
    header.setInt32(22, canvas.height, true);
    header.setUint16(26, 1, true);
    header.setUint16(28, 24, true);
    header.setUint32(34, stride * canvas.height, true);
    const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (let y = 0; y < canvas.height; y++) {
      for (let x = 0; x < canvas.width; x++) {
        const input = (y * canvas.width + x) * 4;
        const output = 54 + (canvas.height - 1 - y) * stride + x * 3;
        bytes[output] = pixels[input + 2];
        bytes[output + 1] = pixels[input + 1];
        bytes[output + 2] = pixels[input];
      }
    }
    let binary = '';
    for (let offset = 0; offset < bytes.length; offset += 32768) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 32768));
    }
    return 'data:image/bmp;base64,' + root.btoa(binary);
  }

  function exportImage(format, source, returnImage, width, height) {
    const canvas = resized(source, width, height);
    if (!canvas) return false;
    const mime = 'image/' + format;
    const data = format === 'bmp' ? bitmap(canvas) : canvas.toDataURL(mime);
    if (!data || !data.startsWith('data:' + mime + ';')) return false;
    if (returnImage) {
      const image = document.createElement('img');
      image.src = data;
      return image;
    }
    return saveDataURL(data, 'download.' + (format === 'jpeg' ? 'jpg' : format));
  }
  function saveDataURL(data, filename) {
    if (!/^data:image\/(png|jpeg|bmp);base64,/.test(data)) return false;
    const link = document.createElement('a');
    link.href = data;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    return true;
  }
  root.Canvas2Image = {
    saveDataURL,
    saveAsPNG: (canvas, returnImage, width, height) => exportImage('png', canvas, returnImage, width, height),
    saveAsJPEG: (canvas, returnImage, width, height) => exportImage('jpeg', canvas, returnImage, width, height),
    saveAsBMP: (canvas, returnImage, width, height) => exportImage('bmp', canvas, returnImage, width, height)
  };
})(window);
