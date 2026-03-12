# PRECISE-HBR 法規追溯範例

## 完整追溯鏈示意圖

```
                    ┌─────────────────────────────────┐
                    │  TFDA 軟體確效報告提交物          │
                    │  (Software Validation Report)    │
                    └──────────────┬──────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│ 軟體需求規格     │  │ 風險管理檔案      │  │ 軟體確效測試報告     │
│ (SRS)           │  │ (ISO 14971)      │  │ (V&V Report)        │
│                 │  │                  │  │                     │
│ GitHub Issues   │  │ GitHub Issues    │  │ CI/CD Artifacts     │
│ label:          │  │ label:           │  │                     │
│  requirement    │  │  risk            │  │ - JUnit XML         │
│                 │  │  ISO-14971       │  │ - HTML Report       │
│ ┌─────────────┐ │  │ ┌──────────────┐ │  │ - Coverage Report   │
│ │ SRS-001     │◄├──┤►│ RISK-001     │ │  │ - Traceability.json │
│ │ 分數計算     │ │  │ │ 計算錯誤風險  │ │  │                     │
│ └──────┬──────┘ │  │ └──────┬───────┘ │  │                     │
│        │        │  │        │         │  │                     │
│ ┌──────▼──────┐ │  │        │         │  │                     │
│ │ SRS-002     │◄├──┤────────┘         │  │                     │
│ │ 風險分類     │ │  │                  │  │                     │
│ └─────────────┘ │  └──────────────────┘  └─────────────────────┘
└────────┬────────┘                                  ▲
         │                                           │
         ▼                                           │
┌─────────────────┐     ┌──────────────────┐         │
│ 軟體設計規格     │     │ 測試案例          │         │
│ (SDS)           │     │ (Test Cases)     │         │
│                 │     │                  │         │
│ GitHub Issues   │     │ GitHub Issues    │         │
│ label: design   │     │ label: test      │         │
│                 │     │                  │         │
│ ┌─────────────┐ │     │ ┌──────────────┐ │         │
│ │ SDS-001     │◄├─────┤►│ TC-001       │─┼─────────┘
│ │ 計算模組設計  │ │     │ │ Golden Data  │ │   pytest 執行結果
│ └─────────────┘ │     │ └──────────────┘ │   自動上傳為 artifact
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────────────────┐
│ Pull Request    │     │ Git History                       │
│                 │     │                                  │
│ ┌─────────────┐ │     │ commit abc123                    │
│ │ Regulatory  │ │     │   "feat: implement PRECISE-HBR   │
│ │ Traceability│ │     │    score calculation"             │
│ │             │ │     │                                  │
│ │ Implements: │ │     │   PR #42 → SRS-001, SDS-001     │
│ │  SRS-001    │ │     │   Mitigates: RISK-001            │
│ │ Design:     │ │     │   Verifies: TC-001               │
│ │  SDS-001    │ │     │                                  │
│ │ Mitigates:  │ │     │ tag: v1.0.0                      │
│ │  RISK-001   │ │     │   → triggers regulatory-         │
│ │ Verifies:   │ │     │     artifacts.yml workflow        │
│ │  TC-001     │ │     │   → auto-generates all reports   │
│ └─────────────┘ │     └──────────────────────────────────┘
└─────────────────┘

```

## 範例檔案清單

| 檔案 | 對應 TFDA 文件 | 說明 |
|------|--------------|------|
| `issue-SRS-001.md` | 軟體需求規格書 (SRS) | 「系統應計算 PRECISE-HBR 分數」需求定義 |
| `issue-SDS-001.md` | 軟體設計規格書 (SDS) | 計算模組的設計決策與介面規格 |
| `issue-RISK-001.md` | 風險管理報告 (ISO 14971) | 「計算錯誤」的風險分析與控制措施 |
| `issue-TC-001.md` | 測試案例文件 (V&V) | Golden Dataset 測試案例定義 |

## 自動產出的報告（每次跑 pytest）

| 檔案 | 說明 |
|------|------|
| `reports/test-traceability.md` | 追溯矩陣：每個測試 → 需求/風險/設計 |
| `reports/test-traceability.json` | 機器可讀的追溯資料 (可匯入其他工具) |
| `reports/demo-test-results.xml` | JUnit XML (可匯入任何 CI/CD 報告工具) |
| `reports/demo-test-report.html` | 漂亮的 HTML 測試報告 |

## 如何使用

### 日常開發
1. 建 `[SRS]` Issue（用 template）
2. 建 `[SDS]` Issue（連結到 SRS）
3. 建 `[RISK]` Issue（連結到 SRS）
4. 寫測試加上 `@pytest.mark.requirement("SRS-001")` 標記
5. 提 PR 填寫法規追溯欄位
6. CI 自動產出追溯報告

### TFDA 送審
1. 打 release tag: `git tag v1.0.0 && git push --tags`
2. GitHub Actions 自動跑 `regulatory-artifacts.yml`
3. 下載 artifact → 就是你的軟體確效報告附件
