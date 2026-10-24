# 鍛造聲音 — Opusmith Film — 作品構成報告

音樂時間 46.500 秒；含尾音 WAV 48.000 秒。
160 BPM；調性標籤：D minor（創作者標註，非自動判定）；4/4 拍。

風格標籤：melodic broken beat, liquid electronic（創作意圖，非分類器驗證）。

## 實際段落

| 段落 | 起訖秒 | 音軌（有音符起點） |
|---|---|---|
| 章節 1 | 0.00–6.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive |
| 章節 2 | 6.00–12.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive, 碎拍・Kick, 碎拍・Snare, 細分・Hi-hat |
| 章節 3 | 12.00–18.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive, 碎拍・Kick, 碎拍・Snare, 細分・Hi-hat |
| 章節 4 | 18.00–24.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive, 碎拍・Kick, 碎拍・Snare, 細分・Hi-hat |
| 章節 5 | 24.00–30.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive, 碎拍・Kick, 碎拍・Snare, 細分・Hi-hat |
| 章節 6 | 30.00–36.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive |
| 章節 7 | 36.00–42.00 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive, 碎拍・Kick, 碎拍・Snare, 細分・Hi-hat |
| 章節 8 | 42.00–46.50 | 章節落點・柔和 FM, 主題・濾波 Pluck, 和聲・柔暖長音, 低音・Additive |

## 音符、音源與處理

### 章節落點・柔和 FM (keys)

11 個音符；音域 MIDI 55–69；音高類別 C, D, F, G, A, A#。
前 12 個實際音符（拍:音高/長度）：0:62/1.1, 16:58/1.1, 32:60/1.1, 48:60/1.1, 64:55/1.1, 80:58/1.1, 96:60/1.1, 112:62/1.1, 120:62/1.6, 120:65/1.6, 120:69/1.6
音源 `fm`；可重現參數：
```json
{"engine": "fm", "attack": 0.008, "decay": 0.35, "sustain": 0.2, "release": 0.65, "cutoff_hz": 3200.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 1.0, "fm_index": 0.45, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -20 dB，Pan 0.15；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.11, "reverb_size": 0.35, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 主題・濾波 Pluck (pluck)

66 個音符；音域 MIDI 55–69；音高類別 C, D, E, F, G, A, A#。
前 12 個實際音符（拍:音高/長度）：0:62/0.9, 3:65/0.48, 6:62/0.48, 10:69/0.9, 12.75:62/0.48, 16:65/0.9, 17.5:62/0.48, 19:65/0.48, 19.75:58/0.9, 22:62/0.48, 23.5:65/0.48, 26:62/0.9
音源 `pluck`；可重現參數：
```json
{"engine": "pluck", "attack": 0.006, "decay": 0.18, "sustain": 0.2, "release": 0.22, "cutoff_hz": 3200.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -9 dB，Pan -0.35；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.28125, "delay_mix": 0.1, "reverb_mix": 0.06, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 和聲・柔暖長音 (pad)

27 個音符；音域 MIDI 43–57；音高類別 C, D, E, F, G, A, A#。
前 12 個實際音符（拍:音高/長度）：0:50/15.7, 0:53/15.7, 0:57/15.7, 16:46/15.7, 16:50/15.7, 16:53/15.7, 32:48/15.7, 32:53/15.7, 32:57/15.7, 48:48/15.7, 48:52/15.7, 48:55/15.7
音源 `pad`；可重現參數：
```json
{"engine": "pad", "attack": 0.22, "decay": 0.3, "sustain": 0.7, "release": 0.42, "cutoff_hz": 1250.0, "resonance": 0.7, "detune_cents": 5.0, "voices": 3, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -16 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 160.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.09, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 低音・Additive (bass)

91 個音符；音域 MIDI 31–38；音高類別 C, D, G, A#。
前 12 個實際音符（拍:音高/長度）：0:38/0.65, 1.75:38/0.65, 2.5:38/0.65, 4:38/0.65, 5.75:38/0.65, 6.5:38/0.65, 8:38/0.65, 9.75:38/0.65, 10.5:38/0.65, 12:38/0.65, 13.75:38/0.65, 14.5:38/0.65
音源 `additive`；可重現參數：
```json
{"engine": "additive", "attack": 0.009, "decay": 0.15, "sustain": 0.7, "release": 0.1, "cutoff_hz": 450.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.13, 0.04]}
```
增益 -13 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 1300.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 碎拍・Kick (kick)

60 個音符；音域 MIDI 36–36；音高類別 C。
前 12 個實際音符（拍:音高/長度）：16:36/0.35, 17.5:36/0.35, 18.75:36/0.35, 20:36/0.35, 20.75:36/0.35, 22.5:36/0.35, 24:36/0.35, 25.5:36/0.35, 26.75:36/0.35, 28:36/0.35, 28.75:36/0.35, 30.5:36/0.35
音源 `kick`；可重現參數：
```json
{"engine": "kick", "attack": 0.001, "decay": 0.13, "sustain": 0.0, "release": 0.04, "cutoff_hz": 6000.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -11 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 碎拍・Snare (snare)

60 個音符；音域 MIDI 38–38；音高類別 D。
前 12 個實際音符（拍:音高/長度）：17:38/0.18, 19:38/0.18, 19.75:38/0.18, 21:38/0.18, 23:38/0.18, 23.75:38/0.18, 25:38/0.18, 27:38/0.18, 27.75:38/0.18, 29:38/0.18, 31:38/0.18, 31.75:38/0.18
音源 `snare`；可重現參數：
```json
{"engine": "snare", "attack": 0.001, "decay": 0.09, "sustain": 0.0, "release": 0.04, "cutoff_hz": 6000.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -11 dB，Pan 0；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

### 細分・Hi-hat (hat)

160 個音符；音域 MIDI 42–42；音高類別 F#。
前 12 個實際音符（拍:音高/長度）：16:42/0.08, 16.5:42/0.08, 17:42/0.08, 17.5:42/0.08, 18:42/0.08, 18.5:42/0.08, 19:42/0.08, 19.5:42/0.08, 20:42/0.08, 20.5:42/0.08, 21:42/0.08, 21.5:42/0.08
音源 `hat`；可重現參數：
```json
{"engine": "hat", "attack": 0.001, "decay": 0.04, "sustain": 0.0, "release": 0.025, "cutoff_hz": 6000.0, "resonance": 0.7, "detune_cents": 12.0, "voices": 5, "lfo_hz": 2.0, "fm_ratio": 2.0, "fm_index": 2.0, "drive": 1.0, "sample": null, "root_note": 60, "partials": [1.0, 0.4, 0.2, 0.1]}
```
增益 -15 dB，Pan 0.25；0 CC、0 Pitch Bend、0 Automation lanes。
實際 DSP 設定：`{"highpass_hz": 25.0, "lowpass_hz": 18000.0, "compressor_db": -18.0, "ratio": 2.0, "delay_seconds": 0.375, "delay_mix": 0.0, "reverb_mix": 0.0, "reverb_size": 0.5, "sidechain_from": null, "duck_db": 0.0, "duck_release": 0.18}`

## 創作決策與版本

以下為創作者註記；可觀測音樂資料以上方音符及 score.json 為準。

- 160 BPM；每幕 16 拍；原創碎拍、濾波 pluck、長音及合成鼓。
- 音樂主體 46.5 秒，加 1.5 秒效果尾音，總長精確 48 秒。
- 45 秒終止起音，最後不接回鼓循環；無取樣、歌聲或外部生成模型。

外部／本地素材紀錄 0 筆；詳 ASSET_CREDITS.md。

母帶：LUFS 量測後施加固定增益，以 4 倍過取樣峰值限制增益，無動態 limiter。
實際母帶增益 3.92 dB；LUFS 目標達成：False。

Stems 為同起點、含個別效果及 ducking 的 24-bit FLAC；相加對應浮點 premaster，Master 另施加 render.json 記載的固定增益。

音源由 score.json 記載；附有 vocal 的音軌使用本地 OpenUtau 歌聲渲染，其聲庫、引擎、授權與原始乾聲詳 vocals.json 及對應 receipt.json。其餘音軌使用本地合成或已核對素材。未呼叫外部作曲／音訊生成服務。

- 2026-10-24T21:49:57.735302+00:00 · 初始化 · user · 再一個介紹 opusmith 這個專案
- 2026-10-24T21:49:58.123567+00:00 · v001 · agent · 為 48 秒專案介紹創作原創碎拍配樂。

## 未完成／評估限制

未進行；訊號分析不能代替聆聽。
未自動驗證風格辨識、藝術感染力或全部自然語言條件；需由目前 Agent 對照原始提示詞。
