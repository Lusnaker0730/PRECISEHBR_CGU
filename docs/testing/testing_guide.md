# PRECISE-HBR 測試指南

## 📋 目錄
1. [快速開始](#快速開始)
2. [測試架構](#測試架構)
3. [執行測試](#執行測試)
4. [撰寫測試](#撰寫測試)
5. [測試最佳實踐](#測試最佳實踐)
6. [CI/CD 整合](#cicd-整合)

## 快速開始

### 安裝測試依賴

```bash
# 安裝所有依賴（包含測試套件）
pip install -r requirements.txt

# 或僅安裝測試相關套件
pip install pytest pytest-cov flask-wtf coverage
```

### 執行測試

**Windows (PowerShell):**
```powershell
.\run_tests.ps1
```

**Linux/macOS:**
```bash
chmod +x run_tests.sh
./run_tests.sh
```

**或直接使用 pytest:**
```bash
# 執行所有測試
python -m pytest tests/ -v

# 執行測試 + 覆蓋率報告
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# 執行特定測試文件
python -m pytest tests/test_twcore_adapter.py -v
```

## 測試架構

### 測試分類

我們使用 pytest markers 來分類測試：

- **`@pytest.mark.unit`**: 單元測試 - 測試單一功能或方法
- **`@pytest.mark.integration`**: 整合測試 - 測試多個組件的協作
- **`@pytest.mark.security`**: 安全測試 - 測試安全相關功能
- **`@pytest.mark.slow`**: 慢速測試 - 執行時間較長的測試

### 測試結構

```
tests/
├── __init__.py
├── conftest.py                    # 共用 fixtures
├── test_app_basic.py              # 應用程式基本功能測試
├── test_audit_logging.py          # 審計日誌測試
├── test_ccd_export.py             # CCD 匯出測試
├── test_condition_checker_config.py  # 條件檢查器配置測試
├── test_fhir_service.py           # FHIR 服務測試
├── test_security.py               # 安全測試
└── test_twcore_adapter.py         # TW Core Adapter 測試
```

### Fixtures

我們在 `conftest.py` 中定義了共用的 fixtures：

- **`app`**: Flask 應用程式實例
- **`client`**: Flask 測試客戶端
- **`mock_fhir_client`**: 模擬的 FHIR 客戶端
- **`mock_patient_data`**: 模擬的病患資料
- **`mock_observation_data`**: 模擬的觀察值資料
- **`mock_hbr_criteria`**: 模擬的 HBR 條件

## 執行測試

### 基本命令

```bash
# 執行所有測試
pytest tests/

# 詳細輸出
pytest tests/ -v

# 顯示測試覆蓋率
pytest tests/ --cov=. --cov-report=term-missing

# 生成 HTML 覆蓋率報告
pytest tests/ --cov=. --cov-report=html
```

### 選擇性執行

```bash
# 執行特定測試文件
pytest tests/test_twcore_adapter.py

# 執行特定測試類別
pytest tests/test_twcore_adapter.py::TestTWCorePatient

# 執行特定測試函數
pytest tests/test_twcore_adapter.py::TestTWCorePatient::test_chinese_name_extraction

# 執行特定標記的測試
pytest tests/ -m unit           # 只執行單元測試
pytest tests/ -m integration    # 只執行整合測試
pytest tests/ -m "not slow"     # 排除慢速測試
```

### 調試選項

```bash
# 失敗時進入 pdb 調試器
pytest tests/ --pdb

# 顯示本地變數
pytest tests/ -l

# 完整的錯誤追蹤
pytest tests/ --tb=long

# 簡短的錯誤追蹤
pytest tests/ --tb=short

# 只顯示失敗的測試
pytest tests/ --tb=no
```

### 並行執行

```bash
# 安裝 pytest-xdist
pip install pytest-xdist

# 使用多核心執行測試
pytest tests/ -n auto
```

## 撰寫測試

### 基本測試結構

```python
"""測試模塊的文檔字串"""

import pytest
from services.my_service import my_function


class TestMyFeature:
    """測試類別的文檔字串"""
    
    def test_basic_functionality(self):
        """測試基本功能"""
        # Arrange (準備)
        input_data = "test"
        expected_output = "TEST"
        
        # Act (執行)
        result = my_function(input_data)
        
        # Assert (驗證)
        assert result == expected_output
    
    def test_edge_case(self):
        """測試邊界情況"""
        result = my_function("")
        assert result == ""
    
    def test_error_handling(self):
        """測試錯誤處理"""
        with pytest.raises(ValueError):
            my_function(None)
```

### 使用 Fixtures

```python
import pytest


@pytest.fixture
def sample_patient():
    """創建測試用的病患資料"""
    return {
        'resourceType': 'Patient',
        'id': 'test-123',
        'name': [{'family': '王', 'given': ['小明']}]
    }


def test_with_fixture(sample_patient):
    """使用 fixture 的測試"""
    assert sample_patient['id'] == 'test-123'
    assert sample_patient['name'][0]['family'] == '王'
```

### 參數化測試

```python
import pytest


@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("123", "123"),
])
def test_uppercase(input, expected):
    """參數化測試"""
    assert input.upper() == expected
```

### 模擬 (Mocking)

```python
from unittest.mock import Mock, patch, MagicMock


def test_with_mock():
    """使用 mock 的測試"""
    # 創建 mock 物件
    mock_client = Mock()
    mock_client.get.return_value = {"status": "ok"}
    
    # 使用 mock
    result = mock_client.get("/api/test")
    assert result["status"] == "ok"
    mock_client.get.assert_called_once_with("/api/test")


def test_with_patch():
    """使用 patch 的測試"""
    with patch('services.fhir_client_service.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        
        # 執行需要被 patch 的函數
        # result = fetch_data()
        
        mock_get.assert_called_once()
```

### 測試標記

```python
import pytest


@pytest.mark.unit
def test_unit_example():
    """單元測試"""
    assert True


@pytest.mark.integration
def test_integration_example():
    """整合測試"""
    assert True


@pytest.mark.slow
def test_slow_example():
    """慢速測試"""
    import time
    time.sleep(2)
    assert True


@pytest.mark.security
def test_security_example():
    """安全測試"""
    assert True
```

## 測試最佳實踐

### 1. AAA 模式

使用 **Arrange-Act-Assert** 模式組織測試：

```python
def test_example():
    # Arrange: 準備測試資料和環境
    patient_data = create_test_patient()
    
    # Act: 執行被測試的功能
    result = process_patient(patient_data)
    
    # Assert: 驗證結果
    assert result['status'] == 'processed'
```

### 2. 測試命名

- 使用描述性的測試名稱
- 遵循 `test_<功能>_<情境>_<預期結果>` 格式

```python
# 好的命名
def test_validate_taiwan_id_with_valid_id_returns_true():
    pass

def test_validate_taiwan_id_with_invalid_format_returns_false():
    pass

# 不好的命名
def test_taiwan_id():
    pass

def test_1():
    pass
```

### 3. 測試獨立性

每個測試應該獨立運行，不依賴其他測試：

```python
# 好的做法
class TestPatientService:
    def test_create_patient(self):
        patient = create_patient({"name": "王小明"})
        assert patient is not None
    
    def test_get_patient(self):
        patient = create_patient({"name": "李小華"})  # 獨立創建
        result = get_patient(patient['id'])
        assert result['name'] == "李小華"

# 不好的做法 - 測試互相依賴
class TestPatientService:
    patient_id = None
    
    def test_create_patient(self):
        patient = create_patient({"name": "王小明"})
        self.patient_id = patient['id']  # 依賴共享狀態
    
    def test_get_patient(self):
        result = get_patient(self.patient_id)  # 依賴前一個測試
        assert result is not None
```

### 4. 測試覆蓋率目標

- **關鍵功能**：90%+ 覆蓋率
- **一般功能**：70-80% 覆蓋率
- **UI/視圖層**：50-60% 覆蓋率

但記住：**高覆蓋率不等於高品質測試**。重要的是測試**正確的東西**。

### 5. 測試資料管理

```python
# 在 conftest.py 中集中管理測試資料
@pytest.fixture
def sample_fhir_patient():
    """標準的 FHIR Patient 資源"""
    return {
        'resourceType': 'Patient',
        'id': 'test-patient-001',
        'name': [{
            'use': 'official',
            'family': '王',
            'given': ['小明']
        }],
        'birthDate': '1970-01-01',
        'gender': 'male'
    }


@pytest.fixture
def sample_twcore_patient():
    """TW Core IG Patient 資源"""
    return {
        'resourceType': 'Patient',
        'id': 'twcore-patient-001',
        'identifier': [{
            'system': 'http://www.moi.gov.tw/',
            'value': 'A123456789'
        }],
        'name': [{
            'use': 'official',
            'text': '王小明',
            'extension': [{
                'url': 'http://hl7.org/fhir/StructureDefinition/iso21090-EN-representation',
                'valueCode': 'IDE'
            }]
        }]
    }
```

### 6. 錯誤處理測試

```python
def test_error_handling():
    """確保錯誤被正確處理"""
    # 測試預期的異常
    with pytest.raises(ValueError, match="Invalid input"):
        process_invalid_data(None)
    
    # 測試錯誤日誌
    with pytest.raises(Exception) as exc_info:
        risky_operation()
    assert "expected error message" in str(exc_info.value)
```

### 7. 整合測試策略

```python
@pytest.mark.integration
class TestRiskAssessmentFlow:
    """測試完整的風險評估流程"""
    
    def test_complete_hbr_assessment(self, app, client):
        """從登入到風險評估的完整流程"""
        # 1. 模擬 SMART on FHIR 認證
        # 2. 獲取病患資料
        # 3. 評估 HBR 風險
        # 4. 生成報告
        pass
```

## CI/CD 整合

### GitHub Actions 範例

在 `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v --cov=. --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        files: ./coverage.xml
        fail_ci_if_error: true
```

### Docker 環境測試

```bash
# 在 Docker 容器中執行測試
docker-compose run --rm app pytest tests/ -v
```

## 疑難排解

### 常見問題

1. **ModuleNotFoundError**
   ```bash
   # 確保測試環境有正確的 Python path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   pytest tests/
   ```

2. **Fixture not found**
   ```python
   # 確保 conftest.py 在正確的位置
   tests/
   ├── conftest.py  # 這裡
   └── test_*.py
   ```

3. **Coverage 報告不準確**
   ```bash
   # 清除舊的 coverage 資料
   coverage erase
   pytest tests/ --cov=. --cov-report=html
   ```

## 相關資源

- [Pytest 官方文檔](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [測試狀態報告](./test_status_report.md)
- [專案架構文檔](../architecture/microservices.md)

---

**需要幫助？** 查看 [測試狀態報告](./test_status_report.md) 或聯繫開發團隊。

