# Browser compatibility components

`static/scripts/logPanel.js` and `static/scripts/canvasExport.js` are original
DAVE implementations distributed under the repository's Apache License 2.0.
Their source headers carry SPDX-License-Identifier: Apache-2.0 and attribution to
DAVE contributors. The full license is shipped in the app and notice companion.
They introduce no third-party dependency or remote service.

These replace the former vendor logger and stripped Canvas2Image implementation,
whose redistribution provenance could not be established. The former files are
removed, and all templates/tests reference the new project modules. Existing
`Logger`, logging helpers and `Canvas2Image` names are compatibility interfaces,
not retained vendor implementations.

The panel uses native DOM nodes and Web Animations with the existing CSS IDs,
classes, dimensions, timestamp format, row limit and level colors. Messages remain
text nodes. Show/hide, enable/disable, clearing, keyboard/mouse toggling and rapid
animation reversals are covered by browser regressions.

Image conversion uses native canvas PNG/JPEG encoding and an independently written
24-bit BMP encoder following BITMAPINFOHEADER: bottom-up BGR rows aligned to four
bytes. The synchronous return-image and optional resize interfaces remain available.
Downloads use an anchor's download attribute rather than page navigation, preserving
workspace state. The default filename is download.png, download.jpg or download.bmp.
Regression tests decode actual output pixels, dimensions and BMP padding and exercise
the actual plot PNG/PDF actions with the bundled Plotly renderer and original DAVE PDF writer.

Plot exports now use Plotly.toImage, an API of the already bundled MIT-licensed
Plotly library. The former html2canvas path produced blank images for SVG plots;
regressions check actual trace-colored pixels in the PNG and embedded PDF JPEG.
PDF images are fitted within the existing portrait page so axes and labels are
not clipped. The export menus, PNG/PDF choices and on-screen plots are unchanged.
The obsolete html2canvas script is no longer loaded by the application.

API/format references:
- https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement/toDataURL
- https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapinfoheader

The separate Electron/Python logger is unchanged. The remaining legacy browser
vendor advisory review and final source obligations are tracked independently;
this replacement is not a claim of whole-application security/legal clearance.


`static/scripts/imagePDF.js` is also original DAVE code under Apache-2.0. It replaces
jsPDF for the existing single-plot-image PDF action. It writes a PDF 1.3 catalog,
page, JPEG image object, drawing stream and byte-counted cross-reference table.
The same Plotly JPEG is fitted to the same portrait A4 page and 10 mm margins.
There are no HTML, form, encryption, script or remote-resource paths. No MD5 code
is included. Tests check actual pixels, PDF offsets, portrait fit and input rejection.
The file is implemented from the format specification, not adapted from jsPDF:
https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/pdfreference1.3.pdf.
