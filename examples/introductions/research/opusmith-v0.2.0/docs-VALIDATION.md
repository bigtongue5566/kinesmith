# 驗收與測試邊界

所有 Python 以 uv 執行，依賴由 `uv.lock` 鎖定。
v0.2 實體聲庫驗收模式：**76 passed**；Ruff 與兩個 Skill 的 quick_validate 均通過。
預設無聲庫環境為 75 passed、1 skipped；略過的整合測試不視為歌聲渲染成功。
`uv run pytest -q` 驗證音樂／工程不變量；`uv run ruff check .` 靜態檢查。
`uv run scripts/doctor.py` 實際 MIDI + WAV/MP3 生產；不使用 mock audio。

測試包含：每種 synth engine 非靜音與可重現、實際 A4 基頻、MIDI 音符／時間／表情回讀、
不支援的 tempo 語意拒絕、局部修改保留其餘欄位與 stem hash、同起點 stems 重建 premaster、
PCM clipping／估計 true peak／NaN、失敗渲染不更新目前版本、提示詞逐字與歷史竄改偵測、
真實 sample pitch/time processing、Openverse cache／429、NC/ND/未知授權拒絕、SSRF／redirect／
大小／偽裝 HTML 拒絕、授權或 hash 不符阻止發行、原生角色 adapter 與無覆寫 installer。

HTTP 單元測試使用 mock transport 來測試錯誤條件，不聲稱它們證明真實網路可用。
另外已實際呼叫 Openverse、打開 Freesound 原頁及 CC0 deed、下載 HQ MP3 預覽、
裁切／降調／時間伸縮後渲染 rain-garden，將來源與品質限制保存在作品帳本。
五首純合成作品以 `uv run --offline` 完成，無網路資產依賴。

每首作品的 `QUALITY_REPORT.md` 區分工程正確性、需求符合度、訊號技術品質與主觀音樂品質。
`COMPOSITION_REPORT.md` 的段落、樂器、音符統計與 DSP 直接讀取本次 Score；
風格、調性與創作理念明確標示為創作者標註，不冒充自動辨識的結論。
本環境未進行主觀聽覺評估，無「已聽起來專業／無瑕」等宣稱。

原生安裝驗證結果另記 `platform-smoke.json`；沒有呼叫第二個生成模型做驗收。
實測 CLI：Codex 0.164.0-alpha.11.1、Claude Code 2.1.310；兩平台均實際安裝並列為 enabled。
此外分別以兩邊安裝快取中的實際副本離線執行 Doctor，兩者均完成真實 MIDI/WAV/MP3 生產；
安裝副本的 synth 來源與發行包一致，Codex 角色 installer 也已從安裝副本執行成功。
v0.1 六首作品通過實際 MIDI 回讀、PCM／峰值與 stems 重建檢查；
混合曲兩小節修改後八條無關 Stems 的 SHA-256 相同。
Ambient 複製至不同目錄後，使用隨附 runtime 與 lock 離線重渲染，Master WAV 與五條 Stems
SHA-256 完全相同，見 `portable-smoke.json`。這是檔案／runtime 可移植性，不冒充模型現場測試。
已登入 Codex 與 Claude 的自然語言自主創作與委派現場驗收，依 `COMPATIBILITY.md` 的案例補做；
不把 schema／安裝／單元測試冒充所有產品能力已獲證明。

`scripts/validate_examples.py` 重新讀取實際 MIDI/PCM、版本 hash、素材與歷史，產生
`examples-validation.json` 與作品索引。其結果是技術證據，不是美學評分。

## v0.2 人聲實測

以官方 OpenUtau 0.1.576 的實際 Core、原生 phonemizers、WORLDLINE 及 ONNX CPU 推理驗證。
橋接以 .NET SDK 10.0.402 建置，不自行重寫合成器或用 mock 歌聲交差。
波音リツ主唱／和聲完成《光の縫い目》：158.84 秒、9 軌、1989 音符（165 個人聲音符）。
當前版本為 v003；Master 約 −14.35 LUFS、估計 true peak −1.00 dBFS，無削波。
綺萱完成中文八音 DiffSinger 實測；AI 合成、绮萱、DiffSinger 署名皆保留。
綺萱範例明確為非商業技術評估，不宣稱聲碼器完整商業鏈已獲核准。

測試另涵蓋 YAML 1.2 與原生未知欄位／註解、MIDI 歌詞往返、局部音符／顫音修改、
凍結乾聲對齊／重取樣、授權旗標型別、未追蹤伴奏拒絕、壓縮檔路徑、
實際 OpenUtau 渲染、USTX／乾聲／收據附件竄改偵測。
`OPUSMITH_VOCAL_SETTINGS=<ritsu-kire-settings.json>` 啟用真正聲庫整合測試；
該測試實際渲染修訂前後的不同母音，不是 monkeypatch 音訊輸出。

整軌 WORLDLINE 重跑會改變未修改歌句波形，故本版 `render_revision` 只替換指定歌句的
新歌聲及短前後文，保留其他乾聲樣本。範例 v002 留作這個問題的實測歷史；v003 採保留乾聲方案。
v003 修改範圍外乾聲逐樣本相同，八條無關 Stems SHA256 相同，原生其餘音符與曲線也相同。
整首搬移後，以隨附 runtime 離線重新混音，Master WAV 與九條 Stems SHA256 完全相同。
詳 [vocal-validation.json](vocal-validation.json)、[vocal-portable-smoke.json](vocal-portable-smoke.json)。

Windows x64 / CPU 已測；未完成 GPU、其他作業系統、所有聲庫／語言及主觀聽覺驗收。
兩平台實際 CLI 安裝及安裝副本可載入人聲模組／USTX；未冒充已登入 Claude 模型的現場創作或委派。
