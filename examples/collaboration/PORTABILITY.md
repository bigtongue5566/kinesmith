# 可攜作品與原始驗收資料

搬移或解壓後請使用 `music-first/project-portable.json` 或 `visual-first/project-portable.json`。這兩份作品使用同目錄的 `.portable.av.json` 交接檔，來源、音訊與場景仍指向既有可編輯檔案，沒有複製另一套音樂作品。

原始 `project.json`、原始 AV 合約、影片與 render／QA 報告保留本次驗收時的內容與雜湊，供版本與修訂稽核。歷史來源中的原絕對路徑不是搬移後的搜尋規則；外部的 upstream-import 是原曲匯入紀錄，重建這份稽核資料仍需要原始 Opusmith 專案。

在搬移後的 Plugin 原始碼根目錄執行：

```powershell
uv run --all-extras kinesmith verify-sources "examples/collaboration/music-first/music.portable.av.json"
uv run --all-extras kinesmith render "examples/collaboration/music-first/project-portable.json"
uv run --all-extras kinesmith render "examples/collaboration/visual-first/project-portable.json"
```

`verify-sources` 以交接檔所在目錄為 base，驗證每個已宣告相對路徑與 SHA256，不回退舊機器的原絕對位置。播放／渲染直接使用作品內的場景、音訊與相對交接檔。如果需要讓 AV 檔內的絕對 `path` 也更新至新位置，可明確執行：

```powershell
uv run --all-extras kinesmith rebase-contract "examples/collaboration/music-first/music.portable.av.json" --base "examples/collaboration/music-first" --output "examples/collaboration/music-first/music.rebased.av.json"
```

只有全部來源與音訊雜湊相同才會輸出新檔。缺檔、越界或 checksum 不符會中止，不會修改音訊、Score 或原始來源。

`uv run --all-extras python scripts/verify_collaboration_portability.py` 可重建旁邊的可攜合約／作品設定，複製整份協作作品（略過快取）到 `.cache/collaboration-moved*`，驗證四份合約的 24 個參照全部在搬移後的作品內，並驗證兩份 project-portable。結果記錄在 `portability.json`；該驗證不冒充重新編碼或主觀影音品質評估。
