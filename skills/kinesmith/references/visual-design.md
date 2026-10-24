# 視覺設計：讓觀眾先看對地方

先以單幀驗證訊息，再加動作。每個場景選一個主體與一個主訊息，使用尺寸、對比、留白及動線引導視線；場景不必套固定版型。保持字形的正式比例，字距與行距依字型實際量測。中文預設使用有商用授權且含所需 glyph 的字型，不用缺字方框假裝完成。

Canvas 可執行文字換行與安全框量測（先 `await document.fonts.ready`）：

```js
function linesFor(ctx, text, maxWidth) {
  const lines = []; let line = '';
  for (const glyph of [...text]) {
    if (glyph === '\n') { lines.push(line); line = ''; continue; }
    if (line && ctx.measureText(line + glyph).width > maxWidth) {
      lines.push(line); line = glyph;
    } else line += glyph;
  }
  if (line) lines.push(line);
  return lines;
}
function title(ctx, text, width, height) {
  ctx.font = '700 52px sans-serif'; ctx.textBaseline = 'top';
  const margin = width * 0.08, leading = 68;
  const lines = linesFor(ctx, text, width - 2 * margin);
  if (lines.length * leading > height * 0.6) throw Error('標題超出版面');
  ctx.fillStyle = '#17252a';
  lines.forEach((line, i) => ctx.fillText(line, margin, height * .18 + i * leading));
}
```

此函式示範逐字換行；長英文可改用 Intl.Segmenter 依詞分段。排版時確認 actualBoundingBoxAscent／Descent、字距及動畫 overshoot 仍落在安全區，不能只量停格狀態。

色彩先指定背景、文字、主色、輔色的職責。文字與背景使用相對亮度計算對比，4.5:1 可作一般小字的起點；最終仍應用輸出尺寸檢查。漸層、顆粒、亮暗場景切換會改變實際可讀性。色彩不只裝飾：同一資料或角色跨場景保持可辨識。

階層範例：主標 64、輔標 28、標籤 18 是起點，可依畫幅調整；不要把數值當規定。先隱藏裝飾，確認主訊息能讀懂。Composition 可使用偏心、對稱、負空間、分割或視覺重量平衡；以作品目的決定。

字型來源、版本與授權記入作品 assets ledger。SIL OFL 允許商業作品但再散佈字型仍須附授權並遵守 Reserved Font Name；不要聲稱所有系統字型都可隨 Plugin 打包。
