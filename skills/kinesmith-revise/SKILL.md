---
name: kinesmith-revise
description: Revise selected Kinesmith scenes, typography, timing or effects while preserving unrelated sources, renders and linked music projects. Use for targeted animation changes and reproducible version history.
---

# 局部修訂

先讀 Prompt history、Motion Brief、project.json、來源及 render manifest，定位使用者指定的 scene ID 和修改範圍。保存修改前 source hashes、設定、版本與成品。只改指定場景或其明確依賴；不要因為調畫面而改音樂、歌詞或外部 Opusmith 專案。

更新原生來源與必要 params，記錄繁體中文修訂理由。用 CLI `revise --help` 查看版本工具；不以整個作品重新初始化來修改一個場景。重渲染該場景，再重合成完整成品；長度或轉場改變時檢查相鄰場景與全局 cue。

比較前後 manifest：未修改場景的輸入雜湊、可重現設定與快取應相同。若有 shared source 變動，明確列出受影響場景並重渲染。檢查修訂畫面及前後過渡，交付新成品、revision 記錄與未受影響項目的實際驗證結果。
