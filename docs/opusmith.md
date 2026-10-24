# Opusmith 雙向協作

Kinesmith 不需要安裝 Opusmith，也不匯入它的 Python 核心或改動音樂原檔。兩個 Plugin 由目前 Codex／Claude Code 的主要 Agent 透過已安裝 Skills 協調；資料交接是 JSON 檔案，不假設有 Plugin-to-Plugin API。

2026-10-25 查核 [正式 Repository](https://github.com/bigtongue5566/opusmith) 與 [最新穩定 Release v0.2.0](https://github.com/bigtongue5566/opusmith/releases/tag/v0.2.0)，Release commit 為 `328e630f33af4b8b0ebe178895d1f87120532875`。`v0.1.0` 與 `v0.2.0` 的 Score 都是 `format_version: 1`；後者增加音符歌詞及人聲來源。軟體版本與作品格式版本不能互相代替。

## 真正讀取的公開資料

Adapter 先識別 project `format_version`，驗證 `CURRENT.json` 的 `version` 與 `versions/vNNN` 路徑一致，再讀取完整版本快照。只有 `status: complete` 的版本可同步；已消費檔案如列在 `version.json` 的 SHA256 清單中，雜湊必須相同。直接指定 `score.json` 時不要求快照存在。

`schemas/opusmith-score-v1-v0.1.schema.json` 與 `schemas/opusmith-score-v1-v0.2.schema.json` 是實際上游 Schema 的版本快照。通過 Schema 及段落／音符範圍語意驗證後，才讀取 BPM、Meter、Sections、Notes、Velocity、Controls、Bends、Automation。可用能力取決於存在且可讀取的資料，版本號只用於來源記錄。未宣告 tempo map 的 v1 Score 不會被臆測成支援變速。

`audio/master.wav`、`audio/stems/*` 是已文件化的輸出。Adapter 使用 SoundFile 量測實際 samples、sample rate、channels、duration；樂譜主體秒數與音訊秒數分別保存。沒有實體音訊時，`tail_seconds` 僅為宣告尾音，`audio_measured` 是 false，不宣稱已量測。

遇到未知 project 版本時，不讀取其 CURRENT／Score；只有明確指定的音訊可交接。未知 Score Schema 或新增語意欄位使現有嚴格 Schema 失敗時，安全降級為可用音訊並附上原因；不靜默猜測欄位。未來新增支援應新增 Schema 快照與轉換 profile、保留舊 profile 及 fixture，再測試能力；不可只放寬 `additionalProperties`。

## 時間契約

`av-contract-v1.schema.json` 是輕量 AV Interchange Contract `1.0`。來源、檔案 SHA256、作品版本、可用能力、Tempo Map、Meter Map、事件、歌詞、音訊、授權記錄、修訂需求與關聯分開保存。

`write_contract` 對交接檔目錄樹內的 sources/audio 寫入 `relative_path`，其基準固定為「該交接檔所在目錄」，不含 `..`。外部來源保留明確絕對位置，不偽裝為已包裝的檔案。搬移包含來源的完整作品目錄後，使用 `rebase_contract(contract, new_directory)` 逐一核對宣告的相對路徑與 SHA256，全部相同才回傳新的交接資料；接著另存交接檔。它不依檔名搜尋、不回退到舊絕對路徑、不複製或改寫來源。缺檔、雜湊不符、越界或仍有外部參照都會中止；外部檔案必須由使用者／Agent 明確取得並包裝後再輸出。`verify_sources(contract, base=new_directory)` 可唯讀檢查搬移後來源與音訊。

```python
from pathlib import Path
import json
from kinesmith.interchange import rebase_contract, write_contract

path = Path("moved-work/music.av.json").resolve()
data = json.loads(path.read_text(encoding="utf-8"))
relocated = rebase_contract(data, path.parent)
write_contract(path.with_name("relocated.av.json"), relocated)
```

一拍固定為 quarter note。時間計算先使用有理數，`fps` 支援 `30000/1001`；JSON 的 seconds 是顯示／互通用數字。frame 定義為 `ceil(seconds * fps)`，end frame exclusive。這表示事件從第一個時間採樣不早於 cue 的 frame 生效。負 offset 允許音訊在畫面零點前開始；渲染時需裁去其前段，不得把負時間夾成零後再同步。主體時間、宣告尾音、實測音訊時間及 offset 分別保存。

MIDI 是獨立、成熟的交接介面：使用 `mido` 讀取同步 SMF type 0/1 的 tempo 變化、Meter、Notes、Velocity、CC、Marker 及 Lyrics；拒絕 type 2／SMPTE／重疊同音歧義。原生 USTX `0.10` 可讀取音符、tick resolution、tempo changes 及以 bar 定位的 Meter，保留來源檔且不執行聲庫。

## 三種模式

Music-First：

```powershell
uv run --all-extras kinesmith import-opusmith "C:/作品/Opusmith-Project" --output "work/music.av.json" --fps "30000/1001" --offset 0
```

讀取交接檔，讓畫面 `interchange` 參照它，並明確選擇對應 Master 音訊。Kinetic／Karaoke Typography 使用 `lyrics` 陣列中的 `start_seconds`、`end_seconds`、`text` 與 `timing_precision`。對照渲染影片的 cue frame 與音訊事件；音符時間不能視為實際 onset。

Visual-First：

```powershell
uv run --all-extras kinesmith handoff "work/project.json" --output "work/score-request.av.json"
```

`make_visual_request` 將原始 scene frame 範圍及情緒轉為 `scene` cue，附音樂需求及視覺來源 SHA256。主要 Agent 讀取此檔並使用已安裝的 Opusmith Skill 作曲；未安裝時可把該檔交給其他音樂工作流程。Kinesmith 不擅自啟動額外模型。

Joint Creation：

```python
from kinesmith.interchange import revise_contract, write_contract

updated = revise_contract(contract, request_id="visual-002", target="visual", scope="visual",
                          text="只延長片尾畫面 12 frames；保留所有音樂。")
write_contract("work/revision.av.json", updated)
```

修訂是 `proposed`，不是已套用的宣告。`target` 必須落在使用者授權的 `scope`；只改畫面時不可改音樂，只改音樂時不可改畫面。作品關聯保留視覺／音樂版本與 SHA256；`verify_sources` 可回報 unchanged／changed／missing，不會自動接受或重寫原檔。

## 歌詞、人聲與授權

v0.2.0 的 Score 音符歌詞及 USTX 給出的是音符時間，因此標記 `score-note` 或 `ustx-note`。目前 Release 的 `phonemes.json` 是 alias/error 清單，沒有音素起訖時間。Adapter 會明確警告，沒有 `phoneme-measured` 事件；不得把 alias 清單均分成假音素時間。一般音訊分析的節拍也只能標記 estimated。

人聲 receipt 及 assets ledger 以來源 hash 保留。`commercial_output_verified` 只是上游當時的查核記錄，Kinesmith 不替使用者宣布完整商業權利。聲庫、聲碼器、角色圖像、音訊及字型的授權分別審查；`evaluation_only` 或未確認人聲鏈必須保留警示。Plugin 的 MIT 授權不涵蓋使用者素材、聲庫或編碼器。

本次含人聲的六秒協作範例使用《Seams of Dawn》v003、波音リツ傳統 UTAU／WORLDLINE-R，不是綺萱／DiffSinger。2026-10-25 已直接查閱[原作者現行條款](https://www.canon-voice.com/terms/)：允許該 UTAU 聲庫的商用使用，UTAU 現行網頁條款優先於舊附帶條款；其他合成軟體仍須遵守各自規約。範例保存原始 receipt、音訊與引擎 hash，自願署名「歌聲：波音リツ；OpenUtau / WORLDLINE」，未使用角色插畫。這項確認只涵蓋此聲庫與該範例的已記錄用途，不推及其他聲庫、權重、圖像或所有未來作品。

## 相容性與驗證

`examples/opusmith-v0.1.0`、`examples/opusmith-v0.2.0` 保存真實 Score；v0.2 fixture 另含原生 USTX。來源 commit、上游檔案路徑與 MIT 授權一起保存，沒有重新生成假專案。`tests/test_opusmith.py`、`tests/test_interchange.py` 驗證舊版／新版、未知 Schema、未知 project、路徑越界、失敗快照、SHA256 不符、尾音、負 offset、rational FPS、變速 MIDI、歌詞精度與限定範圍修訂。

本機完整 Opusmith `seams-of-dawn` v003 專案已實際讀取：1989 notes、165 lyric notes、9 stems、2 vocal source references、實測 master 158.83873015873016 秒，樂譜主體 154.83870967741936 秒。該記錄只代表 Adapter 的實際資料讀取；影片渲染、視覺品質與平台自主委派必須另外以實際產物驗證。
