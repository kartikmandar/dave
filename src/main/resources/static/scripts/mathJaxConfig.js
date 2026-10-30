/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 DAVE contributors. See the repository LICENSE.
 */
// Keep scientific TeX/SVG rendering local and reject executable/file URLs in TeX.
window.MathJax = {
  extensions: ['Safe.js'],
  Safe: { safeProtocols: { http: true, https: true, file: false, javascript: false } }
};
