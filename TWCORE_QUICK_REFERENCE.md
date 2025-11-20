# TW Core IG 快速參考卡 (Quick Reference)

## 📋 立即開始

### 安裝與導入

```python
from fhir_data_service import get_patient_demographics
from services.twcore_adapter import twcore_adapter
```

---

## 🏥 1. 中文姓名支援

### 提取中文姓名

```python
# FHIR Patient 資源
patient = {
    "name": [{"text": "陳加玲", "use": "official"}],
    "gender": "female",
    "birthDate": "1990-05-15"
}

# 自動提取中文姓名
demographics = get_patient_demographics(patient)
print(demographics['name'])          # "陳加玲"
print(demographics['name_chinese'])  # "陳加玲"
```

### ✅ 支援的名字格式
- ✓ 純中文姓名：`"王小明"`
- ✓ 純英文姓名：`"John Smith"`
- ✓ 中英文混合（自動識別優先順序）

---

## 💊 2. 健保藥品代碼 (NHI Codes)

### 提取健保藥品代碼

```python
medication = {
    "medicationCodeableConcept": {
        "coding": [{
            "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
            "code": "AC45856100",
            "display": "立普妥膜衣錠10毫克"
        }]
    }
}

nhi_info = twcore_adapter.extract_nhi_medication_code(medication)
print(nhi_info['nhi_code'])         # "AC45856100"
print(nhi_info['medication_name'])  # "立普妥膜衣錠10毫克"
```

### 搜尋特定健保藥品

```python
medications = [...]  # 藥品清單
results = twcore_adapter.search_nhi_medication_by_code(medications, "AC45856100")
```

### ✅ 支援的藥品編碼
- ✓ 健保藥品代碼（12 位）
- ✓ NHI Code System URL
- ✓ 自動識別 12 位數字母組合

---

## 🏥 3. ICD-10-CM 診斷代碼

### 提取 ICD-10 診斷

```python
condition = {
    "code": {
        "coding": [{
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": "I21.0",
            "display": "ST elevation myocardial infarction"
        }],
        "text": "急性心肌梗塞"
    }
}

diagnosis = twcore_adapter.extract_icd10_diagnosis(condition)
print(diagnosis['icd10_code'])      # "I21.0"
print(diagnosis['condition_text'])  # "急性心肌梗塞"
```

### 搜尋特定診斷

```python
conditions = [...]  # 診斷清單
# 搜尋所有心肌梗塞 (I21.*)
mi_conditions = twcore_adapter.search_conditions_by_icd10(conditions, "I21")
```

### ✅ 支援的診斷編碼
- ✓ ICD-10-CM（完整支援）
- ✓ ICD-10（相容支援）
- ✓ 模糊搜尋（如 `I21` 匹配 `I21.0`, `I21.1` 等）

---

## 🆔 4. 台灣身分證字號

### 提取身分證字號

```python
patient = {
    "identifier": [{
        "system": "http://www.moi.gov.tw/",
        "value": "A123456789"
    }]
}

demographics = get_patient_demographics(patient)
print(demographics['taiwan_id'])  # "A123456789"
```

### 驗證身分證字號格式

```python
is_valid = twcore_adapter.validate_taiwan_id("A123456789")
print(is_valid)  # True
```

### ✅ 支援的識別碼
- ✓ 身分證字號（1 字母 + 9 數字）
- ✓ 居留證號碼
- ✓ 病歷號

---

## 📊 完整範例：處理台灣病患資料

```python
from fhir_data_service import get_fhir_data, get_patient_demographics
from services.twcore_adapter import twcore_adapter

# 1. 獲取 FHIR 資料
raw_data, error = get_fhir_data(
    fhir_server_url="https://your-server.com/fhir",
    access_token="your_token",
    patient_id="patient-123",
    client_id="your_client"
)

# 2. 提取病患資訊（含中文姓名）
demographics = get_patient_demographics(raw_data['patient'])
print(f"姓名: {demographics['name_chinese']}")
print(f"身分證: {demographics['taiwan_id']}")
print(f"病歷號: {demographics['medical_record_number']}")

# 3. 檢查健保藥品
for med in raw_data.get('med_requests', []):
    nhi_info = twcore_adapter.extract_nhi_medication_code(med)
    if nhi_info['has_nhi_code']:
        print(f"藥品: {nhi_info['medication_name']} ({nhi_info['nhi_code']})")

# 4. 檢查 ICD-10 診斷
for condition in raw_data.get('conditions', []):
    diagnosis = twcore_adapter.extract_icd10_diagnosis(condition)
    if diagnosis['has_icd10']:
        print(f"診斷: {diagnosis['condition_text']} ({diagnosis['icd10_code']})")
```

---

## 🔍 常見使用場景

### 場景 1: 病患註冊（中文姓名）

```python
patient_data = {
    "name_chinese": "王小明",
    "gender": "male",
    "birthDate": "1985-03-20",
    "taiwan_id": "A123456789"
}

patient_resource = twcore_adapter.get_twcore_compatible_patient_resource(patient_data)
# 產生 TW Core IG 相容的 Patient 資源
```

### 場景 2: 藥品查詢（健保代碼）

```python
# 查詢特定健保藥品
nhi_code = "AC45856100"  # 立普妥
medications = [...]

results = twcore_adapter.search_nhi_medication_by_code(medications, nhi_code)
if results:
    print(f"找到藥品: {results[0]['nhi_info']['medication_name']}")
```

### 場景 3: 診斷篩選（ICD-10）

```python
# 篩選心肌梗塞病患
conditions = [...]
mi_patients = twcore_adapter.search_conditions_by_icd10(conditions, "I21")

print(f"找到 {len(mi_patients)} 位心肌梗塞病患")
```

---

## ⚠️ 注意事項

### 1. 預設啟用 TW Core 支援
```python
# TW Core 支援預設啟用
demographics = get_patient_demographics(patient)

# 若要停用（使用傳統格式）
demographics = get_patient_demographics(patient, use_twcore=False)
```

### 2. 資料隱私保護
```python
# 身分證字號會自動遮罩記錄
# 日誌顯示: "A********" 而非 "A123456789"
```

### 3. 編碼系統 URL
```python
# 健保藥品代碼
"https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw"

# ICD-10-CM 診斷代碼
"http://hl7.org/fhir/sid/icd-10-cm"

# 台灣身分證系統
"http://www.moi.gov.tw/"
```

---

## 🧪 測試狀態

✅ **所有測試通過**: 13/13 (100%)

- ✅ 中文姓名提取
- ✅ 英文姓名提取  
- ✅ 混合姓名處理
- ✅ 身分證字號提取
- ✅ 病歷號提取
- ✅ 健保藥品代碼提取
- ✅ 12 位數健保代碼識別
- ✅ 健保藥品搜尋
- ✅ ICD-10 診斷提取
- ✅ ICD-10 診斷搜尋
- ✅ 身分證字號驗證
- ✅ 無效身分證格式檢測
- ✅ TW Core 資源產生

---

## 📚 相關資源

- [TW Core IG 完整指南](./TWCORE_IG_GUIDE.md)
- [測試程式碼](./tests/test_twcore_adapter.py)
- [TW Core IG 官方文件](https://twcore.mohw.gov.tw/ig/twcore/)
- [衛福部健保署藥品查詢](https://info.nhi.gov.tw/INAE3000/INAE3000S01)

---

**版本**: 1.0  
**更新**: 2025-11-20  
**測試狀態**: ✅ 全部通過

