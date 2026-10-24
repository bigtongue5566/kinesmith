# 原生來源、影格時間軸與可重現渲染

Kinesmith 不定義動畫物件。Agent 可自由撰寫 Canvas、Rough.js、p5.js、Three.js、Manim Scene 與 Blender Python；共用層只管理時間、來源、影格、圖層與交付。

## 安裝與執行

```powershell
uv sync --python 3.11 --all-extras --locked
uv run --all-extras scripts/bootstrap_web.py --chromium
uv run --all-extras kinesmith doctor
uv run --all-extras kinesmith init my-film
uv run --all-extras kinesmith render my-film --format webm
uv run --all-extras kinesmith qa my-film/renders/v1.webm --output-dir my-film/renders/qa --project my-film
```

Python 3.11 是本次六引擎一起驗證的環境；Blender bpy wheel 有 Python／作業系統限制。只有瀏覽器引擎時可省略 `--all-extras`。不要在需要原生引擎時執行不帶 extras 的 `uv sync`；uv 會移除未選取的選用依賴。網路只用於取得開源依賴；bootstrap 完成後加 `--offline` 可離線創作。`KINESMITH_CHROMIUM` 可指定現有 Chromium 的完整可執行路徑。

## 作品格式

`schemas/project-1.schema.json` 是實際驗證的格式。`fps` 為字串，如 `24` 或 `30000/1001`。`duration_frames`、`start_frame` 都是整數。場景覆蓋半開區間 `[start_frame, start_frame + duration_frames)`；在影格 n 取樣的時間為 `n / fps`，不使用實時錄影或等待網頁播放。

每個場景指定 `id`、`engine`、`source`、`start_frame`、`duration_frames`。可加 `layer`、`opacity`、`transition_in`、`transition_out`、`params` 及 `dependencies`。場景重疊時依 layer、檔案列出順序依次 alpha 合成。fade、wipe-left、wipe-right 作用在原生來源的 RGBA 影格，轉場長度用整數影格表示。沒有場景覆蓋的時間使用深藍底色。

專案的 `dependencies` 對所有場景有效；場景的 `dependencies` 只影響該場景。把來源引用的外部圖片、字型、import helper、shader 及其他檔案全部列入，才能正確重建快取。來源／素材必須在作品目錄內，拒絕 `../` 或指向外部的 symlink。原生來源是可執行程式碼，請像一般程式專案一樣審閱。

## Browser 原生介面

HTML 內提供 `<canvas id="stage">` 與 `window.renderFrame(frame, ctx)`；函式可回傳 Promise。`window.kinesmithReady` 可設定為引擎初始化的 Promise。每個影格完成後，Canvas 必須精確等於作品 width／height。渲染器等待字型載入，直接讀 Canvas 的 PNG，不擷取作業系統視窗。

`ctx` 含 `frame`、`globalFrame`、`time`（場景秒）、`duration`、`duration_frames`、`fps`、`fps_number`、`width`、`height`、`seed`、`params`、`features`、`interchange`。這是時間與輸入資料，不限制各引擎的繪圖能力。需要精確事件時，以 globalFrame 和 contract 的 start_frame／end_frame 比較。p5 使用 instance mode、`noLoop()`，每次由 renderFrame 呼叫 `redraw()`；randomSeed／noiseSeed 以作品 seed 控制。粒子模擬需從固定 seed 逐影格積分或直接從時間解析取樣，不能從 wall clock 取速度。

網頁可引用同專案內素材及 `/vendor/rough/rough.js`、`/vendor/p5/p5.min.js`、`/vendor/three/three.module.min.js`。Playwright 透過 route.fulfill 直接供應虛擬 http://kinesmith.local 來源，完全不啟動伺服器或網路 socket，拒絕外部 CDN。Three Renderer 必須能取出畫布（如 `preserveDrawingBuffer: true`）。每次影格運算預設最多 30 秒，可用 KINESMITH_FRAME_TIMEOUT 調整；原生迴圈有錯時會停止並指出影格。不同 GPU／字型 rasterizer 可能有不同像素；需保留工具版本並在相同環境比較，不能承諾跨 GPU bit-identical。

## Manim 與 Blender

Manim 預設類別 `MotionScene`，可用 `class_name` 指定。原生 Scene 用 `KINESMITH_CONTEXT` 環境變數指向的 JSON 讀取設定；Scene 的總 `run_time` 必須精確等於 `duration_frames / fps`。渲染器使用 Cairo 的逐 PNG 輸出，檢查影格數而非強制補／裁錯誤長度。要用數學公式時自行安裝合法的 LaTeX 發行版；內附範例不需要 LaTeX。

Blender 來源提供 `build_scene(ctx)`；可完整使用 bpy、Geometry Nodes、材質節點、燈光、攝影機和原生 keyframes。worker 設定解析度、有理數 fps／fps_base，再以 `scene.frame_set(n)` 逐影格渲染，另外保存完整 `editable.blend`。Blender 與 Manim 各自獨立 subprocess，避免全域狀態互相污染；預設場景逾時 3600 秒，可用 KINESMITH_NATIVE_TIMEOUT 調整。大型作品可自行使用正式 Blender CLI 產出 PNG Sequence，再以 image／video 來源整合。

## 聲音、格式與局部修訂

`audio: {source, offset_seconds, gain}` 用作品相對路徑。正 offset 延後音訊；負 offset 裁去音訊開頭，最後補靜音／裁至明確的影片長度。不會用 `-shortest` 意外刪掉畫面。音樂主體結束不代表效果尾音結束，應以 Adapter 的實測 master 長度決定時間軸，或明確記錄刻意裁切的創作決定。

WebM 使用 VP9／Opus；MP4 使用實際 FFmpeg 的 x264／AAC；GIF 使用 palettegen／paletteuse；`--format png` 輸出 PNG Sequence。缺少編碼器時會回報 FFmpeg 錯誤。不同 FFmpeg build、軟體再散布與編碼器專利義務見 `docs/licenses.md`。

```powershell
uv run --all-extras kinesmith revise my-film --scene canvas --prompt "只改主場景強調色" --params '{"accent":"#ff775a"}'
uv run --all-extras kinesmith render my-film --scene canvas
```

`revise` 保存之前的 project.json、來源、Prompt 和雜湊。每次原生渲染也保存精確來源與宣告依賴；由 Agent 直接編輯後應記錄修訂，不把快取當版本控制。快取包含來源、參數、宣告素材、共享資料、渲染器、工具版本和 vendor 檔案雜湊；重用前核對全部影格。其他場景可保留逐像素一致的快取。不要把所有素材放入全域 dependencies 後期待局部快取。

成品旁保存實際工具版本、場景來源、SHA256、編碼日誌與繁中 Motion Report。渲染完成前會再次核對來源、宣告依賴及工具雜湊；中途有變更就拒絕發布不一致的快取。請執行 `qa` 並檢查 Contact Sheet、文字安全區、轉場前後影格及音畫；機器解碼通過不代表創作或主觀視覺品質通過。
