# Opusmith 介紹片｜事實來源與權利

2026-10-25 查核 GitHub API 的最新穩定 Release：v0.2.0，發布於 2026-10-24 19:54:21 UTC。main 與 Release 目前均指向 `328e630f33af4b8b0ebe178895d1f87120532875`；影片不是對未來版本的功能保證。

| 片中內容 | 上游一手來源 |
|---|---|
| 目前 Codex／Claude Code Agent 作曲、編曲、合成與修訂；保留 MIDI、JSON Score、Python、Stems、來源與版本 | [固定版本 README](https://github.com/bigtongue5566/opusmith/blob/328e630f33af4b8b0ebe178895d1f87120532875/README.md) |
| 本地 OpenUtau、USTX、傳統 UTAU／DiffSinger 可選能力；聲庫與聲碼器授權需分開查核 | [v0.2.0 Release](https://github.com/bigtongue5566/opusmith/releases/tag/v0.2.0)、[人聲指南](https://github.com/bigtongue5566/opusmith/blob/328e630f33af4b8b0ebe178895d1f87120532875/docs/VOCALS.md) |
| 上游驗收的實測範圍與限制 | [VALIDATION](https://github.com/bigtongue5566/opusmith/blob/328e630f33af4b8b0ebe178895d1f87120532875/docs/VALIDATION.md) |
| Opusmith 與 Kinesmith 透過 Skills、可攜資料與版本關聯協作 | 本 repository 的 `docs/opusmith.md`、實際產生的 `opusmith-music.av.json`；不假設通用跨 Plugin API |

研究文件副本、MIT LICENSE 與各檔 SHA256 在 `research/opusmith-v0.2.0/`。GitHub 網頁的快取 README 曾顯示舊版，故實作依 GitHub API 最新 Release 與固定 commit 的實際檔案查核。

本片實際使用七軌器樂合成；沒有歌聲、聲庫、DiffSinger 權重、外部生成服務或人聲旁白。第六幕為 USTX 編輯的概念示意，不能當作歌聲實測或精確音素時間。聲庫與聲碼器授權的提示不是宣稱所有選項已可商用；本片不使用那些資產。

上游目前沒有隨 repository 提供品牌圖示，本片直接以字型排印 Opusmith 名稱，唱片與合成器是本片原創插畫，沒有宣稱其為官方 logo。動畫／工具程式 MIT，原創配樂、音符與 MIDI CC0-1.0；Noto Sans TC 原字型 OFL-1.1。上游 runtime／文件維持 MIT 與其 copyright，原始聲明隨附；實際 DSP、FFmpeg、Chromium 依第三方聲明，不重包其二進位。
