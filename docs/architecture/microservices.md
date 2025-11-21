# 微服務架構文檔 (Microservices Architecture Documentation)

## 概述 (Overview)

原本的 `fhir_data_service.py` (1896 行) 已被重構為 7 個清晰的微服務模組，遵循單一職責原則 (Single Responsibility Principle)，提高了可維護性、可測試性和可擴展性。

---

## 服務架構 (Service Architecture)

### 1. **配置管理服務** (`services/config_loader.py`)
**職責：** 統一管理和載入 CDSS 配置

**主要功能：**
- 從 `cdss_config.json` 載入配置
- 提供 LOINC 代碼查詢
- 提供 SNOMED 代碼查詢
- 提供藥物關鍵字查詢
- Singleton 模式確保全局唯一實例

**使用範例：**
```python
from services.config_loader import config_loader

# 獲取完整配置
config = config_loader.config

# 獲取 LOINC 代碼
loinc_codes = config_loader.get_loinc_codes()

# 獲取特定類別的 SNOMED 代碼
bleeding_codes = config_loader.get_snomed_codes('prior_bleeding')
```

---

### 2. **單位轉換服務** (`services/unit_conversion_service.py`)
**職責：** 處理所有實驗室數值的單位轉換

**主要功能：**
- 定義標準目標單位 (TARGET_UNITS)
- 從 FHIR Observation 提取數值並轉換單位
- 使用 CKD-EPI 2021 公式計算 eGFR
- 支援多種單位格式（如 g/dL, g/L, mmol/L 等）

**使用範例：**
```python
from services.unit_conversion_service import unit_converter

# 從觀察結果提取並轉換值
hb_value = unit_converter.get_value_from_observation(
    observation, 
    unit_converter.TARGET_UNITS['HEMOGLOBIN']
)

# 計算 eGFR
egfr, method = unit_converter.calculate_egfr(
    creatinine_val=1.2,  # mg/dL
    age=65,
    gender='male'
)
```

---

### 3. **FHIR 客戶端服務** (`services/fhir_client_service.py`)
**職責：** 管理所有與 FHIR 伺服器的互動

**主要功能：**
- 設置 FHIR 客戶端認證
- 獲取病患資源 (Patient)
- 透過 LOINC 代碼查詢觀察結果 (Observations)
- 透過文字搜尋查詢觀察結果
- 獲取條件 (Conditions)、程序 (Procedures)、藥物請求 (MedicationRequests)
- 自動重試和超時處理

**使用範例：**
```python
from services.fhir_client_service import FHIRClientService

# 創建 FHIR 服務實例
fhir_service = FHIRClientService(
    fhir_server_url="https://fhir.example.com",
    access_token="your_token",
    client_id="your_client_id"
)

# 獲取完整病患數據
raw_data, error = fhir_service.get_all_patient_data(patient_id)

# 獲取特定觀察結果
observations = fhir_service.get_observations_by_loinc(
    patient_id, 
    ['718-7', '4548-4']  # LOINC codes
)
```

---

### 4. **條件檢查服務** (`services/condition_checker.py`)
**職責：** 檢查特定醫療條件和風險因素

**主要功能：**
- 檢查出血性素質 (Bleeding Diathesis)
- 檢查既往出血史 (Prior Bleeding)
- 檢查肝硬化合併門脈高壓
- 檢查活動性惡性腫瘤
- 檢查口服抗凝血藥物
- 檢查 NSAIDs 或皮質類固醇使用
- 檢查血小板減少症
- 詳細的 ARC-HBR 因素分析

**使用範例：**
```python
from services.condition_checker import condition_checker

# 檢查既往出血史
has_bleeding, evidence = condition_checker.check_prior_bleeding(conditions)

# 檢查口服抗凝血藥物
has_oac = condition_checker.check_oral_anticoagulation(medications)

# 獲取詳細的 ARC-HBR 因素
arc_details = condition_checker.check_arc_hbr_factors_detailed(
    raw_data, 
    medications
)
```

---

### 5. **風險分類服務** (`services/risk_classifier.py`)
**職責：** 處理風險分類和出血風險百分比計算

**主要功能：**
- 根據 PRECISE-HBR 分數計算 1 年出血風險百分比
- 獲取風險類別資訊（非高出血風險、HBR、非常 HBR）
- 生成完整的顯示資訊和建議

**使用範例：**
```python
from services.risk_classifier import risk_classifier

# 計算出血風險百分比
risk_percent = risk_classifier.calculate_bleeding_risk_percentage(
    precise_hbr_score=25
)

# 獲取風險類別資訊
risk_info = risk_classifier.get_risk_category_info(
    precise_hbr_score=25
)

# 獲取完整顯示資訊
display_info = risk_classifier.get_precise_hbr_display_info(
    precise_hbr_score=25
)
```

---

### 6. **PRECISE-HBR 計算器** (`services/precise_hbr_calculator.py`)
**職責：** 計算 PRECISE-HBR 出血風險評分

**主要功能：**
- 實施 PRECISE-HBR V5.0 方法論
- 計算連續變量評分（年齡、血紅蛋白、eGFR、WBC）
- 計算分類變量評分（出血史、抗凝治療、ARC-HBR 條件）
- 應用截斷規則到有效值
- 生成詳細的評分組件

**使用範例：**
```python
from services.precise_hbr_calculator import precise_hbr_calculator

# 計算 PRECISE-HBR 評分
components, total_score = precise_hbr_calculator.calculate_score(
    raw_data, 
    demographics
)

# 查看評分組件
for component in components:
    print(f"{component['parameter']}: {component['value']} (分數: {component['score']})")
```

---

### 7. **Tradeoff 模型計算器** (`services/tradeoff_model_calculator.py`)
**職責：** 處理出血-血栓權衡風險分析

**主要功能：**
- 從 FHIR 伺服器獲取 tradeoff 相關數據
- 載入 ARC-HBR tradeoff 模型
- 檢測 tradeoff 因素（糖尿病、心肌梗塞、吸煙等）
- 使用 Cox 比例風險模型計算出血和血栓評分
- 將風險比 (HR) 轉換為事件機率
- 支援互動式評分計算

**使用範例：**
```python
from services.tradeoff_model_calculator import tradeoff_calculator

# 獲取 tradeoff 數據
tradeoff_data = tradeoff_calculator.get_tradeoff_data(
    fhir_server_url, 
    access_token, 
    client_id, 
    patient_id
)

# 計算 tradeoff 評分
scores = tradeoff_calculator.calculate_tradeoff_scores(
    raw_data, 
    demographics, 
    tradeoff_data
)

print(f"出血風險: {scores['bleeding_score']}%")
print(f"血栓風險: {scores['thrombotic_score']}%")
```

---

## 向後兼容性 (Backward Compatibility)

原始的 `fhir_data_service.py` 現在作為統一入口點，重新導出所有舊版函數，確保現有代碼無需修改即可繼續運作。

**遷移策略：**
```python
# 舊代碼（仍然有效）
from fhir_data_service import get_fhir_data, calculate_precise_hbr_score

# 新代碼（推薦）
from services.fhir_client_service import FHIRClientService
from services.precise_hbr_calculator import precise_hbr_calculator
```

---

## 依賴關係圖 (Dependency Graph)

```
config_loader (基礎層)
    ↓
unit_conversion_service (單位層)
    ↓
condition_checker (業務邏輯層)
    ↓
precise_hbr_calculator ← risk_classifier
    ↓
tradeoff_model_calculator
    ↓
fhir_client_service (整合層)
```

---

## 優勢 (Benefits)

### 1. **可維護性**
- 每個服務有明確的職責
- 單一修改點，降低錯誤風險
- 更容易理解和修改代碼

### 2. **可測試性**
- 每個服務可獨立測試
- 更容易建立單元測試
- 可使用 mock 物件隔離依賴

### 3. **可重用性**
- 服務可在多個上下文中重用
- 減少代碼重複
- 促進模組化設計

### 4. **可擴展性**
- 新功能可作為新服務添加
- 不影響現有服務
- 支援並行開發

### 5. **效能優化**
- 可針對特定服務進行效能調優
- 潛在的並行處理機會
- 更好的資源管理

---

## 測試建議 (Testing Recommendations)

### 單元測試範例
```python
import unittest
from services.unit_conversion_service import unit_converter

class TestUnitConversion(unittest.TestCase):
    def test_hemoglobin_conversion(self):
        obs = {
            'valueQuantity': {
                'value': 120,
                'unit': 'g/l'
            }
        }
        result = unit_converter.get_value_from_observation(
            obs, 
            unit_converter.TARGET_UNITS['HEMOGLOBIN']
        )
        self.assertEqual(result, 12.0)  # 120 g/L = 12.0 g/dL
```

### 整合測試範例
```python
def test_precise_hbr_calculation():
    from services.precise_hbr_calculator import precise_hbr_calculator
    
    # 準備測試資料
    raw_data = {...}
    demographics = {'age': 70, 'gender': 'male'}
    
    # 執行計算
    components, score = precise_hbr_calculator.calculate_score(
        raw_data, 
        demographics
    )
    
    # 驗證結果
    assert isinstance(score, int)
    assert 0 <= score <= 100
```

---

## 部署建議 (Deployment Recommendations)

1. **保持 services/ 目錄結構**
2. **確保 cdss_config.json 在適當位置**
3. **驗證所有依賴項已安裝**
4. **運行整合測試驗證功能**
5. **監控日誌以發現潛在問題**

---

## 未來改進方向 (Future Enhancements)

1. **添加快取層** - 減少重複的 FHIR 查詢
2. **實施異步處理** - 提高並發性能
3. **添加資料驗證層** - 增強輸入驗證
4. **實施監控和指標** - 追蹤服務健康狀態
5. **添加 API 層** - 將服務暴露為 RESTful API

---

## 支援與貢獻 (Support & Contribution)

如有問題或建議，請：
1. 查看日誌文件以了解詳細錯誤資訊
2. 檢查配置文件是否正確
3. 驗證 FHIR 伺服器連接
4. 提交 issue 或 pull request

---

**文檔版本：** 1.0  
**最後更新：** 2025-11-20  
**重構完成日期：** 2025-11-20

