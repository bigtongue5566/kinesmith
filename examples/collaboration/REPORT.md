# 雙向影音協作驗收

已透過真實 Opusmith 專案與實際 Plugin CLI 執行三種模式，數據見 validation.json。

Music-first：從《Seams of Dawn》v003 擷取第一個歌詞段六秒，使用真實 master（含合成人聲），保留原 score、授權 receipt、來源 SHA256 及剪輯位置。字幕是 score-note，沒有音素時間。

Visual-first：先產生兩個三秒場景的實際交接需求，再由當前 Agent 撰寫可編輯 compose.py，透過本機真正 Opusmith v0.2.0 合成新配樂、MIDI、stems、版本與報告，回傳並同步到六秒畫面。

Joint：建立只改畫面的需求，用 native revise 修改第二場景 accent，重渲染；音樂 master、第一場景設定與原始 HTML SHA256 保持不變。

影片為 640×360、24 FPS 的功能驗收片段；每段皆提供全片解碼、Contact Sheet 與客觀 QA。未宣稱已完成主觀聆聽或專業藝術品質審定，也未以這次本機工具流程冒充兩平台模型自主委派驗收。
