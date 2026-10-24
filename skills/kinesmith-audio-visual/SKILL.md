---
name: kinesmith-audio-visual
description: Synchronize motion graphics to ordinary audio, Opusmith scores, lyrics or vocals; create music-first, visual-first and jointly revised audio-visual projects without modifying the other project's sources.
---

# 音畫協作

一般音訊不需 Opusmith。使用傳統訊號分析的 Energy、Onset、Frequency 及估計節拍，保留分析參數與來源 checksum；tempo estimator 結果標為估計，不能冒充樂譜拍點。讀 [audio-visual knowledge](../kinesmith/references/audio-visual.md)。

Opusmith 整合前讀 [Adapter 文件](../../docs/opusmith.md)，透過 Adapter 偵測 format、schema、可用檔案與功能。不要直接依外部 Plugin 內部 Python class 存取，不要綁死 package version；未知格式回報可用能力與降級原因。不能默默猜未知欄位或寫回原始音樂專案。

- Music-First：匯入實際 Opusmith 專案或公開 interchange，保存 score events、實際 master 長度、tempo map、offset 及來源關聯，再創作場景。
- Visual-First：從 Kinesmith 場景輸出版本化 AV contract，列出場景、情緒、cue、配樂需求及允許修改範圍；主要 Agent 使用已安裝 Opusmith Skills 接手，或交付可攜 JSON，不能假設通用 Plugin-to-Plugin API。
- Joint Creation：讀回新版本，確認 parent/source checksums 與 revision request；只改獲授權的音樂或動畫範圍。原音樂資料不覆寫，保存雙方新版本關聯。

音樂 beat 以 tempo map 積分為秒數，再套明確 offset，再映射影格；meter 的拍數與 beat unit 不可混淆。主體音符結束與音檔尾音結束各自保存。不要為湊拍而裁掉使用者要求的片長。

歌詞依可取得 line／syllable／note／phoneme 時間製作 Lyric Video 或 Karaoke。USTX 音符是名義時間，不代表實際唱出的音素邊界；拼音分解或能量分析不是 forced alignment。缺精確資料可以依音符同步，但標為 `nominal`／`estimated`。聲庫、角色圖像與人聲渲染器分開查商用條款，渲染成功不代表有權商用。
