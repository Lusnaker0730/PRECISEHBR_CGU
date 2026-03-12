# TWCDI 合規性修正報告

**日期**: 2026-03-12
**TWCDI 版本**: TW Core IG (FHIR 4.0.1)
**Package**: `twcdi/package.tgz`
**應用程式**: PRECISE-HBR SMART on FHIR Application

---

## 一、修正摘要

| 修正項目 | 優先序 | 嚴重性 | 狀態 |
|---|---|---|---|
| Search Parameter `patient` → `subject` | P0 | 高 | **已修正** |
| MedicationRequest `category` 改為 client-side | P1 | 中 | **已修正** |
| Procedure/Condition 新增 ICD-10 代碼對應 | P2 | 中 | **已修正** |
| Condition 查詢加入 `clinical-status=active` | P3 | 低 | **已修正** |
| Consent 查詢加入 graceful degradation 註解 | P4 | 低 | **已確認** |

---

## 二、修正明細

### P0: Search Parameter `patient` → `subject` (高風險)

**問題**: TWCDI Server CapabilityStatement 中，Condition、Procedure、MedicationRequest 的搜尋參數僅定義 `subject`（reference 類型），本應用原使用 `patient` 參數可能導致 TWCDI 嚴格伺服器回傳錯誤或忽略該參數。

**影響檔案**:

#### `services/fhir_client_service.py`

| 方法 | 修正前 | 修正後 |
|---|---|---|
| `get_conditions()` | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |
| `get_procedures()` | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |
| `get_medication_requests()` | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |

#### `services/tradeoff_model_calculator.py`

| 查詢目標 | 修正前 | 修正後 |
|---|---|---|
| Condition 查詢 (L150) | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |
| Procedure 查詢 (L239) | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |
| MedicationRequest 查詢 (L263) | `'patient': patient_id` | `'subject': f'Patient/{patient_id}'` |

**注意**: Observation 的搜尋參數維持使用 `patient`，因為 TWCDI Server CapabilityStatement 對 Observation 同時定義了 `patient` 和 `subject` 兩個參數。

**FHIR 規範依據**: `subject` 參數值使用完整的 Reference 格式 `Patient/{id}`，符合 FHIR R4 reference search parameter 規範。

---

### P1: MedicationRequest `category` 移至 Client-side 過濾 (中風險)

**問題**: TWCDI Server CapabilityStatement 對 MedicationRequest 定義的搜尋參數為 `_id`, `status`, `intent`, `subject`, `encounter`, `authoredon`，**不包含 `category`**。使用 `category` 作為 server-side 搜尋參數可能導致查詢失敗。

**修正方式**:

#### `services/fhir_client_service.py`

- **移除**: Server-side `category` 搜尋參數
- **新增**: `_filter_by_category()` 靜態方法進行 client-side 過濾
- 過濾邏輯：遍歷 `MedicationRequest.category[].coding[].code` 和 `category[].text`

```python
@staticmethod
def _filter_by_category(med_list, category):
    filtered = []
    for med in med_list:
        for cat in med.get('category', []):
            matched = any(
                coding.get('code') == category
                for coding in cat.get('coding', [])
            )
            if matched or cat.get('text', '').lower() == category.lower():
                filtered.append(med)
                break
    return filtered
```

#### `services/tradeoff_model_calculator.py`

- **移除**: `'category': 'outpatient'` 搜尋參數
- **新增**: `_is_outpatient_category()` 模組層級函式進行 client-side 過濾
- 在遍歷 `med_requests.entry` 時逐筆檢查 category

**取捨考量**: Client-side 過濾會增加網路傳輸量（取得所有 MedicationRequest 而非僅 outpatient），但確保在所有 TWCDI 伺服器上都能正常運作。

---

### P2: 新增 ICD-10-CM/PCS 代碼對應 (中風險)

**問題**: TWCDI Procedure Profile (`Procedure-twcore`) 的 `code.coding` binding 為 ICD-10-PCS（台灣健保處置碼），Condition Profile 使用 ICD-10-CM。台灣的 FHIR 伺服器可能僅有 ICD-10 代碼而缺乏 SNOMED CT，導致比對失敗。

**修正方式**:

#### `config/cdss_config.json`

新增 `icd10_codes` 區塊於 `tradeoff_analysis` 配置中：

```json
"icd10_codes": {
    "_description": "ICD-10-CM/PCS codes for TWCDI-compliant servers that may lack SNOMED CT",
    "copd": ["J44"],
    "nstemi": ["I21.4"],
    "stemi": ["I21.0", "I21.1", "I21.2", "I21.3"],
    "diabetes": ["E10", "E11", "E13"],
    "myocardial_infarction": ["I21", "I22", "I25.2"],
    "complex_pci": ["02703", "02713", "02723", "02733"],
    "bare_metal_stent": ["02703Z", "02713Z", "02723Z", "02733Z"]
}
```

| 臨床概念 | SNOMED CT (原有) | ICD-10-CM/PCS (新增) |
|---|---|---|
| COPD | 13645005 | J44.x |
| NSTEMI | 164868009 | I21.4 |
| STEMI | 164869001 | I21.0-I21.3 |
| 糖尿病 | 73211009 | E10, E11, E13 |
| 心肌梗塞 | 22298006 | I21, I22, I25.2 |
| 複雜 PCI | 397682003 | 02703, 02713, 02723, 02733 (ICD-10-PCS) |
| 裸金屬支架 | 427183000 | 02703Z, 02713Z, 02723Z, 02733Z (ICD-10-PCS) |

#### `services/tradeoff_model_calculator.py`

- **新增**: `_resource_has_icd10_prefix()` 靜態方法，支援 ICD-10-CM、ICD-10-PCS、ICD-10 三種 system URI
- **修改**: Condition 比對邏輯 — SNOMED 比對失敗後 fallback 至 ICD-10-CM
- **修改**: Procedure 比對邏輯 — SNOMED 比對失敗後 fallback 至 ICD-10-PCS
- **修改**: NSTEMI/STEMI 比對邏輯 — 同樣加入 ICD-10 fallback

**比對策略**: Prefix matching（前綴比對），例如 `"J44"` 可匹配 `"J44.0"`, `"J44.1"`, `"J44.9"` 等。

---

### P3: Condition 查詢加入 `clinical-status=active` (低風險)

**問題**: 原本取得所有 conditions（含 resolved/inactive），增加不必要的網路傳輸與處理負擔。TWCDI Server 支援 `clinical-status` 搜尋參數，且 Condition Profile 要求 `clinicalStatus` 最小基數為 1。

**修正方式**:

- `services/fhir_client_service.py` `get_conditions()`: 新增 `'clinical-status': 'active'`
- `services/tradeoff_model_calculator.py` Condition 查詢: 新增 `'clinical-status': 'active'`

**注意**: `condition_checker.py` 中的 `_get_clinical_status()` 方法仍保留 client-side 狀態檢查作為防禦性程式設計，以處理伺服器未正確過濾的情況。

---

### P4: Consent 查詢 Graceful Degradation (低風險)

**問題**: TWCDI CapabilityStatement 不包含 Consent 資源類型，TWCDI 嚴格伺服器可能回傳 HTTP 400/404。

**現狀確認**: `services/consent_service.py` 已具備完整的 graceful degradation：
- `ImportError` → 回傳 `_default_permit_result()` (deny by default)
- 任何 `Exception` → 回傳 `_error_result()`
- SMART client 未設定 → 回傳 `_default_permit_result()`

**修正**: 新增 TWCDI 不支援的文件註解，提醒維護者此查詢在 TWCDI 環境下可能失敗。

---

## 三、未修改項目（已符合 TWCDI）

| 項目 | 說明 |
|---|---|
| Patient 讀取 (`read` by ID) | 使用 `Patient.read(id, server)`，符合 TWCDI |
| Observation 搜尋 (`patient` 參數) | TWCDI 同時支援 `patient` 和 `subject` |
| LOINC 檢驗代碼查詢 | 標準 LOINC 碼，TWCDI 相容 |
| TW Core Patient Profile 解析 | `twcore_adapter.py` 支援中文姓名、身分證、病歷號 |
| NHI 健保藥品代碼比對 | 支援 `medication-nhi-tw` code system |
| ICD-10-CM 診斷碼解析 | `twcore_adapter.py` 已支援 |
| OAuth2 Bearer Token 認證 | SMART on FHIR 標準流程 |
| `application/fhir+json` Content-Type | 已正確設定 |

---

## 四、測試結果

```
修正後測試結果:
  - 直接相關測試: 186/186 通過
  - 全部測試: 662 passed, 15 failed (pre-existing), 2 skipped
  - 所有 15 個失敗測試均為預先存在的問題（已驗證 git stash 乾淨碼也會失敗）
  - 未引入任何新的測試失敗
```

---

## 五、修正後 FHIR 查詢對照表

| 資源類型 | 修正後查詢 URL Pattern | TWCDI 搜尋參數對應 |
|---|---|---|
| Patient | `GET /Patient/{id}` | `read` interaction |
| Observation | `GET /Observation?patient={id}&code={LOINC}` | `patient` (token) + `code` (token) |
| Condition | `GET /Condition?subject=Patient/{id}&clinical-status=active` | `subject` (reference) + `clinical-status` (token) |
| Procedure | `GET /Procedure?subject=Patient/{id}` | `subject` (reference) |
| MedicationRequest | `GET /MedicationRequest?subject=Patient/{id}` | `subject` (reference) |
| Consent | `GET /Consent?patient={id}&status=active` | **非 TWCDI 範圍**（graceful degradation） |

---

## 六、修改檔案清單

| 檔案路徑 | 修正內容 |
|---|---|
| `services/fhir_client_service.py` | P0: `subject` 參數; P1: client-side category filter; P3: `clinical-status` |
| `services/tradeoff_model_calculator.py` | P0: `subject` 參數; P1: outpatient category filter; P2: ICD-10 fallback; P3: `clinical-status` |
| `services/consent_service.py` | P4: TWCDI 不支援 Consent 的文件註解 |
| `config/cdss_config.json` | P2: 新增 `icd10_codes` 配置區塊 |
