# 兩部完整介紹短片

本目錄提供 Kinesmith 專案介紹與「Codex 是什麼？」兩部 48 秒介紹作品。每片 1920×1080、30fps、8 個可獨立修改的章節、各自的原創電子配樂；保留程式、字型、MIDI、音符事件、Cue Sheet、字幕、分鏡與來源說明。

```powershell
# 由 repository 根目錄執行；已安裝依賴可使用 --no-sync --offline
uv run --all-extras examples/introductions/verify.py --preflight
uv run --all-extras examples/introductions/verify.py --render
```

也可直接渲染各自的作品：

```powershell
uv run --all-extras kinesmith render examples/introductions/project-kinesmith.json --format mp4 --output outputs/introductions/kinesmith-introduction.mp4
uv run --all-extras kinesmith render examples/introductions/project-codex.json --format mp4 --output outputs/introductions/codex-explained.mp4
```

成品與報告在 `outputs/introductions/`。`verify.py` 會實際解碼每一影格、檢查尺寸／FPS／時長、測量配樂響度與峰值、核對共用 Cue、產生 Contact Sheet；主觀視覺檢查另外記錄，不將產生縮圖等同已經看過。沒有播放／試聽能力時不宣稱全片觀賞或音色品質通過。

目前 Kinesmith 片為修訂 2，已修正 30–36 秒字幕與圓環相交；Codex 片為修訂 1。最終作品直接用現有 `project-*.json` 渲染即可。要只更新其中一片並保留另一片的檢查紀錄，可執行 `uv run --all-extras examples/introductions/verify.py --render --only kinesmith`。

修改 `project-*.json` 的指定章節參數，或用 `kinesmith revise ... --scene ... --source ... --prompt ...` 為該場景分叉來源，再重新渲染。`scenes/drawing.js` 是這兩部作品的 Canvas 繪圖便利函式；不是跨引擎動畫物件 API。各原生 HTML 可直接編輯。

`prepare.py` 保存本次作者的初稿時間軸產生方式，會寫回兩個 project JSON、Cue Sheet 與 SRT；它不是重現最終影片的必要步驟。修改後不要不加分辨地重跑，否則會回到尚未做視覺修訂的初稿。`compose.py` 可用 `uv run --all-extras examples/introductions/compose.py` 重建配樂；日常修改畫面只需 `render`，不必重新作曲。

內容、授權與界限見 [sources.md](sources.md)、[Kinesmith 分鏡](brief-kinesmith.md)、[Codex 分鏡](brief-codex.md)。本片是繁體中文動態字排解說，未製作人聲旁白。
