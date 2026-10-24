---
name: kinesmith-render
description: Render, composite, inspect and verify Kinesmith animation projects with deterministic frames and FFmpeg. Use for final video, contact sheets, multi-engine composition or rendering failures.
---

# 渲染與品質

讀作品 project.json 及原生來源，先執行 `uv run --all-extras --project <plugin-root> kinesmith validate <project.json>`，使用 CLI `--help` 確認渲染選項。固定解析度、FPS、種子、場景輸入與工具版本。用每影格的明確時間驅動瀏覽器／原生引擎，不使用即時錄影。

執行 `uv run --all-extras --project <plugin-root> kinesmith render <project.json>`。保留 PNG Sequence、場景快取與 render manifest，FFmpeg 合成場景、圖層及轉場。MP4 的可用性依實際 encoder 和授權；WebM 是預設自由格式，GIF 用 palettegen/paletteuse。最終 PNG Sequence 是合成後的 RGB 影格；原生 RGBA 中間影格保留在場景快取。不要僅改副檔名。

品質流程：

1. 對最終檔完整解碼，確認真正的 format、codec、duration、FPS、width/height、frame count、音軌長度。
2. 產生代表性影格與 Contact Sheet，開圖檢查構圖、字體、裁切、轉場前後與最後影格。
3. 檢查黑畫面、重複影格、亮度突變的候選區段；這些是 heuristic flags，可能是刻意停格／閃爍，必須看時間與上下文。
4. 音畫 cue 比較原始秒數、偏移、量化後影格，報告最多半影格的四捨五入誤差；尾音獨立於 score 主體長度處理。
5. 重渲染短區段並比較 frame hashes，確認可重現；修改單一場景時驗證其餘來源雜湊與快取未變。

自動檢查不能證明文字無裁切、所有轉場舒服或音樂好聽。人工檢視未執行的項目在繁體中文 Motion Report 中寫「未驗證」。授權依 [license guidance](../kinesmith/references/licenses.md) 記錄。
