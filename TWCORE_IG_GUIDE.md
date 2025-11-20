# TW Core IG 整合指南

## 概述

本應用程式已整合 **台灣核心實作指引 (Taiwan Core Implementation Guide, TW Core IG)**，支援台灣特定的 FHIR 資料格式和編碼系統。

**參考文件**: [TW Core IG 官方文件](https://twcore.mohw.gov.tw/ig/twcore/)

---

## 🎯 支援的台灣特定功能

### 1. ✅ 中文姓名支援

根據 TW Core IG Patient Profile，支援在 `name.text` 欄位中的中文姓名。

**範例**:
```python
from fhir_data_service import get_patient_demographics, twcore_adapter

# FHIR Patient 資源（TW Core IG 格式）
patient_resource = {
    "resourceType": "Patient",
    "name": [{
        "text": "陳加玲",  # 中文姓名
        "use": "official"
    }],
    "gender": "female",
    "birthDate": "1990-05-15"
}

# 提取人口統計資料（自動啟用 TW Core 支援）
demographics = get_patient_demographics(patient_resource)

print(demographics['name'])          # "陳加玲"
print(demographics['name_chinese'])  # "陳加玲"
print(demographics['age'])           # 計算的年齡
```

### 2. ✅ 台灣健保藥品代碼 (NHI Codes)

支援從 [衛福部健保署藥品代碼查詢](https://info.nhi.gov.tw/INAE3000/INAE3000S01) 系統提取藥品資訊。

**編碼系統**: `https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw`

**範例**:
```python
from services.twcore_adapter import twcore_adapter

# FHIR MedicationRequest 資源
medication_request = {
    "resourceType": "MedicationRequest",
    "medicationCodeableConcept": {
        "coding": [{
            "system": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
            "code": "AC45856100",  # 健保藥品代碼（12位）
            "display": "立普妥膜衣錠10毫克"
        }],
        "text": "立普妥膜衣錠10毫克"
    }
}

# 提取健保藥品代碼
nhi_info = twcore_adapter.extract_nhi_medication_code(medication_request)

print(nhi_info['has_nhi_code'])      # True
print(nhi_info['nhi_code'])          # "AC45856100"
print(nhi_info['medication_name'])   # "立普妥膜衣錠10毫克"
```

**搜尋特定健保藥品**:
```python
# 在藥品清單中搜尋特定健保代碼
medications = [...]  # FHIR MedicationRequest 資源清單

matching_meds = twcore_adapter.search_nhi_medication_by_code(
    medications, 
    "AC45856100"
)

for match in matching_meds:
    print(f"找到藥品: {match['nhi_info']['medication_name']}")
```

### 3. ✅ ICD-10-CM 診斷代碼

支援 ICD-10-CM 診斷代碼，用於條件/診斷資源。

**編碼系統**: `http://hl7.org/fhir/sid/icd-10-cm`

**範例**:
```python
from services.twcore_adapter import twcore_adapter

# FHIR Condition 資源
condition_resource = {
    "resourceType": "Condition",
    "clinicalStatus": {
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": "active"
        }]
    },
    "code": {
        "coding": [{
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": "I21.0",  # ICD-10-CM: ST 段上升型心肌梗塞
            "display": "ST elevation myocardial infarction"
        }],
        "text": "急性心肌梗塞"
    }
}

# 提取 ICD-10 診斷代碼
diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition_resource)

print(diagnosis_info['has_icd10'])      # True
print(diagnosis_info['icd10_code'])     # "I21.0"
print(diagnosis_info['icd10_display'])  # "ST elevation myocardial infarction"
print(diagnosis_info['condition_text']) # "急性心肌梗塞"
```

**搜尋特定 ICD-10 診斷**:
```python
# 搜尋所有心肌梗塞 (I21.*) 診斷
conditions = [...]  # FHIR Condition 資源清單

mi_conditions = twcore_adapter.search_conditions_by_icd10(
    conditions, 
    "I21"  # 會匹配 I21.0, I21.1, I21.2 等
)

for match in mi_conditions:
    diagnosis = match['diagnosis_info']
    print(f"找到診斷: {diagnosis['icd10_code']} - {diagnosis['condition_text']}")
```

---

## 📋 完整使用範例

### 範例 1: 處理台灣病患完整資料

```python
from fhir_data_service import get_fhir_data, get_patient_demographics
from services.twcore_adapter import twcore_adapter

# 1. 從 FHIR 伺服器獲取資料
raw_data, error = get_fhir_data(
    fhir_server_url="https://your-fhir-server.com/fhir",
    access_token="your_token",
    patient_id="patient-12345",
    client_id="your_client_id"
)

if error:
    print(f"錯誤: {error}")
    exit(1)

# 2. 提取病患人口統計資料（含中文姓名）
demographics = get_patient_demographics(raw_data['patient'], use_twcore=True)

print("=== 病患資訊 ===")
print(f"中文姓名: {demographics['name_chinese']}")
print(f"英文姓名: {demographics['name_english']}")
print(f"身分證字號: {demographics['taiwan_id']}")
print(f"病歷號: {demographics['medical_record_number']}")
print(f"性別: {demographics['gender']}")
print(f"年齡: {demographics['age']}")

# 3. 檢查藥品（健保代碼）
print("\n=== 藥品資訊 ===")
medications = raw_data.get('med_requests', [])
for med in medications:
    nhi_info = twcore_adapter.extract_nhi_medication_code(med)
    if nhi_info['has_nhi_code']:
        print(f"健保藥品: {nhi_info['medication_name']}")
        print(f"  代碼: {nhi_info['nhi_code']}")

# 4. 檢查診斷（ICD-10）
print("\n=== 診斷資訊 ===")
conditions = raw_data.get('conditions', [])
for condition in conditions:
    diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
    if diagnosis_info['has_icd10']:
        print(f"診斷: {diagnosis_info['condition_text']}")
        print(f"  ICD-10: {diagnosis_info['icd10_code']}")
        print(f"  狀態: {diagnosis_info['clinical_status']}")
```

### 範例 2: 建立 TW Core IG 相容的 Patient 資源

```python
from services.twcore_adapter import twcore_adapter

# 準備病患資料
patient_data = {
    "name_chinese": "王小明",
    "gender": "male",
    "birthDate": "1985-03-20",
    "taiwan_id": "A123456789",
    "medical_record_number": "MR20230001"
}

# 建立 TW Core IG 相容的 Patient 資源
patient_resource = twcore_adapter.get_twcore_compatible_patient_resource(patient_data)

print(patient_resource)
# 輸出:
# {
#   "resourceType": "Patient",
#   "meta": {
#     "profile": ["https://twcore.mohw.gov.tw/ig/twcore/StructureDefinition/Patient-twcore"]
#   },
#   "identifier": [
#     {
#       "system": "http://www.moi.gov.tw/",
#       "type": {...},
#       "value": "A123456789"
#     },
#     ...
#   ],
#   "name": [
#     {"text": "王小明", "use": "official"}
#   ],
#   ...
# }
```

### 範例 3: 驗證台灣身分證字號

```python
from services.twcore_adapter import twcore_adapter

# 驗證身分證字號格式
taiwan_id = "A123456789"
is_valid = twcore_adapter.validate_taiwan_id(taiwan_id)

if is_valid:
    print(f"身分證字號 {taiwan_id} 格式正確")
else:
    print(f"身分證字號 {taiwan_id} 格式錯誤")
```

---

## 🔧 配置設定

### 在 `cdss_config.json` 中添加台灣特定設定

```json
{
  "taiwan_core_ig": {
    "enabled": true,
    "default_language": "zh-TW",
    "coding_systems": {
      "nhi_medication": "https://twcore.mohw.gov.tw/ig/twcore/CodeSystem/medication-nhi-tw",
      "icd10cm": "http://hl7.org/fhir/sid/icd-10-cm"
    },
    "patient_id_validation": {
      "require_taiwan_id": false,
      "require_medical_record_number": true
    }
  }
}
```

---

## 📊 支援的 TW Core IG Profiles

| Profile | 支援狀態 | 說明 |
|---------|---------|------|
| **TW Core Patient** | ✅ 完全支援 | 中文姓名、身分證字號、病歷號 |
| **TW Core Medication** | ✅ 完全支援 | 健保藥品代碼 (NHI Codes) |
| **TW Core MedicationRequest** | ✅ 完全支援 | 藥品處方含健保代碼 |
| **TW Core Condition** | ✅ 完全支援 | ICD-10-CM 診斷代碼 |
| **TW Core Observation** | ✅ 相容 | 使用標準 LOINC 代碼 |
| **TW Core Organization** | 🔄 規劃中 | 醫療機構資料 |
| **TW Core Practitioner** | 🔄 規劃中 | 醫事人員資料 |

---

## 🧪 測試範例

### 單元測試

```python
import unittest
from services.twcore_adapter import twcore_adapter

class TestTWCoreAdapter(unittest.TestCase):
    
    def test_chinese_name_extraction(self):
        """測試中文姓名提取"""
        patient = {
            "name": [{"text": "陳加玲", "use": "official"}],
            "gender": "female",
            "birthDate": "1990-05-15"
        }
        
        demographics = twcore_adapter.extract_patient_demographics_twcore(patient)
        
        self.assertEqual(demographics['name_chinese'], "陳加玲")
        self.assertEqual(demographics['name'], "陳加玲")
        self.assertIsNone(demographics['name_english'])
    
    def test_nhi_code_extraction(self):
        """測試健保藥品代碼提取"""
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
        
        self.assertTrue(nhi_info['has_nhi_code'])
        self.assertEqual(nhi_info['nhi_code'], "AC45856100")
        self.assertEqual(nhi_info['medication_name'], "立普妥膜衣錠10毫克")
    
    def test_icd10_extraction(self):
        """測試 ICD-10 診斷代碼提取"""
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
        
        diagnosis_info = twcore_adapter.extract_icd10_diagnosis(condition)
        
        self.assertTrue(diagnosis_info['has_icd10'])
        self.assertEqual(diagnosis_info['icd10_code'], "I21.0")
        self.assertEqual(diagnosis_info['condition_text'], "急性心肌梗塞")
    
    def test_taiwan_id_validation(self):
        """測試身分證字號驗證"""
        self.assertTrue(twcore_adapter.validate_taiwan_id("A123456789"))
        self.assertFalse(twcore_adapter.validate_taiwan_id("123456789"))  # 缺少字母
        self.assertFalse(twcore_adapter.validate_taiwan_id("AB12345678"))  # 兩個字母

if __name__ == '__main__':
    unittest.main()
```

---

## 🔗 相關資源

- [TW Core IG 官方文件](https://twcore.mohw.gov.tw/ig/twcore/)
- [TW Core IG 範例](https://twcore.mohw.gov.tw/ig/twcore/examples.html)
- [衛福部健保署藥品代碼查詢](https://info.nhi.gov.tw/INAE3000/INAE3000S01)
- [ICD-10-CM 診斷代碼](https://www.cdc.gov/nchs/icd/icd-10-cm.htm)

---

## 📞 支援

如有問題或建議，請：
1. 查看 TW Core IG 官方文件
2. 檢查應用程式日誌
3. 提交 issue 或聯繫開發團隊

---

**文件版本**: 1.0  
**最後更新**: 2025-11-20  
**TW Core IG 版本**: 0.3.2

