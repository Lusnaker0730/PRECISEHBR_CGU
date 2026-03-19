// PRECISE-HBR Main Application JavaScript
// Extracted from main.html for better maintainability

// ==========================================================================
// PRECISE-HBR Risk Calculator - Main Application Module
// Wrapped in IIFE to avoid global scope pollution
// ==========================================================================
(function () {
    'use strict';

    // Module-scoped variables
    let currentFeedbackType = null;
    let currentPatientData = null;
    let scoreComponentData = [];
    let unitSettings = {
        hemoglobin: 'g/dL',  // or 'mmol/L'
    };

    // Dynamic scoring configuration loaded from backend API
    // This eliminates hardcoded coefficients and ensures frontend/backend consistency
    let scoringConfig = null;

    // Module-scoped data warnings (previously on window object for security)
    let dataWarnings = [];
    let initialMissingCriticalData = [];

    // Session state key for preserving clinician input across re-launches
    const FORM_STATE_KEY = 'precise_hbr_form_state';

    /**
     * Save all editable form inputs to sessionStorage.
     * Called before showing session-expired UI to preserve clinician work.
     */
    function saveFormState() {
        try {
            const state = {};
            document.querySelectorAll('#results-container input').forEach(function (input) {
                if (!input.id) return;
                if (input.type === 'checkbox') {
                    state[input.id] = { type: 'checkbox', checked: input.checked };
                } else if (input.type === 'number' || input.type === 'text') {
                    if (input.value) {
                        state[input.id] = { type: input.type, value: input.value };
                    }
                }
            });
            if (Object.keys(state).length > 0) {
                sessionStorage.setItem(FORM_STATE_KEY, JSON.stringify(state));
            }
        } catch (e) {
            // sessionStorage may be unavailable in some contexts
            console.warn('Could not save form state:', e.message);
        }
    }

    /**
     * Restore form inputs from sessionStorage after re-launch.
     * Only restores values that differ from server defaults (user overrides).
     */
    function restoreFormState() {
        try {
            const raw = sessionStorage.getItem(FORM_STATE_KEY);
            if (!raw) return;
            const state = JSON.parse(raw);
            let restored = 0;
            Object.keys(state).forEach(function (id) {
                const el = document.getElementById(id);
                if (!el) return;
                const saved = state[id];
                if (saved.type === 'checkbox') {
                    el.checked = saved.checked;
                    restored++;
                } else if (saved.value) {
                    el.value = saved.value;
                    restored++;
                }
            });
            if (restored > 0) {
                console.info(`Restored ${restored} form field(s) from previous session`);
                // Clear after successful restore
                sessionStorage.removeItem(FORM_STATE_KEY);
            }
        } catch (e) {
            console.warn('Could not restore form state:', e.message);
        }
    }

    /**
     * Fetch scoring configuration from backend API.
     * Must be called before any score calculations.
     * Falls back to default values if API fails.
     */
    async function fetchScoringConfig() {
        try {
            const response = await fetch('/api/config/scoring');
            if (!response.ok) {
                console.error('Failed to load scoring config:', response.status);
                scoringConfig = getDefaultScoringConfig();
                console.warn('Using fallback scoring config');
                return scoringConfig;
            }
            const configData = await response.json();

            // Validate response structure before using
            if (!validateScoringConfigResponse(configData)) {
                console.warn('Scoring config validation failed, using fallback');
                scoringConfig = getDefaultScoringConfig();
                return scoringConfig;
            }

            scoringConfig = configData;
            console.log('Scoring config loaded and validated');
            updateTooltipsWithConfig();
            return scoringConfig;
        } catch (error) {
            console.error('Error fetching scoring config:', error);
            scoringConfig = getDefaultScoringConfig();
            console.warn('Using fallback scoring config due to error');
            return scoringConfig;
        }
    }

    /**
     * Returns default scoring configuration as fallback when API is unavailable.
     */
    function getDefaultScoringConfig() {
        return {
            base_score: 2,
            coefficients: {
                age: { threshold: 30, coefficient: 0.25, truncation_min: 30, truncation_max: 80 },
                hemoglobin: { threshold: 15.0, coefficient: 2.5, truncation_min: 5.0, truncation_max: 15.0 },
                egfr: { threshold: 100, coefficient: 0.055, truncation_min: 5, truncation_max: 100 },
                wbc: { threshold: 3.0, coefficient: 0.8, truncation_min: 3.0, truncation_max: 15.0 }
            },
            binary_scores: {
                prior_bleeding: 7,
                oral_anticoagulation: 5,
                arc_hbr: 3
            }
        };
    }

    /**
     * Update clinical tooltips with dynamic coefficient values from config.
     */
    function updateTooltipsWithConfig() {
        if (!scoringConfig) return;

        const c = scoringConfig.coefficients;

        if (clinicalTooltips['Age']) {
            clinicalTooltips['Age'].riskFactors =
                `Score Weight: +${c.age.coefficient} points per year increase<br>` +
                `Example: 65 years = (65-${c.age.threshold})  ${c.age.coefficient} = ${((65 - c.age.threshold) * c.age.coefficient).toFixed(2)} points`;
            clinicalTooltips['Age'].normalRange =
                `Calculation Range: ${c.age.truncation_min}-${c.age.truncation_max} years`;
        }
        if (clinicalTooltips['Hemoglobin']) {
            clinicalTooltips['Hemoglobin'].riskFactors =
                `Score Weight: +${c.hemoglobin.coefficient} points per 1 g/dL decrease<br>` +
                `Example: 12 g/dL = (${c.hemoglobin.threshold}-12)  ${c.hemoglobin.coefficient} = ${((c.hemoglobin.threshold - 12) * c.hemoglobin.coefficient).toFixed(1)} points`;
            clinicalTooltips['Hemoglobin'].normalRange =
                `Calculation Range: ${c.hemoglobin.truncation_min}-${c.hemoglobin.truncation_max} g/dL`;
        }
        if (clinicalTooltips['eGFR']) {
            clinicalTooltips['eGFR'].riskFactors =
                `Score Weight: +${c.egfr.coefficient} points per 1 mL/min decrease<br>` +
                `Example: 60 mL/min = (${c.egfr.threshold}-60)  ${c.egfr.coefficient} = ${((c.egfr.threshold - 60) * c.egfr.coefficient).toFixed(1)} points`;
        }
        if (clinicalTooltips['White Blood Cell Count']) {
            clinicalTooltips['White Blood Cell Count'].riskFactors =
                `Score Weight: +${c.wbc.coefficient} points per 1 \u00d710\u00b3/\u00b5L increase<br>` +
                `Example: 10 \u00d710\u00b3/\u00b5L = (10-${c.wbc.threshold}) \u00d7 ${c.wbc.coefficient} = ${((10 - c.wbc.threshold) * c.wbc.coefficient).toFixed(1)} points`;
        }
    }

    // === Security: Response validation utilities ===

    /**
     * Validates the structure of risk data API response.
     * Ensures required fields exist before processing to prevent runtime errors.
     * @param {Object} data - The response data from /api/calculate_risk
     * @returns {boolean} - True if response structure is valid
     */
    function validateRiskDataResponse(data) {
        if (!data || typeof data !== 'object') {
            console.error('Response validation failed: data is not an object');
            return false;
        }

        // Check for required top-level properties
        if (!data.patient_info || typeof data.patient_info !== 'object') {
            console.error('Response validation failed: missing or invalid patient_info');
            return false;
        }

        if (!Array.isArray(data.score_components)) {
            console.error('Response validation failed: score_components is not an array');
            return false;
        }

        // Validate patient_info has at least some identifying information
        const patientInfo = data.patient_info;
        if (!patientInfo.patient_id && !patientInfo.id && !patientInfo.name) {
            console.error('Response validation failed: patient_info missing identification');
            return false;
        }

        // Validate each score component has required fields
        for (let i = 0; i < data.score_components.length; i++) {
            const component = data.score_components[i];
            if (!component || typeof component !== 'object') {
                console.error('Response validation failed: invalid score_component at index', i);
                return false;
            }
            if (typeof component.parameter !== 'string') {
                console.error('Response validation failed: score_component missing parameter at index', i);
                return false;
            }
        }

        return true;
    }

    /**
     * Validates the structure of scoring config API response.
     * @param {Object} config - The response data from /api/config/scoring
     * @returns {boolean} - True if response structure is valid
     */
    function validateScoringConfigResponse(config) {
        if (!config || typeof config !== 'object') {
            console.error('Scoring config validation failed: config is not an object');
            return false;
        }

        // Check for required properties
        if (typeof config.base_score !== 'number') {
            console.error('Scoring config validation failed: missing or invalid base_score');
            return false;
        }

        if (!config.coefficients || typeof config.coefficients !== 'object') {
            console.error('Scoring config validation failed: missing or invalid coefficients');
            return false;
        }

        // Validate coefficient structure for required parameters
        const requiredCoefficients = ['age', 'hemoglobin', 'egfr', 'wbc'];
        for (const key of requiredCoefficients) {
            const coef = config.coefficients[key];
            if (!coef || typeof coef !== 'object') {
                console.error('Scoring config validation failed: missing coefficient', key);
                return false;
            }
            if (typeof coef.threshold !== 'number' || typeof coef.coefficient !== 'number') {
                console.error('Scoring config validation failed: invalid coefficient structure for', key);
                return false;
            }
        }

        if (!config.binary_scores || typeof config.binary_scores !== 'object') {
            console.error('Scoring config validation failed: missing or invalid binary_scores');
            return false;
        }

        return true;
    }

    // === Security: HTML escape utility to prevent XSS ===
    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    // === NEW: Clinical tooltips data ===
    const clinicalTooltips = {
        'Age': {
            title: 'Age',
            content: 'Age is a continuous variable in the PRECISE-HBR model. It is truncated to the 30-80 years range during calculation; older age increases the score.',
            normalRange: 'Calculation Range: 30-80 years',
            riskFactors: 'Score Weight: +0.25 points per year increase<br>Example: 65 years = (65-30)  0.25 = 8.75 points'
        },
        'Hemoglobin': {
            title: 'Hemoglobin',
            content: 'Hemoglobin is a continuous variable in the PRECISE-HBR model. It is truncated to the 5-15 g/dL range during calculation; lower hemoglobin increases the score.',
            normalRange: 'Calculation Range: 5-15 g/dL',
            riskFactors: 'Score Weight: +2.5 points per 1 g/dL decrease<br>Example: 12 g/dL = (15-12)  2.5 = 7.5 points'
        },
        'eGFR': {
            title: 'eGFR (Estimated Glomerular Filtration Rate)',
            content: 'eGFR is a continuous variable in the PRECISE-HBR model. It is truncated to the 5-100 mL/min range; lower kidney function increases the score.',
            normalRange: 'Calculation Range: 5-100 mL/min/1.73m2',
            riskFactors: 'Score Weight: +0.05 points per 1 mL/min decrease<br>Example: 60 mL/min = (100-60)  0.05 = 2.0 points'
        },
        'White Blood Cell Count': {
            title: 'White Blood Cell Count',
            content: 'WBC count is a continuous variable in the PRECISE-HBR model. It is truncated to the 3-15 \u00d710\u00b3/\u00b5L range; higher WBC increases the score.',
            normalRange: 'Calculation Range: 3-15 \u00d710\u00b3/\u00b5L',
            riskFactors: 'Score Weight: +0.8 points per 1 \u00d710\u00b3/\u00b5L increase<br>Example: 10 \u00d710\u00b3/\u00b5L = (10-3) \u00d7 0.8 = 5.6 points'
        },
        'Previous bleeding': {
            title: 'Previous Bleeding',
            content: 'History of spontaneous bleeding is the strongest predictor of future bleeding. Includes gastrointestinal bleeding, intracranial hemorrhage, or bleeding requiring transfusion.',
            normalRange: 'No history of bleeding',
            riskFactors: 'Significant risk increase for those with history (+7 points)'
        },
        'Long-term oral anticoagulation': {
            title: 'Long-term Oral Anticoagulation',
            content: 'Long-term use of oral anticoagulants (e.g., Warfarin, DOACs) significantly increases bleeding risk. Bleeding risk is further elevated when used with dual or triple antiplatelet therapy.',
            normalRange: 'Not used',
            riskFactors: 'ARC-HBR Major Criterion (+5 points)'
        },
        'Platelet count': {
            title: 'Platelet Count',
            content: 'Platelets are key for coagulation. Low platelet count (<100 \u00d710\u2079/L) impairs clotting ability, increasing risk of spontaneous and post-traumatic bleeding. Can be caused by marrow disease, hypersplenism, or medications.',
            normalRange: '150-400 \u00d710\u2079/L',
            riskFactors: '<100 \u00d710\u2079/L is an ARC-HBR Major Criterion<br><50 \u00d710\u2079/L is severe thrombocytopenia'
        },

        'Chronic bleeding diathesis': {
            title: 'Chronic Bleeding Diathesis',
            content: 'Refers to congenital or acquired coagulation disorders, such as Hemophilia, von Willebrand disease, etc. These patients have inherent clotting defects, and antiplatelet therapy further increases risk.',
            normalRange: 'No coagulation disorder',
            riskFactors: 'ARC-HBR Major Criterion<br>Includes: Hemophilia, von Willebrand disease, Factor deficiency'
        },
        'Liver cirrhosis': {
            title: 'Liver Cirrhosis with Portal Hypertension',
            content: 'Cirrhosis reduces coagulation factor synthesis, while portal hypertension causes esophageal varices and hypersplenism (low platelets). Together, these significantly increase risk of major GI bleeding.',
            normalRange: 'No cirrhosis',
            riskFactors: 'ARC-HBR Major Criterion<br>Mortality from variceal bleeding is 20-30%'
        },
        'Active malignancy': {
            title: 'Active Malignancy',
            content: 'Active cancer (diagnosed or treated within past 12 months, excluding non-melanoma skin cancer) increases bleeding risk. The tumor itself, chemotherapy, and radiation can affect coagulation and platelets.',
            normalRange: 'No active malignancy',
            riskFactors: 'ARC-HBR Major Criterion<br>Risk depends on tumor type, stage, and treatment'
        },
        'Chronic use of nsaids': {
            title: 'Chronic Use of NSAIDs or Corticosteroids',
            content: 'NSAIDs inhibit platelet function and damage gastric mucosa, increasing GI bleeding risk. Long-term steroids weaken vessel walls. Risk is additive when combined with antiplatelet drugs. Chronic use is defined as e.g. \u22654 days/week.',
            normalRange: 'No chronic use (\u22654 days/week is considered chronic)',
            riskFactors: 'ARC-HBR Minor Criterion<br>Includes: ibuprofen, naproxen, steroids, etc.'
        },
        'Recent Major Surgery or Trauma': {
            title: 'Recent Major Surgery or Trauma',
            content: 'Recent major surgery or trauma within 30 days before PCI. Surgical wounds and tissue trauma activate coagulation pathways, and combining antiplatelet therapy increases perioperative bleeding risk.',
            normalRange: 'No major surgery or trauma within 30 days before PCI',
            riskFactors: 'ARC-HBR Minor Criterion<br>Defined as major surgery or trauma \u226430 days before PCI'
        },

    };

    document.addEventListener("DOMContentLoaded", function () {

        // Setup all event listeners (CSP compliance)
        setupEventListeners();

        // The patient_id is rendered into the template from the session by Flask
        // Get patient ID from HTML data attribute (set by Jinja2 in main.html)
        const appContainer = document.getElementById('app-container');
        const patientId = appContainer ? appContainer.dataset.patientId : null;
        if (patientId && patientId !== 'N/A') {
            fetchRiskData(patientId);
        } else {
            console.error("Patient ID not found in template. Cannot fetch risk data.");
            displayError("Could not identify the patient. Please try launching the app again.");
        }
    });

    function setupEventListeners() {
        // Static buttons
        document.getElementById('thumbsUpBtn')?.addEventListener('click', () => submitFeedback('thumbs_up'));
        document.getElementById('thumbsDownBtn')?.addEventListener('click', () => submitFeedback('thumbs_down'));
        document.getElementById('submitCommentBtn')?.addEventListener('click', submitComment);
        document.getElementById('cancelFeedbackBtn')?.addEventListener('click', cancelFeedback);
        document.getElementById('copyResultBtn')?.addEventListener('click', copyResult);

        // Reload buttons
        document.querySelectorAll('.reload-btn').forEach(btn => {
            btn.addEventListener('click', () => window.location.reload());
        });

        // Guideline Image - with URL validation for security
        document.querySelectorAll('.guideline-img').forEach(img => {
            img.addEventListener('click', (e) => {
                const imgSrc = e.target.src;
                // Validate URL is from same origin to prevent opening arbitrary URLs
                try {
                    const url = new URL(imgSrc, window.location.origin);
                    if (url.origin === window.location.origin) {
                        window.open(url.href, '_blank', 'noopener,noreferrer');
                    } else {
                        console.warn('Blocked attempt to open external URL:', url.origin);
                    }
                } catch (err) {
                    console.error('Invalid image URL:', err.message);
                }
            });
        });

        // Dynamic Table Delegation
        const tableBody = document.getElementById('score-components');
        if (tableBody) {
            tableBody.addEventListener('input', (e) => {
                const target = e.target;
                if (target.tagName === 'INPUT' && target.type === 'number') {
                    // Extract parameter name from ID "input-Parameter Name"
                    const id = target.id;
                    if (id && id.startsWith('input-')) {
                        const param = id.substring(6);
                        handleValueInput(param, target);
                    }
                }
            });
            tableBody.addEventListener('change', (e) => {
                if (e.target.tagName === 'INPUT' && e.target.type === 'checkbox') {
                    recalculateAndRefreshUI();
                }
            });
            // Click delegation for unit toggle buttons
            tableBody.addEventListener('click', (e) => {
                if (e.target.classList.contains('unit-toggle-btn')) {
                    const inputGroup = e.target.closest('.input-group');
                    const input = inputGroup?.querySelector('input');
                    if (input) toggleHemoglobinUnit(input);
                }
            });
        }
    }

    async function fetchRiskData(patientId) {
        document.getElementById('loading-container').classList.remove('d-none');
        document.getElementById('results-container').classList.add('d-none');
        document.getElementById('error-container').classList.add('d-none');

        // Ensure scoring config is loaded before calculating
        if (!scoringConfig) {
            await fetchScoringConfig();
        }

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch('/api/calculate_risk', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ patientId: patientId })
            });

            if (!response.ok) {
                let errorMessage = `HTTP error: ${response.status}`;
                let requiresReauth = false;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                    requiresReauth = errorData.requires_reauth === true;
                } catch (parseError) {
                    // Response wasn't JSON, use status text
                    errorMessage = `Server error: ${response.status} ${response.statusText}`;
                }
                if (response.status === 401 || requiresReauth) {
                    displaySessionExpired();
                    return;
                }
                throw new Error(errorMessage);
            }
            const data = await response.json();

            // Validate response structure before processing
            if (!validateRiskDataResponse(data)) {
                throw new Error('Invalid response format from server');
            }

            displayResults(data);
        } catch (error) {
            // Structured error logging (PHI redacted for security)
            const errorInfo = {
                message: error.message,
                // Redact patient ID to prevent PHI exposure in browser console
                patientId: patientId ? '[REDACTED]' : 'missing',
                timestamp: new Date().toISOString(),
                type: error.name || 'Error'
            };
            console.error('Risk calculation error:', errorInfo);

            // User-friendly error message
            let userMessage = error.message;
            if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
                userMessage = 'Unable to connect to the server. Please check your network connection.';
            } else if (error.message.includes('timeout')) {
                userMessage = 'The request timed out. Please try again.';
            }
            displayError(userMessage);
        }
    }

    function displayResults(data) {
        currentPatientData = data;
        scoreComponentData = data.score_components; // Store for recalculation

        // Store data warnings from backend (missing FHIR resources)
        // Using module-scoped variable instead of window object for security
        dataWarnings = data.data_warnings || [];

        // Check for required data completeness
        const requiredParameters = ['Age', 'Hemoglobin', 'eGFR', 'White Blood Cell'];
        const missingCriticalData = [];

        scoreComponentData.forEach(item => {
            const paramName = item.parameter || '';
            requiredParameters.forEach(required => {
                if (paramName.includes(required)) {
                    const isMissing = item.value === 'Not available' ||
                        item.value === 'N/A' ||
                        (item.raw_value === null && item.is_present === null);
                    if (isMissing) {
                        missingCriticalData.push(required);
                    }
                }
            });
        });

        // Hide loading, show results (even if data is missing)
        document.getElementById('loading-container').classList.add('d-none');
        document.getElementById('results-container').classList.remove('d-none');

        // Store missing data info for later use
        // Using module-scoped variable instead of window object for security
        initialMissingCriticalData = missingCriticalData;

        // Patient Info
        const patientId = data.patient_info.patient_id ||
            data.patient_info.id ||
            sessionStorage.getItem('current_patient_id') ||
            'N/A';

        // Only update if we have a valid patient ID and it's different from current content
        const patientIdEl = document.getElementById('patient-id');
        if (patientId && patientId !== 'N/A' && patientIdEl.textContent.trim() !== patientId) {
            patientIdEl.textContent = patientId;
            // Ensure the badge styling is maintained
            if (!patientIdEl.classList.contains('bg-primary')) {
                patientIdEl.classList.add('badge', 'bg-primary', 'text-white');
            }
        }
        document.getElementById('patient-name').textContent = data.patient_info.name || 'N/A';
        document.getElementById('patient-age').textContent = data.patient_info.age !== null ? data.patient_info.age : 'N/A';
        document.getElementById('patient-gender').textContent = data.patient_info.gender || 'N/A';

        // Render the interactive table for the first time
        renderInteractiveTable();

        // Restore any previously saved form state (e.g., after session expiry re-launch)
        restoreFormState();

        // Note: CCD export button visibility is handled by recalculateAndRefreshUI()
        // based on data completeness - no need to show it here

        // Perform the initial calculation and UI update
        recalculateAndRefreshUI();
    }

    function getUnitForParameter(parameterName) {
        // Return the appropriate unit based on parameter name
        if (parameterName.includes("Age")) return "years";
        if (parameterName.includes("Hemoglobin")) {
            return unitSettings.hemoglobin || "g/dL";
        }
        if (parameterName.includes("eGFR")) return "mL/min/1.73m2";
        if (parameterName.includes("White Blood Cell")) return "10³/µL";
        return "";
    }

    // === NEW: Unit Conversion Functions ===
    function convertHemoglobin(value, fromUnit, toUnit) {
        // Hemoglobin conversion: g/dL ? mmol/L
        // 1 g/dL = 0.6206 mmol/L
        if (fromUnit === toUnit) return value;

        if (fromUnit === 'g/dL' && toUnit === 'mmol/L') {
            return value * 0.6206;
        } else if (fromUnit === 'mmol/L' && toUnit === 'g/dL') {
            return value / 0.6206;
        }
        return value;
    }

    function toggleHemoglobinUnit(inputElement) {
        const currentValue = parseFloat(inputElement.value);
        if (isNaN(currentValue)) return;

        const currentUnit = unitSettings.hemoglobin;
        const newUnit = currentUnit === 'g/dL' ? 'mmol/L' : 'g/dL';

        // Convert value
        const newValue = convertHemoglobin(currentValue, currentUnit, newUnit);

        // Update
        inputElement.value = newValue.toFixed(2);
        unitSettings.hemoglobin = newUnit;

        // Update unit display
        const unitSpan = inputElement.closest('.input-group').querySelector('.input-group-text');
        if (unitSpan) {
            unitSpan.textContent = newUnit;
        }

        // Recalculate
        recalculateAndRefreshUI();
    }

    // === Clinical Validation Ranges ===
    // min/max: Hard bounds that block calculation (clinically impossible values)
    // warnMax: Soft upper bound that shows warning but allows calculation
    // Note: Age uses 75 as elderly threshold (hardcoded in validateValue)
    const VALIDATION_RANGES = {
        Age: { min: 18, max: 120, warnMax: 100 },
        Hemoglobin: { min: 3, max: 22, warnMin: 7, warnMax: 18 },  // g/dL
        eGFR: { min: 0, max: 200, warnMax: 150 },                   // mL/min/1.73m²
        WBC: { min: 0.1, max: 50, warnMin: 4, warnMax: 20 },       // 10⁹/L
        Platelet: { min: 5, max: 1000, warnMin: 100, warnMax: 450 } // 10⁹/L
    };

    // === Risk Score Thresholds ===
    // PRECISE-HBR score thresholds for bleeding risk categorization
    const RISK_THRESHOLDS = {
        NOT_HIGH: 22,  // Score <= 22: Not high bleeding risk
        HBR: 23,       // Score 23-26: High Bleeding Risk
        VERY_HBR: 27   // Score >= 27: Very High Bleeding Risk
    };

    function validateValue(parameterName, value) {
        const numValue = parseFloat(value);
        if (isNaN(numValue)) return { valid: true, level: 'normal', message: '', blockCalculation: false };

        let result = { valid: true, level: 'normal', message: '', blockCalculation: false };

        if (parameterName.includes("Age")) {
            const range = VALIDATION_RANGES.Age;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = `Age must be between ${range.min} and ${range.max} years`;
                result.blockCalculation = true;
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Age exceeds typical range (>100 years)';
            } else if (numValue >= 75) {
                result.level = 'warning';
                result.message = 'Elderly patient (≥75 years) - increased bleeding risk';
            }
        } else if (parameterName.includes("Hemoglobin")) {
            const range = VALIDATION_RANGES.Hemoglobin;
            const unit = unitSettings.hemoglobin || 'g/dL';

            // Convert limits if using mmol/L (1 g/dL = 0.6206 mmol/L)
            const factor = unit === 'mmol/L' ? 0.6206 : 1;
            const min = range.min * factor;
            const max = range.max * factor;
            const warnMin = range.warnMin * factor;
            const warnMax = range.warnMax * factor;

            if (numValue < min || numValue > max) {
                result.level = 'error';
                result.message = `Hemoglobin must be between ${min.toFixed(1)} and ${max.toFixed(1)} ${unit}`;
                result.blockCalculation = true;
            } else if (numValue < warnMin) {
                result.level = 'warning';
                result.message = `Low hemoglobin (<${warnMin.toFixed(1)} ${unit}) - Anemia`;
            } else if (numValue > warnMax) {
                result.level = 'warning';
                result.message = `Elevated hemoglobin (>${warnMax.toFixed(1)} ${unit})`;
            }
        } else if (parameterName.includes("eGFR")) {
            const range = VALIDATION_RANGES.eGFR;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = `eGFR must be between ${range.min} and ${range.max} mL/min`;
                result.blockCalculation = true;
            } else if (numValue < 15) {
                result.level = 'warning';
                result.message = 'Severe renal impairment (<15) - Very high risk';
            } else if (numValue < 30) {
                result.level = 'warning';
                result.message = 'Severe renal impairment (<30) - High risk';
            } else if (numValue < 60) {
                result.level = 'warning';
                result.message = 'Moderate renal impairment (30-60)';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'eGFR unusually high (>150) - Please verify';
            }
        } else if (parameterName.includes("White Blood Cell")) {
            const range = VALIDATION_RANGES.WBC;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = `WBC must be between ${range.min} and ${range.max} 10⁹/L`;
                result.blockCalculation = true;
            } else if (numValue < range.warnMin) {
                result.level = 'warning';
                result.message = 'Low WBC (<4 10⁹/L) - Leukopenia';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Elevated WBC (>20 10⁹/L) - Leukocytosis';
            }
        } else if (parameterName.includes("Platelet")) {
            const range = VALIDATION_RANGES.Platelet;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = `Platelet must be between ${range.min} and ${range.max} 10⁹/L`;
                result.blockCalculation = true;
            } else if (numValue < range.warnMin) {
                result.level = 'warning';
                result.message = 'Thrombocytopenia (<100 10⁹/L) - High bleeding risk';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Thrombocytosis (>450 10⁹/L)';
            }
        }

        return result;
    }

    // Check all inputs for validation errors that should block calculation
    function hasValidationErrors() {
        let errors = [];

        scoreComponentData.forEach(item => {
            const inputElement = document.getElementById(`input-${item.parameter}`);
            if (inputElement && inputElement.type === 'number' && inputElement.value) {
                const validation = validateValue(item.parameter, inputElement.value);
                if (validation.blockCalculation) {
                    errors.push({
                        parameter: item.parameter,
                        message: validation.message
                    });
                }
            }
        });

        return errors;
    }


    function applyValidationStyling(inputElement, validation) {
        // Remove all validation classes
        inputElement.classList.remove('value-normal', 'value-warning', 'value-error');

        // Apply appropriate class
        if (validation.level === 'error') {
            inputElement.classList.add('value-error');
        } else if (validation.level === 'warning') {
            inputElement.classList.add('value-warning');
        } else {
            inputElement.classList.add('value-normal');
        }

        // Show/hide validation message
        const inputGroup = inputElement.closest('.input-group') || inputElement.parentElement;
        const container = inputGroup.parentElement;

        // First, remove any existing validation messages for this input
        const existingMessages = container.querySelectorAll('.validation-message');
        existingMessages.forEach(msg => msg.remove());

        // Then create new message if needed
        if (validation.message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'validation-message';
            messageDiv.textContent = validation.message;
            if (validation.level === 'error') messageDiv.classList.add('text-danger');
            if (validation.level === 'warning') messageDiv.classList.add('text-warning');
            container.appendChild(messageDiv);
        }
    }

    function formatValueWithUnit(value, unit) {
        // Format the value nicely with appropriate decimal places
        if (typeof value === 'number') {
            if (unit === "years") return Math.round(value);
            if (unit === "g/dL" || unit === "mmol/L") return value.toFixed(2);
            if (unit === "mL/min/1.73m2") return Math.round(value);
            if (unit === "10³/µL") return value.toFixed(2);
            return value.toFixed(2);
        }
        return value;
    }

    // === NEW: Handle input with validation ===
    function handleValueInput(parameterName, inputElement) {
        // Validate the input
        const validation = validateValue(parameterName, inputElement.value);

        // Apply styling based on validation
        applyValidationStyling(inputElement, validation);

        // Recalculate risk
        recalculateAndRefreshUI();
    }

    function renderInteractiveTable() {
        const componentsBody = document.getElementById('score-components');

        // Track missing data for warning display
        let missingDataItems = [];

        // Clear existing content safely
        while (componentsBody.firstChild) {
            componentsBody.removeChild(componentsBody.firstChild);
        }

        if (scoreComponentData && scoreComponentData.length > 0) {
            let conditionSeparatorAdded = false;
            scoreComponentData.forEach(item => {
                // Skip Base Score - don't display it
                if (item.parameter && item.parameter.includes("Base Score")) {
                    return;
                }

                // Add separator bar before the first condition/medication boolean item
                if (!conditionSeparatorAdded && item.is_present !== null && typeof item.is_present === 'boolean') {
                    conditionSeparatorAdded = true;
                    const sepTr = document.createElement('tr');
                    sepTr.className = 'table-active';
                    const sepTd = document.createElement('td');
                    sepTd.colSpan = 4;
                    sepTd.className = 'text-center fw-bold py-2 condition-separator';
                    sepTd.textContent = 'Below condition and medication checker should be secondary confirmed by clinician';
                    sepTr.appendChild(sepTd);
                    componentsBody.appendChild(sepTr);
                }

                const cleanParameterName = translateParameterName(item.parameter || 'Unnamed Criterion');
                const unit = getUnitForParameter(item.parameter);

                // Check if this is missing data
                const isMissingData = (item.value === 'Not available' || item.value === 'N/A' ||
                    (item.raw_value === null && item.is_present === null));

                // Create table row using DOM APIs
                const tr = document.createElement('tr');

                // === Parameter Name Cell ===
                const tdParam = document.createElement('td');
                tdParam.className = 'table-cell-lg';
                tdParam.textContent = cleanParameterName;

                // Generate tooltip for clinical information
                const tooltipKey = cleanParameterName.split('(')[0].trim();
                const tooltipElement = createTooltipElement(tooltipKey);
                if (tooltipElement) {
                    tdParam.appendChild(tooltipElement);
                }
                tr.appendChild(tdParam);

                // === Value Control Cell ===
                const tdValue = document.createElement('td');
                const valueControl = createValueControl(item, unit, isMissingData);
                if (valueControl) {
                    tdValue.appendChild(valueControl);
                }
                if (isMissingData) {
                    missingDataItems.push(cleanParameterName);
                }
                tr.appendChild(tdValue);

                // === Score Badge Cell ===
                const tdScore = document.createElement('td');
                if (item.is_arc_hbr_element === true) {
                    const span = document.createElement('span');
                    span.className = 'text-muted arc-badge-placeholder';
                    span.textContent = 'X';
                    tdScore.appendChild(span);
                } else {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-primary score-badge';
                    badge.id = `score-${item.parameter}`;
                    badge.textContent = item.score;
                    tdScore.appendChild(badge);
                }
                tr.appendChild(tdScore);

                // === Date Cell ===
                const tdDate = document.createElement('td');
                tdDate.className = 'table-cell-lg';
                if (item.is_outdated) {
                    tdDate.classList.add('text-danger');
                }
                if (item.date && item.date !== 'N/A') {
                    tdDate.textContent = item.date;
                } else {
                    tdDate.textContent = 'N/A';
                }
                if (item.is_outdated) {
                    const br = document.createElement('br');
                    const small = document.createElement('small');
                    const icon = document.createElement('i');
                    icon.className = 'fas fa-exclamation-circle';
                    small.appendChild(icon);
                    small.appendChild(document.createTextNode(' Please Retest'));
                    tdDate.appendChild(br);
                    tdDate.appendChild(small);
                }
                tr.appendChild(tdDate);

                componentsBody.appendChild(tr);
            });

            // Display missing data warning if any
            displayMissingDataWarning(missingDataItems);

            // Display truncation warnings (data quality alerts)
            displayTruncationWarnings();

            // Display unrecognized unit warnings (fail-safe alerts)
            displayUnitWarnings();
        } else {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 4;
            td.className = 'text-center';
            td.textContent = 'No risk components available for editing.';
            tr.appendChild(td);
            componentsBody.appendChild(tr);
        }
    }

    /**
     * Creates a value control element (input/checkbox) for a score component.
     * Uses DOM APIs instead of innerHTML for security.
     */
    function createValueControl(item, unit, isMissingData) {
        if (item.raw_value !== null && typeof item.raw_value === 'number') {
            return createNumberInput(item, unit, false);
        } else if (item.is_present !== null && typeof item.is_present === 'boolean') {
            return createCheckboxInput(item);
        } else if (isMissingData) {
            return createNumberInput(item, unit, true);
        } else {
            const span = document.createElement('span');
            span.className = 'font-weight-500 font-lg';
            span.textContent = item.value;
            return span;
        }
    }

    /**
     * Creates a number input with optional unit display.
     * Uses DOM APIs instead of innerHTML for security.
     */
    function createNumberInput(item, unit, isMissing) {
        const div = document.createElement('div');
        div.className = 'input-group input-group-lg-text';

        const input = document.createElement('input');
        input.type = 'number';
        input.className = isMissing ? 'form-control input-missing' : 'form-control input-number-lg';
        input.id = `input-${item.parameter}`;
        input.step = unit === 'years' ? '1' : '0.01';

        if (isMissing) {
            input.placeholder = unit ? `Enter value in ${unit}` : 'Enter value';
            input.setAttribute('data-missing', 'true');
        } else {
            input.value = formatValueWithUnit(item.raw_value, unit);
        }

        div.appendChild(input);

        // Add unit span if unit exists
        if (unit) {
            const unitSpan = document.createElement('span');
            unitSpan.className = isMissing ? 'input-group-text unit-missing' : 'input-group-text input-unit-lg';
            unitSpan.textContent = unit;
            div.appendChild(unitSpan);
        }

        // Add warning icon for missing data
        if (isMissing) {
            const iconSpan = document.createElement('span');
            iconSpan.className = 'input-group-text icon-missing';
            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle text-warning';
            icon.title = 'Missing data - please enter manually if available';
            iconSpan.appendChild(icon);
            div.appendChild(iconSpan);
        }

        // Add unit toggle button for Hemoglobin
        if (item.parameter.includes('Hemoglobin')) {
            const toggleBtn = document.createElement('button');
            toggleBtn.type = 'button';
            toggleBtn.className = 'unit-toggle-btn';
            toggleBtn.title = 'Toggle Unit';
            toggleBtn.textContent = '⇄';
            div.appendChild(toggleBtn);
        }

        return div;
    }

    /**
     * Creates a checkbox input for boolean values.
     * Uses DOM APIs instead of innerHTML for security.
     */
    function createCheckboxInput(item) {
        const div = document.createElement('div');
        div.className = 'form-check form-switch';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.className = 'form-check-input form-switch-lg';
        input.id = `input-${item.parameter}`;
        input.checked = item.is_present;
        input.setAttribute('data-is-arc-element', item.is_arc_hbr_element === true);

        const label = document.createElement('label');
        label.className = 'form-check-label form-check-label-lg';
        label.htmlFor = `input-${item.parameter}`;
        label.textContent = item.value;

        div.appendChild(input);
        div.appendChild(label);

        return div;
    }

    /**
     * Creates a tooltip element using DOM APIs instead of innerHTML.
     */
    function createTooltipElement(parameterKey) {
        const tooltip = clinicalTooltips[parameterKey];
        if (!tooltip) return null;

        const span = document.createElement('span');
        span.className = 'info-tooltip';

        const icon = document.createElement('i');
        icon.className = 'fas fa-info-circle';
        span.appendChild(icon);

        const content = document.createElement('span');
        content.className = 'tooltip-content';

        // Build tooltip content safely
        const title = document.createElement('strong');
        title.textContent = tooltip.title;
        content.appendChild(title);
        content.appendChild(document.createElement('br'));
        content.appendChild(document.createElement('br'));
        content.appendChild(document.createTextNode(tooltip.content));
        content.appendChild(document.createElement('br'));
        content.appendChild(document.createElement('br'));

        const normalLabel = document.createElement('strong');
        normalLabel.textContent = 'Normal Range:';
        content.appendChild(normalLabel);
        content.appendChild(document.createElement('br'));
        content.appendChild(document.createTextNode(tooltip.normalRange));
        content.appendChild(document.createElement('br'));
        content.appendChild(document.createElement('br'));

        const riskLabel = document.createElement('strong');
        riskLabel.textContent = 'Risk Factors:';
        content.appendChild(riskLabel);
        content.appendChild(document.createElement('br'));
        // Note: riskFactors may contain <br> tags from config updates, so we handle it specially
        const riskText = tooltip.riskFactors.replace(/<br>/g, '\n');
        riskText.split('\n').forEach((line, idx, arr) => {
            content.appendChild(document.createTextNode(line));
            if (idx < arr.length - 1) {
                content.appendChild(document.createElement('br'));
            }
        });

        span.appendChild(content);
        return span;
    }

    function displayMissingDataWarning(missingItems) {
        const warningDiv = document.getElementById('missing-data-warning');
        const missingList = document.getElementById('missing-data-list');

        // Get FHIR resource warnings from module-scoped variable
        const currentDataWarnings = dataWarnings || [];
        const hasFhirWarnings = currentDataWarnings.length > 0;
        const hasMissingLabData = missingItems && missingItems.length > 0;

        if (hasMissingLabData || hasFhirWarnings) {
            // Clear list safely using DOM API
            clearElement(missingList);

            // Add FHIR resource warnings first (more critical)
            if (hasFhirWarnings) {
                currentDataWarnings.forEach(warning => {
                    const li = document.createElement('li');
                    const strong = document.createElement('strong');
                    strong.textContent = (warning.resource || 'Unknown') + ' Records:';
                    li.appendChild(strong);
                    li.appendChild(document.createTextNode(' ' + (warning.message || '')));
                    li.className = 'missing-list-item fhir-warning-item';
                    missingList.appendChild(li);
                });
            }

            // Add missing lab data items
            if (hasMissingLabData) {
                missingItems.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = `${item}: No data available from FHIR server`;
                    li.className = 'missing-list-item lab-warning-item';
                    missingList.appendChild(li);
                });
            }

            // Show the warning
            warningDiv.classList.remove('d-none');
        } else {
            // Hide the warning if no missing data
            warningDiv.classList.add('d-none');
        }
    }

    /**
     * Display data quality warnings for values that were truncated/capped.
     * Uses data_warnings from the backend API response.
     */
    function displayTruncationWarnings() {
        const warningDiv = document.getElementById('truncation-warning');
        const warningList = document.getElementById('truncation-warning-list');

        if (!warningDiv || !warningList) return;

        // Filter for truncated_value warnings from backend
        const truncationWarnings = (dataWarnings || []).filter(
            w => w.type === 'truncated_value'
        );

        if (truncationWarnings.length > 0) {
            clearElement(warningList);

            truncationWarnings.forEach(warning => {
                const li = document.createElement('li');
                const strong = document.createElement('strong');
                strong.textContent = (warning.parameter || 'Unknown') + ': ';
                li.appendChild(strong);
                li.appendChild(document.createTextNode(warning.message || ''));
                warningList.appendChild(li);
            });

            warningDiv.classList.remove('d-none');
        } else {
            warningDiv.classList.add('d-none');
        }
    }

    /**
     * Display data quality warnings for values with unrecognized or missing units.
     * These values were excluded from score calculation (fail-safe for Class C).
     */
    function displayUnitWarnings() {
        const warningDiv = document.getElementById('unit-warning');
        const warningList = document.getElementById('unit-warning-list');

        if (!warningDiv || !warningList) return;

        const unitWarnings = (dataWarnings || []).filter(
            w => w.type === 'unrecognized_unit'
        );

        if (unitWarnings.length > 0) {
            clearElement(warningList);

            unitWarnings.forEach(warning => {
                const li = document.createElement('li');
                const strong = document.createElement('strong');
                strong.textContent = (warning.parameter || 'Unknown') + ': ';
                li.appendChild(strong);
                li.appendChild(document.createTextNode(warning.message || ''));
                warningList.appendChild(li);
            });

            warningDiv.classList.remove('d-none');
        } else {
            warningDiv.classList.add('d-none');
        }
    }

    /**
     * Display incomplete data warning using safe DOM APIs.
     * Replaces innerHTML-based approach to prevent XSS.
     */
    function displayIncompleteDataWarning(missingCriticalData) {
        const totalScoreEl = document.getElementById('total-score');
        const riskLevelEl = document.getElementById('risk-level');
        const recommendationEl = document.getElementById('recommendation');

        // Clear and rebuild total-score element
        clearElement(totalScoreEl);
        const warningIcon = document.createElement('i');
        warningIcon.className = 'fas fa-exclamation-triangle text-warning';
        totalScoreEl.appendChild(warningIcon);

        // Clear and rebuild risk-level element
        clearElement(riskLevelEl);
        const riskSpan = document.createElement('span');
        riskSpan.className = 'text-warning';
        riskSpan.textContent = 'Incomplete Data';
        riskLevelEl.appendChild(riskSpan);

        // Clear and rebuild recommendation element
        clearElement(recommendationEl);
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning mb-0';
        alertDiv.setAttribute('role', 'alert');

        const strongEl = document.createElement('strong');
        const editIcon = document.createElement('i');
        editIcon.className = 'fas fa-edit';
        strongEl.appendChild(editIcon);
        strongEl.appendChild(document.createTextNode(' Please enter the following missing data:'));
        alertDiv.appendChild(strongEl);

        const ul = document.createElement('ul');
        ul.className = 'mb-0 mt-2';

        const displayNames = {
            'Age': 'Age',
            'Hemoglobin': 'Hemoglobin',
            'eGFR': 'eGFR (Glomerular Filtration Rate)',
            'White Blood Cell': 'White Blood Cell Count'
        };

        missingCriticalData.forEach(param => {
            const li = document.createElement('li');
            const strong = document.createElement('strong');
            strong.textContent = displayNames[param] || param;
            li.appendChild(strong);
            ul.appendChild(li);
        });

        alertDiv.appendChild(ul);

        const p = document.createElement('p');
        p.className = 'mb-0 mt-2';
        const small = document.createElement('small');
        small.textContent = 'Once complete data is entered, the risk score will be calculated automatically.';
        p.appendChild(small);
        alertDiv.appendChild(p);

        recommendationEl.appendChild(alertDiv);
    }

    /**
     * Display validation errors warning using safe DOM APIs.
     * Replaces innerHTML-based approach to prevent XSS.
     */
    function displayValidationErrorsWarning(validationErrors) {
        const totalScoreEl = document.getElementById('total-score');
        const riskLevelEl = document.getElementById('risk-level');
        const recommendationEl = document.getElementById('recommendation');

        // Clear and rebuild total-score element
        clearElement(totalScoreEl);
        const errorIcon = document.createElement('i');
        errorIcon.className = 'fas fa-times-circle text-danger';
        totalScoreEl.appendChild(errorIcon);

        // Clear and rebuild risk-level element
        clearElement(riskLevelEl);
        const riskSpan = document.createElement('span');
        riskSpan.className = 'text-danger';
        riskSpan.textContent = 'Invalid Values';
        riskLevelEl.appendChild(riskSpan);

        // Clear and rebuild recommendation element
        clearElement(recommendationEl);
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger mb-0';
        alertDiv.setAttribute('role', 'alert');

        const strongEl = document.createElement('strong');
        const exclamIcon = document.createElement('i');
        exclamIcon.className = 'fas fa-exclamation-circle';
        strongEl.appendChild(exclamIcon);
        strongEl.appendChild(document.createTextNode(' Cannot calculate risk score - Please correct the following errors:'));
        alertDiv.appendChild(strongEl);

        const ul = document.createElement('ul');
        ul.className = 'mb-0 mt-2';

        validationErrors.forEach(err => {
            const li = document.createElement('li');
            const strong = document.createElement('strong');
            const cleanParam = err.parameter.replace('PRECISE-HBR - ', '');
            strong.textContent = cleanParam + ':';
            li.appendChild(strong);
            li.appendChild(document.createTextNode(' ' + err.message));
            ul.appendChild(li);
        });

        alertDiv.appendChild(ul);

        const p = document.createElement('p');
        p.className = 'mb-0 mt-2';
        const small = document.createElement('small');
        small.textContent = 'Please enter clinically valid values to calculate the risk score.';
        p.appendChild(small);
        alertDiv.appendChild(p);

        recommendationEl.appendChild(alertDiv);
    }

    /**
     * Safely clear all child elements from an element.
     */
    function clearElement(element) {
        while (element.firstChild) {
            element.removeChild(element.firstChild);
        }
    }

    function recalculateAndRefreshUI() {
        // Check for critical data before calculating
        const requiredParameters = ['Age', 'Hemoglobin', 'eGFR', 'White Blood Cell'];
        const missingCriticalData = [];

        scoreComponentData.forEach(item => {
            const paramName = item.parameter || '';
            requiredParameters.forEach(required => {
                if (paramName.includes(required)) {
                    const inputElement = document.getElementById(`input-${item.parameter}`);
                    if (inputElement && inputElement.type === 'number') {
                        // Check if the input is empty or has no valid value
                        const isEmpty = !inputElement.value || inputElement.value.trim() === '';
                        if (isEmpty) {
                            missingCriticalData.push(required);
                        }
                    }
                }
            });
        });

        // If critical data is missing, show warning in the Total Risk Score area
        if (missingCriticalData.length > 0) {
            // Show warning message instead of risk score using safe DOM APIs
            displayIncompleteDataWarning(missingCriticalData);

            // Hide CCD export button when data is incomplete
            document.getElementById('copyResultBtn').classList.add('d-none');

            return; // Stop calculation but keep UI visible
        }

        // === Check for validation errors that should block calculation ===
        const validationErrors = hasValidationErrors();
        if (validationErrors.length > 0) {
            // Show validation error message instead of risk score using safe DOM APIs
            displayValidationErrorsWarning(validationErrors);

            // Hide CCD export button when there are validation errors
            document.getElementById('copyResultBtn').classList.add('d-none');

            return; // Stop calculation
        }

        // If we get here, all critical data is present and valid
        // Show CCD export button
        document.getElementById('copyResultBtn').classList.remove('d-none');

        let totalScoreRaw = 0;

        // Find the base score from the original data and add it.
        const baseScoreItem = scoreComponentData.find(c => c.parameter.includes("Base Score"));
        const defaultBaseScore = scoringConfig?.base_score || 2;
        totalScoreRaw += baseScoreItem ? baseScoreItem.score : defaultBaseScore;

        // Track ARC-HBR elements state for calculating the summary score
        let arcHbrElementsChecked = 0;

        scoreComponentData.forEach(item => {
            if (item.parameter.includes("Base Score")) return; // Skip base score, already added
            if (item.parameter.includes("ARC-HBR Summary")) return; // Skip summary, will calculate later

            let currentScore = 0;
            let currentScoreRaw = 0;
            const inputElement = document.getElementById(`input-${item.parameter}`);
            if (!inputElement) return;

            if (inputElement.type === 'number') {
                // Check if this was originally missing data
                const isMissingData = inputElement.getAttribute('data-missing') === 'true';

                // Only calculate if we have a value (not empty)
                if (inputElement.value && inputElement.value.trim() !== '') {
                    const value = parseFloat(inputElement.value);

                    // Use dynamic coefficients from backend config
                    const c = scoringConfig?.coefficients || {};

                    if (item.parameter.includes("Age")) {
                        const cfg = c.age || { threshold: 30, coefficient: 0.25, truncation_min: 30, truncation_max: 80 };
                        const effective = Math.max(cfg.truncation_min, Math.min(cfg.truncation_max, value));
                        if (effective > cfg.threshold) currentScoreRaw = (effective - cfg.threshold) * cfg.coefficient;
                    } else if (item.parameter.includes("Hemoglobin")) {
                        const cfg = c.hemoglobin || { threshold: 15, coefficient: 2.5, truncation_min: 5.0, truncation_max: 15.0 };
                        // Convert to g/dL if needed for calculation
                        let hbValue = value;
                        if (unitSettings.hemoglobin === 'mmol/L') {
                            hbValue = convertHemoglobin(value, 'mmol/L', 'g/dL');
                        }
                        const effective = Math.max(cfg.truncation_min, Math.min(cfg.truncation_max, hbValue));
                        if (effective < cfg.threshold) currentScoreRaw = (cfg.threshold - effective) * cfg.coefficient;
                    } else if (item.parameter.includes("eGFR")) {
                        const cfg = c.egfr || { threshold: 100, coefficient: 0.05, truncation_min: 5, truncation_max: 100 };
                        const effective = Math.max(cfg.truncation_min, Math.min(cfg.truncation_max, value));
                        if (effective < cfg.threshold) currentScoreRaw = (cfg.threshold - effective) * cfg.coefficient;
                    } else if (item.parameter.includes("White Blood Cell")) {
                        const cfg = c.wbc || { threshold: 3.0, coefficient: 0.8, truncation_min: 3.0, truncation_max: 15.0 };
                        const effective = Math.max(cfg.truncation_min, Math.min(cfg.truncation_max, value));
                        if (effective > cfg.threshold) currentScoreRaw = (effective - cfg.threshold) * cfg.coefficient;
                    }

                    // If user manually entered data, update styling to show it's no longer missing
                    if (isMissingData) {
                        inputElement.classList.remove('input-missing');
                        inputElement.classList.add('form-control'); // Re-add default form-control styling

                        const inputGroup = inputElement.closest('.input-group');
                        if (inputGroup) {
                            const unitSpans = inputGroup.querySelectorAll('.input-group-text');
                            unitSpans.forEach(span => {
                                span.classList.remove('unit-missing', 'icon-missing');
                                span.classList.add('input-unit-lg'); // Re-add default unit styling
                            });
                        }
                        inputElement.removeAttribute('data-missing'); // Mark as no longer missing
                    }
                }
                // Note: If input is empty, we already checked for critical data at the start
                // Non-critical empty fields (Previous bleeding, OAC) will simply contribute 0 score
            } else if (inputElement.type === 'checkbox') {
                const isChecked = inputElement.checked;
                const label = document.querySelector(`label[for='${inputElement.id}']`);
                const isArcElement = inputElement.getAttribute('data-is-arc-element') === 'true';

                if (isChecked) {
                    const binaryScores = scoringConfig?.binary_scores || { prior_bleeding: 7, oral_anticoagulation: 5 };
                    if (item.parameter.includes("Prior Bleeding")) currentScoreRaw = binaryScores.prior_bleeding;
                    if (item.parameter.includes("Oral Anticoagulation")) currentScoreRaw = binaryScores.oral_anticoagulation;
                    // Individual ARC-HBR elements don't add score directly
                    if (isArcElement) {
                        arcHbrElementsChecked++;
                    }
                    if (label) label.textContent = "Yes";
                } else {
                    if (label) label.textContent = "No";
                }
            }

            totalScoreRaw += currentScoreRaw;
            currentScore = Math.round(currentScoreRaw);

            // Update individual score badge (but not for ARC-HBR elements)
            const scoreBadge = document.getElementById(`score-${item.parameter}`);
            if (scoreBadge && !item.is_arc_hbr_element) {
                scoreBadge.textContent = currentScore;
                scoreBadge.className = `badge ${currentScore > 0 ? 'bg-danger' : 'bg-secondary'} score-badge`;
            }
        });

        // Calculate ARC-HBR Summary score (3 points if any element is checked)
        const arcHbrScore = scoringConfig?.binary_scores?.arc_hbr || 3;
        const arcHbrSummaryScore = arcHbrElementsChecked > 0 ? arcHbrScore : 0;
        totalScoreRaw += arcHbrSummaryScore;

        // Update ARC-HBR Summary badge
        const arcHbrSummaryItem = scoreComponentData.find(c => c.parameter.includes("ARC-HBR Summary"));
        if (arcHbrSummaryItem) {
            const arcSummaryBadge = document.getElementById(`score-${arcHbrSummaryItem.parameter}`);
            if (arcSummaryBadge) {
                arcSummaryBadge.textContent = arcHbrSummaryScore;
                arcSummaryBadge.className = `badge ${arcHbrSummaryScore > 0 ? 'bg-danger' : 'bg-secondary'} score-badge`;
            }
        }

        const finalScore = Math.round(totalScoreRaw);

        // Check if any component is outdated (check original scoreComponentData for is_outdated flag)
        // AND use the check if the value hasn't been manually overruled (though currently we don't track overruled easily, 
        // so we stick to the safe assumption: if source was outdated, warn the user).
        let hasOutdatedData = false;
        if (scoreComponentData) {
            hasOutdatedData = scoreComponentData.some(item => item.is_outdated === true);
        }

        updateTotalScoreUI(finalScore, hasOutdatedData);

        // Update missing data warning after recalculation
        updateMissingDataWarning();
    }

    function updateMissingDataWarning() {
        // Check for any remaining missing data (empty input fields with data-missing="true")
        const missingInputs = document.querySelectorAll('input[data-missing="true"]');
        const remainingMissingItems = [];

        missingInputs.forEach(input => {
            if (!input.value || input.value.trim() === '') {
                // Find the corresponding parameter name
                const row = input.closest('tr');
                if (row) {
                    const parameterCell = row.querySelector('td:first-child');
                    if (parameterCell) {
                        remainingMissingItems.push(parameterCell.textContent.trim());
                    }
                }
            }
        });

        // Update the warning display
        displayMissingDataWarning(remainingMissingItems);
    }

    function updateTotalScoreUI(score, hasOutdatedData = false) {
        const totalScoreEl = document.getElementById('total-score');
        const riskLevelEl = document.getElementById('risk-level');

        let riskCategory = "";
        let colorClass = "";
        let scoreColor = "";
        let recommendation = "";
        let riskPercent = 0;

        // Determine risk level and colors using RISK_THRESHOLDS constants
        if (score <= RISK_THRESHOLDS.NOT_HIGH) {
            riskPercent = 0.5 + (score / RISK_THRESHOLDS.NOT_HIGH) * 3.0;
            riskCategory = `Not high bleeding risk (score ≤${RISK_THRESHOLDS.NOT_HIGH})`;
            colorClass = 'text-success';
            scoreColor = '#28a745'; // green
        } else if (score < RISK_THRESHOLDS.VERY_HBR) {
            riskPercent = 3.5 + ((score - RISK_THRESHOLDS.NOT_HIGH) / 4) * 2.0;
            riskCategory = `HBR (score ${RISK_THRESHOLDS.HBR}-${RISK_THRESHOLDS.VERY_HBR - 1})`;
            colorClass = 'text-warning';
            scoreColor = '#fd7e14'; // orange
        } else { // score >= VERY_HBR
            riskPercent = 5.5 + ((score - (RISK_THRESHOLDS.VERY_HBR - 1)) / 4) * 2.5;
            if (score > 30) riskPercent = 8.0 + ((score - 30) / 5) * 4.0;
            if (score > 35) riskPercent = 12.0 + ((score - 35) / 10) * 3.0;
            riskCategory = `Very HBR (score ≥${RISK_THRESHOLDS.VERY_HBR})`;
            colorClass = 'text-danger';
            scoreColor = '#dc3545'; // red
        }
        riskPercent = Math.min(15.0, riskPercent);
        recommendation = `1-year risk of major bleeding: ${riskPercent.toFixed(2)}% (Bleeding Academic Research Consortium [BARC] type 3 or 5)`;

        // Apply color and bold to total score
        totalScoreEl.textContent = score;
        totalScoreEl.className = `display-3 font-weight-900 ${colorClass}`;

        riskLevelEl.textContent = riskCategory;
        riskLevelEl.className = `h4 ${colorClass}`;
        document.getElementById('recommendation').textContent = recommendation;

        // Update currentPatientData with latest score and risk level
        if (currentPatientData) {
            currentPatientData.total_score = score;
            currentPatientData.risk_level = riskCategory;
            currentPatientData.recommendation = recommendation;
        }

        // --- Add/Remove Tradeoff Analysis Link ---
        const totalScoreCard = document.getElementById('risk-level').parentElement;
        // First, remove any existing tradeoff link to prevent duplicates
        const existingLink = totalScoreCard.querySelector('#tradeoff-link-container');
        if (existingLink) {
            existingLink.remove();
        }

        // Add the link only if score meets HBR threshold
        if (score >= RISK_THRESHOLDS.HBR) {
            const tradeoffDiv = createTradeoffLinkElement(RISK_THRESHOLDS.HBR);
            totalScoreCard.appendChild(tradeoffDiv);
        }

        // Show/Hide HBR Recommendations Section
        const hbrRecommendationsSection = document.getElementById('hbr-recommendations-section');
        if (score >= RISK_THRESHOLDS.HBR) {
            // Show HBR recommendations with smooth animation
            hbrRecommendationsSection.classList.remove('d-none');
            // Smooth scroll to recommendations after a brief delay
            setTimeout(() => {
                hbrRecommendationsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 500);
        } else {
            // Hide HBR recommendations if score drops below threshold
            hbrRecommendationsSection.classList.add('d-none');
        }

        // --- Outdated Data Warning ---
        // Add warning about outdated data
        const outdatedWarningId = 'outdated-data-warning';
        const existingOutdated = totalScoreCard.querySelector(`#${outdatedWarningId}`);
        if (existingOutdated) existingOutdated.remove();

        if (hasOutdatedData) {
            const outdatedDiv = createOutdatedWarningElement(outdatedWarningId);
            totalScoreCard.appendChild(outdatedDiv);
        }
    }

    /**
     * Creates tradeoff analysis link element using safe DOM APIs.
     */
    function createTradeoffLinkElement(threshold) {
        const div = document.createElement('div');
        div.id = 'tradeoff-link-container';
        div.className = 'alert alert-info mt-3';

        const strong = document.createElement('strong');
        strong.textContent = 'High Bleeding Risk Detected (PRECISE-HBR ≥' + threshold + ').';
        div.appendChild(strong);

        div.appendChild(document.createElement('br'));
        div.appendChild(document.createElement('br'));

        const link = document.createElement('a');
        link.href = '/tradeoff_analysis';
        link.className = 'btn btn-info btn-sm mt-2';
        link.target = '_blank';
        link.rel = 'noopener noreferrer';

        const icon = document.createElement('i');
        icon.className = 'fas fa-chart-line';
        link.appendChild(icon);
        link.appendChild(document.createTextNode(' View Bleeding vs. Thrombosis Trade-off Analysis'));

        div.appendChild(link);
        return div;
    }

    /**
     * Creates outdated data warning element using safe DOM APIs.
     */
    function createOutdatedWarningElement(elementId) {
        const div = document.createElement('div');
        div.id = elementId;
        div.className = 'alert alert-danger mt-3 mb-0';

        const icon = document.createElement('i');
        icon.className = 'fas fa-exclamation-triangle';
        div.appendChild(icon);
        div.appendChild(document.createTextNode(' '));

        const strong = document.createElement('strong');
        strong.textContent = 'Data Outdated (>3 months):';
        div.appendChild(strong);

        div.appendChild(document.createTextNode(' Risk score may be unreliable. Please re-verify values.'));
        return div;
    }

    function displayError(errorMessage) {
        document.getElementById('loading-container').classList.add('d-none');
        document.getElementById('error-container').classList.remove('d-none');
        document.getElementById('error-message').textContent = errorMessage;
    }

    /**
     * Display session expired UI when token is invalid/expired (401).
     * Saves current form state to sessionStorage before showing the message,
     * so the clinician's input can be restored after re-launch.
     */
    function displaySessionExpired() {
        // P1: Save form state before showing expired message
        saveFormState();

        document.getElementById('loading-container').classList.add('d-none');
        document.getElementById('results-container').classList.add('d-none');

        const errorContainer = document.getElementById('error-container');
        errorContainer.classList.remove('d-none');
        errorContainer.className = 'alert alert-warning';
        errorContainer.innerHTML = `
            <h4><i class="fas fa-lock" aria-hidden="true"></i> Session Expired</h4>
            <p>Your authentication session has expired. This can happen after a period of inactivity.</p>
            <p><strong>Your input has been saved.</strong> Please re-launch the application from your EHR to continue.</p>
            <a href="/" class="btn btn-primary" aria-label="Return to launch page">
                <i class="fas fa-redo" aria-hidden="true"></i> Re-launch Application
            </a>
        `;
    }

    function translateParameterName(parameterName) {
        // Clean up parameter names for better display
        const translations = {
            'PRECISE-HBR - Base Score': 'Base Score (fixed)',
            'PRECISE-HBR - Age': 'Age (truncated 30-80 years)',
            'PRECISE-HBR - Hemoglobin': 'Hemoglobin (truncated 5-15 g/dL)',
            'PRECISE-HBR - eGFR': 'eGFR (truncated 5-100)',
            'PRECISE-HBR - White Blood Cell Count': 'White Blood Cell Count (truncated 3-15)',
            'PRECISE-HBR - Prior Bleeding': 'Previous bleeding',
            'PRECISE-HBR - Oral Anticoagulation': 'Long-term oral anticoagulation',
            'PRECISE-HBR - Platelet Count': 'Platelet count (<100 \u00d710\u2079/L)',
            'PRECISE-HBR - Chronic Bleeding Diathesis': 'Chronic bleeding diathesis',
            'PRECISE-HBR - Liver Cirrhosis': 'Liver cirrhosis (with portal hypertension)',
            'PRECISE-HBR - Active Malignancy': 'Active malignancy',
            'PRECISE-HBR - NSAIDs/Corticosteroids': 'Chronic use of nsaids (or corticosteroids)',
            'PRECISE-HBR - Recent Major Surgery or Trauma': 'Recent Major Surgery or Trauma',
            'PRECISE-HBR - ARC-HBR Summary': 'ARC-HBR Elements ?1'
        };

        return translations[parameterName] || parameterName;
    }

    // Feedback System Functions
    function submitFeedback(feedbackType) {
        currentFeedbackType = feedbackType;

        // Show comment section for additional feedback
        document.getElementById('commentSection').classList.remove('d-none');

        // Update button states
        document.getElementById('thumbsUpBtn').disabled = true;
        document.getElementById('thumbsDownBtn').disabled = true;

        // Highlight selected button
        if (feedbackType === 'thumbs_up') {
            document.getElementById('thumbsUpBtn').classList.remove('btn-outline-success');
            document.getElementById('thumbsUpBtn').classList.add('btn-success');
        } else {
            document.getElementById('thumbsDownBtn').classList.remove('btn-outline-danger');
            document.getElementById('thumbsDownBtn').classList.add('btn-danger');
        }
    }

    async function submitComment() {
        if (!currentPatientData) {
            console.error('No patient data available for feedback');
            return;
        }

        const comment = document.getElementById('feedbackComment').value;
        const submitBtn = document.getElementById('submitCommentBtn');

        // Get patient ID from various sources
        const patientId = currentPatientData.patient_info?.patient_id ||
            currentPatientData.patient_info?.id ||
            sessionStorage.getItem('current_patient_id') ||
            'unknown';

        // Prepare feedback data
        const feedbackData = {
            patient_id: patientId,
            feedback_type: currentFeedbackType,
            comment: comment,
            score: currentPatientData.total_score,
            risk_level: currentPatientData.risk_level
        };

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Submitting...';

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            const response = await fetch('/api/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(feedbackData)
            });

            const data = await response.json();

            // Validate response is an object with expected structure
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid response format from feedback API');
            }

            if (data.status === 'success') {
                document.getElementById('feedbackMessage').textContent = data.message;
                document.getElementById('feedbackSuccess').classList.remove('d-none');
                document.getElementById('feedbackError').classList.add('d-none');

                // Hide comment section and buttons
                document.getElementById('commentSection').classList.add('d-none');
                document.getElementById('thumbsUpBtn').classList.add('d-none');
                document.getElementById('thumbsDownBtn').classList.add('d-none');

                // Show thank you message after delay
                setTimeout(() => {
                    document.getElementById('feedbackSection').innerHTML = `
                        <div class="text-center py-3 feedback-thank-you">
                            <i class="fas fa-heart text-danger fa-2x mb-2"></i>
                            <h5 class="text-success">Thank you for your valuable feedback!</h5>
                            <p class="text-muted mb-0">Your feedback helps us improve the accuracy of our calculations.</p>
                        </div>
                    `;
                }, 2000);
            } else {
                document.getElementById('feedbackError').classList.remove('d-none');
                document.getElementById('feedbackSuccess').classList.add('d-none');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
            document.getElementById('feedbackError').classList.remove('d-none');
            document.getElementById('feedbackSuccess').classList.add('d-none');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane mr-1"></i>Submit Feedback';
        }
    }

    function cancelFeedback() {
        // Hide comment section
        document.getElementById('commentSection').classList.add('d-none');

        // Reset button states
        document.getElementById('thumbsUpBtn').disabled = false;
        document.getElementById('thumbsDownBtn').disabled = false;

        // Reset button classes
        document.getElementById('thumbsUpBtn').classList.remove('btn-success');
        document.getElementById('thumbsUpBtn').classList.add('btn-outline-success');
        document.getElementById('thumbsDownBtn').classList.remove('btn-danger');
        document.getElementById('thumbsDownBtn').classList.add('btn-outline-danger');

        // Clear comment
        document.getElementById('feedbackComment').value = '';

        // Reset feedback type
        currentFeedbackType = null;
    }

    // ==========================================================================
    // Copy Result to Clipboard
    // Copies the risk assessment result as formatted text
    // ==========================================================================

    async function copyResult() {
        if (!currentPatientData) {
            alert('No patient data available. Please calculate risk first.');
            return;
        }

        // Check if required risk data exists
        if (!currentPatientData.total_score || !currentPatientData.risk_level) {
            alert('Risk score is incomplete. Please ensure all required data is filled in.');
            return;
        }

        const copyBtn = document.getElementById('copyResultBtn');
        const originalHtml = copyBtn.innerHTML;

        try {
            // Build formatted result text
            const patientInfo = currentPatientData.patient_info || {};
            const scoreComponents = scoreComponentData || [];

            let resultText = `PRECISE-HBR Bleeding Risk Assessment\n`;
            resultText += `${'='.repeat(50)}\n\n`;

            // Patient Info
            resultText += `Patient: ${patientInfo.name || 'N/A'}\n`;
            resultText += `Age: ${patientInfo.age || 'N/A'} years\n`;
            resultText += `Gender: ${patientInfo.gender || 'N/A'}\n\n`;

            // Risk Score
            resultText += `Total Risk Score: ${currentPatientData.total_score}\n`;
            resultText += `Risk Level: ${currentPatientData.risk_level}\n`;
            if (currentPatientData.recommendation) {
                resultText += `Recommendation: ${currentPatientData.recommendation.replace(/<[^>]*>/g, '')}\n`;
            }
            resultText += `\n`;

            // Score Components
            resultText += `Score Components:\n`;
            resultText += `${'-'.repeat(40)}\n`;
            scoreComponents.forEach(item => {
                if (!item.parameter.includes('Base Score')) {
                    const inputEl = document.getElementById(`input-${item.parameter}`);
                    let value = item.value || 'N/A';
                    if (inputEl) {
                        if (inputEl.type === 'checkbox') {
                            value = inputEl.checked ? 'Yes' : 'No';
                        } else if (inputEl.value) {
                            value = inputEl.value;
                        }
                    }
                    const score = item.is_arc_hbr_element ? '-' : (item.score || 0);
                    resultText += `• ${item.parameter}: ${value} (Score: ${score})\n`;
                }
            });

            resultText += `\n${'-'.repeat(40)}\n`;
            resultText += `Generated: ${new Date().toLocaleString()}\n`;
            resultText += `Source: PRECISE-HBR Calculator\n`;

            // Copy to clipboard
            await navigator.clipboard.writeText(resultText);

            // Show success feedback
            copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            copyBtn.classList.remove('btn-outline-primary');
            copyBtn.classList.add('btn-success');

            setTimeout(() => {
                copyBtn.innerHTML = originalHtml;
                copyBtn.classList.remove('btn-success');
                copyBtn.classList.add('btn-outline-primary');
            }, 2000);

        } catch (error) {
            console.error('Copy failed:', error);
            alert('Failed to copy to clipboard. Please try again.');
            copyBtn.innerHTML = originalHtml;
        }
    }

})(); // End of main application module

// ==========================================================================
// ONC COMPLIANCE: 45 CFR 170.315 (d)(5) - Automatic Access Time-out
// Automatically stop user access after predetermined period of inactivity
// ==========================================================================

(function () {
    // Configuration
    const INACTIVITY_TIMEOUT_SECONDS = 5 * 60; // 5 minutes in seconds
    const WARNING_BEFORE_TIMEOUT = 60;  // Show warning 60 seconds before timeout

    let remainingSeconds = INACTIVITY_TIMEOUT_SECONDS;
    let countdownInterval = null;
    let warningModal = null;

    // Events that indicate user activity
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    function updateTimerDisplay() {
        const timerElement = document.getElementById('session-timer');
        if (timerElement) {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    function startCountdown() {
        // Clear any existing interval
        if (countdownInterval) clearInterval(countdownInterval);

        countdownInterval = setInterval(function () {
            remainingSeconds--;
            updateTimerDisplay();

            // Show warning at 1 minute remaining
            if (remainingSeconds === WARNING_BEFORE_TIMEOUT) {
                showTimeoutWarning();
            }

            // Perform logout at 0
            if (remainingSeconds <= 0) {
                performLogout();
            }
        }, 1000);
    }

    function resetInactivityTimer() {
        // Reset countdown
        remainingSeconds = INACTIVITY_TIMEOUT_SECONDS;
        updateTimerDisplay();

        // Close warning modal if open
        if (warningModal) closeWarningModal();
    }

    function showTimeoutWarning() {
        // Create modal if it doesn't exist
        if (!warningModal) {
            warningModal = document.createElement('div');
            warningModal.className = 'modal fade show d-block modal-backdrop-dim';
            warningModal.innerHTML = `
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content">
                            <div class="modal-header bg-warning text-dark">
                                <h5 class="modal-title">
                                    <i class="fas fa-exclamation-triangle"></i> Session Timeout Warning
                                </h5>
                            </div>
                            <div class="modal-body">
                                <p><strong>Your session will expire in 1 minute due to inactivity.</strong></p>
                                <p>For security purposes, access to patient information is automatically stopped after 5 minutes of inactivity.</p>
                                <p>Click "Stay Logged In" to continue working, or you will be automatically logged out.</p>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-primary" id="stay-logged-in-btn">
                                    <i class="fas fa-check"></i> Stay Logged In
                                </button>
                                <button type="button" class="btn btn-secondary" id="logout-now-btn">
                                    <i class="fas fa-sign-out-alt"></i> Logout Now
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            document.body.appendChild(warningModal);

            // Attach event handlers
            document.getElementById('stay-logged-in-btn').addEventListener('click', function () {
                closeWarningModal();
                resetInactivityTimer();
            });

            document.getElementById('logout-now-btn').addEventListener('click', function () {
                performLogout();
            });
        }
    }

    function closeWarningModal() {
        if (warningModal) {
            warningModal.remove();
            warningModal = null;
        }
    }

    function performLogout() {
        // Clear countdown interval
        if (countdownInterval) clearInterval(countdownInterval);

        // Remove event listeners to prevent further activity tracking
        activityEvents.forEach(function (eventName) {
            document.removeEventListener(eventName, resetInactivityTimer);
        });

        // Display logout message
        const body = document.body;
        body.innerHTML = `
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <div class="card border-warning">
                                <div class="card-header bg-warning text-dark">
                                    <h4><i class="fas fa-clock"></i> Session Expired</h4>
                                </div>
                                <div class="card-body text-center">
                                    <p class="lead">Your session has been automatically ended due to inactivity.</p>
                                    <p>This is a security measure to protect patient information.</p>
                                    <hr>
                                    <p class="text-muted">
                                        <small>
                                            <i class="fas fa-shield-alt"></i> 
                                            Compliant with ONC 45 CFR 170.315 (d)(5) - Automatic Access Time-out (5 minutes)
                                        </small>
                                    </p>
                                    <a href="/" class="btn btn-primary mt-3">
                                        <i class="fas fa-redo"></i> Return to Login
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

        // Make a backend call to invalidate the session with CSRF token
        // This is critical for security - server-side session must be invalidated
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const headers = csrfMeta ? { 'X-CSRFToken': csrfMeta.getAttribute('content') } : {};

        fetch('/logout', {
            method: 'POST',
            credentials: 'same-origin',
            headers: headers
        })
            .then(function (response) {
                if (!response.ok) {
                    // Server-side logout may have failed - log warning
                    // Note: Client UI already shows logged-out state for UX
                    console.warn('Server logout returned non-OK status:', response.status,
                        '- Server session may still be active. User should close browser.');
                }
            })
            .catch(function (err) {
                // Network error - server session may still be active
                console.error('Logout request failed:', err.message,
                    '- Server session may still be active. User should close browser.');
            });
    }

    // Attach activity listeners
    activityEvents.forEach(function (eventName) {
        document.addEventListener(eventName, resetInactivityTimer, { passive: true });
    });

    // Start the countdown on page load
    startCountdown();
})();

// ==========================================================================
// TOKEN HEALTH MONITOR: Proactive token expiry detection and refresh
// Checks token status periodically and attempts refresh before expiry.
// ==========================================================================
(function () {
    'use strict';

    const CHECK_INTERVAL_MS = 60 * 1000;  // Check every 60 seconds
    const REFRESH_THRESHOLD_SECONDS = 120; // Attempt refresh when < 2 min remaining
    let refreshInProgress = false;
    let monitorInterval = null;

    async function checkTokenHealth() {
        if (refreshInProgress) return;

        try {
            const resp = await fetch('/api/session-status');
            if (!resp.ok) {
                if (resp.status === 401) {
                    showTokenExpiredBanner();
                    stopMonitor();
                }
                return;
            }

            const data = await resp.json();

            if (data.token_expired) {
                // Token already expired — try refresh if possible
                if (data.has_refresh_token) {
                    const refreshed = await attemptRefresh();
                    if (!refreshed) {
                        showTokenExpiredBanner();
                        stopMonitor();
                    }
                } else {
                    showTokenExpiredBanner();
                    stopMonitor();
                }
                return;
            }

            // Token still valid but expiring soon — proactive refresh
            if (data.token_remaining_seconds !== null &&
                data.token_remaining_seconds <= REFRESH_THRESHOLD_SECONDS &&
                data.has_refresh_token) {
                await attemptRefresh();
            }
        } catch (e) {
            // Network error — skip this check cycle
            console.warn('Token health check failed:', e.message);
        }
    }

    async function attemptRefresh() {
        refreshInProgress = true;
        try {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const headers = { 'Accept': 'application/json' };
            if (csrfMeta) headers['X-CSRFToken'] = csrfMeta.getAttribute('content');

            const resp = await fetch('/api/refresh-token', {
                method: 'POST',
                credentials: 'same-origin',
                headers: headers
            });

            if (resp.ok) {
                console.info('Token refreshed successfully');
                return true;
            }

            const data = await resp.json().catch(function () { return {}; });
            if (data.requires_reauth) {
                return false;
            }
            // Rate limited or transient error — will retry next cycle
            return true;
        } catch (e) {
            console.warn('Token refresh failed:', e.message);
            return false;
        } finally {
            refreshInProgress = false;
        }
    }

    function showTokenExpiredBanner() {
        // Save form state before showing banner (for main page)
        try {
            const resultsContainer = document.getElementById('results-container');
            if (resultsContainer) {
                const state = {};
                resultsContainer.querySelectorAll('input').forEach(function (input) {
                    if (!input.id) return;
                    if (input.type === 'checkbox') {
                        state[input.id] = { type: 'checkbox', checked: input.checked };
                    } else if (input.value) {
                        state[input.id] = { type: input.type, value: input.value };
                    }
                });
                if (Object.keys(state).length > 0) {
                    sessionStorage.setItem('precise_hbr_form_state', JSON.stringify(state));
                }
            }
        } catch (e) { /* ignore */ }

        // Only show if not already showing a session-expired message
        if (document.querySelector('.token-expired-banner')) return;

        const banner = document.createElement('div');
        banner.className = 'token-expired-banner alert alert-warning alert-dismissible position-fixed w-100 top-0 start-0 expired-banner';
        banner.setAttribute('role', 'alert');
        banner.innerHTML =
            '<strong><i class="fas fa-lock"></i> Session Expired</strong> ' +
            'Your authentication has expired. Your input has been saved. ' +
            '<a href="/" class="btn btn-sm btn-primary ms-2">Re-launch Application</a>';
        document.body.prepend(banner);
    }

    function stopMonitor() {
        if (monitorInterval) {
            clearInterval(monitorInterval);
            monitorInterval = null;
        }
    }

    // Start monitoring
    monitorInterval = setInterval(checkTokenHealth, CHECK_INTERVAL_MS);
    // Run first check after a short delay (let page finish loading)
    setTimeout(checkTokenHealth, 5000);
})();