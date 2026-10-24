# 代表影格人工檢視

本次 Agent 實際開啟三張 Contact Sheet：music-first/qa、visual-first/qa、visual-first/joint-qa。每張 12 個代表影格，影片均為 640×360、24 FPS、144 frames／6 秒。

- Music-First：日文歌詞可見，未見文字越界或全黑；原始 Score 的音節依序為「よ／る／の／ま／ち／に／ひ／か／り」。最後保留刻意的歌詞間歇；QA 的定格提示對應延長音節與該留白。畫面掃色是視覺裝飾，不是音素精確同步。
- Visual-First：文字與圓弧完整呈現；前段青色、後段珊瑚色。開場只有 KINE 的影格是遮罩入場過程。第 72 frame 對應第二場景／Score 第 6 beat，明確 cue 為 3 秒。
- Joint：前三秒構圖與原片相同，第二場景變成紫色。72 個無關場景原始 PNG SHA256 逐一相同且重用快取；音樂 Master SHA256 相同。

這是代表影格的實際視覺檢視，未宣稱逐影格確認全片動作流暢、文字閱讀速度、精確演唱 onset、實際音素時序或主觀聆聽品質。真正歌聲與原伴奏都來自 Opusmith v0.2.0 的已渲染 Master；保留上游收據及評估限制。

Visual-First 需求來源另存 `picture-v1-request.json`，其 SHA256 等於最初送出的畫面版本。第一份交接需求原檔保留為 `visual-request-v1-original.av.json`（原先來源路徑指向之後會修訂的 project.json，因此 verify-sources 會正確回報 changed）；`visual-request.av.json` 指向保存的同內容版本，讓後續搬移與核對更清楚。音樂回傳與首次驗收的 request SHA256 仍可在保留原檔驗證。
