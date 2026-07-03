/**
 * 提出書類チェックリストのPDF生成（外部ライブラリ不使用）
 *
 * ブラウザの印刷ダイアログが使えない環境（サンドボックス内表示など）でも
 * PDFを保存できるよう、チェックリストをCanvasに描画し、
 * 各ページをJPEG画像として最小構成のPDFに組み立ててダウンロードする。
 */
(function (global) {
  'use strict';

  // A4 (595.28pt × 841.89pt) を2倍解像度で描画
  const PAGE_W = 1190;
  const PAGE_H = 1684;
  const MARGIN = 90;
  const FONT = '"Hiragino Kaku Gothic ProN", "Hiragino Sans", "BIZ UDPGothic", Meiryo, sans-serif';

  function createPage() {
    const canvas = document.createElement('canvas');
    canvas.width = PAGE_W;
    canvas.height = PAGE_H;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, PAGE_W, PAGE_H);
    ctx.textBaseline = 'top';
    return { canvas, ctx };
  }

  // 日本語は任意の位置で折り返せるため1文字単位で折り返す
  function wrapChars(ctx, text, maxWidth) {
    const lines = [];
    let line = '';
    for (const ch of text) {
      if (ch === '\n') {
        lines.push(line);
        line = '';
        continue;
      }
      if (line && ctx.measureText(line + ch).width > maxWidth) {
        lines.push(line);
        line = ch;
      } else {
        line += ch;
      }
    }
    lines.push(line);
    return lines;
  }

  function renderPages(checklist, generatedDate) {
    const pages = [];
    let page = createPage();
    let y = MARGIN;

    function ensureSpace(height) {
      if (y + height > PAGE_H - MARGIN) {
        pages.push(page.canvas);
        page = createPage();
        y = MARGIN;
      }
    }

    function text(str, opts) {
      const { size = 22, weight = '', color = '#2b2b2b', indent = 0, lineHeight = 1.5, spaceAfter = 0, box = false } = opts || {};
      const fontSpec = `${weight ? weight + ' ' : ''}${size}px ${FONT}`;
      page.ctx.font = fontSpec;
      const boxWidth = box ? Math.round(size * 1.6) : 0;
      const maxWidth = PAGE_W - MARGIN * 2 - indent - boxWidth;
      const lines = wrapChars(page.ctx, str, maxWidth);
      const lh = Math.round(size * lineHeight);
      lines.forEach((line, i) => {
        ensureSpace(lh);
        const ctx = page.ctx; // 改ページ後は新しいページのctxを使う
        ctx.font = fontSpec;
        ctx.fillStyle = color;
        let x = MARGIN + indent;
        if (box && i === 0) {
          const bs = Math.round(size * 0.9);
          ctx.strokeStyle = '#5f6b64';
          ctx.lineWidth = 2;
          ctx.strokeRect(x, y + Math.round((lh - bs) / 2), bs, bs);
        }
        x += boxWidth;
        ctx.fillText(line, x, y + Math.round((lh - size) / 2));
        y += lh;
      });
      y += spaceAfter;
    }

    function rule() {
      ensureSpace(20);
      const ctx = page.ctx;
      ctx.strokeStyle = '#2e7d4f';
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(MARGIN, y + 6);
      ctx.lineTo(PAGE_W - MARGIN, y + 6);
      ctx.stroke();
      y += 20;
    }

    text('世田谷区 子育て支援 申請書類チェックリスト', { size: 34, weight: 'bold', color: '#1f5c39', spaceAfter: 8 });
    text(`作成日: ${generatedDate}`, { size: 20, color: '#5f6b64', spaceAfter: 4 });
    text('※ このリストは参考情報です。必要書類は状況により異なるため、申請前に必ず各制度の公式ページまたは窓口でご確認ください。',
      { size: 18, color: '#b3541e', spaceAfter: 24 });

    if (checklist.common.length > 0) {
      ensureSpace(140);
      text('複数の申請で共通して必要になる書類', { size: 26, weight: 'bold', color: '#1f5c39' });
      rule();
      checklist.common.forEach((doc) => text(doc, { size: 22, indent: 10, box: true }));
      y += 28;
    }

    checklist.perBenefit.forEach((b) => {
      ensureSpace(160);
      text(b.name, { size: 26, weight: 'bold', color: '#1f5c39' });
      rule();
      text(`申請窓口: ${b.window}`, { size: 19, color: '#5f6b64', spaceAfter: 6 });
      b.documents.forEach((doc) => text(doc, { size: 22, indent: 10, box: true }));
      if (b.notes) text(`※ ${b.notes}`, { size: 18, color: '#b3541e', indent: 10 });
      text(`公式ページ: ${b.url}`, { size: 17, color: '#5f6b64', indent: 10, spaceAfter: 32 });
    });

    pages.push(page.canvas);
    return pages;
  }

  function dataUrlToBytes(dataUrl) {
    const bin = atob(dataUrl.split(',')[1]);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }

  function ascii(str) {
    const bytes = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i) & 0xff;
    return bytes;
  }

  // Canvas群を1ページ1画像(JPEG/DCTDecode)のPDFに組み立てる
  function canvasesToPdfBlob(canvases) {
    const PT_W = '595.28';
    const PT_H = '841.89';
    const chunks = [];
    let offset = 0;
    const objOffsets = [];

    function push(data) {
      const bytes = typeof data === 'string' ? ascii(data) : data;
      chunks.push(bytes);
      offset += bytes.length;
    }

    function beginObj(num) {
      objOffsets[num] = offset;
      push(`${num} 0 obj\n`);
    }

    push('%PDF-1.4\n%âãÏÓ\n');

    const n = canvases.length;
    const pageRefs = canvases.map((_, i) => `${3 + i * 3} 0 R`);

    beginObj(1);
    push('<< /Type /Catalog /Pages 2 0 R >>\nendobj\n');
    beginObj(2);
    push(`<< /Type /Pages /Kids [${pageRefs.join(' ')}] /Count ${n} >>\nendobj\n`);

    canvases.forEach((canvas, i) => {
      const pageNum = 3 + i * 3;
      const contentNum = pageNum + 1;
      const imageNum = pageNum + 2;
      const jpeg = dataUrlToBytes(canvas.toDataURL('image/jpeg', 0.85));
      const content = `q ${PT_W} 0 0 ${PT_H} 0 0 cm /Im${i} Do Q`;

      beginObj(pageNum);
      push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${PT_W} ${PT_H}] /Contents ${contentNum} 0 R ` +
        `/Resources << /XObject << /Im${i} ${imageNum} 0 R >> >> >>\nendobj\n`);

      beginObj(contentNum);
      push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream\nendobj\n`);

      beginObj(imageNum);
      push(`<< /Type /XObject /Subtype /Image /Width ${canvas.width} /Height ${canvas.height} ` +
        `/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`);
      push(jpeg);
      push('\nendstream\nendobj\n');
    });

    const objCount = 2 + n * 3;
    const xrefOffset = offset;
    let xref = `xref\n0 ${objCount + 1}\n0000000000 65535 f \n`;
    for (let i = 1; i <= objCount; i++) {
      xref += String(objOffsets[i]).padStart(10, '0') + ' 00000 n \n';
    }
    push(xref);
    push(`trailer\n<< /Size ${objCount + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`);

    return new Blob(chunks, { type: 'application/pdf' });
  }

  function downloadChecklistPdf(checklist, generatedDate, filename) {
    const pages = renderPages(checklist, generatedDate);
    const blob = canvasesToPdfBlob(pages);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
    return pages.length;
  }

  global.downloadChecklistPdf = downloadChecklistPdf;
})(typeof window !== 'undefined' ? window : globalThis);
