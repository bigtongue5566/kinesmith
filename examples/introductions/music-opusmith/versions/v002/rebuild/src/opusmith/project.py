"""Local project provenance, immutable version snapshots and evidence-based reports."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .audio import render
from .midi import write_midi
from .model import Score, inside, json_write


def sha(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def now() -> str:
    return datetime.now(UTC).isoformat()


def create_project(root: Path, prompt: str, brief: str, *, source: Path | None = None,
                   author: str = "user") -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root/"ORIGINAL_PROMPT.txt").write_bytes(prompt.encode("utf-8"))
    (root/"CREATIVE_BRIEF.md").write_text(brief, encoding="utf-8")
    (root/"versions").mkdir()
    (root/"assets").mkdir()
    json_write(root/"assets.json", [])
    json_write(root/"project.json", {"format_version": 1, "created_at": now(),
               "original_prompt_sha256": sha(root/"ORIGINAL_PROMPT.txt"),
               "prompt_author": author, "storage": "local"})
    if source:
        shutil.copyfile(source, root/"source.py")
    append_history(root, prompt, version=None, kind="original", author=author)
    return root


def verify_history(root: Path) -> list[dict]:
    metadata = json.loads((root/"project.json").read_text(encoding="utf-8"))
    if sha(root/"ORIGINAL_PROMPT.txt") != metadata["original_prompt_sha256"]:
        raise ValueError("original prompt was modified")
    events, previous = [], ""
    for line in (root/"PROMPT_HISTORY.jsonl").read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        digest = event.pop("sha256")
        canonical = json.dumps(event, ensure_ascii=False, sort_keys=True).encode()
        if event["previous_sha256"] != previous or hashlib.sha256(canonical).hexdigest() != digest:
            raise ValueError("history hash chain was modified")
        event["sha256"] = digest
        events.append(event)
        previous = digest
    if not events or events[0]["text"] != (root/"ORIGINAL_PROMPT.txt").read_bytes().decode("utf-8"):
        raise ValueError("history must begin with the exact original prompt")
    return events


def append_history(root: Path, text: str, *, version: str | None, kind: str = "revision",
                   author: str = "user", assumptions: list[str] | None = None):
    history = root/"PROMPT_HISTORY.jsonl"
    events = verify_history(root) if history.exists() else []
    event = {"time_utc": now(), "kind": kind, "author": author, "text": text,
             "version": version, "assumptions": assumptions or [],
             "previous_sha256": events[-1]["sha256"] if events else ""}
    canonical = json.dumps(event, ensure_ascii=False, sort_keys=True).encode()
    event["sha256"] = hashlib.sha256(canonical).hexdigest()
    with history.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False)+"\n")


def _asset_check(root: Path, score: Score) -> list[dict]:
    from .assets import approved

    ledger = json.loads((root/"assets.json").read_text(encoding="utf-8"))
    for track in score.tracks:
        if track.vocal or track.patch.engine != "sample":
            continue
        file = inside(root, track.patch.sample)
        if not file.is_file():
            raise ValueError(f"missing sample: {track.patch.sample}")
        record = next((a for a in ledger if a["file"] == track.patch.sample), None)
        if record is None or not approved(record) or record["sha256"] != sha(file):
            raise ValueError(f"sample needs verified provenance/hash: {track.patch.sample}")
        if track.id not in record.get("used_by_tracks", []):
            raise ValueError(f"asset usage location missing: {track.id}")
    return ledger


def snapshot_runtime(root: Path, repository: Path):
    """Copy the small implementation + lock, never a venv or sample library."""
    dest = root/"rebuild"
    dest.mkdir(exist_ok=False)
    shutil.copytree(repository/"src", dest/"src", ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(repository/name, dest/name)
    if (repository/"LICENSE").exists():
        shutil.copyfile(repository/"LICENSE", dest/"LICENSE")
    # Optional singing can be rebuilt without relying on the Agent conversation.
    for relative in ("adapters/openutau", "skills/opusmith/references/vocals"):
        if (repository/relative).is_dir():
            shutil.copytree(repository/relative, dest/relative,
                            ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))
    if (repository/"scripts/setup_vocals.py").is_file():
        (dest/"scripts").mkdir(exist_ok=True)
        shutil.copyfile(repository/"scripts/setup_vocals.py", dest/"scripts/setup_vocals.py")


def publish(root: Path, score: Score, *, request: str, author: str = "agent",
            assumptions: list[str] | None = None, sample_rate: int = 44100, mp3: bool = True,
            commercial_ready: bool = True) -> Path:
    """Versioned render. Failures leave a labelled failed version, never a success report."""
    root = Path(root)
    score = Score.model_validate(score.model_dump())
    verify_history(root)
    assets = _asset_check(root, score)
    from .vocals import verify_vocals
    vocals = verify_vocals(root, score, commercial=commercial_ready)
    lock = root/".publishing"
    with lock.open("x", encoding="utf-8"):
        pass
    try:
        used = [int(p.name[1:]) for p in (root/"versions").glob("v*")
                if p.is_dir() and p.name[1:].isdigit()]
        version = f"v{max(used, default=0)+1:03d}"
        out = root/"versions"/version
        out.mkdir(exist_ok=False)
        score.save(out/"score.json")
        shutil.copyfile(root/"CREATIVE_BRIEF.md", out/"CREATIVE_BRIEF.md")
        shutil.copyfile(root/"assets.json", out/"assets.json")
        if (root/"LYRICS.md").is_file():
            shutil.copyfile(root/"LYRICS.md", out/"LYRICS.md")
        if vocals:
            json_write(out/"vocals.json", vocals)
            for track in score.tracks:
                if track.vocal:
                    for relative in track.vocal.model_dump().values():
                        target = inside(out, relative)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(inside(root, relative), target)
                    phonemes = inside(root, track.vocal.receipt).parent/"phonemes.json"
                    if phonemes.exists():
                        shutil.copyfile(phonemes, inside(out, track.vocal.receipt).parent/phonemes.name)
                    record = next(v for v in vocals if v["track_id"] == track.id)
                    for name in record.get("support_files", {}):
                        relative = (Path(track.vocal.receipt).parent/name).as_posix()
                        target = inside(out, relative)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(inside(root, relative), target)
        for source_file in root.glob("*.py"):
            shutil.copyfile(source_file, out/source_file.name)
        if (root/"source").is_dir():
            shutil.copytree(root/"source", out/"source", ignore=shutil.ignore_patterns("__pycache__"))
        if (root/"rebuild").is_dir():
            # Freeze the implementation actually executing this render, not an older
            # copied runtime. Keep dependency locks and current sources beside the version.
            runtime = out/"rebuild"
            runtime.mkdir()
            for name in ("pyproject.toml", "uv.lock"):
                shutil.copyfile(root/"rebuild"/name, runtime/name)
            for name in ("scripts", "adapters", "skills"):
                if (root/"rebuild"/name).is_dir():
                    shutil.copytree(root/"rebuild"/name, runtime/name,
                                    ignore=shutil.ignore_patterns("bin", "obj", "__pycache__"))
            shutil.copytree(Path(__file__).resolve().parent, runtime/"src/opusmith",
                            ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(runtime/"src", root/"rebuild/src", dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        append_history(root, request, version=version, author=author, assumptions=assumptions)
        try:
            write_midi(score, out/"multitrack.mid")
            result = render(score, root, out/"audio", sample_rate=sample_rate, mp3=mp3)
            from .assets import write_credits

            write_credits(out/"ASSET_CREDITS.md", assets)
            if vocals:
                with (out/"ASSET_CREDITS.md").open("a", encoding="utf-8") as credits:
                    credits.write("\n## 合成歌聲\n\n")
                    for v in vocals:
                        credits.write(f"- {v['track_id']}：{v['license']['credit']}；"
                                      f"[使用條款]({v['license']['terms_url']})。\n")
                        if v.get("evaluation_only"):
                            credits.write("  本作品僅供非商業技術評估；尚未核准整條歌聲鏈的商業用途。\n")
            _reports(score, result, out, verify_history(root), assets)
            files = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob("*") if p.is_file()}
            json_write(out/"version.json", {"status": "complete", "time_utc": now(), "sha256": files,
                                          "commercial_ready": commercial_ready})
        except Exception as exc:
            json_write(out/"version.json", {"status": "failed", "error": str(exc), "time_utc": now()})
            raise
        # Current pointers are written only after all required artifacts are complete.
        score.save(root/"score.json")
        json_write(root/"CURRENT.json", {"version": version, "path": f"versions/{version}"})
        for name in ("COMPOSITION_REPORT.md", "QUALITY_REPORT.md", "ASSET_CREDITS.md"):
            shutil.copyfile(out/name, root/name)
        return out
    finally:
        lock.unlink(missing_ok=True)


def _reports(score: Score, result: dict, out: Path, history: list[dict], assets: list[dict]):
    master = result["master"]
    content = [f"# {score.title} — 作品構成報告", "",
               f"音樂時間 {score.seconds:.3f} 秒；含尾音 WAV {master['duration_seconds']:.3f} 秒。",
               f"{score.bpm:g} BPM；調性標籤：{score.key}（創作者標註，非自動判定）；"
               f"{score.meter[0]}/{score.meter[1]} 拍。", "",
               f"風格標籤：{', '.join(score.genres)}（創作意圖，非分類器驗證）。", "",
               "## 實際段落", "", "| 段落 | 起訖秒 | 音軌（有音符起點） |", "|---|---|---|"]
    for section in score.sections:
        tracks = [t.name for t in score.tracks if any(section.start <= n.start < section.end
                                                      for n in t.notes)]
        content.append(f"| {section.name} | {section.start*60/score.bpm:.2f}–"
                       f"{section.end*60/score.bpm:.2f} | {', '.join(tracks)} |")
    content += ["", "## 音符、音源與處理", ""]
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    for t in score.tracks:
        pitches = [n.pitch for n in t.notes]
        pcs = sorted(set(n % 12 for n in pitches))
        prefix = ", ".join(f"{n.start:g}:{n.pitch}/{n.duration:g}" for n in t.notes[:12])
        content += [f"### {t.name} ({t.id})", "",
                    f"{len(t.notes)} 個音符；音域 MIDI {min(pitches) if pitches else '—'}–"
                    f"{max(pitches) if pitches else '—'}；音高類別 {', '.join(names[n] for n in pcs)}。",
                    f"前 12 個實際音符（拍:音高/長度）：{prefix}",
                    f"音源 `{'OpenUtau' if t.vocal else t.patch.engine}`；可重現參數：", "```json",
                    json.dumps(t.vocal.model_dump() if t.vocal else t.patch.model_dump(exclude={"wavetable"}), ensure_ascii=False), "```",
                    f"增益 {t.gain_db:g} dB，Pan {t.pan:g}；{len(t.controls)} CC、"
                    f"{len(t.bends)} Pitch Bend、{len(t.automation)} Automation lanes。",
                    f"實際 DSP 設定：`{json.dumps(t.effects.model_dump(), ensure_ascii=False)}`", ""]
    content += ["## 創作決策與版本", "",
                "以下為創作者註記；可觀測音樂資料以上方音符及 score.json 為準。", ""]
    content += [f"- {d}" for d in score.decisions]
    content += ["", f"外部／本地素材紀錄 {len(assets)} 筆；詳 ASSET_CREDITS.md。", "",
                "母帶："+result["mastering"]["method"],
                f"實際母帶增益 {result['mastering']['gain_db']:.2f} dB；"
                f"LUFS 目標達成：{result['mastering']['target_attained']}。", "",
                "Stems 為同起點、含個別效果及 ducking 的 24-bit FLAC；相加對應浮點 premaster，"
                "Master 另施加 render.json 記載的固定增益。", "",
                "音源由 score.json 記載；附有 vocal 的音軌使用本地 OpenUtau 歌聲渲染，"
                "其聲庫、引擎、授權與原始乾聲詳 vocals.json 及對應 receipt.json。"
                "其餘音軌使用本地合成或已核對素材。未呼叫外部作曲／音訊生成服務。", ""]
    content += [f"- {e['time_utc']} · {e['version'] or '初始化'} · {e['author']} · {e['text']}"
                for e in history]
    content += ["", "## 未完成／評估限制", "", master["subjective_listening"],
                "未自動驗證風格辨識、藝術感染力或全部自然語言條件；需由目前 Agent 對照原始提示詞。"]
    if (out/"vocals.json").exists():
        vocal_records = json.loads((out/"vocals.json").read_text(encoding="utf-8"))
        if any(v.get("evaluation_only") for v in vocal_records):
            content += ["", "**此版本僅供非商業技術評估，歌聲整條商業授權鏈尚未核准。**"]
    (out/"COMPOSITION_REPORT.md").write_text("\n".join(content)+"\n", encoding="utf-8")
    quality = ["# 品質報告", "", "## 工程正確性", "",
               "Score 已通過範圍／段落／引用驗證；MIDI、真實 WAV、Stems 與版本快照已產生。",
               f"WAV 非靜音：{master['non_silent']}；有限數值：{master['finite']}；"
               f"削波樣本：{master['clipped_samples']}。", "", "## 使用者需求符合度", "",
               "未由訊號分析器判定。請逐項對照 ORIGINAL_PROMPT.txt 與 Prompt History。", "",
               "## 音訊技術量測", "", "```json", json.dumps(master, ensure_ascii=False, indent=2),
               "```", "", "4 倍過取樣峰值為估計值，非認證 true-peak meter；MP3 有損編碼可能增加峰值。",
               "", "## 主觀音樂品質", "", master["subjective_listening"]]
    (out/"QUALITY_REPORT.md").write_text("\n".join(quality)+"\n", encoding="utf-8")
