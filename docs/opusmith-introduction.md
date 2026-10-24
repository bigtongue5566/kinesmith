# Opusmith 專案介紹｜Motion Report

2026-10-25 製作、真正渲染與驗證。原始需求：「再一個介紹opusmith這個專案」。

## 成品與內容

《Opusmith：把想法，寫成音樂。》為 48.000 秒、1920×1080、30/1 FPS、1440 影格的 MP4／H.264，AAC 48kHz 立體聲。八幕各六秒，以原生 Canvas、固定整數影格、離線本地字型與資料渲染。沒有外部生成模型、旁白或歌聲。

炭黑、暖紙白、琥珀金與朱紅搭配唱片、音符、音色與分軌。Piano Roll 取自真實 Score 第 32–48 拍；七軌能量取自實際 Stems 每 50ms 的 RMS，顯示以非線性比例增強辨識，不冒稱音量表 dB。合成波形、旋鈕與 USTX 編輯畫面為有標記的概念示意。上游沒有隨 repository 提供品牌圖示，直接排印名稱，沒有杜撰官方 logo。

產品功能依最新穩定 v0.2.0 及 commit `328e630f33af4b8b0ebe178895d1f87120532875` 的實際 README、人聲文件、Release 與驗收紀錄查核。日期、原始文件與 SHA256 在研究資料。人聲章節沒有把上游實測當成本片重新合成歌聲的證據。

## 音樂、修訂與協作

真正使用 Opusmith v0.2.0 的 Score、Patch、原生振盪器／噪聲、Pedalboard、版本發布及分軌工具，創作 160 BPM、D minor 的原創旋律碎拍。七軌為 FM 章節落點、Pluck、Pad、Additive Bass、Kick、Snare、Hi-hat，沒有取樣或聲庫。

`music-opusmith/` 保存 v001／v002、Score、MIDI、Python、音色／效果參數、Stems、WAV／MP3、需求／修訂歷史、報告、runtime 與 uv.lock。將第 96–100 拍起音的 Pluck 動機降八度後，其他六條 Stems 的 SHA256 相同，證據在 `LOCAL_REVISION.json`；效果尾音自然延續。

Kinesmith Adapter 真正讀取 v002，驗證 Schema／檔案，產生可攜 `opusmith-music.av.json`，偵測到 Score、Sections、Tempo、Meter、Notes、Velocity、MIDI Reference、Stems、Master Audio。音樂主體 46.5 秒、尾音 1.5 秒，共 48 秒；片尾和弦與主視覺在第 1350 格／45 秒落定。

## 客觀檢查

- MP4 全片音畫解碼成功，尺寸、1440 影格、30fps、48 秒符合設定。
- 1440 個正式影格的文字邊界診斷均無項目；16 張初檢影格亦無越界。
- 八幕以 90→177→90 的非單向取樣確認相同影格像素一致。
- 九個 Cue 為 0、6、12、18、24、30、36、42、45 秒；事件與指定影格相符，MP4 解碼音訊與原 WAV 波形比對均為 0 樣本偏移，容許值一影格。
- WAV、AAC 解碼及獨立 MP3 解碼均為 2,304,000 個 48kHz 立體聲樣本，即 48 秒；母帶無削波，MP4 真峰值低於 0dBTP。

| 對象 | Integrated LUFS | True Peak dBTP |
|---|---:|---:|
| WAV，FFmpeg 實測 | −22.70 | −1.50 |
| MP4 的 AAC，解碼後實測 | −22.75 | −1.46 |

採上游量測後固定增益母帶，為保留峰值，未達 Score 設定的 −16 LUFS 目標；沒有將目標當成量測，也沒有第二次正規化。可由 Stems／Score 重新混音。響度與同步不證明主觀品質。

畫面 heuristic 沒有全黑區間；刻意的章節硬切列為亮度差候選，閱讀停留、細微旋轉及片尾定格列為 possible_freeze。原始旗標保留，不當成未跳格或沒有閃爍的完整證明。

## 視覺抽查與重現

已直接檢視 16 張初檢 Contact Sheet、關鍵畫面的 1080p 原圖、12 張成片 Contact Sheet、七個切點前／當下／後的 21 張影格，以及最後完整影格。抽查中的繁體中文字型完整、沒有文字裁切或主體相互遮擋，片尾字排與進度條完整落定。

另真正製作三秒動態研究片，抽取 0、0.2、0.5、1、1.5、2、2.97 秒，檢視需求紙條、四個決定錯峰入場及定格的完整動作。這是時間影格抽查，沒有宣稱連續播放看完全片或已主觀試聽。

音樂搬移後從自帶 runtime／uv.lock 建立獨立 uv 環境，完全離線重建 v002 Score；母帶與七條 Stems SHA256 一致。另在新目錄依 relative_path 搬移 AV Contract 的 14 個來源／音訊，重新定位與校驗通過，見 `reproduction.json`。前兩片影片及原配樂 SHA256 均未變，見 `previous-films.json`。

新增程式 Ruff 通過；Plugin 路徑、渲染／局部修訂及攜帶資料相關既有測試為 8 passed。本片未重新驗證六引擎、雙平台安裝或 OpenUtau 人聲。環境為 Windows x64；跨 OS／GPU／依賴版本的位元一致性未驗證。

## 授權與交付

原創動畫與程式 MIT，音樂、音符與 MIDI CC0-1.0。Noto Sans TC 原字型 OFL-1.1、Opusmith runtime／研究文件 MIT，原始聲明隨附。實際音樂環境套件與授權 metadata 在 `music-opusmith/SOFTWARE.json`；Pedalboard、其他 DSP、FFmpeg、Chromium 依各自條款，不重包其二進位。沒有聲庫、聲碼器權重、角色圖片或外部素材。

可編輯 ZIP 保存動畫來源、字型、時間軸、Cue、字幕、兩版配樂與分軌、校驗、研究文件及驗證證據。逐檔 manifest、ZIP CRC、解壓後 SHA256 均核對；公開附件另有 SHA256SUMS。原始 PNG 快取與 venv 不隨包散布。
