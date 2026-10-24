"""Write the two authored 48-second timelines, cue sheets and optional SRT captions."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TITLES = {
 'kinesmith': ['把想法，鍛造成動態。', '一句想法，展開一部作品。', '形狀、文字，都有節奏。',
               '從平面，走進空間。', '每一格，都能重現。', '音樂與畫面，彼此回應。',
               '只改你指定的那一幕。', 'Craft motion, not just animate it.'],
 'codex': ['Codex 是什麼？OpenAI 的 AI 程式開發代理。', '先理解，再動手：讀取專案脈絡與既有規範。',
           '把需求，變成可檢查的修改。', '執行、測試、再修正。', '在桌面 App、CLI、IDE 或 Web 協作。',
           'Skills 保存方法，Plugin 讓別人也能安裝。', '你定方向，也審查差異與驗證結果。',
           '從一個清楚的任務開始，把開發工作一步步做到完成。'],
}


def main():
    for name in ('kinesmith', 'codex'):
        scenes = []
        for i in range(8):
            three = name == 'kinesmith' and i == 3
            source = 'scenes/dimension.html' if three else f'scenes/{name}.html'
            scenes.append(dict(id=f'{name}-{i+1:02}', engine='three' if three else 'rough' if name == 'kinesmith' and i == 2 else 'canvas',
                               source=source, start_frame=i*180, duration_frames=180, params=dict(chapter=i),
                               dependencies=['scenes/drawing.js']))
        project = dict(schema_version='1.0', id=f'{name}-introduction',
                       title='Kinesmith：把想法鍛造成動態' if name == 'kinesmith' else 'Codex 是什麼？',
                       revision=1, fps='30', width=1920, height=1080, duration_frames=1440, seed=640,
                       prompt='新增一支介紹 Kinesmith 專案的完整短片' if name == 'kinesmith' else '新增一支介紹什麼是 Codex 的完整短片',
                       brief=f'brief-{name}.md', dependencies=['assets/NotoSansTC-VF.ttf'],
                       audio=dict(source=f'audio/{name}-score.wav', offset_seconds=0, gain=1),
                       licenses=[
                           dict(asset='scene code, original graphics and animation', license='MIT', author='Kinesmith contributors', source='This repository'),
                           dict(asset=f'audio/{name}-score.wav and MIDI composition', license='CC0-1.0', author='Kinesmith contributors', source='examples/introductions/compose.py; no samples'),
                           dict(asset='NotoSansTC-VF.ttf', license='OFL-1.1', source='https://github.com/google/fonts/tree/main/ofl/notosanstc', notice='assets/OFL-NotoSansTC.txt; unmodified font'),
                           dict(asset='render tools and codecs', license='See THIRD_PARTY_NOTICES.md', source='Canvas Web Standard; Rough.js MIT; Three.js MIT; FFmpeg build configuration'),
                       ], revisions=[dict(revision=1, prompt='範例不夠，增加 Kinesmith 與 Codex 的介紹作品。', date='2026-10-25')], scenes=scenes)
        (ROOT/f'project-{name}.json').write_text(json.dumps(project, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        cues = [dict(frame=i*180, time_seconds=i*6, title=title, sound_event='authored keys onset / chord boundary',
                     visual_event=f'chapter {i+1} begins', tolerance_frames=1) for i, title in enumerate(TITLES[name])]
        cues.append(dict(frame=1380, time_seconds=46, sound_event='final C-major resolution', visual_event='final card settled; hold to end', tolerance_frames=1))
        (ROOT/f'cues-{name}.json').write_text(json.dumps(cues, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        captions = []
        for i, title in enumerate(TITLES[name]):
            start, end = i*6, (i+1)*6
            captions.append(f'{i+1}\n00:00:{start:02},000 --> 00:00:{end:02},000\n{title}\n')
        (ROOT/f'{name}.srt').write_text('\n'.join(captions), encoding='utf-8')
        print(f'{name}: 8 chapters / 1440 frames / 48 seconds')


if __name__ == '__main__':
    main()
