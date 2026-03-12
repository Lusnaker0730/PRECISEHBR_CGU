    中文化策略                                                                                                          
    1. GitHub Issue Templates — 中文版                                                                               
  
    Issue Templates 本身用中文撰寫，因為這些內容未來會直接匯出成 TFDA 文件：

    - software_requirement.md → 標題前綴 [需求]，欄位：需求描述、臨床情境、驗收條件、風險等級
    - design_specification.md → 標題前綴 [設計]，欄位：設計方案、架構影響、關聯需求、安全考量
    - risk_analysis.md → 標題前綴 [風險]，欄位：危害情境、嚴重度、發生機率、風險控制措施、殘餘風險
    - verification_record.md → 標題前綴 [驗證]，欄位：測試目的、測試步驟、預期結果、關聯需求

    2. Git Commit / PR — 雙語

    - Commit message：英文（程式碼層級，維持國際慣例）
    - PR description：中文為主，用 PR Template 中文欄位（變更說明、測試紀錄、風險評估）
    - PR review comments：中文，這些會成為「設計審查紀錄」

    3. Labels — 中英對照

    IEC62304:需求 (requirement)
    IEC62304:設計 (design)
    IEC62304:驗證 (verification)
    ISO14971:風險 (risk)
    變更管制 (change-control)
    安全性等級-A / B / C (safety class)

    4. 測試報告輸出 — 中文

    pytest 搭配自訂 plugin 產出中文報告，包含：
    - 測試案例名稱：用中文 docstring（def test_egfr_calculation(): """eGFR 計算 - 低於閾值應判定為 HBR"""）
    - CI 產出的 HTML/XML 報告加上中文封面頁，標明：文件編號、版本、日期、測試環境、執行者
    - Coverage report 加上中文摘要說明

    5. 最終匯出結構

    regulatory_docs/
    ├── 軟體需求規格書_SRS.md        ← 從 [需求] Issues 自動彙整
    ├── 軟體設計規格書_SDS.md        ← 從 [設計] Issues + ADRs 彙整
    ├── 風險管理報告.md               ← 從 [風險] Issues 彙整
    ├── 軟體驗證報告.md               ← 從 pytest 報告 + [驗證] Issues 彙整
    ├── 追溯矩陣.md                  ← 需求↔設計↔測試↔風險 雙向對映表
    ├── 變更管制紀錄.md               ← 從 Git tags + PRs 彙整
    └── scripts/
        └── generate_regulatory_docs.py  ← GitHub API 自動抓取並產出上述文件

    6. 關鍵原則

    - Issue / PR 內容寫中文 → 未來匯出時不需翻譯
    - 程式碼、變數名、commit message 維持英文 → 維持程式碼可維護性
    - 測試 docstring 寫中文 → 匯出驗證報告時直接可讀
    - 自動化腳本產出的報告 → 中文模板，符合 TFDA 格式要求（文件編號、版本控制、簽核欄位）

    這樣日常開發用中文記錄需求、設計決策、風險分析、測試目的，程式碼層級維持英文，最後用腳本自動彙整成 TFDA
    要求格式的中文法規文件，不需要事後補寫。