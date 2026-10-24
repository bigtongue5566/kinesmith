# 音畫設計與時間

音樂既可驅動剪輯，也可由視覺提出需求。以樂句、音色、張力曲線與敘事決定關係；不是每個音符都必須變成閃光。穩定拍點可驅動重動作，細節用較弱的頻譜反應，長音可對應持續變形或鏡頭運動。

已知 tempo map 時：對每一段積分 `seconds += beats * 60 / bpm`。BPM 以四分音符計時時，6/8 的一小節是三個 quarter beats，而不是六個；文件化的 beat unit 優先。套入明確 `audio_offset_seconds` 後才轉影格。尾音長度以真實音檔測量，不以最後音符截斷。

明確時間取樣的 envelope 範例：

```python
import numpy as np

def envelope_at(times, rms, t, attack=.03, release=.18):
    # 平滑在分析階段從固定時間順序產生，求值不依渲染播放順序。
    y = np.zeros_like(np.asarray(rms, dtype=float))
    for i in range(1, len(y)):
        tau = attack if rms[i] > y[i-1] else release
        a = np.exp(-(times[i]-times[i-1])/tau)
        y[i] = a*y[i-1] + (1-a)*rms[i]
    return float(np.interp(t, times, y, left=0, right=0))
```

實務上只計算一次平滑陣列並保存；每個影格只做 interpolation。正規化用穩健百分位避免單一峰值壓扁全曲。Onset 是能量或頻譜變化候選，不等於小節重拍，除非有 score/MIDI 等精確依據。

Energy curve 是宏觀分鏡工具：將數秒至數十秒的張力對應場景密度、運動速度、色彩與鏡頭距離；drop 前留空間，高潮才有對比。使用者改一個場景時不擅自改配樂 drop，必要時輸出 revision request 待音樂工作流程處理。

Lyric 的 timing precision 必須附來源：人工校準音素可標 manual／observed；USTX note 只能標 nominal；依字數、拍點、音量估計標 estimated。多聲部 vocal 疊唱可各自做圖層，且清楚記錄是哪個 stem。可取得的人聲資料不等於有聲庫商用權。

AV interchange 只交換版本化資料、檔案 checksum、來源版本與需求，沒有常駐跨 Plugin runtime。讀來源後保留 read-only 原始資料，場景事件另外衍生。
