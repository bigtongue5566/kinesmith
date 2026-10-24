# 引擎選擇與原生來源

|引擎|適合|保持的原生能力|
|---|---|---|
|Canvas API|幾何、品牌、Typography、資訊圖|原生 path、text、clip、compositing、ImageData|
|Rough.js|Sketch、Whiteboard、手繪線條|原生 rough.canvas／rough.svg、seed、options|
|p5.js|Noise、流場、粒子、Creative Coding|原生 p5 sketch、noise、drawing API|
|Three.js|Realtime 3D、Shader、程序幾何|Scene、Camera、Geometry、Material、Shader、Instancing|
|Manim Community|數學、技術、科學解說|Scene、Mobject、Transform、ValueTracker、原生 animation|
|Blender|電影式 3D、材質、燈光、Geometry Nodes|.blend、bpy、Nodes、Cycles／Eevee、原生 keyframes|

讀 `examples/` 中相應引擎來源及專案 schema，不要另發明限制六種原生 API 的統一 animation object。作品層共用的只有時間、場景、圖層、轉場、輸出設定與來源檔。

瀏覽器來源是一般 HTML，包含 `canvas#stage` 並定義 `window.renderFrame(frame, ctx)`；可為 async。初始化可放 `window.kinesmithReady` Promise。`ctx` 提供 `frame,time,duration,globalFrame,width,height,seed,params,features,interchange`。原生程式自己管理物件，helper 只在明確影格呼叫並截取 canvas。以下 HTML 可作 Canvas 最小來源，換掉 draw 程式就能自由創作：

```html
<!doctype html><canvas id="stage"></canvas><script>
const canvas=document.querySelector('#stage'), c=canvas.getContext('2d');
window.renderFrame=(frame,ctx)=>{
  if(canvas.width!==ctx.width||canvas.height!==ctx.height){
    canvas.width=ctx.width;canvas.height=ctx.height;
  }
  c.fillStyle='#f3eee5';c.fillRect(0,0,ctx.width,ctx.height);
  c.fillStyle='#007f73';c.beginPath();
  c.arc(ctx.width/2+Math.sin(ctx.time*2)*120,ctx.height/2,70,0,Math.PI*2);c.fill();
};
</script>
```

Rough.js 載入 `/vendor/rough/rough.js`，p5.js `/vendor/p5/p5.min.js`，Three.js 以 module import `/vendor/three/three.module.min.js`。來源使用虛擬 `http://kinesmith.local` origin，由 Playwright route.fulfill 直接提供本機檔案，不開 socket／本機 server，拒絕其他 origin 的網路請求。Manim 原生 class 預設 `MotionScene`，透過 `KINESMITH_CONTEXT` 指向 JSON 取得作品參數。Blender Python 定義 `build_scene(ctx)`，worker 先建原生場景，再依明確 frame_set 求值並保存 .blend。

瀏覽器初始化依賴在本機 vendor 資產載入，正式渲染不依賴 CDN。字型與貼圖等待載入完成後再擷取 frame；網路內容另行下載並核對授權與 checksum。Three.js 用 software WebGL 渲染可重現驗收片，但正式高品質影片可選硬體或 Blender；記錄實際 device。

Manim 保留原生 Scene；使用 Cairo 不需付費 renderer。MathTex 需要 TeX 工具鏈；沒有 TeX 時用 Text 或原生幾何解說，清楚說明限制。聲稱數學公式渲染成功之前需要真正渲染而非只 import。

可直接以 `uv run --all-extras manim -ql example.py MotionScene` 執行的技術解說：

```python
from manim import Scene, Axes, Dot, ValueTracker, always_redraw, Create, FadeIn, linear

class MotionScene(Scene):
    def construct(self):
        axes = Axes(x_range=[0, 4, 1], y_range=[0, 4, 1], x_length=8, y_length=4)
        graph = axes.plot(lambda x: x*x/4, x_range=[0, 4], color='#64d9c5')
        tracker = ValueTracker(0)
        dot = always_redraw(lambda: Dot(axes.c2p(tracker.get_value(), tracker.get_value()**2/4)))
        self.play(Create(axes), Create(graph), run_time=.8)
        self.play(FadeIn(dot), run_time=.2)
        self.play(tracker.animate.set_value(4), run_time=2, rate_func=linear)
        self.wait(.5)
```

與 Kinesmith 合成時把總片長設為 scene frame count，精確 FPS 由 project 設定傳入。此例用幾何與 graph，不依賴 TeX。

Blender headless 用明確 frame range、fps、resolution 及 output path。啟動 Python 或開 .blend 都是執行來源程式，使用者專案應先閱讀；不默默安裝任意外部 addons。Blender 缺失不能用 Three.js 輸出代替其驗收。

完整原生程式與執行命令以 `examples/`、CLI `--help` 及 [安裝文件](../../../docs/installation.md) 為準。
