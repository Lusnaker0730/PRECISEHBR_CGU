# PRECISE-HBR 論文與實作係數比對分析報告

**論文**: Costa F, et al. *The PRECISE-HBR Score for Bleeding Risk Prediction in Patients Undergoing Percutaneous Coronary Intervention.*
Circulation. 2025;151:343–355. DOI: 10.1161/CIRCULATIONAHA.124.072009

**分析日期**: 2026-03-12
**實作版本**: cdss_config.json v2.3.0

---

## 1. 評分方法論

### 1.1 論文方法
- 基於 Fine-Gray subdistribution hazard model（競爭風險模型）
- 模型輸出為 Subdistribution Hazard Ratios (SHR)
- 簡化為線性評分公式：**Score = Σ (10 × ln(SHR) × variable_value)**
- 連續變數設有截斷範圍（truncation），二元變數直接加分

### 1.2 實作方法
- 採用相同的 `10 × ln(SHR)` 線性近似方式
- 公式: `base(2) + age_score + hb_score + egfr_score + wbc_score + bleeding + anticoag + arc_hbr`
- 最終分數使用標準四捨五入取整（`math.floor(score + 0.5)`）

---

## 2. 係數比對（Table 2 SHR → 實作係數）

| 變數 | 論文 SHR (Table 2) | 理論係數 10×ln(SHR) | 實作係數 | 差異(%) | 備註 |
|------|-------------------|---------------------|---------|---------|------|
| **Age** (每10年) | 1.28 | 2.47 → 0.247/年 | **0.25** | +1.2% | 四捨五入至 0.25 |
| **Hemoglobin** (每 g/dL↓) | 0.78 (保護因子取倒數) | 10×ln(1/0.78) = 2.485 | **2.5** | +0.6% | 幾乎一致 |
| **eGFR** (每10 mL/min↓) | 0.95 (保護因子取倒數) | 10×ln(1/0.95)/10 = 0.0513/unit | **0.05** | −2.5% | 幾乎一致 |
| **WBC** (每 10⁹/L) | 1.08 | 10×ln(1.08) = 0.770 | **0.8** | +3.9% | 輕微向上取整 |
| **Prior Bleeding** | 1.96 | 10×ln(1.96) = 6.73 | **7** | +4.0% | 取整為整數 |
| **Oral Anticoag** | 1.58 | 10×ln(1.58) = 4.57 | **5** | +9.4% | 取整為整數 |
| **ARC-HBR** | 1.34 | 10×ln(1.34) = 2.93 | **3** | +2.4% | 取整為整數 |
| **Base Score** | — | — | **2** | — | 論文正文未明確揭示，可能出自 Supplemental Figure S4 |

### 係數轉換公式說明

- **連續變數（正向）**: `coefficient = 10 × ln(SHR) / scale`
  - Age: SHR=1.28 per 10 years → `10 × ln(1.28) / 10 = 0.247/year`
  - WBC: SHR=1.08 per 10⁹/L → `10 × ln(1.08) = 0.77`
- **連續變數（反向/保護因子）**: `coefficient = 10 × ln(1/SHR) / scale`
  - Hb: SHR=0.78 per g/dL → `10 × ln(1/0.78) = 2.485`
  - eGFR: SHR=0.95 per 10 units → `10 × ln(1/0.95) / 10 = 0.0513`
- **二元變數**: `coefficient = 10 × ln(SHR)`
  - Prior Bleeding: `10 × ln(1.96) = 6.73`
  - OAC: `10 × ln(1.58) = 4.57`
  - ARC-HBR: `10 × ln(1.34) = 2.93`

---

## 3. 風險閾值比對

| 風險分類 | 論文 (Figure 2) | 實作 | 狀態 |
|---------|----------------|------|------|
| Non-HBR (低風險) | ≤22 分 (出血率 <4%) | ≤22 | ✅ 完全一致 |
| HBR (高風險) | 23–26 分 (出血率 ≥4%) | 23–26 | ✅ 完全一致 |
| Very HBR (極高風險) | ≥27 分 (出血率 ≥6%) | ≥27 | ✅ 完全一致 |

---

## 4. 截斷範圍（Truncation）比對

| 變數 | 實作截斷範圍 | 合理性分析 |
|------|------------|-----------|
| Age | [30, 80] 歲 | ✅ 低於30歲不計分，高於80歲截斷以避免極端值 |
| Hemoglobin | [5.0, 15.0] g/dL | ✅ 15 g/dL 為閾值（高於不計分），5 g/dL 為臨床極低值 |
| eGFR | [5, 100] mL/min/1.73m² | ✅ 100 為閾值（高於不計分），5 為臨床極低值 |
| WBC | [3.0, 15.0] × 10⁹/L | ✅ 3 為閾值（低於不計分），15 為截斷上限 |

> **注意**: 論文正文未明確列出完整截斷範圍，上述範圍可能源自 Supplemental Materials (Figure S4) 的簡化評分表。

---

## 5. 差異分析與臨床影響評估

### 5.1 最大理論偏差計算

以最極端情境（所有變數同時取極端值）：

| 變數 | 最大偏差 | 條件 |
|------|---------|------|
| Age | (0.25−0.247)×50 = +0.15 分 | Age=80 |
| WBC | (0.8−0.77)×12 = +0.36 分 | WBC=15 |
| Bleeding | 7−6.73 = +0.27 分 | bleeding=true |
| OAC | 5−4.57 = +0.43 分 | anticoag=true |
| ARC-HBR | 3−2.93 = +0.07 分 | arc_hbr=true |
| **累計最大偏差** | **+1.28 分** | 所有同時極端 |

### 5.2 臨床影響

- 最大累積偏差 ≈ 1.28 分（取整後 ≤ 1 分）
- 在閾值邊界（22→23 或 26→27）**可能**將分類提高一級
- 但此情境要求所有變數同時取極端值，臨床上極罕見
- **所有二元變數係數均向上取整**，整體偏向保守（slightly overestimates risk），從臨床安全角度屬可接受

### 5.3 結論

| 項目 | 評估 |
|------|------|
| 評分方法 | ✅ 正確（10 × ln(SHR) 線性近似） |
| 風險閾值 | ✅ 完全一致 |
| 連續變數係數 | ⚠️ 輕微差異（<5%），已修正 age 為 0.25 |
| 二元變數係數 | ⚠️ 向上取整（4-9%），保守偏差，臨床可接受 |
| 截斷範圍 | ✅ 臨床合理 |
| **整體判定** | **✅ 實作與論文一致，差異在臨床可接受範圍內** |

---

## 6. 修正紀錄

| 日期 | 修正項目 | 修正前 | 修正後 | 理由 |
|------|---------|--------|--------|------|
| 2026-03-12 | Age coefficient | 0.26 | 0.25 | 更接近理論值 0.247，四捨五入至 0.25 更精確 |
| 2026-03-12 | 取整方式 | Python banker's rounding (`round()`) | 標準四捨五入 (`math.floor(x+0.5)`) | 14.5 應進位為 15，符合臨床慣例 |

---

## 7. 參考資料

1. Costa F, Montalto C, Branca M, et al. The PRECISE-HBR Score for Bleeding Risk Prediction in Patients Undergoing Percutaneous Coronary Intervention. *Circulation*. 2025;151:343-355.
2. `config/cdss_config.json` — 評分參數設定檔
3. `services/precise_hbr_calculator.py` — 核心計算邏輯
4. `tests/verify_precise_hbr.py` — 獨立參考實作驗證
