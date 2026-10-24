# 安裝與本機執行

需要 `uv` 與支援本機 Plugin 的 Codex／Claude Code。Python 由 uv 管理；沒有 API key、付費 renderer 或額外生成模型需求。工具首次下載需要網路，下載後可用 `uv run --all-extras --offline` 重現。Python 套件平台 wheel 與瀏覽器／GPU 支援依 OS 實際情況判斷。

在解壓後 Plugin 根目錄執行：

```powershell
uv sync --python 3.11 --all-extras --locked
uv run --all-extras playwright install chromium
uv run --all-extras scripts/bootstrap_web.py
uv run --all-extras kinesmith doctor
uv run --all-extras scripts/validate_plugins.py
```

受限環境可把 `UV_CACHE_DIR` 與 `UV_PYTHON_INSTALL_DIR` 設成可寫位置；不要變更使用者 HOME。`KINESMITH_CHROMIUM` 可指定既有 Chromium。以上安裝全部引擎；只需要瀏覽器時可省略 `--all-extras`。**uv run 也需保持同一 extras 選項，否則 uv 會移除先前同步的選用引擎**。完整版本以 `uv.lock` 為準；目前 Blender helper 使用 bpy wheel，doctor 會回報實際可用性。FFmpeg 由 imageio-ffmpeg 提供的本地程式使用，保留其實際 build 與 encoder 資訊。

## Codex

先建立發行包與本地 marketplace：

```powershell
uv run --all-extras scripts/build_release.py
codex plugin marketplace add "<Kinesmith>/dist/marketplace"
codex plugin add kinesmith@kinesmith-local
codex plugin list --json
```

目前測試版 Codex 使用 `plugin add`；其他版本先看 `codex plugin --help`。安裝後開新聊天，確認 `$kinesmith` 或 namespaced Skills 出現。Plugin 不攜帶額外 MCP server。

Codex 原生自訂 agents 使用作品範圍 `.codex/agents/*.toml`，不假設 Plugin 的 Claude `agents/*.md` 會被 Codex 自動載入：

```powershell
uv run --all-extras scripts/install_codex_roles.py --project "<作品目錄>"
```

安裝器遇到已修改的同名角色拒絕覆寫，不更改全局設定。Codex 必須將該作品目錄視為 trusted project 才會載入其原生自訂角色；在 Codex 正常開啟並信任該作品後開新聊天。可委派 `kinesmith_motion_director`、`kinesmith_motion_designer`、`kinesmith_generative_3d_artist`、`kinesmith_audio_visual_designer`、`kinesmith_render_visual_critic`。原生 spawn 的 `agent_type` inventory 應包含五個角色；不指定模型，繼承目前對話。安裝器不自動替使用者信任真實專案。

## Claude Code

同一個發行 Plugin 含 `.claude-plugin/plugin.json`、共用 `skills/` 及原生 `agents/`：

```powershell
claude plugin marketplace add "<Kinesmith>/dist/marketplace"
claude plugin install kinesmith@kinesmith-local --scope user
claude plugin list --json
```

也可用 `claude --plugin-dir "<Kinesmith>"` 直接測試。Skills 使用 `/kinesmith:kinesmith` 等 namespaced 名稱；agent 使用 `kinesmith:motion-director` 等。所有 Claude agents 明確設 `model: inherit`。不需同時啟用五個角色。

## 驗證與證據

`uv run --all-extras scripts/validate_plugins.py --native` 會在 `.cache/platform-validation-*` 使用隔離的產品設定目錄執行已存在的 Codex／Claude CLI，安裝本地包並驗證 Skills／agents；Codex 另做 app-server Skills discovery，沒有登入或模型生成呼叫。加 `--render-smoke` 可從兩平台實際安裝的 Plugin 分別執行 Canvas 渲染，以確認封裝資源可執行。可用 `--claude <binary>` 指定既有官方 CLI。結果保存 `outputs/platform-validation.json`；缺 CLI 或被平台拒絕時顯示失敗／未驗證，不能標通過。

Codex 透過 `debug prompt-input` 原生 `spawn_agent.agent_type` 清單確認五個角色可用；Claude 透過 `plugin details kinesmith@kinesmith-local` 確認 Skills(5)／Agents(5)。測試只對自己產生的隔離作品設 trust。CLI 安裝、檔案一致與原生 discovery 不等於已登入模型的自然語言創作驗證；後者需要在各自平台的新聊天實際要求創作並看渲染結果。此差異在驗證報告保留，發行包另附 `docs/platform-validation.json` 原始證據。

官方格式來源（2026-10-25 查閱）：[OpenAI Plugin packaging](https://developers.openai.com/plugins/build/plugins)、[Codex native agents](https://learn.chatgpt.com/docs/agent-configuration/subagents)、[Claude Plugin manifest](https://code.claude.com/docs/en/plugins-reference)、[Claude subagents](https://code.claude.com/docs/en/sub-agents)。
