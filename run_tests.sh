#!/bin/bash
# PRECISE-HBR 測試執行腳本
# Linux/macOS 版本

echo "========================================"
echo "PRECISE-HBR 測試套件"
echo "========================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 檢查 pytest 是否已安裝
echo -e "${YELLOW}檢查測試環境...${NC}"
if ! python -m pytest --version &> /dev/null; then
    echo -e "${RED}❌ pytest 未安裝，正在安裝必要套件...${NC}"
    pip install pytest pytest-cov flask-wtf coverage
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 安裝失敗，請手動執行: pip install pytest pytest-cov flask-wtf coverage${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ pytest 已安裝${NC}"
fi

echo ""

# 詢問用戶要執行的測試類型
echo -e "${CYAN}選擇測試類型：${NC}"
echo "  1) 執行所有測試"
echo "  2) 執行所有測試 + 覆蓋率報告"
echo "  3) 僅執行單元測試"
echo "  4) 僅執行整合測試"
echo "  5) 僅執行安全測試"
echo "  6) 執行特定測試文件"
echo ""

read -p "請選擇 (1-6): " choice

echo ""
echo "========================================"

case $choice in
    1)
        echo -e "${YELLOW}執行所有測試...${NC}"
        python -m pytest tests/ -v --tb=short --no-cov
        ;;
    2)
        echo -e "${YELLOW}執行所有測試 + 生成覆蓋率報告...${NC}"
        python -m pytest tests/ -v --tb=short --cov=. --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}✅ 覆蓋率報告已生成：htmlcov/index.html${NC}"
        read -p "是否開啟覆蓋率報告? (Y/N): " openReport
        if [[ $openReport == "Y" || $openReport == "y" ]]; then
            # 根據操作系統選擇適當的開啟命令
            if [[ "$OSTYPE" == "darwin"* ]]; then
                open htmlcov/index.html
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                xdg-open htmlcov/index.html
            fi
        fi
        ;;
    3)
        echo -e "${YELLOW}執行單元測試...${NC}"
        python -m pytest tests/ -v -m unit --tb=short --no-cov
        ;;
    4)
        echo -e "${YELLOW}執行整合測試...${NC}"
        python -m pytest tests/ -v -m integration --tb=short --no-cov
        ;;
    5)
        echo -e "${YELLOW}執行安全測試...${NC}"
        python -m pytest tests/ -v -m security --tb=short --no-cov
        ;;
    6)
        echo -e "${CYAN}可用的測試文件：${NC}"
        ls tests/test_*.py | xargs -n 1 basename | while read file; do
            echo "  - $file"
        done
        echo ""
        read -p "請輸入測試文件名稱 (例如: test_twcore_adapter.py): " testFile
        echo ""
        echo -e "${YELLOW}執行 $testFile...${NC}"
        python -m pytest "tests/$testFile" -v --tb=short --no-cov
        ;;
    *)
        echo -e "${RED}❌ 無效的選擇${NC}"
        exit 1
        ;;
esac

echo ""
echo "========================================"

# 顯示測試結果統計
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 所有測試通過！${NC}"
else
    echo -e "${YELLOW}⚠️ 有測試失敗，請查看上方詳細資訊${NC}"
    echo -e "${YELLOW}提示：查看完整測試報告請執行選項 2${NC}"
fi

echo "========================================"
echo ""
echo -e "${CYAN}更多資訊請參考：docs/testing/test_status_report.md${NC}"

