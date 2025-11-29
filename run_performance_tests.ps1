# Performance and Load Testing Script for PRECISE-HBR
# PowerShell script for Windows

param(
    [string]$TestType = "all",
    [int]$Users = 10,
    [int]$SpawnRate = 2,
    [int]$Duration = 60,
    [string]$Host = "http://localhost:8080"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PRECISE-HBR Performance Testing Suite" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check if required packages are installed
function Check-Dependencies {
    Write-Host "Checking dependencies..." -ForegroundColor Yellow
    
    # Check locust
    $locustInstalled = pip show locust 2>$null
    if (-not $locustInstalled) {
        Write-Host "Installing locust..." -ForegroundColor Yellow
        pip install locust
    }
    
    # Check pytest-benchmark
    $benchmarkInstalled = pip show pytest-benchmark 2>$null
    if (-not $benchmarkInstalled) {
        Write-Host "Installing pytest-benchmark..." -ForegroundColor Yellow
        pip install pytest-benchmark
    }
    
    Write-Host "Dependencies OK" -ForegroundColor Green
}

# Run pytest performance tests
function Run-PerformanceTests {
    Write-Host ""
    Write-Host "Running Performance Tests..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    python -m pytest tests/test_performance.py -v --tb=short -q
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Performance tests PASSED" -ForegroundColor Green
    } else {
        Write-Host "Some performance tests FAILED" -ForegroundColor Red
    }
}

# Run load tests with Locust
function Run-LoadTests {
    param(
        [int]$NumUsers,
        [int]$SpawnRatePerSec,
        [int]$DurationSec,
        [string]$HostUrl
    )
    
    Write-Host ""
    Write-Host "Running Load Tests..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    Write-Host "Users: $NumUsers"
    Write-Host "Spawn Rate: $SpawnRatePerSec/sec"
    Write-Host "Duration: $DurationSec seconds"
    Write-Host "Host: $HostUrl"
    Write-Host ""
    
    # Run locust in headless mode
    locust -f tests/load_tests/locustfile.py `
        --host=$HostUrl `
        --users=$NumUsers `
        --spawn-rate=$SpawnRatePerSec `
        --run-time="${DurationSec}s" `
        --headless `
        --only-summary `
        --csv=load_test_results
    
    if (Test-Path "load_test_results_stats.csv") {
        Write-Host ""
        Write-Host "Load test results saved to load_test_results_*.csv" -ForegroundColor Green
    }
}

# Run quick smoke test
function Run-SmokeTest {
    Write-Host ""
    Write-Host "Running Quick Smoke Test..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    locust -f tests/load_tests/locustfile.py `
        --host=$Host `
        --users=5 `
        --spawn-rate=5 `
        --run-time="10s" `
        --headless `
        --only-summary `
        QuickSmokeTest
}

# Run stress test
function Run-StressTest {
    Write-Host ""
    Write-Host "Running Stress Test..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    locust -f tests/load_tests/locustfile.py `
        --host=$Host `
        --users=50 `
        --spawn-rate=10 `
        --run-time="120s" `
        --headless `
        --csv=stress_test_results `
        StressTest
}

# Run soak test
function Run-SoakTest {
    Write-Host ""
    Write-Host "Running Soak Test (5 minutes)..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    locust -f tests/load_tests/locustfile.py `
        --host=$Host `
        --users=20 `
        --spawn-rate=2 `
        --run-time="300s" `
        --headless `
        --csv=soak_test_results `
        SoakTest
}

# Start Locust Web UI
function Start-LoadTestUI {
    Write-Host ""
    Write-Host "Starting Locust Web UI..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    Write-Host "Web UI will be available at http://localhost:8089" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    
    locust -f tests/load_tests/locustfile.py --host=$Host
}

# Generate performance report
function Generate-Report {
    Write-Host ""
    Write-Host "Generating Performance Report..." -ForegroundColor Yellow
    Write-Host "-------------------------------------------"
    
    $reportPath = "performance_report_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
    
    $report = @"
# Performance Test Report

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
**Host:** $Host

## Test Results Summary

### Performance Tests
$(python -m pytest tests/test_performance.py -v --tb=no -q 2>&1 | Out-String)

### Load Test Files
"@

    if (Test-Path "load_test_results_stats.csv") {
        $report += "`n- load_test_results_stats.csv"
    }
    if (Test-Path "stress_test_results_stats.csv") {
        $report += "`n- stress_test_results_stats.csv"
    }
    if (Test-Path "soak_test_results_stats.csv") {
        $report += "`n- soak_test_results_stats.csv"
    }

    $report | Out-File -FilePath $reportPath -Encoding utf8
    Write-Host "Report saved to $reportPath" -ForegroundColor Green
}

# Main execution
Check-Dependencies

switch ($TestType.ToLower()) {
    "performance" {
        Run-PerformanceTests
    }
    "load" {
        Run-LoadTests -NumUsers $Users -SpawnRatePerSec $SpawnRate -DurationSec $Duration -HostUrl $Host
    }
    "smoke" {
        Run-SmokeTest
    }
    "stress" {
        Run-StressTest
    }
    "soak" {
        Run-SoakTest
    }
    "ui" {
        Start-LoadTestUI
    }
    "report" {
        Generate-Report
    }
    "all" {
        Run-PerformanceTests
        Write-Host ""
        Write-Host "Note: Load tests require the application to be running." -ForegroundColor Yellow
        Write-Host "Start the app with 'python APP.py' and then run:" -ForegroundColor Yellow
        Write-Host "  .\run_performance_tests.ps1 -TestType load" -ForegroundColor Cyan
    }
    default {
        Write-Host "Usage: .\run_performance_tests.ps1 -TestType <type> [options]" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Test Types:"
        Write-Host "  performance  - Run pytest performance tests"
        Write-Host "  load         - Run load tests with Locust"
        Write-Host "  smoke        - Quick smoke test (10 seconds)"
        Write-Host "  stress       - Stress test (2 minutes)"
        Write-Host "  soak         - Soak test (5 minutes)"
        Write-Host "  ui           - Start Locust Web UI"
        Write-Host "  report       - Generate performance report"
        Write-Host "  all          - Run all tests"
        Write-Host ""
        Write-Host "Options:"
        Write-Host "  -Users       - Number of simulated users (default: 10)"
        Write-Host "  -SpawnRate   - Users spawned per second (default: 2)"
        Write-Host "  -Duration    - Test duration in seconds (default: 60)"
        Write-Host "  -Host        - Target host URL (default: http://localhost:8080)"
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Performance Testing Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

