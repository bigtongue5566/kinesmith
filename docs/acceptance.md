# Kinesmith 實作與驗收紀錄

日期：2026-10-25，Asia/Taipei。此文件區分實際渲染、程式測試、原生 Plugin 安裝、畫面抽查與尚未驗證的項目。

## 交付內容

- 雙平台 Plugin manifests、可安裝本地 marketplace、5 個共用 Skills、8 份按需載入的知識參考、5 個原生專業角色。
- Canvas、Rough.js、p5.js、Three.js、Manim Community、Blender 原生可編輯來源，無統一動畫物件 API。
- 有理數 FPS／整數影格時間軸、RGBA 圖層、fade／wipe、可校驗影格快取、局部修訂、原生 .blend、WebM／MP4／GIF／PNG Sequence。
- 一般音訊的 RMS／頻帶／估計 onset；版本化 AV Contract、Opusmith v0.1.0／v0.2.0 Schema、MIDI tempo map、USTX、未知版本安全降級及明確可攜重定位。
- 三種協作模式的真實影片、原生音樂回傳、歌詞片段、來源與版本關聯、授權帳本與繁中報告。

## 十項驗收

| 需求 | 實際證據與範圍 |
|---|---|
| 六種引擎各自可播放 | outputs/engines/{canvas,rough,p5,three,manim,blender}.webm，每支 640×360、24 FPS、48 影格、2 秒、VP9；全片解碼，代表影格確實不同 |
| 多引擎合成 | outputs/orbital-craft.webm 及 .mp4，12 秒／288 影格；outputs/cross-engine-transitions.webm 實際重疊三引擎並使用 alpha fade／wipe |
| 一般音訊反應 | outputs/audio-reactive.webm，12 秒；原創 CC0 WAV 與分析 JSON 可獨立重建，無 Opusmith 依賴 |
| 真實 Opusmith 專案 | 實際讀取上游 v0.2.0 seams-of-dawn v003，1989 notes、165 lyric events，music body 約 154.838710 秒／master 158.838730 秒；完整保留效果尾音差異 |
| 三模式協作 | examples/collaboration 的 Music-First、Visual-First、Joint 各一支 6 秒影片；Visual-First 透過真正 Opusmith 產生 20 notes、3 tracks、MIDI、stems、版本快照；來源 169 檔 SHA256 不變 |
| 歌詞／人聲 | music-first/preview.webm 使用真實含人聲 master 摘錄與 9 個 score-note 歌詞事件；未把音符／線性高亮描述為精確演唱或音素對齊 |
| 版本／安全降級 | 真實 v0.1.0／v0.2.0 fixtures、Schema validation、未知格式 audio-only、安全路徑、checksum 拒絕、負 offset、分數 FPS、MIDI tempo changes、可攜搬移測試 |
| 局部修改 | outputs/local-revision 的 before／after；只改 Canvas 強調色，其他五場景 raw PNG hashes 全相同、重用快取、音樂不變；Joint 另有 72 無關影格逐一相同證據 |
| 雙平台安裝／Skills／角色 | Codex 0.164.0-alpha.11.1、Claude Code 2.1.310：16 項原生命令成功，各發現 Skills(5)、角色(5)，兩個安裝副本各自真正渲染 48 影格 Canvas；詳細見 platform-validation.md／json |
| 免費工具與授權 | 零額外模型／生成 API 呼叫；開源依賴與 Web 標準。保存 web package 原 LICENSE、固定來源 archives、FFmpeg 真實 build／GPL 資訊、音源專屬條款與素材紀錄 |

機器可讀的完整結果：`outputs/render-validation.json`、`outputs/platform-validation.json`、`examples/collaboration/validation.json`、`examples/collaboration/portability.json`。版本、來源 SHA256 與編碼日誌在影片旁的 render.json／ffmpeg.log。發行包內另外保存 `docs/render-validation.json`、`docs/platform-validation.json`，大型影片與完整 PNG 快取不塞進安裝包。

## 實際視覺抽查

已直接檢視六引擎 Gallery Contact Sheet、Manim 原生逐步繪製 Contact Sheet、跨引擎轉場 Contact Sheet，及三種 Opusmith 協作影片的 Contact Sheet。字形、主要標題、Blender 原生文字和主體在抽查影格內完整可見；未看到非預期全黑畫面。Manim 的細線逐步繪製與小點移動，被低解析度定格 heuristic 標示為 possible_freeze；逐影格抽查可見曲線和標記持續改變，因此保留該候選與檢視解釋，不刪掉原始量測。

轉場短片故意讓兩個完整畫面交疊，展示 alpha／wipe 能力；不是經人工藝術指導的正式品牌片剪輯。2 秒引擎片段是能力研究長度，閱讀停留與正式敘事需按作品重新設計。歌詞片段末尾的「Listen to the space.」是有意留白，不是字幕遺漏。

## 測試與可重現性

本次最終自動測試結果為 **62 passed、7 skipped**；Ruff 全部通過。`uv run --all-extras pytest -q` 執行自動測試，包括實際 Chromium 時間／亂數重現性、無限迴圈逾時與清理、畫布尺寸錯誤，FFmpeg 音訊正負偏移實測（誤差小於 15ms）、完全超出時間軸的靜音、快取損壞／缺漏、共用來源局部修訂、PNG 序列縮短及渲染中途來源變更拒絕。

另有 7 個昂貴的 opt-in 重複渲染測試，預設不啟動；用 `KINESMITH_RUN_RENDER_TESTS=1` 啟動。這 7 個 pytest case 在一般測試紀錄顯示 skipped，不能說全套 pytest 皆已執行；相應六引擎、跨引擎與局部修改能力已由 `scripts/verify_rendering.py` 真正渲染並獨立驗收。`scripts/verify_collaboration.py` 執行實際 Opusmith 工作流。`scripts/validate_plugins.py --native --render-smoke` 驗證兩平台安裝副本。

本機 Python 3.11.13、Playwright 1.64.1／Chromium 156.0.8078.4、Manim 0.19.2、bpy 4.2.0、FFmpeg 7.1；完整依賴由 uv.lock 固定。Browser 使用離線 route.fulfill 供應本地素材與固定 seed；Blender 使用 CPU Cycles、4 threads；每個原生引擎逐影格輸出，非螢幕錄製。原生影格、editable.blend 與消費來源快照保存在作品 .render-cache，交付的獨立 .blend 另存 outputs/editable-orbital.blend。最後另比對雙平台安裝副本的全部核心 .py，與交付原始碼一致；Plugin ZIP 每個檔案皆符合 source-manifest SHA256，三個交付 ZIP 完整性檢查通過。

## 新增完整介紹作品

2026-10-25 新增「Kinesmith：把想法鍛造成動態」及「Codex 是什麼？」兩部作品，各 48 秒、1920×1080、30fps、1440 個真實渲染影格，配上不同的原創電子配樂。兩片完整解碼、文字邊界、AAC 量測與 9 個 Cue 波形對齊通過；另有實際代表／切點連續影格視覺抽查、Kinesmith 單幕修訂與其餘七幕逐影格雜湊保留證據。詳細數據及未測項目見 [介紹作品 Motion Report](introduction-films.md) 與 `introduction-validation.json`。這是新增作品驗證，未以此宣稱重新驗證全部平台或全部六種引擎。

2026-10-25 另新增第三部 Opusmith 介紹片：同為 48 秒、1080p／30fps，真正使用 Opusmith v0.2.0 製作七軌配樂，讀取原生 Score／Stems。全片解碼、九個 Cue 對齊、六軌局部修訂保留、搬移後離線重建母帶及七軌、14 個可攜來源校驗均通過；視覺抽查與未測項目詳見 [本片 Motion Report](opusmith-introduction.md)。

## 實際限制

- 尚未在 Codex／Claude 登入模型回合中實際測試 Skills 遵循與原生角色委派；已驗證的是原生可發現性、安裝及安裝後真實渲染。創作使用目前 Agent，沒有額外呼叫其他模型。
- 沒有宣稱已主觀聆聽配樂／演唱、完成全片連續觀看或逐音素歌唱對齊；技術同步與代表影格檢查不能取代這些項目。
- 初版六引擎驗收環境是 Windows x64、640×360、24 FPS；分數 FPS 另有影片測試。新增介紹作品已實測 Windows x64、1920×1080、30fps；4K、長片、大量圖層、Linux／macOS、各 GPU 未逐一實機驗證。可用格式並非所有環境一定有相同編碼器。
- 像素級重現性限相同工具／字型／渲染環境；未承諾跨 GPU／作業系統位元相同。更新 Opusmith 時先偵測能力、驗證新 Schema，再新增 profile；未知版本維持明確降級。
- 所有外部字型、聲庫、角色、取樣與新增素材都要保留個別授權紀錄；本範例的特定條款查核不能推廣為所有素材皆可商用。
