# Test Traceability Report (IEC 62304)
Generated: 2026-03-13T06:37:01.399966+00:00

## Summary
- Total tests: 948
- Traced tests: 841 (88.7%)
- **Untraced tests: 107**
- Passed: 841, Failed: 0

## Traced Tests

| Test | Result | Requirements | Risks | Design |
|------|--------|-------------|-------|--------|
| `tests/test_app_basic.py::test_cds_services_endpoint` | passed | SRS-008 | - | - |
| `tests/test_app_basic.py::test_launch_endpoint_exists` | passed | SRS-005 | - | - |
| `tests/test_app_basic.py::test_callback_endpoint_exists` | passed | SRS-005 | - | - |
| `tests/test_app_basic.py::test_cors_headers` | passed | SRS-008 | - | - |
| `tests/test_app_basic.py::test_security_headers` | passed | SRS-006 | - | - |
| `tests/test_app_e2e.py::TestCDSServicesEndpoint::test_cds_services_returns_200` | passed | SRS-008 | - | - |
| `tests/test_app_e2e.py::TestCDSServicesEndpoint::test_cds_services_returns_json` | passed | SRS-008 | - | - |
| `tests/test_app_e2e.py::TestCDSServicesEndpoint::test_cds_services_contains_services` | passed | SRS-008 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditLoggerInitialization::test_audit_logger_creates_directory` | passed | SRS-010 | - | SDS-010 |
| `tests/test_audit_logger_extended.py::TestAuditLoggerInitialization::test_audit_logger_initializes_log_file` | passed | SRS-010 | - | SDS-010 |
| `tests/test_audit_logger_extended.py::TestAuditLoggerInitialization::test_audit_logger_auto_detects_path_local` | passed | SRS-010 | - | SDS-010 |
| `tests/test_audit_logger_extended.py::TestAuditLoggerInitialization::test_audit_logger_auto_detects_path_gae` | passed | SRS-010 | - | SDS-010 |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_basic` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_with_patient_id` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_with_resource_info` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_with_outcome` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_with_details` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditEventLogging::test_log_event_with_network_info` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestTamperResistance::test_hash_chain_integrity` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestTamperResistance::test_hash_calculation_deterministic` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestTamperResistance::test_hash_changes_with_data` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestTamperResistance::test_verify_chain_integrity_success` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestTamperResistance::test_detect_tampered_entry` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAuditDecorator::test_decorator_logs_ephi_access` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditDecorator::test_decorator_captures_ip_address` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditDecorator::test_decorator_captures_user_agent` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditQuery::test_query_by_user_id` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditQuery::test_query_by_patient_id` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditQuery::test_query_by_event_type` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAuditQuery::test_query_by_action` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestErrorHandling::test_handles_read_only_filesystem` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestErrorHandling::test_handles_write_error` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestErrorHandling::test_handles_corrupted_log_file` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestComplianceFeatures::test_timestamp_in_iso_format_with_milliseconds` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestComplianceFeatures::test_all_required_fields_present` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestComplianceFeatures::test_log_header_contains_compliance_info` | passed | SRS-010 | - | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_fhir_user_recorded_in_log_event` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_fhir_user_none_when_not_provided` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_get_request_context_extracts_forwarded_ip` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_get_request_context_fallback_to_remote_addr` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_get_request_context_extracts_fhir_user_from_session` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_get_trace_context_extracts_trace_id` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_get_trace_context_empty_without_header` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_trace_context_merged_into_details` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestAudit5WCompliance::test_decorator_passes_fhir_user` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestGCPStructuredLogging::test_structured_log_emitted_on_gae` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestGCPStructuredLogging::test_no_structured_log_outside_gae` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestGCPStructuredLogging::test_structured_log_includes_trace_link` | passed | SRS-010 | RISK-008 | - |
| `tests/test_audit_logger_extended.py::TestGCPStructuredLogging::test_hash_chain_still_valid_with_fhir_user` | passed | SRS-010 | RISK-008 | - |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_parameters_generation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_parameters_are_unique` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_validation_success` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_validation_failure_mismatch` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_validation_failure_missing_verifier` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_validation_failure_missing_challenge` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_challenge_uses_sha256` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestPKCESecurity::test_pkce_parameters_use_secure_random` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_launch_missing_iss_parameter` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_launch_stores_parameters_in_session` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_launch_generates_state_parameter` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_launch_generates_pkce_parameters` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_launch_includes_pkce_in_auth_url` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_callback_handles_error_response` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_callback_requires_code_parameter` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestAuthRouteSecurity::test_callback_with_valid_code_renders_page` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_validates_state_parameter` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_requires_smart_config_in_session` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_validates_pkce_parameters` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_stores_token_securely` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_includes_pkce_verifier_in_request` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestTokenExchangeSecurity::test_exchange_code_handles_token_endpoint_error` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestSmartConfigSecurity::test_get_smart_config_uses_https_preferred` | passed | SRS-005 | - | - |
| `tests/test_auth_security.py::TestSmartConfigSecurity::test_get_smart_config_handles_network_error` | passed | SRS-005 | - | - |
| `tests/test_auth_security.py::TestSmartConfigSecurity::test_get_smart_config_validates_required_endpoints` | passed | SRS-005 | - | - |
| `tests/test_auth_security.py::TestSmartConfigSecurity::test_get_smart_config_falls_back_to_metadata` | passed | SRS-005 | - | - |
| `tests/test_auth_security.py::TestSmartConfigSecurity::test_get_smart_config_uses_timeout` | passed | SRS-005 | - | - |
| `tests/test_auth_security.py::TestSessionSecurity::test_state_parameter_is_consumed_after_use` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestSessionSecurity::test_session_contains_no_sensitive_data_in_plain_text` | passed | SRS-005 | RISK-005 | - |
| `tests/test_auth_security.py::TestErrorHandlingSecurity::test_error_page_does_not_leak_stack_trace` | passed | SRS-006 | RISK-006 | - |
| `tests/test_auth_security.py::TestErrorHandlingSecurity::test_error_page_sanitizes_user_input` | passed | SRS-006 | RISK-006 | - |
| `tests/test_bola_deep.py::TestTradeoffBOLA::test_tradeoff_rejects_different_patient_id` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestTradeoffBOLA::test_tradeoff_accepts_authorized_patient_id` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestTradeoffBOLA::test_tradeoff_missing_patient_id_returns_400` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestTradeoffBOLA::test_tradeoff_no_session_returns_403` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestTradeoffBOLA::test_tradeoff_active_factors_bypasses_bola` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_patient_resource_matching_id` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_patient_resource_mismatched_id` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_observation_with_correct_subject` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_observation_with_wrong_subject` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_condition_with_full_url_reference` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_condition_with_full_url_wrong_patient` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_resource_without_subject_passes` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestResourceOwnershipValidation::test_none_resource_passes` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestFilterOwnedResources::test_filters_out_mismatched_resources` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestFilterOwnedResources::test_empty_list_returns_empty` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestGetAllPatientDataOwnership::test_rejects_patient_resource_ownership_mismatch` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_bola_deep.py::TestGetAllPatientDataOwnership::test_filters_mismatched_observations` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_initial_state_is_closed` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_stays_closed_under_threshold` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_opens_at_threshold` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_success_resets_failure_count` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_half_open_after_recovery_timeout` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_half_open_success_closes_circuit` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_half_open_failure_reopens_circuit` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerStateMachine::test_manual_reset` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerMetrics::test_metrics_track_successes` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerMetrics::test_metrics_track_failures` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerMetrics::test_metrics_track_rejected` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerRegistry::test_returns_same_instance_for_same_name` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerRegistry::test_returns_different_instances_for_different_names` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerRegistry::test_server_a_open_does_not_affect_server_b` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerRegistry::test_get_all_metrics` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerThreadSafety::test_concurrent_failures_trip_circuit` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCircuitBreakerThreadSafety::test_concurrent_registry_access` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHooksFallbackCards::test_timeout_fallback_card` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHooksFallbackCards::test_circuit_open_fallback_card` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHooksFallbackCards::test_error_fallback_card` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHooksFallbackCards::test_fallback_card_has_valid_structure` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSDeadlineEnforcement::test_check_deadline_passes_when_within_limit` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSDeadlineEnforcement::test_check_deadline_raises_when_exceeded` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSDeadlineEnforcement::test_deadline_constant_is_reasonable` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHookEndpointFallback::test_medication_hook_returns_fallback_on_error` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHookEndpointFallback::test_patient_view_returns_fallback_on_error` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_circuit_breaker.py::TestCDSHookEndpointFallback::test_patient_view_no_patient_returns_empty` | passed | SRS-001 | RISK-002 | SDS-001 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_check_active_cancer_icd10` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_check_bleeding_diathesis_icd10` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_check_nsaids_nhi` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_check_oral_anticoagulation_nhi` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_check_prior_bleeding_icd10` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_condition_checker_config.py::TestConditionCheckerConfigIntegration::test_config_has_new_fields` | passed | SRS-012 | RISK-001 | SDS-012 |
| `tests/test_config_loader.py::TestConfigLoader::test_singleton_pattern` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigLoader::test_config_loaded` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigLoader::test_get_version` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigLoader::test_get_scoring_logic` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestPreciseHbrParameters::test_get_precise_hbr_parameters` | passed | SRS-001 | - | SDS-001 |
| `tests/test_config_loader.py::TestPreciseHbrParameters::test_get_age_parameter` | passed | SRS-001 | - | SDS-001 |
| `tests/test_config_loader.py::TestPreciseHbrParameters::test_get_hemoglobin_parameter` | passed | SRS-001 | - | SDS-001 |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_bleeding_diathesis` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_prior_bleeding` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_active_cancer` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_liver_cirrhosis` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_thrombocytopenia` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestSnomedCodes::test_get_snomed_codes_invalid_key` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestMedicationKeywords::test_get_medication_keywords` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestMedicationKeywords::test_get_oral_anticoagulants` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestMedicationKeywords::test_get_nsaids_corticosteroids` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestBleedingHistoryKeywords::test_get_bleeding_history_keywords` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestLaboratoryValues::test_get_lab_value_extraction_config` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestLaboratoryValues::test_get_hemoglobin_loinc_codes` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestLaboratoryValues::test_get_creatinine_loinc_codes` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestLaboratoryValues::test_get_platelet_loinc_codes` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestUnitConversionConfig::test_get_unit_conversion_config` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestUnitConversionConfig::test_hemoglobin_conversion_factors` | passed | SRS-003 | - | - |
| `tests/test_config_loader.py::TestConfigReload::test_reload_config` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigValidation::test_config_has_required_sections` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigValidation::test_version_format` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestConfigValidation::test_scoring_method` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestErrorHandling::test_get_nonexistent_snomed_codes` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestErrorHandling::test_config_with_missing_file` | passed | SRS-001 | - | - |
| `tests/test_config_loader.py::TestICD10Codes::test_bleeding_diathesis_has_icd10_codes` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestICD10Codes::test_active_cancer_has_icd10_codes` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestNHICodes::test_oral_anticoagulants_have_nhi_codes` | passed | SRS-012 | - | - |
| `tests/test_config_loader.py::TestNHICodes::test_nsaids_have_nhi_codes` | passed | SRS-012 | - | - |
| `tests/test_config_loader_thread_safety.py::TestConfigLoaderSingleton::test_singleton_returns_same_instance` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConfigLoaderSingleton::test_config_loaded_on_first_access` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConfigLoaderSingleton::test_has_lock_attribute` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConcurrentInstantiation::test_concurrent_threads_get_same_instance` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConcurrentInstantiation::test_load_config_called_exactly_once` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConcurrentReads::test_concurrent_reads_return_consistent_config` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_config_loader_thread_safety.py::TestConcurrentReads::test_config_not_none_after_concurrent_init` | passed | SRS-006 | RISK-005 | SDS-006 |
| `tests/test_consent_service.py::TestConsentStatus::test_status_values_defined` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentStatus::test_status_enum_members` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentProvision::test_provision_values` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentResult::test_create_consent_result` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentResult::test_consent_result_to_dict` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_init_without_client` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_init_with_client` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_set_client` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_check_consent_without_client` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_check_consent_with_no_results` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentService::test_check_consent_with_active_consent` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentFiltering::test_filter_with_active_consent` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentFiltering::test_filter_with_no_consent` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentFiltering::test_filter_with_deny_provision` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestIsResourcePermitted::test_permitted_resource` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestIsResourcePermitted::test_denied_resource` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestIsResourcePermitted::test_no_consent_denies_all` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConvenienceFunctions::test_check_consent_before_access` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentSensitiveResources::test_sensitive_resources_defined` | passed | SRS-011 | - | SDS-011 |
| `tests/test_consent_service.py::TestConsentSensitiveResources::test_patient_not_in_sensitive` | passed | SRS-011 | - | SDS-011 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_patient_resource_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_observation_resource_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_condition_resource_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_bundle_entry_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_medication_request_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_consent_resource_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_dict_with_subject_key_treated_as_fhir` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_dict_with_identifier_key_treated_as_fhir` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_dict_with_telecom_treated_as_fhir` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestFhirResourceDetection::test_future_fhir_resource_with_extension` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_safe_keys_pass_through` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_unknown_keys_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_risk_score_keys_pass` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_nested_safe_dict` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_nested_unknown_keys_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_empty_dict_passes` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestDictKeyAllowlist::test_all_safe_keys_constant_coverage` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_ssn_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_us_phone_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_email_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_date_mmddyyyy_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_date_yyyymmdd_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_taiwan_national_id_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_taiwan_arc_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_taiwan_phone_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_taiwan_phone_intl_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_chinese_name_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_chinese_name_with_colon` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_chinese_patient_name` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_patient_reference_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_practitioner_reference_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_english_name_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_bearer_token_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_api_key_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_safe_operational_message_unchanged` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_safe_metric_message_unchanged` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestRegexPatterns::test_safe_error_message_unchanged` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestJsonBlobDetection::test_embedded_patient_json_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestJsonBlobDetection::test_embedded_observation_json_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestJsonBlobDetection::test_non_fhir_json_not_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_string_message_scrubbed` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_dict_args_sanitized` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_fhir_resource_in_args_fully_redacted` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_tuple_args_sanitized` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_filter_always_returns_true` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_none_msg_handled` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestLogRecordIntegration::test_none_args_handled` | passed | SRS-006 | RISK-008 | SDS-010 |
| `tests/test_ephi_allowlist_filter.py::TestCompletenessRegression::test_fhir_signals_include_demographics` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_allowlist_filter.py::TestCompletenessRegression::test_fhir_signals_include_clinical` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_allowlist_filter.py::TestCompletenessRegression::test_fhir_signals_include_identifiers` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_allowlist_filter.py::TestCompletenessRegression::test_fhir_signals_include_twcore_extension` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_allowlist_filter.py::TestCompletenessRegression::test_safe_keys_do_not_overlap_fhir_signals` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIAccessControl::test_ephi_requires_authentication` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIAccessControl::test_ephi_requires_authorization` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIAccessControl::test_minimum_necessary_principle` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHITransmission::test_https_enforced_in_production` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHITransmission::test_no_phi_in_url_parameters` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHITransmission::test_phi_in_request_body_only` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHIStorage::test_session_storage_secure` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHIStorage::test_no_phi_in_client_cookies` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHIStorage::test_session_data_encrypted` | passed | SRS-006 | - | - |
| `tests/test_ephi_protection.py::TestePHILogging::test_ephi_access_creates_audit_log` | passed | SRS-010 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHILogging::test_audit_log_includes_user_id` | passed | SRS-010 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHILogging::test_audit_log_includes_timestamp` | passed | SRS-010 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHILogging::test_audit_log_includes_action` | passed | SRS-010 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHILogging::test_phi_redacted_in_general_logs` | passed | SRS-010 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIDisclosure::test_no_phi_in_error_messages` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIDisclosure::test_no_phi_in_http_headers` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestePHIDisclosure::test_no_phi_in_referrer` | passed | SRS-006 | RISK-008 | - |
| `tests/test_ephi_protection.py::TestDataRetention::test_session_cleanup_after_logout` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestDataRetention::test_temporary_data_cleanup` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestDataRetention::test_audit_log_retention_period` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestBreachNotification::test_security_incident_logging` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestBreachNotification::test_failed_access_attempts_tracked` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestPatientPrivacy::test_patient_consent_tracking` | passed | SRS-011 | - | - |
| `tests/test_ephi_protection.py::TestPatientPrivacy::test_data_minimization` | passed | SRS-011 | - | - |
| `tests/test_ephi_protection.py::TestPatientPrivacy::test_right_to_access` | passed | SRS-011 | - | - |
| `tests/test_ephi_protection.py::TestSecurityMonitoring::test_unusual_activity_detection` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestSecurityMonitoring::test_security_alerts_configured` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestSecurityMonitoring::test_log_analysis_capability` | passed | SRS-010 | - | - |
| `tests/test_ephi_protection.py::TestThirdPartyIntegration::test_fhir_server_authentication` | passed | SRS-005 | - | - |
| `tests/test_ephi_protection.py::TestThirdPartyIntegration::test_api_key_not_in_code` | passed | SRS-005 | - | - |
| `tests/test_ephi_protection.py::TestThirdPartyIntegration::test_external_api_timeout` | passed | SRS-005 | - | - |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_patient_demographics_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_calculate_egfr_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_value_from_observation_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_precise_hbr_display_info_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_risk_category_info_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_calculate_bleeding_risk_percentage_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_score_from_table_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_bleeding_history_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_oral_anticoagulation_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_bleeding_diathesis_updated_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_active_cancer_updated_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_arc_hbr_factors_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_active_medications_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_check_medication_interactions_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_get_condition_text_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeDeprecationWarnings::test_convert_hr_to_probability_warns` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_get_patient_demographics_matches_twcore` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_get_precise_hbr_display_info_matches_classifier` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_calculate_egfr_matches_converter` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_get_score_from_table_matches_classifier` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_check_arc_hbr_factors_matches_checker` | passed | SRS-003 | - | SDS-003 |
| `tests/test_facade_deprecation.py::TestFacadeBackwardCompatibility::test_get_active_medications_matches_checker` | passed | SRS-003 | - | SDS-003 |
| `tests/test_fhir_service.py::TestPatientDemographics::test_get_patient_demographics_basic` | passed | SRS-004 | - | SDS-004 |
| `tests/test_fhir_service.py::TestPatientDemographics::test_get_patient_demographics_twcore` | passed | SRS-004 | - | SDS-004 |
| `tests/test_fhir_service.py::TestUnitConversion::test_calculate_egfr` | passed | SRS-003 | RISK-003 | - |
| `tests/test_fhir_service.py::TestUnitConversion::test_get_value_from_observation` | passed | SRS-003 | RISK-003 | - |
| `tests/test_fhir_service.py::TestConditionChecker::test_check_bleeding_diathesis` | passed | SRS-012 | RISK-001 | - |
| `tests/test_fhir_service.py::TestConditionChecker::test_check_active_cancer` | passed | SRS-012 | RISK-001 | - |
| `tests/test_fhir_service.py::TestConditionChecker::test_check_oral_anticoagulation` | passed | SRS-012 | RISK-001 | - |
| `tests/test_fhir_service.py::TestRiskCalculation::test_calculate_bleeding_risk_percentage` | passed | SRS-002 | RISK-001 | - |
| `tests/test_fhir_service.py::TestRiskCalculation::test_get_risk_category_info` | passed | SRS-002 | RISK-001 | - |
| `tests/test_fhir_service.py::TestRiskCalculation::test_get_precise_hbr_display_info` | passed | SRS-002 | RISK-001 | - |
| `tests/test_fhir_service.py::TestArcHbrFactors::test_check_arc_hbr_factors_basic` | passed | SRS-012 | - | - |
| `tests/test_fhir_service.py::TestArcHbrFactors::test_check_arc_hbr_factors_detailed` | passed | SRS-012 | - | - |
| `tests/test_fhir_service.py::TestMedicationFunctions::test_get_active_medications` | passed | SRS-012 | - | - |
| `tests/test_fhir_service.py::TestMedicationFunctions::test_check_medication_interactions` | passed | SRS-012 | - | - |
| `tests/test_fhir_service.py::TestHelperFunctions::test_get_score_from_table` | passed | SRS-001 | - | - |
| `tests/test_fhir_service.py::TestHelperFunctions::test_get_condition_text` | passed | SRS-001 | - | - |
| `tests/test_fhir_service.py::TestErrorHandling::test_invalid_patient_demographics` | passed | SRS-004 | RISK-004 | SDS-004 |
| `tests/test_fhir_service.py::TestErrorHandling::test_invalid_observation_value` | passed | SRS-004 | RISK-004 | SDS-004 |
| `tests/test_fhir_service.py::TestErrorHandling::test_egfr_with_invalid_inputs` | passed | SRS-004 | RISK-004 | SDS-004 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_aspirin_by_code` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_aspirin_by_name` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_dapt_combination` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_anticoagulant` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_empty_medications` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestMedicationChecking::test_check_malformed_medications` | passed | SRS-012 | - | SDS-008 |
| `tests/test_hooks.py::TestCardCreation::test_create_card_very_hbr` | passed | SRS-008 | - | SDS-008 |
| `tests/test_hooks.py::TestCardCreation::test_create_card_hbr` | passed | SRS-008 | - | SDS-008 |
| `tests/test_hooks.py::TestCardCreation::test_create_card_low_risk` | passed | SRS-008 | - | SDS-008 |
| `tests/test_hooks.py::TestCardCreation::test_card_contains_required_fields` | passed | SRS-008 | - | SDS-008 |
| `tests/test_hooks.py::TestCardCreation::test_card_medication_list_formatting` | passed | SRS-008 | - | SDS-008 |
| `tests/test_hooks.py::TestCDSServicesEndpoint::test_cds_services_discovery_success` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestCDSServicesEndpoint::test_cds_services_discovery_file_not_found` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestCDSServicesEndpoint::test_cds_services_discovery_invalid_json` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestCDSServicesEndpoint::test_cds_services_returns_json` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestPreciseHBRHook::test_hook_requires_post` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestPreciseHBRHook::test_hook_handles_missing_context` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestPreciseHBRHook::test_hook_handles_invalid_json` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestPreciseHBRHook::test_hook_returns_json` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestCORSConfiguration::test_cors_allows_options` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestCORSConfiguration::test_cors_headers_present` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestErrorHandling::test_handles_file_read_error` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestErrorHandling::test_handles_json_decode_error` | passed | SRS-008 | - | - |
| `tests/test_hooks.py::TestIntegration::test_full_hook_workflow` | passed | SRS-008 | - | - |
| `tests/test_input_validation.py::TestXSSPrevention::test_reflected_xss_in_parameters` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestXSSPrevention::test_stored_xss_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestXSSPrevention::test_dom_xss_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestSQLInjectionPrevention::test_sql_injection_in_search` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestSQLInjectionPrevention::test_parameterized_queries_used` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestCommandInjectionPrevention::test_shell_injection_in_parameters` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestCommandInjectionPrevention::test_no_shell_execution` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestPathTraversalPrevention::test_directory_traversal_in_parameters` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestPathTraversalPrevention::test_file_path_sanitization` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestXMLInjectionPrevention::test_xxe_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestXMLInjectionPrevention::test_xml_bomb_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestJSONInjectionPrevention::test_json_injection_in_api` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestJSONInjectionPrevention::test_json_prototype_pollution` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestHeaderInjection::test_crlf_injection_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestHeaderInjection::test_response_splitting_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestLDAPInjectionPrevention::test_ldap_injection_in_search` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestInputSizeValidation::test_maximum_request_size` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestInputSizeValidation::test_maximum_json_depth` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestInputSizeValidation::test_array_size_limit` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestDataTypeValidation::test_type_confusion_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestDataTypeValidation::test_null_byte_handling` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestEncodingValidation::test_utf8_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestEncodingValidation::test_unicode_normalization` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestBusinessLogicValidation::test_age_range_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestBusinessLogicValidation::test_lab_value_range_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestBusinessLogicValidation::test_date_format_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRateLimitingAndDoS::test_request_rate_limiting` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRateLimitingAndDoS::test_slowloris_protection` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRateLimitingAndDoS::test_large_payload_rejection` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRegexValidation::test_email_format_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRegexValidation::test_url_format_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestRegexValidation::test_patient_id_format_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestContentTypeValidation::test_json_content_type_required` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestContentTypeValidation::test_content_type_not_spoofed` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestContentTypeValidation::test_multipart_form_data_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestSpecialCharacterHandling::test_unicode_character_handling` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestSpecialCharacterHandling::test_control_character_filtering` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestSpecialCharacterHandling::test_newline_character_handling` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestWhitelistValidation::test_allowed_fhir_resources` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestWhitelistValidation::test_allowed_http_methods` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestOutputEncoding::test_html_output_encoded` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestOutputEncoding::test_json_output_encoded` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validation.py::TestOutputEncoding::test_api_output_encoded` | passed | SRS-006 | RISK-006 | - |
| `tests/test_input_validator_module.py::TestURLValidation::test_valid_https_urls` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_valid_http_urls` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_internal_ips` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_allow_localhost_when_enabled` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_invalid_schemes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_dangerous_characters` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_excessive_length` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_empty_or_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestURLValidation::test_reject_missing_hostname` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestPatientIDValidation::test_valid_patient_ids` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestPatientIDValidation::test_accept_uuid_format` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestPatientIDValidation::test_reject_special_characters` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestPatientIDValidation::test_reject_empty_or_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestPatientIDValidation::test_reject_excessive_length` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestResourceTypeValidation::test_valid_resource_types` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestResourceTypeValidation::test_reject_invalid_resource_types` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestResourceTypeValidation::test_case_sensitivity` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestJSONStructureValidation::test_valid_json_structures` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestJSONStructureValidation::test_validate_required_fields` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestJSONStructureValidation::test_reject_excessive_nesting` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestJSONStructureValidation::test_reject_non_dict` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestScopeValidation::test_valid_scopes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestScopeValidation::test_reject_invalid_scopes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestScopeValidation::test_reject_empty_or_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestCodeValidation::test_valid_authorization_codes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestCodeValidation::test_reject_invalid_codes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestCodeValidation::test_reject_empty_or_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStateValidation::test_valid_state_parameters` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStateValidation::test_reject_invalid_states` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStateValidation::test_reject_empty_or_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStringSanitization::test_sanitize_removes_control_characters` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStringSanitization::test_sanitize_truncates_length` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStringSanitization::test_sanitize_handles_none` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestStringSanitization::test_sanitize_preserves_valid_content` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSecurityPatterns::test_detect_path_traversal_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSecurityPatterns::test_detect_sql_injection_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSecurityPatterns::test_detect_xss_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSecurityPatterns::test_detect_command_injection_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestEdgeCases::test_unicode_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestEdgeCases::test_whitespace_in_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestEdgeCases::test_boundary_lengths` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestLOINCCodeValidation::test_valid_loinc_codes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestLOINCCodeValidation::test_reject_invalid_loinc_formats` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestLOINCCodeValidation::test_reject_loinc_injection` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestFHIRDateValidation::test_valid_fhir_dates` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestFHIRDateValidation::test_valid_fhir_date_prefixes` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestFHIRDateValidation::test_reject_invalid_date_formats` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamNameValidation::test_allowed_search_params` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamNameValidation::test_allowed_params_with_modifiers` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamNameValidation::test_reject_unknown_params` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamValueValidation::test_valid_search_values` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamValueValidation::test_reject_injection_attempts` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSearchParamValueValidation::test_reject_excessive_length` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestDetectInjectionPatterns::test_detects_sql_injection` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestDetectInjectionPatterns::test_detects_template_injection` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestDetectInjectionPatterns::test_detects_path_traversal` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestDetectInjectionPatterns::test_clean_values_pass` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_valid_search_params_dict` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_empty_params_valid` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_reject_too_many_params` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_reject_injection_in_params` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_validates_date_params` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestValidateFHIRSearchParams::test_validates_patient_id` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSanitizeFHIRSearchValue::test_preserves_valid_fhir_syntax` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSanitizeFHIRSearchValue::test_removes_dangerous_chars` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSanitizeFHIRSearchValue::test_truncates_long_values` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_input_validator_module.py::TestSanitizeFHIRSearchValue::test_handles_empty_input` | passed | SRS-006 | RISK-006 | SDS-006 |
| `tests/test_mfa_validator.py::TestMFAMethodsConstants::test_mfa_methods_contains_standard_methods` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestMFAMethodsConstants::test_password_methods_defined` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestMFAMethodsConstants::test_mfa_and_password_methods_are_disjoint` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_has_mfa_true_for_mfa_method` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_has_mfa_true_for_otp` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_has_mfa_true_for_hardware_key` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_has_mfa_false_for_password_only` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_unknown_status_for_empty_methods` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_returns_all_mfa_methods_used` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestCheckMFAStatus::test_preserves_all_auth_methods` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestIsMFAAuthenticated::test_returns_true_when_mfa_in_session` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestIsMFAAuthenticated::test_returns_false_when_no_mfa_in_session` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestIsMFAAuthenticated::test_returns_false_when_no_session` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestRequireMFADecorator::test_allows_access_with_mfa` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestRequireMFADecorator::test_denies_access_without_mfa` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestRequireMFADecorator::test_denies_access_with_unknown_status` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestRequireMFADecorator::test_logs_mfa_access_on_success` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestRequireMFADecorator::test_logs_mfa_access_on_denial` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestGetMFASummary::test_returns_mfa_verified_status` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestGetMFASummary::test_returns_password_only_status` | passed | SRS-005 | - | - |
| `tests/test_mfa_validator.py::TestGetMFASummary::test_returns_unknown_status` | passed | SRS-005 | - | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorAlgorithms::test_rejects_none_algorithm` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorAlgorithms::test_rejects_hs256_algorithm` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorAlgorithms::test_allowed_algorithms_are_asymmetric` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorClaimsValidation::test_missing_token_raises_error` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorClaimsValidation::test_invalid_token_format_raises_error` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorJWKSDiscovery::test_discovers_jwks_from_oidc_config` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestOIDCValidatorJWKSDiscovery::test_falls_back_to_smart_config` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestValidateIdTokenSafe::test_returns_none_for_empty_token` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestValidateIdTokenSafe::test_returns_none_for_none_token` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestValidateIdTokenSafe::test_returns_error_for_invalid_token` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestFhirUserExtraction::test_extracts_fhir_user_from_claims` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestFhirUserExtraction::test_returns_none_when_fhir_user_missing` | passed | SRS-005 | RISK-005 | - |
| `tests/test_oidc_validator.py::TestFhirUserExtraction::test_get_user_identity` | passed | SRS-005 | RISK-005 | - |
| `tests/test_patient_context.py::TestGetAuthorizedPatientId::test_returns_patient_id_from_session` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestGetAuthorizedPatientId::test_falls_back_to_fhir_data` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestGetAuthorizedPatientId::test_returns_none_when_not_set` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestValidatePatientContext::test_valid_context_passes` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestValidatePatientContext::test_mismatched_context_fails` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestValidatePatientContext::test_missing_patient_id_fails` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestValidatePatientContext::test_no_authorized_patient_fails` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestValidatePatientContext::test_whitespace_normalization` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestRequirePatientContextDecorator::test_passes_with_valid_context` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestRequirePatientContextDecorator::test_rejects_invalid_context` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestRequirePatientContextDecorator::test_rejects_request_without_patient_id` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestVerifyPatientAccess::test_passes_with_valid_access` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_patient_context.py::TestVerifyPatientAccess::test_raises_on_invalid_access` | passed | SRS-006 | RISK-009 | SDS-006 |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_oversized_payload` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_deeply_nested_json` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_xss_in_patient_name` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_null_bytes_in_context` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_sql_injection_in_patient_id` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_invalid_content_type` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_empty_body` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksPayloadInjection::test_malformed_prefetch_structure` | passed | SRS-008 | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksCORS::test_cors_allows_all_origins` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksCORS::test_cors_no_credentials` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestCDSHooksCORS::test_non_hooks_endpoint_no_cors` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSessionSecurity::test_session_not_in_url` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestSessionSecurity::test_session_cookie_flags` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestSessionSecurity::test_unauthenticated_access_to_main` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestSessionSecurity::test_unauthenticated_api_access` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestSessionSecurity::test_session_data_tampering` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestBOLAAttacks::test_bola_patient_id_mismatch` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestBOLAAttacks::test_bola_empty_patient_id` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestBOLAAttacks::test_bola_null_patient_id` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestBOLAAttacks::test_bola_tradeoff_endpoint` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestAuthBypass::test_exchange_without_state` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestAuthBypass::test_exchange_with_wrong_state` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestAuthBypass::test_exchange_with_expired_pkce` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestAuthBypass::test_refresh_without_session` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestAuthBypass::test_refresh_rate_limiting` | passed | SRS-005 | RISK-005 | - |
| `tests/test_penetration.py::TestInjectionAttacks::test_xss_in_iss_parameter` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestInjectionAttacks::test_ssti_in_complaint_form` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestInjectionAttacks::test_crlf_injection_in_headers` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestInjectionAttacks::test_host_header_injection` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestInjectionAttacks::test_path_traversal_in_complaints` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestSSRFPrevention::test_ssrf_private_ip_in_iss` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestSSRFPrevention::test_ssrf_private_ip_127` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestSSRFPrevention::test_ssrf_cloud_metadata` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestSSRFPrevention::test_ssrf_dns_rebinding` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestSSRFPrevention::test_ssrf_redirect_in_token_url` | passed | SRS-006 | RISK-006 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_error_page_no_stack_trace` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_api_error_no_internal_details` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_token_not_in_response` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_health_endpoint_no_secrets` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_scoring_config_no_secrets` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestInformationDisclosure::test_token_exchange_error_no_leak` | passed | SRS-010 | RISK-008 | - |
| `tests/test_penetration.py::TestHTTPMethodTampering::test_get_on_post_only_endpoints` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestHTTPMethodTampering::test_put_on_api_endpoints` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestPatientIDValidation::test_special_characters_rejected` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestPatientIDValidation::test_extremely_long_patient_id` | passed | SRS-006 | RISK-009 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_csp_header` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_hsts_header` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_x_frame_options` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_x_content_type_options` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_cache_control_on_api` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_referrer_policy` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestSecurityHeaders::test_permissions_policy` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestTradeoffEndpointSecurity::test_tradeoff_requires_auth` | passed | SRS-007 | RISK-007 | - |
| `tests/test_penetration.py::TestTradeoffEndpointSecurity::test_tradeoff_page_requires_auth` | passed | SRS-007 | RISK-007 | - |
| `tests/test_penetration.py::TestTradeoffEndpointSecurity::test_tradeoff_malicious_factors` | passed | SRS-007 | RISK-007 | - |
| `tests/test_penetration.py::TestComplaintFormSecurity::test_captcha_bypass_attempt` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestComplaintFormSecurity::test_captcha_replay_attack` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestComplaintFormSecurity::test_xss_in_complaint_fields` | passed | - | RISK-006 | - |
| `tests/test_penetration.py::TestLogoutSecurity::test_logout_clears_session` | passed | - | RISK-005 | - |
| `tests/test_penetration.py::TestLogoutSecurity::test_post_logout_session_invalid` | passed | - | RISK-005 | - |
| `tests/test_penetration.py::TestTokenExchangeInfoLeak::test_error_response_text_leaked` | passed | - | RISK-008 | - |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_low_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_moderate_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_high_risk` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_23` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_boundary_score_27` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_zero_score` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskClassification::test_classify_very_high_score` | passed | SRS-002 | RISK-001 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_low_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_moderate_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_high_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_zero_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskPercentage::test_bleeding_risk_returns_valid_format` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_low_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_moderate_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestColorCoding::test_color_for_high_risk` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_includes_percentage` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_includes_score_range` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskCategoryInfo::test_category_info_consistency` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestEdgeCases::test_negative_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_very_large_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_float_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestEdgeCases::test_string_score` | passed | SRS-002 | RISK-001 | - |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_22_not_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_23_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_26_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestRiskThresholds::test_threshold_27_very_high_hbr` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_increases_with_score` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestBleedingRiskFormula::test_bleeding_risk_reasonable_range` | passed | SRS-002 | RISK-002 | SDS-002 |
| `tests/test_risk_classifier.py::TestSingletonPattern::test_singleton_instance` | passed | SRS-002 | - | - |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_classify_risk_returns_dict` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_classify_risk_has_required_keys` | passed | SRS-002 | - | SDS-002 |
| `tests/test_risk_classifier.py::TestReturnValueStructure::test_bleeding_risk_percentage_type` | passed | SRS-002 | - | SDS-002 |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_unauthorized_access_blocked` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_patient_data_access_control` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_api_endpoint_authentication` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_session_cookie_secure_flag` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_session_cookie_httponly` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_secret_key_configured` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_sql_injection_in_parameters` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_command_injection_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_ldap_injection_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_rate_limiting_exists` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_session_timeout_configured` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_debug_mode_disabled_in_production` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_error_messages_not_verbose` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_security_headers_present` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_dependencies_not_vulnerable` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_no_default_credentials` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_session_regeneration_after_login` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_password_not_in_url` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_no_unsigned_data_accepted` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_audit_logging_enabled` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_failed_login_attempts_logged` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestOWASPTop10::test_ssrf_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_ephi_access_logging` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_unique_user_identification` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_automatic_logoff` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_encryption_in_transit` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_audit_log_retention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestHIPAACompliance::test_emergency_access_procedure` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAuthenticationSecurity::test_oauth_state_parameter` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAuthenticationSecurity::test_oauth_code_verifier` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAuthenticationSecurity::test_token_not_in_logs` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAuthenticationSecurity::test_session_fixation_prevention` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestInputValidation::test_patient_id_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestInputValidation::test_json_input_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestInputValidation::test_content_type_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestInputValidation::test_file_upload_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestInputValidation::test_url_parameter_length_limit` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestDataProtection::test_sensitive_data_not_in_response` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestDataProtection::test_error_messages_sanitized` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestDataProtection::test_cors_configuration` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestDataProtection::test_patient_data_isolation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestCryptography::test_jwt_signature_validation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestCryptography::test_secure_random_generation` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAPISecurityTest::test_api_versioning` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAPISecurityTest::test_api_rate_limiting` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAPISecurityTest::test_api_authentication_required` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestAPISecurityTest::test_api_accepts_only_json` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestSecurityConfiguration::test_environment_variables_loaded` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestSecurityConfiguration::test_secure_defaults` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_comprehensive.py::TestSecurityConfiguration::test_production_config_different_from_dev` | passed | SRS-006 | RISK-006 | - |
| `tests/test_security_labels.py::TestExtractSecurityLabels::test_extracts_labels_from_meta_security` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestExtractSecurityLabels::test_returns_empty_list_for_no_labels` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestExtractSecurityLabels::test_handles_none_resource` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestConfidentialityLevel::test_from_code_returns_correct_level` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestConfidentialityLevel::test_from_code_returns_none_for_invalid` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestConfidentialityLevel::test_requires_elevated_access` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestGetConfidentialityLevel::test_gets_level_from_labels` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestGetConfidentialityLevel::test_returns_highest_level` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestGetConfidentialityLevel::test_returns_none_for_no_confidentiality` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestAnalyzeResourceSecurity::test_detects_restricted_resource` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestAnalyzeResourceSecurity::test_detects_very_restricted_resource` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestAnalyzeResourceSecurity::test_normal_resource_no_restrictions` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestFilterRestrictedFields::test_masks_fields_for_very_restricted` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestFilterRestrictedFields::test_no_filtering_for_normal` | passed | SRS-006 | - | - |
| `tests/test_security_labels.py::TestGetSecuritySummary::test_summarizes_multiple_resources` | passed | SRS-006 | - | - |
| `tests/test_smart_security.py::TestSMARTLaunchSecurity::test_launch_requires_iss_parameter` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSMARTLaunchSecurity::test_launch_validates_iss_format` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSMARTLaunchSecurity::test_launch_parameter_sanitization` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestOAuthSecurity::test_state_parameter_generated` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestOAuthSecurity::test_state_parameter_validated` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestOAuthSecurity::test_pkce_code_challenge` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestOAuthSecurity::test_pkce_code_verifier_stored_securely` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestOAuthSecurity::test_authorization_code_single_use` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestTokenSecurity::test_token_not_in_url` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestTokenSecurity::test_token_stored_securely` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestTokenSecurity::test_token_expiration_checked` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestTokenSecurity::test_refresh_token_security` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopeSecurity::test_scope_validation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopeSecurity::test_scope_enforcement` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopeSecurity::test_minimal_scope_principle` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestFHIRServerSecurity::test_fhir_server_url_validation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestFHIRServerSecurity::test_fhir_server_certificate_validation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestFHIRServerSecurity::test_fhir_response_validation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSessionSecurity::test_session_id_regeneration` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSessionSecurity::test_session_timeout` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSessionSecurity::test_session_cookie_attributes` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSessionSecurity::test_concurrent_session_handling` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestCSRFProtection::test_csrf_token_in_forms` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestCSRFProtection::test_csrf_validation_on_post` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestCSRFProtection::test_csrf_token_uniqueness` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestHeadersSecurity::test_x_content_type_options` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestHeadersSecurity::test_x_frame_options` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestHeadersSecurity::test_content_security_policy` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestHeadersSecurity::test_strict_transport_security` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestHeadersSecurity::test_x_xss_protection` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestLoggingSecurity::test_sensitive_data_redacted_in_logs` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestLoggingSecurity::test_audit_log_integrity` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestLoggingSecurity::test_log_rotation_configured` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataSanitization::test_html_escaping` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataSanitization::test_json_encoding` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataSanitization::test_url_encoding` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestErrorHandlingSecurity::test_generic_error_messages` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestErrorHandlingSecurity::test_no_stack_traces_in_production` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestErrorHandlingSecurity::test_error_logging_without_sensitive_data` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPKCESecurity::test_code_verifier_generation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPKCESecurity::test_code_challenge_generation` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPKCESecurity::test_code_challenge_method_s256` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopesSecurity::test_patient_scopes_only` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopesSecurity::test_read_only_scopes` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestScopesSecurity::test_minimal_scopes_requested` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestAuditTrailSecurity::test_all_ephi_access_logged` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestAuditTrailSecurity::test_authentication_attempts_logged` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestAuditTrailSecurity::test_audit_log_immutability` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestAuditTrailSecurity::test_audit_log_includes_required_fields` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataEncryption::test_sensitive_config_encrypted` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataEncryption::test_patient_data_not_in_logs` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestDataEncryption::test_phi_encryption_at_rest` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestComplianceRequirements::test_user_access_logging` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestComplianceRequirements::test_data_export_capability` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestComplianceRequirements::test_complaint_process_exists` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestComplianceRequirements::test_privacy_policy_accessible` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSecurityBestPractices::test_no_sensitive_data_in_git` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSecurityBestPractices::test_dependencies_pinned` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSecurityBestPractices::test_no_hardcoded_secrets` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestSecurityBestPractices::test_secure_random_for_tokens` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPenetrationTestScenarios::test_directory_traversal` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPenetrationTestScenarios::test_http_verb_tampering` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPenetrationTestScenarios::test_parameter_pollution` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPenetrationTestScenarios::test_null_byte_injection` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_smart_security.py::TestPenetrationTestScenarios::test_unicode_bypass_attempts` | passed | SRS-005 | RISK-005 | SDS-005 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_normal_values_no_warnings` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_hb_above_max_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_hb_below_min_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_egfr_above_max_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_egfr_below_min_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_wbc_above_max_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_age_above_max_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_multiple_truncations_all_warned` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_boundary_values_no_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestTruncationWarnings::test_boundary_min_values_no_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestComponentDisplayTruncation::test_hb_truncated_shows_capped` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestComponentDisplayTruncation::test_egfr_truncated_shows_capped` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestComponentDisplayTruncation::test_wbc_truncated_shows_capped` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestComponentDisplayTruncation::test_age_truncated_shows_capped` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestComponentDisplayTruncation::test_normal_hb_no_capped_label` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_truncation_warnings.py::TestWarningMessageContent::test_warning_includes_raw_and_effective` | passed | SRS-001 | RISK-001 | - |
| `tests/test_truncation_warnings.py::TestWarningMessageContent::test_warning_includes_expected_range` | passed | SRS-001 | RISK-001 | - |
| `tests/test_truncation_warnings.py::TestWarningMessageContent::test_warning_suggests_verification` | passed | SRS-001 | RISK-001 | - |
| `tests/test_truncation_warnings.py::TestWarningMessageContent::test_warning_severity_is_high` | passed | SRS-001 | RISK-001 | - |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_contains_chinese` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_demographics_empty` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_icd10_diagnosis` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_medical_record_number` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_nhi_medication_code_pattern` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_nhi_medication_code_standard` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_nhi_medication_reference` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_patient_demographics_basic` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_patient_demographics_chinese_name` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_patient_demographics_english_name` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_patient_demographics_invalid_date` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_patient_demographics_mixed_names` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_resident_id` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_extract_taiwan_id` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_get_twcore_compatible_patient_resource` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_search_conditions_by_icd10` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_search_nhi_medication_by_code` | passed | SRS-009 | - | SDS-009 |
| `tests/test_twcore_adapter.py::TestTWCoreAdapter::test_validate_taiwan_id` | passed | SRS-009 | - | SDS-009 |
| `tests/test_unit_conversion_service.py::TestGetValueFromObservation::test_returns_none_for_none_input` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestGetValueFromObservation::test_returns_none_for_non_dict_input` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestGetValueFromObservation::test_returns_none_for_missing_value_quantity` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestGetValueFromObservation::test_returns_none_for_null_value` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestGetValueFromObservation::test_returns_none_for_non_numeric_value` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestHemoglobinConversion::test_direct_match_g_dl` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestHemoglobinConversion::test_case_insensitive_match` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestHemoglobinConversion::test_convert_g_l_to_g_dl` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestHemoglobinConversion::test_convert_mmol_l_to_g_dl` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestHemoglobinConversion::test_returns_none_for_unknown_unit` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCreatinineConversion::test_direct_match_mg_dl` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCreatinineConversion::test_convert_umol_l_to_mg_dl` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestWBCConversion::test_direct_match` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestWBCConversion::test_convert_k_ul` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestWBCConversion::test_convert_cells_per_ul` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRConversion::test_standard_format` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRConversion::test_cerner_format` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCalculateEGFR::test_healthy_male` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCalculateEGFR::test_healthy_female` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCalculateEGFR::test_elderly_patient` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCalculateEGFR::test_elevated_creatinine` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestCalculateEGFR::test_returns_integer` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_none_creatinine` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_none_age` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_none_gender` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_invalid_gender` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_negative_creatinine` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_creatinine_below_minimum` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_creatinine_above_maximum` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_age_below_adult` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestEGFRValidation::test_age_above_maximum` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestValidateEGFRInputs::test_valid_inputs` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_conversion_service.py::TestValidateEGFRInputs::test_boundary_values` | passed | SRS-003 | RISK-003 | SDS-003 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_ok_status_direct_match` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_ok_status_after_conversion` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_unknown_unit_status` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_missing_unit_status` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_empty_string_unit_is_missing` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_whitespace_only_unit_is_missing` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_no_data_status_none_obs` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_no_data_status_empty_dict` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_no_value_status` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_backward_compat_get_value_from_observation` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestGetValueWithStatus::test_backward_compat_get_value_from_observation_ok` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_unknown_hb_unit_tracked` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_missing_hb_unit_tracked` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_no_fhir_data_no_unit_issue` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_unknown_wbc_unit_tracked` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_unknown_egfr_unit_tracked` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitIssueTracking::test_multiple_unknown_units_all_tracked` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_unknown_unit_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_missing_unit_generates_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_no_fhir_data_no_unit_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_known_unit_no_unit_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_warning_message_includes_expected_unit` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_warning_message_includes_verify` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_hb_component_shows_not_available` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitWarningGeneration::test_unknown_unit_does_not_affect_score` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitEdgeCases::test_case_insensitive_unit_match` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitEdgeCases::test_unit_with_extra_whitespace` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitEdgeCases::test_none_unit_field` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitEdgeCases::test_creatinine_unknown_unit_egfr_fallback_fails` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/test_unit_failsafe.py::TestUnitEdgeCases::test_egfr_unknown_but_creatinine_ok_no_warning` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case0]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case1]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case2]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case3]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case4]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case5]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case6]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case7]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case8]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case9]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case10]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case11]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case12]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case13]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case14]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case15]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case16]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case17]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case18]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_golden_dataset_verification[case19]` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_precise_hbr.py::test_boundary_values` | passed | SRS-001 | RISK-001 | SDS-001 |
| `tests/verify_tradeoff.py::TestTradeoffModelSafety::test_high_risk_patient` | passed | SRS-007 | RISK-007 | SDS-007 |
| `tests/verify_tradeoff.py::TestTradeoffModelSafety::test_missing_data_behavior` | passed | SRS-007 | RISK-007 | SDS-007 |

## Untraced Tests (Missing Regulatory Markers)

The following tests lack `@pytest.mark.requirement`, `@pytest.mark.risk`, or `@pytest.mark.design` markers and cannot be traced to requirements.

- `tests/test_app_basic.py::test_app_exists`
- `tests/test_app_basic.py::test_app_is_testing`
- `tests/test_app_basic.py::test_health_endpoint`
- `tests/test_app_basic.py::test_index_redirect`
- `tests/test_app_basic.py::test_static_files_accessible`
- `tests/test_app_e2e.py::TestHealthEndpoint::test_health_returns_200`
- `tests/test_app_e2e.py::TestHealthEndpoint::test_health_returns_json`
- `tests/test_app_e2e.py::TestHealthEndpoint::test_health_contains_status`
- `tests/test_app_e2e.py::TestHealthEndpoint::test_health_contains_timestamp`
- `tests/test_app_e2e.py::TestHealthEndpoint::test_health_contains_service_info`
- `tests/test_app_e2e.py::TestIndexPage::test_index_returns_200_or_redirect`
- `tests/test_app_e2e.py::TestIndexPage::test_index_is_html_or_redirect`
- `tests/test_app_e2e.py::TestStandalonePage::test_standalone_returns_200_or_302`
- `tests/test_app_e2e.py::TestStandalonePage::test_standalone_is_html_or_redirect`
- `tests/test_app_e2e.py::TestLaunchEndpoint::test_launch_without_iss_returns_error`
- `tests/test_app_e2e.py::TestLaunchEndpoint::test_launch_with_valid_iss_redirects`
- `tests/test_app_e2e.py::TestLaunchEndpoint::test_launch_validates_iss_url`
- `tests/test_app_e2e.py::TestCallbackEndpoint::test_callback_without_code_returns_error`
- `tests/test_app_e2e.py::TestCallbackEndpoint::test_callback_with_error_shows_error`
- `tests/test_app_e2e.py::TestCallbackEndpoint::test_callback_with_code_returns_page`
- `tests/test_app_e2e.py::TestCalculateRiskAPI::test_calculate_risk_requires_auth`
- `tests/test_app_e2e.py::TestCalculateRiskAPI::test_calculate_risk_requires_patient_id`
- `tests/test_app_e2e.py::TestCalculateRiskAPI::test_calculate_risk_validates_patient_id`
- `tests/test_app_e2e.py::TestCalculateRiskAPI::test_calculate_risk_with_valid_data`
- `tests/test_app_e2e.py::TestExchangeCodeAPI::test_exchange_code_requires_code`
- `tests/test_app_e2e.py::TestExchangeCodeAPI::test_exchange_code_requires_launch_context`
- `tests/test_app_e2e.py::TestExchangeCodeAPI::test_exchange_code_with_valid_context`
- `tests/test_app_e2e.py::TestMainPage::test_main_requires_auth`
- `tests/test_app_e2e.py::TestMainPage::test_main_with_auth_returns_200`
- `tests/test_app_e2e.py::TestLogout::test_logout_clears_session`
- `tests/test_app_e2e.py::TestErrorHandling::test_404_error`
- `tests/test_app_e2e.py::TestErrorHandling::test_method_not_allowed`
- `tests/test_app_e2e.py::TestErrorHandling::test_invalid_json_in_api`
- `tests/test_app_e2e.py::TestSecurityHeaders::test_content_type_header`
- `tests/test_app_e2e.py::TestSecurityHeaders::test_no_server_header_leak`
- `tests/test_app_e2e.py::TestSessionManagement::test_session_is_created`
- `tests/test_app_e2e.py::TestSessionManagement::test_session_persists`
- `tests/test_app_e2e.py::TestInputValidation::test_xss_in_launch_iss`
- `tests/test_app_e2e.py::TestInputValidation::test_sql_injection_in_patient_id`
- `tests/test_app_e2e.py::TestInputValidation::test_path_traversal_in_patient_id`
- `tests/test_app_e2e.py::TestCORSConfiguration::test_cors_preflight_cds_services`
- `tests/test_app_e2e.py::TestCORSConfiguration::test_cors_headers_present`
- `tests/test_app_e2e.py::TestTradeoffAnalysis::test_tradeoff_analysis_page`
- `tests/test_app_e2e.py::TestAuditLogging::test_api_calls_are_logged`
- `tests/test_app_e2e.py::TestStaticFiles::test_static_directory_accessible`
- `tests/test_app_e2e.py::TestStaticFiles::test_favicon_served`
- `tests/test_app_e2e.py::TestContentNegotiation::test_json_accept_header`
- `tests/test_app_e2e.py::TestContentNegotiation::test_api_returns_json`
- `tests/test_app_e2e.py::TestRateLimiting::test_many_requests_succeed`
- `tests/test_app_e2e.py::TestEdgeCases::test_empty_json_body`
- `tests/test_app_e2e.py::TestEdgeCases::test_null_json_values`
- `tests/test_app_e2e.py::TestEdgeCases::test_very_long_patient_id`
- `tests/test_app_e2e.py::TestEdgeCases::test_unicode_in_patient_id`
- `tests/test_config.py::TestConfigBasics::test_config_class_exists`
- `tests/test_config.py::TestConfigBasics::test_session_type_configured`
- `tests/test_config.py::TestConfigBasics::test_session_permanent_disabled`
- `tests/test_config.py::TestConfigBasics::test_scopes_defined`
- `tests/test_config.py::TestEnvironmentVariables::test_secret_key_from_environment`
- `tests/test_config.py::TestEnvironmentVariables::test_client_id_from_environment`
- `tests/test_config.py::TestEnvironmentVariables::test_redirect_uri_from_environment`
- `tests/test_config.py::TestEnvironmentVariables::test_missing_environment_variables`
- `tests/test_config.py::TestSessionDirectory::test_session_directory_local_environment`
- `tests/test_config.py::TestSessionDirectory::test_session_directory_gae_environment`
- `tests/test_config.py::TestSessionDirectory::test_session_directory_path_is_string`
- `tests/test_config.py::TestInitApp::test_init_app_with_valid_config`
- `tests/test_config.py::TestInitApp::test_init_app_validates_secret_key`
- `tests/test_config.py::TestInitApp::test_init_app_validates_client_id`
- `tests/test_config.py::TestInitApp::test_init_app_validates_redirect_uri`
- `tests/test_config.py::TestInitApp::test_init_app_cleans_redirect_uri_hash`
- `tests/test_config.py::TestInitApp::test_init_app_creates_session_directory`
- `tests/test_config.py::TestInitApp::test_init_app_sets_secure_permissions`
- `tests/test_config.py::TestInitApp::test_init_app_handles_existing_directory`
- `tests/test_config.py::TestInitApp::test_init_app_handles_permission_error`
- `tests/test_config.py::TestSecuritySettings::test_secret_key_not_hardcoded`
- `tests/test_config.py::TestSecuritySettings::test_session_type_is_filesystem`
- `tests/test_config.py::TestSecuritySettings::test_session_cookie_httponly`
- `tests/test_config.py::TestSecuritySettings::test_session_not_permanent`
- `tests/test_config.py::TestSecuritySettings::test_redirect_uri_uses_https`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_launch`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_patient_read`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_observation_read`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_condition_read`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_medication_read`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_openid`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_include_online_access`
- `tests/test_config.py::TestScopesConfiguration::test_scopes_format`
- `tests/test_config.py::TestConfigImmutability::test_config_is_class_not_instance`
- `tests/test_config.py::TestConfigImmutability::test_init_app_is_static_method`
- `tests/test_config.py::TestEdgeCases::test_redirect_uri_with_multiple_hashes`
- `tests/test_config.py::TestEdgeCases::test_redirect_uri_with_whitespace`
- `tests/test_config.py::TestEdgeCases::test_empty_environment_variables`
- `tests/test_performance.py::TestResponseTimePerformance::test_health_endpoint_response_time`
- `tests/test_performance.py::TestResponseTimePerformance::test_cds_services_response_time`
- `tests/test_performance.py::TestResponseTimePerformance::test_static_file_response_time`
- `tests/test_performance.py::TestThroughputPerformance::test_health_endpoint_throughput`
- `tests/test_performance.py::TestThroughputPerformance::test_cds_services_throughput`
- `tests/test_performance.py::TestComputationPerformance::test_egfr_calculation_performance`
- `tests/test_performance.py::TestComputationPerformance::test_hash_calculation_performance`
- `tests/test_performance.py::TestComputationPerformance::test_input_validation_performance`
- `tests/test_performance.py::TestMemoryPerformance::test_no_memory_leak_on_repeated_requests`
- `tests/test_performance.py::TestMemoryPerformance::test_large_json_handling`
- `tests/test_performance.py::TestConcurrencyPerformance::test_concurrent_health_checks`
- `tests/test_performance.py::TestDatabasePerformance::test_audit_log_write_performance`
- `tests/test_performance.py::TestDatabasePerformance::test_config_loading_performance`
- `tests/test_performance.py::TestStartupPerformance::test_app_import_time`
- `tests/test_performance.py::TestStartupPerformance::test_first_request_time`
- `tests/test_performance.py::TestPerformanceBenchmarks::test_benchmark_health_endpoint`