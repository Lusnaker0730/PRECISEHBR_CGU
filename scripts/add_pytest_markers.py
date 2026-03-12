#!/usr/bin/env python3
"""
批次補齊 pytest 法規追溯標記
==============================
掃描所有測試檔案，在 class 或 function 層級加入：
- @pytest.mark.requirement("SRS-XXX")
- @pytest.mark.risk("RISK-XXX")
- @pytest.mark.design("SDS-XXX")

用法: python scripts/add_pytest_markers.py [--dry-run]
"""

import re
import os
import argparse

TESTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests")

# ============================================================
# 標記定義：file → { class_or_function → markers }
# 使用 "__module__" 表示模組層級（加在第一個 class/function 前面）
# 使用 class 名表示 class 層級
# ============================================================
MARKER_MAP = {
    # --- 單位轉換 ---
    "test_unit_conversion_service.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-003")',
            '@pytest.mark.risk("RISK-003")',
            '@pytest.mark.design("SDS-003")',
        ],
    },
    # --- FHIR 服務 ---
    "test_fhir_service.py": {
        "TestPatientDemographics": ['@pytest.mark.requirement("SRS-004")'],
        "TestUnitConversion": ['@pytest.mark.requirement("SRS-003")', '@pytest.mark.risk("RISK-003")'],
        "TestConditionChecker": ['@pytest.mark.requirement("SRS-012")', '@pytest.mark.risk("RISK-001")'],
        "TestRiskCalculation": ['@pytest.mark.requirement("SRS-002")', '@pytest.mark.risk("RISK-001")'],
        "TestArcHbrFactors": ['@pytest.mark.requirement("SRS-012")'],
        "TestMedicationFunctions": ['@pytest.mark.requirement("SRS-012")'],
        "TestHelperFunctions": ['@pytest.mark.requirement("SRS-001")'],
        "TestErrorHandling": ['@pytest.mark.requirement("SRS-004")', '@pytest.mark.risk("RISK-004")'],
    },
    # --- OAuth2 / Auth 安全 ---
    "test_auth_security.py": {
        "TestPKCESecurity": ['@pytest.mark.requirement("SRS-005")', '@pytest.mark.risk("RISK-005")', '@pytest.mark.design("SDS-005")'],
        "TestAuthRouteSecurity": ['@pytest.mark.requirement("SRS-005")', '@pytest.mark.risk("RISK-005")'],
        "TestTokenExchangeSecurity": ['@pytest.mark.requirement("SRS-005")', '@pytest.mark.risk("RISK-005")'],
        "TestSmartConfigSecurity": ['@pytest.mark.requirement("SRS-005")'],
        "TestSessionSecurity": ['@pytest.mark.requirement("SRS-005")', '@pytest.mark.risk("RISK-005")'],
        "TestErrorHandlingSecurity": ['@pytest.mark.requirement("SRS-006")', '@pytest.mark.risk("RISK-006")'],
        "TestCernerSandboxSecurity": ['@pytest.mark.requirement("SRS-005")'],
    },
    # --- SMART Security ---
    "test_smart_security.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-005")',
            '@pytest.mark.risk("RISK-005")',
            '@pytest.mark.design("SDS-005")',
        ],
    },
    # --- OIDC Validator ---
    "test_oidc_validator.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-005")',
            '@pytest.mark.risk("RISK-005")',
        ],
    },
    # --- MFA Validator ---
    "test_mfa_validator.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-005")',
        ],
    },
    # --- 輸入驗證 ---
    "test_input_validation.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-006")',
            '@pytest.mark.risk("RISK-006")',
        ],
    },
    "test_input_validator_module.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-006")',
            '@pytest.mark.risk("RISK-006")',
            '@pytest.mark.design("SDS-006")',
        ],
    },
    # --- Patient Context / BOLA ---
    "test_patient_context.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-006")',
            '@pytest.mark.risk("RISK-009")',
            '@pytest.mark.design("SDS-006")',
        ],
    },
    # --- CDS Hooks ---
    "test_hooks.py": {
        "TestMedicationChecking": ['@pytest.mark.requirement("SRS-008")', '@pytest.mark.requirement("SRS-012")', '@pytest.mark.design("SDS-008")'],
        "TestCardCreation": ['@pytest.mark.requirement("SRS-008")', '@pytest.mark.design("SDS-008")'],
        "TestCDSServicesEndpoint": ['@pytest.mark.requirement("SRS-008")'],
        "TestPreciseHBRHook": ['@pytest.mark.requirement("SRS-008")'],
        "TestCORSConfiguration": ['@pytest.mark.requirement("SRS-008")'],
        "TestErrorHandling": ['@pytest.mark.requirement("SRS-008")'],
        "TestIntegration": ['@pytest.mark.requirement("SRS-008")'],
    },
    # --- TW Core ---
    "test_twcore_adapter.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-009")',
            '@pytest.mark.design("SDS-009")',
        ],
    },
    # --- 稽核日誌 ---
    "test_audit_logger_extended.py": {
        "TestAuditLoggerInitialization": ['@pytest.mark.requirement("SRS-010")', '@pytest.mark.design("SDS-010")'],
        "TestAuditEventLogging": ['@pytest.mark.requirement("SRS-010")'],
        "TestTamperResistance": ['@pytest.mark.requirement("SRS-010")', '@pytest.mark.risk("RISK-008")'],
        "TestAuditDecorator": ['@pytest.mark.requirement("SRS-010")'],
        "TestAuditQuery": ['@pytest.mark.requirement("SRS-010")'],
        "TestErrorHandling": ['@pytest.mark.requirement("SRS-010")'],
        "TestComplianceFeatures": ['@pytest.mark.requirement("SRS-010")'],
    },
    # --- ePHI 保護 ---
    "test_ephi_protection.py": {
        "TestePHIAccessControl": ['@pytest.mark.requirement("SRS-006")', '@pytest.mark.risk("RISK-008")'],
        "TestePHITransmission": ['@pytest.mark.requirement("SRS-006")'],
        "TestePHIStorage": ['@pytest.mark.requirement("SRS-006")'],
        "TestePHILogging": ['@pytest.mark.requirement("SRS-010")', '@pytest.mark.risk("RISK-008")'],
        "TestePHIDisclosure": ['@pytest.mark.requirement("SRS-006")', '@pytest.mark.risk("RISK-008")'],
        "TestDataRetention": ['@pytest.mark.requirement("SRS-010")'],
        "TestBreachNotification": ['@pytest.mark.requirement("SRS-010")'],
        "TestPatientPrivacy": ['@pytest.mark.requirement("SRS-011")'],
        "TestSecurityMonitoring": ['@pytest.mark.requirement("SRS-010")'],
        "TestThirdPartyIntegration": ['@pytest.mark.requirement("SRS-005")'],
    },
    # --- Consent Service ---
    "test_consent_service.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-011")',
            '@pytest.mark.design("SDS-011")',
        ],
    },
    # --- Condition Checker Config ---
    "test_condition_checker_config.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-012")',
            '@pytest.mark.risk("RISK-001")',
            '@pytest.mark.design("SDS-012")',
        ],
    },
    # --- Config Loader ---
    "test_config_loader.py": {
        "TestConfigLoader": ['@pytest.mark.requirement("SRS-001")'],
        "TestPreciseHbrParameters": ['@pytest.mark.requirement("SRS-001")', '@pytest.mark.design("SDS-001")'],
        "TestSnomedCodes": ['@pytest.mark.requirement("SRS-012")'],
        "TestMedicationKeywords": ['@pytest.mark.requirement("SRS-012")'],
        "TestBleedingHistoryKeywords": ['@pytest.mark.requirement("SRS-012")'],
        "TestLaboratoryValues": ['@pytest.mark.requirement("SRS-003")'],
        "TestUnitConversionConfig": ['@pytest.mark.requirement("SRS-003")'],
        "TestConfigReload": ['@pytest.mark.requirement("SRS-001")'],
        "TestConfigValidation": ['@pytest.mark.requirement("SRS-001")'],
        "TestErrorHandling": ['@pytest.mark.requirement("SRS-001")'],
        "TestICD10Codes": ['@pytest.mark.requirement("SRS-009")', '@pytest.mark.requirement("SRS-012")'],
        "TestNHICodes": ['@pytest.mark.requirement("SRS-009")', '@pytest.mark.requirement("SRS-012")'],
    },
    # --- Security Comprehensive ---
    "test_security_comprehensive.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-006")',
            '@pytest.mark.risk("RISK-006")',
        ],
    },
    # --- Security Labels ---
    "test_security_labels.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-006")',
        ],
    },
    # --- Risk Classifier (補充未標記的 classes) ---
    "test_risk_classifier.py": {
        "TestBleedingRiskPercentage": ['@pytest.mark.requirement("SRS-002")', '@pytest.mark.risk("RISK-001")'],
    },
    # --- Tradeoff ---
    "verify_tradeoff.py": {
        "__module_markers__": [
            '@pytest.mark.requirement("SRS-007")',
            '@pytest.mark.risk("RISK-007")',
            '@pytest.mark.design("SDS-007")',
        ],
    },
    # --- App Basic ---
    "test_app_basic.py": {
        "test_cds_services_endpoint": ['@pytest.mark.requirement("SRS-008")'],
        "test_launch_endpoint_exists": ['@pytest.mark.requirement("SRS-005")'],
        "test_callback_endpoint_exists": ['@pytest.mark.requirement("SRS-005")'],
        "test_security_headers": ['@pytest.mark.requirement("SRS-006")'],
        "test_cors_headers": ['@pytest.mark.requirement("SRS-008")'],
    },
    # --- App E2E ---
    "test_app_e2e.py": {
        "TestCDSServicesEndpoint": ['@pytest.mark.requirement("SRS-008")'],
    },
}


def add_module_level_markers(content, markers):
    """在檔案的 import 區塊後，第一個 class/function 前加入 pytestmark"""
    marker_names = []
    for m in markers:
        # Strip @ prefix for pytestmark list syntax
        m_clean = m.lstrip("@")
        marker_names.append(f"    {m_clean},")

    pytestmark_block = "pytestmark = [\n" + "\n".join(marker_names) + "\n]\n"

    # Check if pytestmark already exists
    if "pytestmark" in content:
        return content, False

    # Find insertion point: after all top-level imports, before first class/def
    lines = content.split("\n")
    in_multiline_import = False
    last_import_end = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track multi-line import blocks: from foo import (\n  bar,\n  baz\n)
        if in_multiline_import:
            if ")" in stripped:
                in_multiline_import = False
                last_import_end = i
            continue

        # Only consider top-level lines (no leading whitespace)
        if line != line.lstrip():
            continue

        if stripped.startswith("import ") or stripped.startswith("from "):
            if "(" in stripped and ")" not in stripped:
                in_multiline_import = True
            last_import_end = i

    # Ensure pytest is imported
    has_pytest_import = any(
        line.strip() == "import pytest" and line == line.lstrip()
        for line in lines
    )
    if not has_pytest_import:
        lines.insert(last_import_end + 1, "import pytest")
        last_import_end += 1

    # Insert pytestmark after all imports
    insert_at = last_import_end + 1
    # Skip blank lines after imports
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, pytestmark_block)

    return "\n".join(lines), True


def add_class_level_markers(content, class_name, markers):
    """在指定 class 定義前加入 markers"""
    marker_lines = "\n".join(markers)

    # Pattern: find "class ClassName" that doesn't already have these markers
    pattern = rf"(^(?!.*@pytest\.mark\.))(class {class_name}\b)"
    # More robust: find the class line and check preceding lines
    lines = content.split("\n")
    modified = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(rf"^class {class_name}\b", stripped):
            # Check if markers already exist above this class
            existing_markers = set()
            j = i - 1
            while j >= 0 and lines[j].strip().startswith("@pytest.mark."):
                existing_markers.add(lines[j].strip())
                j -= 1

            indent = len(line) - len(line.lstrip())
            indent_str = " " * indent

            new_markers = []
            for m in markers:
                if m not in existing_markers:
                    new_markers.append(f"{indent_str}{m}")

            if new_markers:
                for idx, nm in enumerate(new_markers):
                    lines.insert(i + idx, nm)
                modified = True
            break

    if modified:
        # Ensure pytest import exists
        has_pytest_import = any("import pytest" in line for line in lines)
        if not has_pytest_import:
            for i, line in enumerate(lines):
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    lines.insert(i, "import pytest")
                    break
        return "\n".join(lines), True
    return content, False


def add_function_level_markers(content, func_name, markers):
    """在指定 function 定義前加入 markers（用於非 class 內的 function）"""
    lines = content.split("\n")
    modified = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(rf"^def {func_name}\b", stripped):
            existing_markers = set()
            j = i - 1
            while j >= 0 and lines[j].strip().startswith("@pytest.mark."):
                existing_markers.add(lines[j].strip())
                j -= 1

            indent = len(line) - len(line.lstrip())
            indent_str = " " * indent

            new_markers = []
            for m in markers:
                if m not in existing_markers:
                    new_markers.append(f"{indent_str}{m}")

            if new_markers:
                for idx, nm in enumerate(new_markers):
                    lines.insert(i + idx, nm)
                modified = True
            break

    if modified:
        has_pytest_import = any("import pytest" in line for line in lines)
        if not has_pytest_import:
            for i, line in enumerate(lines):
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    lines.insert(i, "import pytest")
                    break
        return "\n".join(lines), True
    return content, False


def process_file(filename, marker_config, dry_run=False):
    """處理單一測試檔案"""
    filepath = os.path.join(TESTS_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [跳過] {filename} (檔案不存在)")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    changes = 0

    # Module-level markers
    if "__module_markers__" in marker_config:
        content, changed = add_module_level_markers(content, marker_config["__module_markers__"])
        if changed:
            changes += 1

    # Class-level and function-level markers
    for target, markers in marker_config.items():
        if target == "__module_markers__":
            continue

        # Determine if target is a class or function
        if target[0].isupper() and not target.startswith("test_"):
            # It's a class
            content, changed = add_class_level_markers(content, target, markers)
        else:
            # It's a function
            content, changed = add_function_level_markers(content, target, markers)

        if changed:
            changes += 1

    if content != original:
        if dry_run:
            print(f"  [模擬] {filename}: {changes} 處變更")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  [更新] {filename}: {changes} 處變更")
    else:
        print(f"  [無變更] {filename}")

    return changes


def main():
    parser = argparse.ArgumentParser(description="批次補齊 pytest 法規追溯標記")
    parser.add_argument("--dry-run", action="store_true", help="模擬執行，不實際修改")
    args = parser.parse_args()

    print("=== 批次補齊 pytest 法規追溯標記 ===\n")

    if args.dry_run:
        print("*** 模擬模式 ***\n")

    total_changes = 0
    for filename, marker_config in MARKER_MAP.items():
        total_changes += process_file(filename, marker_config, args.dry_run)

    print(f"\n=== 完成: {total_changes} 處變更 ===")


if __name__ == "__main__":
    main()
