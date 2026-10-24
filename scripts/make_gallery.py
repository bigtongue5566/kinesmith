"""Build editable six-engine and independent audio-reactive examples from native sources."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

from kinesmith.audio import analyze_audio
from make_audio_fixture import make_audio_fixture

ROOT = Path(__file__).resolve().parents[1]
ENGINES = [("canvas", "canvas.html"), ("rough", "rough.html"), ("p5", "p5.html"),
           ("three", "three.html"), ("manim", "manim_scene.py"), ("blender", "blender_scene.py")]


def write_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_gallery(destination: str | Path = ROOT / "examples/gallery") -> Path:
    destination = Path(destination).resolve()
    source = ROOT / "examples/gallery/scenes"
    destination.mkdir(parents=True, exist_ok=True)
    if destination / "scenes" != source:
        shutil.copytree(source, destination / "scenes", dirs_exist_ok=True)
    licenses = [
        {"asset": "original graphics, scene code, motion concept", "license": "MIT", "author": "Kinesmith contributors",
         "source": "This repository; no stock imagery or character assets"},
        {"asset": "audio/electronic-study.wav", "license": "CC0-1.0", "author": "Kinesmith contributors",
         "source": "scripts/make_audio_fixture.py; deterministic synthesis, no samples or voicebank"},
        {"asset": "Arial or system fallback glyphs", "license": "platform-provided font; not redistributed",
         "source": "Installed OS font rendered by browser/Manim; replace if local font terms require"},
        {"asset": "Blender text", "license": "Blender bundled Bfont; font pixels rendered, font file not distributed",
         "source": "Blender installation"},
        {"asset": "renderer dependencies", "license": "See vendor/manifest.json and THIRD_PARTY_NOTICES.md",
         "source": "Canvas Web Standard; Rough.js MIT; p5 LGPL-2.1; Three.js MIT; Manim MIT; Blender GPL-3.0-or-later"},
    ]
    audio = destination / "audio/electronic-study.wav"
    make_audio_fixture(audio, 12, 120)
    analyze_audio(audio, destination / "audio/features.json")
    project = {
        "schema_version": "1.0", "id": "kinesmith-orbital-craft", "title": "Orbital Craft / 軌道工藝",
        "revision": 1, "fps": "24", "width": 640, "height": 360, "duration_frames": 288, "seed": 42,
        "prompt": "以軌道、手勢與流場展示六種原生 MoGraph 技術；原創幾何、深墨色、暖白、青綠與珊瑚色。",
        "brief": "motion-brief.md", "features": "audio/features.json",
        "audio": {"source": "audio/electronic-study.wav", "offset_seconds": 0, "gain": .8},
        "licenses": licenses, "revisions": [],
        "scenes": [{"id": engine, "engine": engine, "source": f"scenes/{name}",
                    "start_frame": index * 48, "duration_frames": 48,
                    "params": {"accent": "#65d4cf"} if engine == "canvas" else {}}
                   for index, (engine, name) in enumerate(ENGINES)],
    }
    write_json(destination / "project.json", project)
    brief = """# Motion Brief — Orbital Craft / 軌道工藝

原始創作需求：讓 Agent 自由使用六種引擎，以同一條設計主線創作可編輯動畫；本片是能力研究作品，並非所有創作必須遵循的模板。

視覺理念：從字形拆解開始，經過手繪、程序流場、即時立體、數學曲線，抵達有材質與光影的軌道雕塑。圓弧作為跨場景形狀連結，青綠主色、暖白文字和珊瑚色焦點維持視覺階層。

| 影格／秒 | 引擎 | 動作與設計 |
|---|---|---|
| 0–47／0–2 | Canvas | KINE / SMITH 遮罩入場，圓弧接力與音訊 RMS 微幅脈動。 |
| 48–95／2–4 | Rough.js | 固定手繪亂數種子、環形構圖與三個概念卡片的軌道運動。 |
| 96–143／4–6 | p5.js | 每影格重新計算有種子的噪音曲線；流場不依賴播放速度或累積背景。 |
| 144–191／6–8 | Three.js | 金屬感 torus knot、原生光照、透視攝影機、畫布文字平面。 |
| 192–239／8–10 | Manim | 由原生幾何路徑逐步畫出極座標花形；不依賴 LaTeX。 |
| 240–287／10–12 | Blender | 原生 Cycles、區域光源、材料、攝影機與 Geometry Nodes 軌道珠。 |

鏡頭在整數影格邊界剪接；不以即時播放記錄正式影片。2 秒場景是技術研究長度，正式品牌影片應依訊息可讀性延長文字停留。修改 Canvas 的 params.accent 示範局部修訂；其他場景的來源與快取可保留。

配樂為原創合成測試音色，不是人聲或真人樂器；檔案末端保留衰減尾音。音訊分析 onset 全部標記 estimated。授權列表位於 project.json；第三方工具授權另見根目錄清單，不將工具 GPL/LGPL 義務誤當作輸出影片必須同樣授權。

可重現性：使用 project.json 的 FPS、解析度、48 影格原生片長與 seed=42。保存渲染工具版本、來源 SHA256、原生 .blend 和逐幀 PNG。瀏覽器與原生工具跨版本／平台可能有浮點、字型與渲染差異，故以實際版本紀錄為準。

品質：應執行 qa 並檢視 contact sheet、首末影格、剪接、文字和音畫同步。沒有檢視的項目不得聲稱通過。Manim／Blender 首次渲染較慢；完整來源保留引擎原生能力，不提供限制動畫物件的統一 API。
"""
    (destination / "motion-brief.md").write_text(brief, encoding="utf-8")
    # Single-engine projects live inside the same project root, reusing source files
    # rather than duplicating engine code or hiding it behind a generic renderer.
    for engine, _ in ENGINES:
        single = deepcopy(project)
        single.update({"id": f"kinesmith-{engine}-study", "title": f"{engine} / 原生動畫研究", "duration_frames": 48})
        single["scenes"] = [deepcopy(next(scene for scene in project["scenes"] if scene["id"] == engine))]
        single["scenes"][0]["start_frame"] = 0
        write_json(destination / f"project-{engine}.json", single)
    reactive = deepcopy(project)
    reactive.update({"id": "kinesmith-audio-reactive", "title": "Independent Audio Reactive / 獨立音訊反應", "duration_frames": 288})
    reactive["scenes"] = [{"id": "audio-reactive", "engine": "canvas", "source": "scenes/audio_reactive.html",
                           "start_frame": 0, "duration_frames": 288, "params": {"audioOffset": 0}}]
    write_json(destination / "project-audio-reactive.json", reactive)
    return destination / "project.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="建立可編輯六引擎作品與一般音訊反應專案")
    parser.add_argument("--output", type=Path, default=ROOT / "examples/gallery")
    args = parser.parse_args()
    print(build_gallery(args.output))
