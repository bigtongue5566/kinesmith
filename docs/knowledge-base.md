# 專業知識與創作方式

核心設計是 **Agent-Native、Skill-Driven、Code-First**。主要 Agent 使用目前模型做概念、程式與評審，沒有額外生成 AI、Agent runtime 或跨 Plugin 常駐服務。Helpers 只處理時間、格式、雜湊、渲染與交接等工程約束。

Skills 按需載入，入口沒有複製完整工具手冊：

|入口|用途|
|---|---|
|`kinesmith`|視覺概念、分鏡、六引擎選擇與創作|
|`kinesmith-setup`|環境、安裝、角色與工具診斷|
|`kinesmith-render`|逐影格渲染、合成、QA 與輸出|
|`kinesmith-audio-visual`|一般音訊、Opusmith、歌詞、人聲與三種協作|
|`kinesmith-revise`|指定場景修訂、版本與不相關內容保護|

詳細知識在 `skills/kinesmith/references/`：Visual Design、Animation、Motion Graphics、Generative Art、Three-Dimensional、Audio-Visual、Engines、Licenses。包含可執行 Canvas、p5、Three.js、Blender 與 Python 技法；原生完整場景在 `examples/`。範例是創作參考，不是所有作品的模板或能力上限。

可選角色由 `roles/*.md` 共用生成。Claude Code 使用 Plugin `agents/*.md`；Codex 使用 `adapters/codex/agents/*.toml` 安裝到作品 `.codex/agents`。不強制啟用所有角色，不更換父模型。原生平台的角色可用性與 Plugin Skills 的可用性分開驗證。

Motion Brief 建議記錄：用途、觀眾、比例、片長、主訊息、視覺概念、動作因果、引擎、場景時間、音畫 cue、素材權利及修訂範圍。Motion Report 應列實際引擎、版本、輸出測量、代表影格、同步精度、授權與尚未驗證項目；沒有實際檢查不可標為通過。

局部修改不重新初始化作品。source／params／工具設定決定場景快取，變更一個場景後只重渲染必要依賴，再合成新版；記錄 Prompt、來源 hash、parent version 及修訂理由。可編輯 HTML／Python／.blend 與音樂來源關聯持續保留。
