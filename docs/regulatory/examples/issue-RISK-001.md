# [RISK-001] 分數計算錯誤導致不當 DAPT 療程決策

> **這是一個範例 GitHub Issue，使用 `risk_analysis.md` template 建立**

---

## Risk ID
**ID**: RISK-001

## Hazard Description

PRECISE-HBR 分數計算邏輯錯誤（例如係數錯誤、截斷錯誤、四捨五入錯誤），
導致分數高估或低估，進而：
- **分數低估** → 高出血風險病人被分類為 non-HBR → 使用較長的 DAPT 療程 → 增加出血風險
- **分數高估** → 低風險病人被分類為 HBR → 使用較短的 DAPT 療程 → 增加血栓風險

## Harm

- 病人出血事件（BARC 3/5 等級）
- 病人支架內血栓事件
- 嚴重情況可能導致死亡

## Risk Estimation (Pre-mitigation)

**Severity** (1-5):
- [ ] 1 - Negligible
- [ ] 2 - Minor
- [ ] 3 - Serious
- [ ] 4 - Critical
- [x] 5 - Catastrophic

**Probability** (1-5):
- [ ] 1 - Incredible
- [ ] 2 - Remote
- [x] 3 - Occasional
- [ ] 4 - Probable
- [ ] 5 - Frequent

**Risk Level**: 15 (5 x 3) — **不可接受，需要風險控制**

## Risk Control Measures

1. **Golden dataset verification** (verify_precise_hbr.py): 使用獨立的參考實作，對 100 組測試資料驗證計算正確性
2. **Boundary value analysis** (verify_precise_hbr.py): 測試所有截斷邊界值
3. **Config-driven coefficients**: 係數從 cdss_config.json 載入，與程式碼分離，可由臨床團隊獨立審查
4. **Unit tests**: 針對每個分數組成部分的獨立單元測試
5. **Code review**: 所有計算邏輯變更需經 PR review

## Risk Estimation (Post-mitigation)

**Residual Severity** (1-5): 5 (嚴重度不變 — 後果仍然嚴重)
**Residual Probability** (1-5): 1 (降低 — 多層測試覆蓋大幅降低發生機率)
**Residual Risk Level**: 5 (5 x 1) — **可接受，附帶持續監控**

## Risk Acceptability
- [ ] Acceptable
- [x] Acceptable with justification
- [ ] Unacceptable - further mitigation required

> **Justification**: 殘餘風險可接受，因為：
> (1) Golden dataset 驗證覆蓋了隨機與邊界情境
> (2) 系統為輔助決策工具，最終決定權在臨床醫師
> (3) 使用者介面顯示分數組成細節，臨床醫師可檢查合理性

## Traceability
- Related requirements: #SRS-001
- Related design: #SDS-001
- Verification (test that confirms mitigation works): #TC-001, #TC-002, #TC-003

## Verification of Risk Control
- [x] Test case confirms mitigation: #TC-001 (golden dataset), #TC-002 (boundary), #TC-003 (risk classification)
- [x] Code review confirms implementation
- [ ] Manual verification performed

---

**Labels**: `risk`, `ISO-14971`, `class-C`
