/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 DAVE contributors. See the repository LICENSE.
 * Original single-JPEG PDF writer using the PDF 1.3 image/XObject specification.
 */
(function (root) {
  'use strict';
  const encoder = new TextEncoder();
  const pageWidth = 595.28;
  const pageHeight = 841.89;
  const margin = 10 * 72 / 25.4;

  async function create(dataURL) {
    if (typeof dataURL !== 'string' || !/^data:image\/jpeg;base64,[A-Za-z0-9+/]+=*$/.test(dataURL)) {
      throw new Error('A JPEG data URL is required');
    }
    const image = new Image();
    image.src = dataURL;
    await image.decode();
    const width = image.naturalWidth;
    const height = image.naturalHeight;
    if (!width || !height) throw new Error('Image dimensions are empty');
    const jpeg = Uint8Array.from(root.atob(dataURL.slice(dataURL.indexOf(',') + 1)), character => character.charCodeAt(0));
    const scale = Math.min((pageWidth - 2 * margin) / width, (pageHeight - 2 * margin) / height);
    const number = value => value.toFixed(4);
    const content = encoder.encode('q\n' + number(width * scale) + ' 0 0 ' + number(height * scale) + ' ' + number(margin) + ' ' + number(pageHeight - margin - height * scale) + ' cm\n/Im0 Do\nQ\n');
    const chunks = [];
    const offsets = [0];
    let length = 0;
    function append(value) {
      const bytes = typeof value === 'string' ? encoder.encode(value) : value;
      chunks.push(bytes);
      length += bytes.length;
    }
    function object(id, value, stream) {
      offsets[id] = length;
      append(id + ' 0 obj\n' + value);
      if (stream) {
        append('\nstream\n');
        append(stream);
        append('\nendstream');
      }
      append('\nendobj\n');
    }
    append('%PDF-1.3\n');
    append(new Uint8Array([37, 226, 227, 207, 211, 10]));
    object(1, '<< /Type /Catalog /Pages 2 0 R >>');
    object(2, '<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
    object(3, '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + pageWidth + ' ' + pageHeight + '] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>');
    object(4, '<< /Type /XObject /Subtype /Image /Width ' + width + ' /Height ' + height + ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ' + jpeg.length + ' >>', jpeg);
    object(5, '<< /Length ' + content.length + ' >>', content);
    const start = length;
    append('xref\n0 6\n0000000000 65535 f \n');
    for (let id = 1; id <= 5; id++) append(String(offsets[id]).padStart(10, '0') + ' 00000 n \n');
    append('trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + start + '\n%%EOF\n');
    return new Blob(chunks, { type: 'application/pdf' });
  }

  async function save(dataURL, filename) {
    const url = URL.createObjectURL(await create(dataURL));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    try { link.click(); } finally {
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
    return true;
  }
  root.DAVEImagePDF = { create, save };
})(window);
