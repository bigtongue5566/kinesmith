# v0.2 人聲製作

本版新增可工作的 OpenUtau 橋接、USTX 往返編輯、真實歌聲渲染、乾聲／混音及授權收據。
作詞作曲仍由目前的 Codex 或 Claude Code 進行。沒有新 LLM、文字整曲服務或自訂 Agent Runtime。

| 能力 | 狀態 |
|---|---|
| 波音リツ傳統 UTAU / WORLDLINE-R | 真實離線渲染，免費商用條款已核對 |
| 綺萱 / OpenVPI DiffSinger | 真實中文歌聲；本版僅供非商業技術評估 |
| USTX 歌詞、音符、音高、顫音、音素表情 | 保留原生格式及未知欄位；可開回 OpenUtau |
| 指定歌句修訂 | 音符結構與未修改 Stems hash 比較，保留舊版本 |
| Codex / Claude 交換 | 相同檔案／runtime；凍結乾聲的混音重建不需另裝聲庫 |
| 其他 OS、GPU、所有聲庫／語言 | 尚未實機驗證；不可由本範例推論皆可用 |
| 主觀聽覺評估、咬字自然度 | 未進行，技術量測不能代替 |

## 安裝

先完成 README 的 Plugin／uv 安裝，再安裝官方 .NET SDK 10。
`dotnet --list-sdks` 應有 10.x。只有 .NET runtime 不足以建置橋接。

```powershell
uv run scripts/setup_vocals.py --bank ritsu-kire --dotnet "C:/.../dotnet.exe"
```

腳本取得官方 OpenUtau 0.1.576 與原版波音リツ壓縮包，核對 SHA256、安全解壓，
建置約百行 C# host，產生本地 `ritsu-kire-settings.json`。不改使用者既有 OpenUtau 設定。
首次約 430MB 下載；解壓、.NET 與 NuGet 另佔空間。聲庫／模型不放進 Git 或 Plugin。
改用 `--directory` 可選獨立快取；`--engine-dir` 可指定已解壓的同版本 runtime。
NuGet lock 隨原始碼提供，第一次建置需網路，之後可使用本地快取。

## 製作與局部修改

```powershell
uv run --offline python examples/vocal_song.py --settings ".cache/vocal-tools/ritsu-kire-settings.json" --output "my-song"
uv run --offline python examples/vocal_song.py --settings ".cache/vocal-tools/ritsu-kire-settings.json" --output "my-song" --revise
```

這是已撰寫的驗收作品，不是所有新歌的模板。自由創作時請直接寫 Note/USTX 與音色、編曲。
逐音歌詞先放 `Note.lyric`，用 `make_ustx` 匯出，再依需要調整原生音高、顫音、音素與表情。
`render_vocal` 一次輸出一軌，`attach_vocal` 接到 Score，`publish` 量測並保存完整版本。
可直接用 `load_ustx`、`edit_notes`、`save_ustx` 修訂既有 USTX，保留無關資料。

修改音符、歌詞或調聲後必須重新渲染該人聲；舊收據不匹配會阻止發佈。
伴奏、和聲與其他版本獨立保留，歌曲中的 `REVISION_PROOF.json` 記錄實際比較結果。
WORLDLINE 整軌重跑也可能改變其他歌句的波形，因此 `render_revision` 重用原乾聲，
只替換選定樂句及短前後文並交叉淡化；其餘乾聲逐樣本相同。原始乾聲及來源仍保留在收據附件。
`vocals/<版本>/dry.wav` 是乾聲；`audio/stems/` 是含混音效果的同起點 Stems。
Native 16-bit 乾聲不因混成 24-bit 而增加原始精度。

歌曲的 `rebuild/` 包含 Python、lock、橋接原始碼、安裝腳本與聲庫目錄。
重新混音可直接讀取 Score 與凍結乾聲；重新生成唱法需另外安裝同版引擎／聲庫。
複製作品後使用其 `uv run --project <song>/rebuild`；兩平台使用同一格式，不依賴對話歷史。
CPU／架構差異可能影響再次推理結果，不能保證任何機器的 DiffSinger 都逐 bit 一致。

## 綺萱與商業範圍

```powershell
uv run scripts/setup_vocals.py --bank qixuan --evaluation --dotnet "C:/.../dotnet.exe"
uv run --offline python examples/vocal_study.py --settings ".cache/vocal-tools/qixuan-settings.json" --output "my-diffsinger-study"
```

`render_vocal(evaluation=True)` 和 `publish(commercial_ready=False)` 明確記錄非商業評估；
預設商用發佈會拒絕尚未核准的人聲鏈。這不是代替權利人的授權條款，也不是任意聲稱 NC
必然套用於所有合成輸出。聲庫、引擎、聲碼器權重、輸出、圖像與重分發分開核對。

綺萱條款要求作品明顯標示「绮萱」「DiffSinger」及 AI 合成；範例、credits 與報告均有記錄。
本套件不修改／轉換其模型，不再分發模型或插畫，不把商用聲庫許可擴張為圖片商用許可。
若取得聲碼器權利人的明確補充，再保存來源、日期及核對理由，更新完整鏈的審查紀錄。

官方依據（2026-10-25 核對）：

- [OpenUtau 原始碼與發行](https://github.com/openutau/OpenUtau/releases/tag/0.1.576)：MIT 核心；橋接重用上游實作。
- [波音リツ作者規約](https://www.canon-voice.com/terms/)：UTAU 現行規約允許免費商用；其他產品規約分開。
- [波音リツ官方下載](https://www.canon-voice.com/voicebanks/)：原版キレ連續音。
- [綺萱 2.7.0 條款](https://github.com/yqzhishen/qixuan-diffsinger/blob/main/terms_of_use/Terms_of_Use.zh-CN.md)：輸出商用及署名規則、模型與圖像限制。
- [OpenVPI 聲碼器發行與 NOTICE](https://github.com/openvpi/vocoders/releases)：模型權重 CC BY-NC-SA 4.0，未直接寫明本案商業推理／輸出範圍。

更多可執行 Python 範例、原生參數單位及診斷見 [共用人聲參考](../skills/opusmith/references/vocals.md)。
