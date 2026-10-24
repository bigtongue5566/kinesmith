---
name: kinesmith-setup
description: Install, inspect or repair Kinesmith local dependencies and native Codex or Claude Code plugin roles. Use for Kinesmith setup and environment diagnostics.
---

# 安裝與環境

從本檔上兩層找到 Plugin 根目錄；完整六引擎環境執行 `uv sync --python 3.11 --all-extras --locked`。後續 `uv run` 也保持 `--all-extras`，避免 uv 移除選用引擎。Python 一律使用 uv，不使用系統 pip；瀏覽器函式庫由 `scripts/bootstrap_web.py` 鎖定版本與完整性下載，不需 npm。引擎安裝方式及確切命令見 [安裝文件](../../docs/installation.md)。不需 API key、付費軟體或第二個 LLM。

執行 `uv run --all-extras --project <plugin-root> kinesmith doctor` 取得實際可用工具。只需 Canvas／音訊時可在 sync 和 run 都省略 `--all-extras`。缺依賴清楚報告，不把圖片、空白框或模擬結果冒充該引擎渲染。

Plugin 安裝與渲染工具安裝是不同工作。Codex 使用本機 marketplace 和 `codex plugin add`；Claude Code 使用 `claude plugin install` 或 `--plugin-dir`。查看 `--help` 確認當前平台版本，別猜旗標。Codex 原生角色另外用 `uv run --all-extras scripts/install_codex_roles.py --project <作品目錄>` 安裝；既有不同內容不覆寫。Claude 由 Plugin 的 `agents/` 原生載入。

執行 `uv run --all-extras scripts/validate_plugins.py` 做封裝、路徑及角色驗證；它不是平台實際載入證明。若可用，執行 `uv run --all-extras scripts/validate_plugins.py --native --render-smoke` 做原生載入及安裝後渲染驗證，查閱 `outputs/platform-validation.json` 實際結果。只報實際成功項目；登入或模型回覆測試未執行時不可宣稱已端到端驗證。
