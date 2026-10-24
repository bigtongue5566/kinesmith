# 品質報告

## 工程正確性

Score 已通過範圍／段落／引用驗證；MIDI、真實 WAV、Stems 與版本快照已產生。
WAV 非靜音：True；有限數值：True；削波樣本：0。

## 使用者需求符合度

未由訊號分析器判定。請逐項對照 ORIGINAL_PROMPT.txt 與 Prompt History。

## 音訊技術量測

```json
{
  "duration_seconds": 48.0,
  "sample_rate": 48000,
  "channels": 2,
  "finite": true,
  "non_silent": true,
  "rms_dbfs": -23.97574317238179,
  "sample_peak_dbfs": -1.5055272677757758,
  "estimated_true_peak_dbfs": -1.500000020140368,
  "integrated_lufs": -22.494107021474566,
  "clipped_samples": 0,
  "dc_offset": [
    1.4748982835044444e-07,
    8.581868371493329e-08
  ],
  "stereo_correlation": 0.9648225292717876,
  "mid_rms_dbfs": -24.060626837680203,
  "side_rms_dbfs": -41.107668334064996,
  "active_fraction": 0.975,
  "subjective_listening": "未進行；訊號分析不能代替聆聽。"
}
```

4 倍過取樣峰值為估計值，非認證 true-peak meter；MP3 有損編碼可能增加峰值。

## 主觀音樂品質

未進行；訊號分析不能代替聆聽。
