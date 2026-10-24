# 商業創作、軟體與素材授權

Kinesmith 自有程式、Skills、知識內容與原創動畫範例採 MIT；原創測試音訊另附 CC0 聲明。Plugin 不呼叫生成式模型或外部付費 API。套件能免費取得不代表所有外部素材已授權。

| 項目 | 實際使用／義務 |
|---|---|
| Canvas／WebGL | Web 標準，瀏覽器引擎本身另有第三方授權 |
| Rough.js 4.6.6 | MIT，保留 copyright 與 LICENSE |
| Three.js 0.180.0 | MIT，保留 copyright 與 LICENSE |
| p5.js 1.11.11 | LGPL-2.1，保留聲明、允許替換 library，散布相應來源及修改來源；Kinesmith 不修改它 |
| Manim Community | MIT；其依賴 Cairo、Pango、FFmpeg、字型另有各自授權 |
| Blender bpy 4.2.0 | GPL-3.0-or-later；安裝工具與創作輸出的權利分開處理。預設 Plugin ZIP 不重包 bpy binary |
| FFmpeg | 依 build 而異。本次 imageio-ffmpeg 0.6.0 的 Windows binary 顯示 FFmpeg 7.1、GPL v3 or later、啟用 GPL／version3／libx264／libx265。不是全數 LGPL build |
| Pillow／NumPy／SciPy／Playwright | 套件與依賴有獨立授權；實際版本及 metadata 存於 software-inventory.json |

`uv run --all-extras scripts/bootstrap_web.py` 驗證 npm tarball 的 SHA512，保存 JS、原 LICENSE、固定版本與檔案 SHA256。`vendor/source/*.tgz` 保存散布之 web library 的對應原套件來源，p5 npm 套件內有完整 `lib/p5.js` 未壓縮來源。修改 library 時需一併提供對應修改來源；不要只更改 minified 檔。固定來源與 tarball URL 記錄於 vendor/manifest.json。release build 應含 vendor、LICENSE 與來源 archives。

`uv run --all-extras scripts/license_inventory.py` 產出目前環境的 metadata 清單、`ffmpeg-license.txt`、`ffmpeg-buildconf.txt`。這是實際工具清單，非法律相容性自動判定。Plugin 不含 Python、Chromium、Manim、Blender、FFmpeg 執行檔，使用 uv／bootstrap 由官方套件來源安裝。若另行封裝或散布這些工具，須履行該 build 的 LICENSE、相應原始碼、修改與其他第三方條件；不能只隨附 Kinesmith 的 MIT 聲明。MP4／AAC／H.264 的專利條件可能因使用方式與地區不同；預設提供 WebM VP9／Opus。

內附 Canvas／Manim 排版使用作業系統 Arial；不散布 Microsoft 字型檔。作品需要跨平台字型一致時，請在 assets 放入可合法再散布的 OFL 字型、原 LICENSE 與雜湊，在 dependencies 宣告並用 @font-face／原生引擎指定。Blender 範例使用隨 Blender 提供的 Bfont。字型作為影片圖像呈現與散布字型檔是不同的權利。

`examples/introductions/` 的兩部 1080p 介紹短片已依上述方式內附 Noto Sans TC Variable 原字型及 OFL-1.1 完整聲明，在 project dependencies 記錄字型檔，並由瀏覽器完成載入才逐格渲染。兩支原創配樂與 MIDI 採 CC0-1.0，使用 `compose.py` 的振盪器與噪聲合成，無取樣、聲庫或外部生成服務；圖形與程式採 MIT。Codex 的片名與產品資訊只作描述，影片明確標示為獨立介紹，沒有官方背書。

Codex 片修訂 3 的開場／片尾使用官方安裝包內未修改的雲形 Codex App 圖示。該圖示仍是 OpenAI 品牌資產，依 [OpenAI Marks 條款](https://openai.com/brand/#usage-terms)，不受本專案 MIT／配樂 CC0 授權涵蓋；在 project licenses 與 `assets/CODEX-BRAND.md` 保存來源及 SHA256。原始圖示為 104×104 RGBA，本片只按原比例縮放顯示，未重繪圖案或改變顏色；不把它作為 Kinesmith 的自有品牌。

Opusmith MIT 範例、Score 與 USTX 的來源／commit／檔案校驗記錄於 examples/opusmith-v0.1.0/PROVENANCE.json 與 examples/opusmith-v0.2.0/PROVENANCE.json。含人聲的真實片段另見 examples/collaboration/music-first/PROVENANCE.json、LICENSE_REVIEW.md、vocal-receipt.json。該傳統 UTAU 聲庫的現行官方條款已逐項查核，結論只適用本範例的實際音源；其他音樂著作、取樣、人聲聲庫、角色圖像與音訊仍各自保存來源與允許的用途。OpenUtau／USTX 能成功渲染，不代表任意聲庫或角色可以商用。未知的資產授權一律保持 `unverified`，不因影片輸出成功提升狀態。

正式作品的 `licenses` 帳本至少記錄 asset／tool、來源、版本或 SHA256、授權、商用及再散布限制、確認方式。請只對實際查證項目宣稱已確認；本清單不能取代使用者加入素材的授權紀錄。

Opusmith 介紹片的七軌原創配樂、音符及 MIDI 採 CC0-1.0，實際使用上游 v0.2.0 原生合成與 Pedalboard。上游 runtime／研究文件維持 MIT 並附原始 LICENSE；音樂環境的實際套件版本與授權 metadata 在 `examples/introductions/music-opusmith/SOFTWARE.json`。作品包沒有聲庫、權重、取樣或第三方執行檔；DSP、FFmpeg 與字型仍依各自授權。原始來源與實測界限見 [本片 Motion Report](opusmith-introduction.md)。
