# 雙平台安裝驗證

2026-10-25（Asia/Taipei）以真實原生 CLI 在隔離本機設定目錄驗證，完整命令與原始結果在 `outputs/platform-validation.json`，發行包另附 `docs/platform-validation.json`。

|平台|實際結果|
|---|---|
|Codex CLI `0.164.0-alpha.11.1`|本地 marketplace 註冊、Plugin 安裝與清單查詢成功；app-server `skills/list` 探索到五個 enabled Skills，無 parse errors；`debug prompt-input` 的原生 `spawn_agent.agent_type` 探索到五個 Kinesmith 角色|
|Claude Code `2.1.310`|原生 Plugin validator、agents directory validator、marketplace 註冊、Plugin 安裝及清單查詢全部成功；`plugin details` 明確列出 Skills(5) 與 Agents(5)|
|共用內容|兩平台快取含五個 Skills 與五個 Claude agent 定義；抽樣 runtime source 與發行包一致|
|Codex 原生角色|五個有效 TOML 安裝到隔離作品 `.codex/agents`，不指定其他模型；安裝器可重複執行並保護使用者修改|
|已安裝 Plugin 的執行能力|兩平台分別從安裝快取建立獨立 uv 環境，離線執行作品驗證及真正 Canvas 渲染；兩支 WebM 均測得 640×360、24 FPS、48 影格、2 秒、VP9|

Skills 為 `kinesmith`、`kinesmith-setup`、`kinesmith-render`、`kinesmith-audio-visual`、`kinesmith-revise`。Claude agent 名稱為 `motion-director`、`motion-designer`、`generative-3d-artist`、`audio-visual-designer`、`render-visual-critic`；Codex 名稱加 `kinesmith_` 前綴並使用底線。

Codex 需要 trusted project 才會載入作品 `.codex/agents`；測試只信任自己的隔離 fixture，未改真實使用者專案或全局設定。此測試沒有登入、發送模型回合、呼叫生成 API 或實際委派原生角色。因此已證實的是可安裝、可解析、Skills／五個角色可探索及安裝後可執行渲染；**各平台模型實際遵循 Skills 並完成角色委派仍未驗證**。其餘引擎能力由獨立的真實渲染驗收記錄佐證，不能把兩者混稱同一次端到端測試。
