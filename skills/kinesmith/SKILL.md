---
name: kinesmith
description: Create professional editable motion graphics, animated explainers, typography, generative art or 3D films using Canvas, Rough.js, p5.js, Three.js, Manim or Blender. Use for Kinesmith visual creation and art direction.
---

# Kinesmith — 動態視覺創作

使用目前 Codex／Claude Code 模型做概念、分鏡、原生程式與修訂；不要呼叫其他生成模型。Helpers 約束時間、格式與重現性，創意由你決定。六個引擎保留完整原生 API，可自行組合、換構圖、寫 Shader 或 Geometry Nodes；範例是參考，沒有指定必用造型或風格。

先定位此 Skill 所在 Plugin 根目錄（本檔上兩層）；所有 `uv run --all-extras --project <plugin-root> kinesmith ...` 從已安裝套件執行，作品保存在使用者指定目錄。第一次使用讀 [setup](../kinesmith-setup/SKILL.md)。

理解用途、片長、比例、觀眾與可修改範圍；資訊不足採合理預設並記錄。保存原始 Prompt、繁體中文 Motion Brief、場景時間表、素材授權、可編輯來源與修訂理由。先設計主訊息、視線順序、動作因果與片尾落點，再寫動畫。做代表性影格及短動態，自我評審後擴展；不必為例行創作步驟等待批准。

按需讀取，避免一次載入所有知識：

- 構圖、色彩、字體、階層：[visual-design](references/visual-design.md)。
- Timing、Spacing、Easing、預備動作、弧線、連續性：[animation](references/animation.md)。
- Morph、遮罩、轉場、動態文字、視差：[motion-graphics](references/motion-graphics.md)。
- Noise、粒子、流場、圖樣：[generative-art](references/generative-art.md)。
- 幾何、材質、燈光、鏡頭、Shader、Geometry Nodes：[three-dimensional](references/three-dimensional.md)。
- 引擎選擇與原生來源契約：[engines](references/engines.md)。
- 音樂、歌詞、人聲：[audio-visual skill](../kinesmith-audio-visual/SKILL.md)。
- 渲染與查核：[render skill](../kinesmith-render/SKILL.md)。

可選用五個專業角色。Claude Code 使用 Plugin 原生 `kinesmith:motion-director` 等 agents；Codex 使用安裝到已信任作品 `.codex/agents/` 的 `kinesmith_motion_director` 等原生 `agent_type`。主要 Agent 決定是否委派；小修改直接完成，不強制啟動角色。角色共用 [roles](../../roles/)，不得額外指定其他生成模型。

正式輸出以前逐影格固定時間 `t = frame / fps`，固定隨機種子與工具版本。不要用播放速度、瀏覽器 requestAnimationFrame 的 wall clock 或錄螢幕當正式輸出。保存原生來源；不能只留下影片。

交付可播放影片、預覽、Contact Sheet、Motion Report 與來源路徑。報告區分測量、人工視覺檢查及尚未驗證；編碼成功不能證明文字未裁切或作品好看。
