# 動作：時間、間距與因果

正式渲染的狀態必須是明確影格時間的函式。定義 `t=frame/fps`，最後有效影格時間是 `(frameCount-1)/fps`，不是 duration 本身。動作在指定 cue 準確落地時，以 cue frame 為整數來源；秒轉影格使用一致的四捨五入政策。

可直接放進任何 JS 動畫來源的基本工具：

```js
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const phase = (t, start, duration) => clamp((t - start) / duration);
const smooth = x => x * x * (3 - 2 * x);
const outCubic = x => 1 - (1 - x) ** 3;
const lerp = (a, b, x) => a + (b - a) * x;
function spring(t, start, omega = 15, damping = 7) {
  const u = Math.max(0, t - start);
  return 1 - Math.exp(-damping * u) * Math.cos(omega * u);
}
// 絕對時間求值；可直接跳到任何影格，無須播放前幀。
function heroPosition(t) {
  const anticipate = smooth(phase(t, 0, .16));
  const travel = outCubic(phase(t, .16, .64));
  return {x: 100 - 14 * anticipate + 514 * travel,
          y: 260 - 90 * Math.sin(Math.PI * travel)};
}
```

Timing 控制事件何時發生，Spacing 控制影格之間的距離。相同總時間的線性與 outCubic 位移有不同重量。預備動作讓觀眾預測方向；overshoot、follow-through 與 secondary motion 用來呈現慣性，不必每個元素都彈跳。

多元素錯峰：`local=t-index*0.055`，仍從絕對時間求值。控制總展開時間，元素多時不要讓最後項目來不及停留。動畫弧線可用 quadratic／cubic Bézier；速度要等距時先建立弧長查找表，使用常見曲線套件或原生 path 量測，不必自己建立大框架。

連續性檢查轉場前後的位置、速度、方向、光源與視線。短片若從圓形擴張遮罩切下一場景，可讓下一場主體沿同方向出現；連續性不等於每一場都長得相同。依目的留節奏停頓，避免為避免靜止而持續抖動。

Random／Noise 使用固定種子；粒子若需 simulation，固定 timestep 並從初始狀態重播或快取 checkpoint，不能以實際渲染耗時當 dt。
