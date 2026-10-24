# Form becomes motion / visual cue response — 作品構成報告

音樂時間 6.000 秒；含尾音 WAV 6.400 秒。
120 BPM；調性標籤：D minor（創作者標註，非自動判定）；4/4 拍。

風格標籤：（創作意圖，非分類器驗證）。

## 實際段落

| 段落 | 起訖秒 | 音軌（有音符起點） |
|---|---|---|
| form | 0.00–3.00 | Form motif, Motion accents, Low anchor |
| motion | 3.00–6.00 | Form motif, Motion accents, Low anchor |

## 音符、音源與處理

### Form motif (pluck)

10 個音符；音域 MIDI 62–74；音高類別 C, D, F, A。
前 12 個實際音符（拍:音高/長度）：0:62/0.65, 1.5:65/0.65, 3:69/0.65, 4.5:65/0.65, 6:74/0.65, 7:72/0.65, 8:69/0.65, 9:65/0.65, 10:69/0.65, 11:62/0.65
音源 `pluck`；可重現參數：
```json
{"engine": "pluck", "attack": 0.004, "decay": 0.3, "sustain": 0.1, "release": 0.28, "cutoff_hz": 3500.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -21 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.08, "reverb_size": 0.35, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### Motion accents (pulse)

8 個音符；音域 MIDI 36–36；音高類別 C。
前 12 個實際音符（拍:音高/長度）：0:36/0.15, 3:36/0.15, 6:36/0.15, 7:36/0.15, 8:36/0.15, 9:36/0.15, 10:36/0.15, 11:36/0.15
音源 `kick`；可重現參數：
```json
{"engine": "kick", "attack": 0.003, "decay": 0.12, "sustain": 0.0, "release": 0.06, "cutoff_hz": 6000.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -20 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### Low anchor (foundation)

2 個音符；音域 MIDI 38–38；音高類別 D。
前 12 個實際音符（拍:音高/長度）：0:38/5.5, 6:38/5.5
音源 `fm`；可重現參數：
```json
{"engine": "fm", "attack": 0.02, "decay": 0.2, "sustain": 0.25, "release": 0.15, "cutoff_hz": 900.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 1.0, "fm_index": 0.2, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -27 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

## 創作決策與版本

以下為創作者註記；可觀測音樂資料以上方音符及 score.json 為準。

- Responds to two 3-second picture cues at quarter-note beats 0 and 6.
- Six-second body plus 0.4-second effects tail, intentionally trimmed by picture edit.
- Original local synthesis only, no third-party samples or generative model.

外部／本地素材紀錄 0 筆；詳 ASSET_CREDITS.md。

母帶：LUFS 量測後施加固定增益，以 4 倍過取樣峰值限制增益，無動態 limiter。
實際母帶增益 18.52 dB；LUFS 目標達成：False。

Stems 為同起點、含個別效果及 ducking 的 24-bit FLAC；相加對應浮點 premaster，Master 另施加 render.json 記載的固定增益。

音源由 score.json 記載；附有 vocal 的音軌使用本地 OpenUtau 歌聲渲染，其聲庫、引擎、授權與原始乾聲詳 vocals.json 及對應 receipt.json。其餘音軌使用本地合成或已核對素材。未呼叫外部作曲／音訊生成服務。

- 2026-10-24T20:30:57.890120+00:00 · 初始化 · user · 依實際 visual-request.av.json 的兩個三秒場景創作配樂。
- 2026-10-24T20:30:58.091392+00:00 · v001 · agent · Visual-first cue response

## 未完成／評估限制

未進行；訊號分析不能代替聆聽。
未自動驗證風格辨識、藝術感染力或全部自然語言條件；需由目前 Agent 對照原始提示詞。
