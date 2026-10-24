# MoGraph 技法

以下是可自由改寫的原生技法，並非所有作品的統一場景物件 API。

## Shape morphing

拓樸一致的輪廓可對應相同數量與方向的節點，再插值。圓到星形的可執行 Canvas 路徑：

```js
function morphPath(ctx, cx, cy, radius, amount, points = 120) {
  ctx.beginPath();
  for (let i = 0; i <= points; i++) {
    const a = i / points * Math.PI * 2 - Math.PI / 2;
    const r = radius * (1 - amount * .32 * (1 - Math.cos(a * 5)));
    const x = cx + r * Math.cos(a), y = cy + r * Math.sin(a);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.closePath();
}
```

任意 SVG 路徑對應可使用 flubber 等成熟套件，記錄套件授權；圖形洞口與自交需另行檢查。

## Mask／reveal／transition

```js
function circleReveal(ctx, canvas, progress, drawNext) {
  ctx.save(); ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height / 2,
          Math.hypot(canvas.width, canvas.height) / 2 * progress, 0, 2*Math.PI);
  ctx.clip(); drawNext(); ctx.restore();
}
```

`save/restore` 保護 clipping／transform 狀態。淡入淡出、wipe、match cut 或原生 shader transition 依敘事選用。跨引擎可以輸出透明 PNG 圖層後用 compositor 合成；RGB video 無法回復已丟失的 alpha。

## Kinetic／karaoke typography

先量每個字的 advance，再做 per-glyph transform；以單一字寬切歌詞會破壞比例字與連字。依 glyph 分割可能破壞複雜腳本 shaping，需整行文字遮罩或使用 HarfBuzz／瀏覽器原生排版。

```js
function karaoke(ctx, text, x, y, width, progress) {
  ctx.fillStyle = '#66717f'; ctx.fillText(text, x, y);
  ctx.save(); ctx.beginPath(); ctx.rect(x, y-80, width*progress, 100); ctx.clip();
  ctx.fillStyle = '#ffb454'; ctx.fillText(text, x, y); ctx.restore();
}
```

Progress 由實際可用的 line／note／syllable／phoneme 時間取得，不能把字數均分宣稱精確口型。停留時間以閱讀需求決定，避免每個字都只閃一影格。

## Parallax

對不同深度 `z` 設 `x=baseX+cameraX/(1+z)`，讓前景動得較快；Three.js 可直接使用透視相機與真正 z。檢查邊緣是否露底，攝影機移動要有足夠 overscan。視差是空間線索，不是為靜態資訊加無目的漂移。
