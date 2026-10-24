# Opusmith

**Craft music, not just generate it.**

Opusmith 讓目前的 Codex 或 Claude Code Agent 自主作曲、編曲、設計合成音色、渲染與修訂作品。
共用 Skills 與音樂知識，使用各平台原生 Subagents，不呼叫其他 LLM、Text-to-MIDI 或整曲生成服務。
v0.2 新增本地 OpenUtau 歌聲：由 Agent 寫詞、作曲與調聲，再以傳統 UTAU 或 DiffSinger 渲染。
每首作品是本地可編輯專案，保留多軌 MIDI、JSON Score、Python、音色參數、WAV/MP3、Stems、
提示詞與版本、授權帳本及繁體中文報告。創作由 Agent 決定，Helpers 只約束工程正確性。

## 快速開始

原始碼：[bigtongue5566/opusmith](https://github.com/bigtongue5566/opusmith)。
[GitHub Releases](https://github.com/bigtongue5566/opusmith/releases/tag/v0.2.0)
提供通用 Plugin、雙平台本地 marketplace、八份可編輯示範與 MP3；其中綺萱範例僅供非商業評估。

需要 `uv`、Python 3.11+；`uv` 可自動取得合適 Python。Windows x64 已實測；其他系統需要
NumPy、SciPy、Pedalboard、SoundFile 與 FFmpeg wheels 支援，尚未在實機全面測試。
器樂路徑不需要 API key、外部模型、付費 DAW、GM SoundFont 或大型 sample library。
人聲為可選能力，另需 .NET SDK 10、OpenUtau 及聲庫；初次下載後可離線渲染。

```powershell
git clone https://github.com/bigtongue5566/opusmith.git
cd opusmith
uv sync --locked
uv run scripts/doctor.py
uv run pytest
```

Doctor 真的合成音樂、匯出再匯入 MIDI、編碼 MP3 並驗證 WAV 非靜音／無削波。
若環境不允許預設 uv cache，可將 `UV_CACHE_DIR` 設為專案 `.cache/uv`。
依賴下載完後，`uv run --offline ...` 可離線製作。

## 安裝 Plugin

兩平台使用**同一份** `skills/`、`roles/`、Python 與作品格式。
解壓 `dist/opusmith-0.2.0.zip` 可取得通用 Plugin；Codex 本地安裝使用另附 marketplace 包。
首次由原始碼建立發行包：

```powershell
uv run scripts/build_adapters.py
uv run scripts/build_release.py
```

Codex（在支援 plugins 的版本）：

```powershell
codex plugin marketplace add "<Opusmith 路徑>/dist/marketplace"
codex plugin add opusmith@opusmith-local
```

桌面版也可從已加入的 Local marketplace 安裝。安裝後在新對話使用 `$opusmith` 或自然語言。
自訂 Codex 角色目前由 `.codex/agents/*.toml` 載入，與 Plugin skills 封裝分開：

```powershell
uv run scripts/install_codex_roles.py "<音樂工作區>"
```

此腳本只安裝五個 `opusmith-*` 原生角色檔，不覆寫不同內容、不變更全域模型／權限。
重開信任的工作區以載入角色；主 Agent 自行決定是否使用。

Claude Code：

```powershell
claude plugin validate "<Opusmith 路徑>/.claude-plugin/plugin.json"
claude --plugin-dir "<Opusmith 路徑>"
```

對話中使用 `/opusmith:opusmith`，或自然語言觸發。持久安裝可執行：

```text
/plugin marketplace add <Opusmith 路徑>/dist/marketplace
/plugin install opusmith@opusmith-local
```

Claude agents 由 `agents/*.md` 自動載入。詳細規格與驗證邊界見 [相容性紀錄](docs/COMPATIBILITY.md)。
Plugin cache 若唯讀，將 `UV_PROJECT_ENVIRONMENT` 指向本地可寫快取，再執行 `uv sync --project`。
作品存到自己的音樂資料夾，勿放到 Plugin 安裝快取。

## 可以直接提出的需求

- 「創作90秒的 Progressive House，以三音動機逐步發展，break 有新的和聲視角，完全離線。」
- 「做 Trance × Dubstep，保留同一主題，在後半段改半拍鼓與 Reese 回應，不要只是疊 layer。」
- 「只修改這個專案第45–46小節的主題，降八度，其他音軌與段落保持不變。」
- 「幫 Ambient 搜尋一小段可商用 field recording，核對原始來源再加工，保留授權及署名。」

這些提示由目前的 Agent 理解與寫作 source code；本套件沒有另一個文字生成模型或僵硬的曲式產生器。
流派慣例只是參考。可使用任意合適的本地音樂套件或額外音源，不必所有操作經由 Helpers。

## 真實作品與重建

[examples/projects](examples/projects) 有五種指定風格、一首外部素材作品、完整人聲歌曲及 DiffSinger 短句，
每首 `CURRENT.json` 指向最近成功版本；`versions/` 保存歷史與失敗狀態。
[作品索引](docs/EXAMPLES.md) 列出目前版本、時間、量測與試聽位置。
Git 保留作品的 MIDI、Score、來源程式、創作紀錄與報告；大型音訊不放入 Git。
請從 [v0.2.0 Release](https://github.com/bigtongue5566/opusmith/releases/tag/v0.2.0)
下載 `opusmith-project-<作品>-0.2.0.zip`，解壓後即含該作品的完整歷史、音訊、Stems 及所需素材。
MP3 亦可個別下載。完整作品包與小型 Plugin ZIP 分開，避免安裝 Plugin 時下載全部音樂。

```powershell
# 在新輸出目錄製作全部五首已撰寫示範（不是通用作曲器）
uv run examples/compose.py --output my-studies --style all
# 只修改混合曲的兩小節主題
uv run examples/compose.py --revise my-studies/trance-dubstep
# 直接依編輯後 Score 重新渲染
uv run examples/compose.py --rerender my-studies/trance-dubstep
```

每首附 `rebuild/` 的小型 Python runtime 與 lock，不附 venv。把整首資料夾複製到另一平台後：

```powershell
uv sync --project "<song>/rebuild" --locked
uv run --project "<song>/rebuild" python "<song>/source.py" --rerender "<song>"
```

跨機器需先下載 Python wheels；相同套件／平台可重現 PCM，跨架構可能有浮點差異。
Stems 是同起點、含個別處理的 24-bit FLAC；相加對應浮點 premaster，Master 另有固定增益。
MIDI 包含標準音符／歌詞／CC／Pitch Bend／標記，不攜帶自訂 patch、DSP 或完整 USTX 調聲；JSON、Python 與原生人聲專案一併保存。

## OpenUtau 人聲

預設聲庫為**波音リツ・キレ連續音**：免費、作者條款明確允許商用的獨立 UTAU 日語聲庫。
以 OpenUtau 原生 VCV phonemizer 與 WORLDLINE-R 真正合成，不以音效或合成器假冒歌聲。
《光の縫い目》是 2:39、九軌的完整驗收作品，包含原創主唱、和聲與局部修訂紀錄。

安裝 [.NET SDK 10](https://dotnet.microsoft.com/download/dotnet/10.0)，再執行：

```powershell
uv run scripts/setup_vocals.py --bank ritsu-kire --dotnet "<dotnet.exe 的完整路徑>"
uv run --offline python examples/vocal_song.py --settings ".cache/vocal-tools/ritsu-kire-settings.json" --output "my-vocal-song"
uv run --offline python examples/vocal_song.py --settings ".cache/vocal-tools/ritsu-kire-settings.json" --output "my-vocal-song" --revise
```

自動安裝目前針對 Windows x64；其他 OS 可提供相應官方 0.1.576 runtime 路徑，但尚未實機驗證。
首次從官方網址下載約 430MB 壓縮檔，SHA256 鎖定；不將聲庫或模型放進 Plugin。
Python Helpers 保留歌詞、原生音高／顫音／音素表情、乾聲及引擎／授權收據；可在 OpenUtau 手動調聲。
歌聲乾聲為上游原生 44.1kHz mono 16-bit，最終多軌混音為 24-bit WAV/FLAC。

OpenVPI/DiffSinger 已用**綺萱 2.7.0** 實際產生中文歌聲。聲庫條款明文允許不限額商用輸出，
但所需聲碼器權重另採 NC；本版未宣告其完整商業鏈已核准，僅開放明確標示的非商業評估。
這不等於斷言所有聲碼器輸出禁止商用。正式商用路徑先使用已核對的波音リツ傳統音源。
完整操作與授權區別見 [人聲製作指南](docs/VOCALS.md)。角色圖片不隨本套件使用或再分發。

## 知識與工具

- [創作 Skill](skills/opusmith/SKILL.md)：漸進載入，依任務閱讀必要知識。
- [流派庫](skills/opusmith/references/genres/index.md)：House、Techno、Trance、Dubstep、Trap、
  Drum & Bass、Ambient、Chillout/Downtempo 及指定子流派、融合方式、擴充約定。
- [製作知識](skills/opusmith/references/production)：理論、動機發展、配器、真實 Patch、混音與母帶。
- [Python 用法](skills/opusmith/references/tools.md)：Score、SMF、局部修改、渲染與外部音源接口。
- [素材規範](skills/opusmith/references/assets.md)：Openverse、原始來源核對、下載與加工紀錄。
- [人聲與調聲](skills/opusmith/references/vocals.md)：OpenUtau、USTX、音素、歌詞、表情與聲庫授權。
- [驗收紀錄](docs/VALIDATION.md)：自動測試、真實輸出與尚未完成的驗收範圍。

離線音色涵蓋 subtractive/supersaw、FM、additive、wavetable、Reese、噪音與合成鼓。
Pedalboard 提供真實 filter、compressor、delay/reverb，FFmpeg 做 MP3 與 sample processing。
FluidSynth/sfizz/Surge XT 是可選擴充，未打包大型素材、也未宣稱全部外部 renderer 已實測。

## 品質與限制

本版固定 BPM／拍號；可寫任意長度段落及拍內事件。MIDI 匯入遇到變速、變拍、延音踏板等
尚未完整支援的語意會拒絕，避免悄悄遺失。最多15條獨立旋律 MIDI channels，鼓組共用 channel10。
同 channel 同音高重疊須先明確分聲部或連結，不可輸出有歧義的 note-off。
Sample engine 不做連續 pitch bend；wavetable 沒有內建多 frame morph，進階設計可自行寫 Python。

母帶採量測後固定增益，估計4倍過取樣峰值控制 headroom；不是完整商用母帶系統或動態 limiter。
不保證每首達到指定 LUFS。技術分析與使用者需求、主觀音樂品質分開；**沒有實際聆聽就不宣稱完成聽覺評估**。
Natural language 在兩個已登入平台的完整現場創作驗收仍需實際帳號／session；本版安裝測試不冒充模型驗收。

外部素材為可選。預設只納入已核對 CC0 或 CC BY；NC/ND/unknown 拒絕，SA 需另外個案審查。
Openverse 結果不視為授權證明。API 故障不阻止合成路徑。全部資料留本地，無自動上傳。

MIT 為本專案程式與知識庫授權；外部音訊、聲庫與歌聲的條款見各作品 `ASSET_CREDITS.md` 及收據。
