# PRECISE-HBR 測試執行腳本
# PowerShell 版本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PRECISE-HBR 測試套件" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 檢查 pytest 是否已安裝
Write-Host "檢查測試環境..." -ForegroundColor Yellow
$pytestCheck = python -m pytest --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ pytest 未安裝，正在安裝必要套件..." -ForegroundColor Red
    pip install pytest pytest-cov flask-wtf coverage
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 安裝失敗，請手動執行: pip install pytest pytest-cov flask-wtf coverage" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ pytest 已安裝" -ForegroundColor Green
}

Write-Host ""

# 詢問用戶要執行的測試類型
Write-Host "選擇測試類型：" -ForegroundColor Cyan
Write-Host "  1) 執行所有測試"
Write-Host "  2) 執行所有測試 + 覆蓋率報告"
Write-Host "  3) 僅執行單元測試"
Write-Host "  4) 僅執行整合測試"
Write-Host "  5) 僅執行安全測試"
Write-Host "  6) 執行特定測試文件"
Write-Host ""

$choice = Read-Host "請選擇 (1-6)"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

switch ($choice) {
    "1" {
        Write-Host "執行所有測試..." -ForegroundColor Yellow
        python -m pytest tests/ -v --tb=short --no-cov
    }
    "2" {
        Write-Host "執行所有測試 + 生成覆蓋率報告..." -ForegroundColor Yellow
        python -m pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term-missing
        Write-Host ""
        Write-Host "✅ 覆蓋率報告已生成：htmlcov/index.html" -ForegroundColor Green
        $openReport = Read-Host "是否開啟覆蓋率報告? (Y/N)"
        if ($openReport -eq "Y" -or $openReport -eq "y") {
            Start-Process "htmlcov/index.html"
        }
    }
    "3" {
        Write-Host "執行單元測試..." -ForegroundColor Yellow
        python -m pytest tests/ -v -m unit --tb=short --no-cov
    }
    "4" {
        Write-Host "執行整合測試..." -ForegroundColor Yellow
        python -m pytest tests/ -v -m integration --tb=short --no-cov
    }
    "5" {
        Write-Host "執行安全測試..." -ForegroundColor Yellow
        python -m pytest tests/ -v -m security --tb=short --no-cov
    }
    "6" {
        Write-Host "可用的測試文件：" -ForegroundColor Cyan
        Get-ChildItem tests\test_*.py | ForEach-Object { Write-Host "  - $($_.Name)" }
        Write-Host ""
        $testFile = Read-Host "請輸入測試文件名稱 (例如: test_twcore_adapter.py)"
        Write-Host ""
        Write-Host "執行 $testFile..." -ForegroundColor Yellow
        python -m pytest "tests/$testFile" -v --tb=short --no-cov
    }
    default {
        Write-Host "❌ 無效的選擇" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "測試執行完畢" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

# 顯示測試結果統計
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 所有測試通過！" -ForegroundColor Green
} else {
    Write-Host "⚠️ 有測試失敗，請查看上方詳細資訊" -ForegroundColor Yellow
    Write-Host "提示：查看完整測試報告請執行選項 2" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "更多資訊請參考：docs/testing/test_status_report.md" -ForegroundColor Cyan

