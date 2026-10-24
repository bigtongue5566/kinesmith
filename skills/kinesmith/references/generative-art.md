# 程序化藝術

選擇圖樣的規則與變化來源：粒子、Noise、流場、遞迴、細胞或點陣皆可。保持構圖焦點、密度與留白，程序複雜不等於訊息清楚。

原生 p5.js 固定種子流場（在 sketch 初始化使用 `p.noLoop()`，由 renderer 明確呼叫）：

```js
function flowField(p, t, width, height) {
  p.randomSeed(231); p.noiseSeed(231);
  p.background(245, 241, 232); p.noFill(); p.stroke(25, 61, 68, 70);
  for (let i = 0; i < 110; i++) {
    let x = p.random(width), y = p.random(height);
    p.beginShape();
    for (let step = 0; step < 50; step++) {
      const angle = p.noise(x * .004, y * .004, t * .15) * Math.PI * 4;
      p.vertex(x, y); x += Math.cos(angle) * 5; y += Math.sin(angle) * 5;
    }
    p.endShape();
  }
}
```

每幀重新建構固定初始粒子，再以 `t` 驅動 Noise，所以任意跳影格仍得到相同畫面。需累積軌跡時用明確 simulation frame 及固定步長；預覽與正式輸出使用相同 seed，避免預覽好看、成片亂跳。

Rough.js 每個 draw 設固定 `seed`，用 strokeDashoffset 或遮罩實現手繪 reveal；若每幀給新 seed，會變成線條閃爍。需要 boiling 效果時以可控低頻更新並在報告中說明是設計意圖。

粒子資料可使用 TypedArray 提高效率，大量 Three.js 粒子用 BufferGeometry／InstancedMesh，避免每影格建立數千個 Object3D。Shader noise 可引用有授權的實作，不能把程式碼來源省略。先決定視覺密度與取樣，再優化；少量粒子直接原生 API 足夠。

FFT 音訊驅動時避免把每幀所有頻帶抖動直接放大。取 log frequency bands，以固定時間常數平滑；如果需要隨機 seek，從預先分析的 envelope 直接插值，而非持續累積 smoothing state。
