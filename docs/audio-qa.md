# 音訊分析與影片品質檢查

Kinesmith 可以獨立分析一般音訊，不需 Opusmith 或生成模型。FFmpeg 解碼第一個音軌為 22050 Hz 單聲道浮點樣本；SciPy Hann window 與 NumPy FFT 計算 RMS、三頻帶能量、正向 spectral flux，以及局部峰值 onset 候選。正規化數值供圖形大小、顏色、粒子密度與 shader uniform 使用；原始 RMS 與來源 SHA256 一併保留。

```powershell
uv run --all-extras kinesmith analyze path/to/audio.wav --output work/audio-features.json
uv run --all-extras kinesmith qa outputs/film.webm --output outputs/qa
```

Python 介面：

```python
from kinesmith.audio import analyze_audio, feature_at
features = analyze_audio("music.wav", "work/audio-features.json")
# 正值代表影片先開始、音樂延後；音訊尚未開始或已結束時回傳零。
amplitude = feature_at(features, time_seconds=2.0, audio_offset_seconds=0.25)["energy"]
# 在 Canvas/p5/Three.js 原生來源中，以這個振幅控制自己的構圖和動作。
```

`frames` 每筆有 `time_seconds`、`rms`、`energy`、`low`、`mid`、`high`、`onset`。輸出 hop 約 23.22 ms，window 約 92.88 ms；檔案時間不含場景／音訊時間軸偏移。分析時間皆標示 `estimated`，不是精確節拍、演唱、音節或音素。`beat_grid` 與 `phoneme_alignment` 保持 null；要精準歌詞請匯入有來源的時間標記，不能將頻譜峰值命名為 phoneme。

`scripts/make_audio_fixture.py` 可產生 CC0 原創確定性電子測試音訊及精確 authored 節拍時間；這是測試訊號，不假裝成真人樂器或人聲。分析得到的 onset 仍標為 estimated。

品質工具會完整解碼影音串流、逐幀計數、量測尺寸／FPS／時長，輸出 12 張含影格編號的原始尺寸代表影格、contact sheet、`qa.json` 與繁體中文 `qa.md`。可傳 `expected={"width":1920,"height":1080,"fps":30,"duration_seconds":10}`，時長容忍為一影格加 2 ms。FPS 由 FFmpeg decoder rational rate 取得，避免將 24000/1001 四捨五入成 23.98。

逐幀低解析度畫面檢查提供黑畫面、連續相同影格、亮度跳變候選，應由 Agent 檢視代表影格並依需求再看特定片段。這些只是假設性提示；刻意黑畫面、定格、場景剪接與閃光都可能是設計。格式正確不會自動將文字裁切、動作連續性、轉場、音畫同步、授權或美感標示通過。畫面量測假設 CFR；外部 VFR 素材要先轉成專案 FPS 或以 PTS 額外驗證。

工具與方法來源：[FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)、[SciPy find_peaks](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.find_peaks.html)。音訊分析不推定輸入素材、聲庫、角色或字型的商業授權。
