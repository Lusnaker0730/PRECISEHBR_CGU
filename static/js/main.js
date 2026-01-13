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
            scoringConfig = await response.json();
            console.log('Scoring config loaded:', scoringConfig);
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
                egfr: { threshold: 100, coefficient: 0.05, truncation_min: 5, truncation_max: 100 },
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
                `Score Weight: +${c.wbc.coefficient} points per 1 10?/L increase<br>` +
                `Example: 10 10?/L = (10-${c.wbc.threshold})  ${c.wbc.coefficient} = ${((10 - c.wbc.threshold) * c.wbc.coefficient).toFixed(1)} points`;
        }
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
            content: 'WBC count is a continuous variable in the PRECISE-HBR model. It is truncated to a maximum of 15 10?/L; higher WBC increases the score.',
            normalRange: 'Calculation Range: 3-15 10?/L',
            riskFactors: 'Score Weight: +0.8 points per 1 10?/L increase<br>Example: 10 10?/L = (10-3)  0.8 = 5.6 points'
        },
        'Previous bleeding': {
            title: 'Previous Bleeding',
            content: 'History of spontaneous bleeding is the strongest predictor of future bleeding. Includes gastrointestinal bleeding, intracranial hemorrhage, or bleeding requiring transfusion.',
            normalRange: 'No history of bleeding',
            riskFactors: 'Significant risk increase for those with history (+7 points)'
        },
        'Long-term OAC': {
            title: 'Long-term Oral Anticoagulation',
            content: 'Long-term use of oral anticoagulants (e.g., Warfarin, DOACs) significantly increases bleeding risk, especially when combined with antiplatelet therapy.',
            normalRange: 'Not used',
            riskFactors: 'Doubles the bleeding risk (+5 points)'
        },
        'Long-term oral anticoagulation': {
            title: 'Long-term Oral Anticoagulation',
            content: 'Long-term use of oral anticoagulants (e.g., Warfarin, DOACs) significantly increases bleeding risk. Bleeding risk is further elevated when used with dual or triple antiplatelet therapy.',
            normalRange: 'Not used',
            riskFactors: 'ARC-HBR Major Criterion'
        },
        'Platelet count': {
            title: 'Platelet Count',
            content: 'Platelets are key for coagulation. Low platelet count (<10010?/L) impairs clotting ability, increasing risk of spontaneous and post-traumatic bleeding. Can be caused by marrow disease, hypersplenism, or medications.',
            normalRange: '150-400 10?/L',
            riskFactors: '<100 10?/L is an ARC-HBR Major Criterion<br><50 10?/L is severe thrombocytopenia'
        },
        'Platelet count <100': {
            title: 'Platelet Count <100 10?/L (Thrombocytopenia)',
            content: 'Platelets are key for coagulation. Low platelet count (<10010?/L) impairs clotting ability, increasing risk of spontaneous and post-traumatic bleeding.',
            normalRange: '150-400 10?/L',
            riskFactors: '<100 10?/L is an ARC-HBR Major Criterion'
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
            content: 'NSAIDs inhibit platelet function and damage gastric mucosa, increasing GI bleeding risk. Long-term steroids weaken vessel walls. Risk is additive when combined with antiplatelet drugs.',
            normalRange: 'No chronic use',
            riskFactors: 'ARC-HBR Minor Criterion<br>Includes: ibuprofen, naproxen, steroids, etc.'
        },
        'Anemia': {
            title: 'Anemia',
            content: 'Anemia (Hb <11 g/dL) may indicate chronic bleeding and reduces tolerance to bleeding complications. Anemic patients are more prone to hemodynamic instability if bleeding occurs.',
            normalRange: 'Hb ?13 g/dL (Male), ?12 g/dL (Female)',
            riskFactors: 'Hb <11 g/dL is an ARC-HBR Minor Criterion'
        },
        'Chronic kidney disease': {
            title: 'Chronic Kidney Disease',
            content: 'CKD (eGFR <60 mL/min) affects platelet function and coagulation factor metabolism. Also, many antithrombotics are renally cleared; impairment leads to accumulation and bleeding.',
            normalRange: 'eGFR ?60 mL/min/1.73m2',
            riskFactors: 'eGFR <60 is an ARC-HBR Minor Criterion<br>eGFR <30 is a Major Criterion'
        },
        'Thrombocytopenia': {
            title: 'Thrombocytopenia',
            content: 'Low platelet count affects primary hemostasis. Moderate thrombocytopenia (<10010?/L) may increase bleeding risk, especially during invasive procedures or antithrombotic therapy.',
            normalRange: '150-400 10?/L',
            riskFactors: '<100 10?/L is an ARC-HBR Major Criterion'
        }
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

        // Guideline Image
        document.querySelectorAll('.guideline-img').forEach(img => {
            img.addEventListener('click', (e) => window.open(e.target.src, '_blank'));
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
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || errorData.message || errorMessage;
                } catch (parseError) {
                    // Response wasn't JSON, use status text
                    errorMessage = `Server error: ${response.status} ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            const data = await response.json();
            displayResults(data);
        } catch (error) {
            // Structured error logging
            const errorInfo = {
                message: error.message,
                patientId: patientId,
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
        window.initialMissingCriticalData = missingCriticalData;

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
        if (parameterName.includes("White Blood Cell")) return "10?/L";
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

    // === ENHANCED: Value Validation Functions with Clinical Bounds ===
    // Clinical validation ranges based on physiologically plausible values
    // Clinical validation ranges - simplified to two levels:
    // min/max: Hard bounds that block calculation (clinically impossible values)
    // warnMin/warnMax: Soft bounds that show warnings but allow calculation
    const VALIDATION_RANGES = {
        Age: { min: 18, max: 120, warnMin: 18, warnMax: 100 },
        Hemoglobin: { min: 3, max: 22, warnMin: 7, warnMax: 18 },  // g/dL
        eGFR: { min: 0, max: 200, warnMin: 15, warnMax: 150 },     // mL/min/1.73m²
        WBC: { min: 0.1, max: 50, warnMin: 4, warnMax: 20 },       // 10⁹/L
        Platelet: { min: 5, max: 1000, warnMin: 100, warnMax: 450 } // 10⁹/L
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

    // === NEW: Generate Tooltip HTML ===
    function generateTooltip(parameterKey) {
        const tooltip = clinicalTooltips[parameterKey];
        if (!tooltip) return '';

        return `
            <span class="info-tooltip">
                <i class="fas fa-info-circle"></i>
                <span class="tooltip-content">
                    <strong>${tooltip.title}</strong><br><br>
                    ${tooltip.content}<br><br>
                    <strong>Normal Range:</strong><br>${tooltip.normalRange}<br><br>
                    <strong>Risk Factors:</strong><br>${tooltip.riskFactors}
                </span>
            </span>
        `;
    }

    function formatValueWithUnit(value, unit) {
        // Format the value nicely with appropriate decimal places
        if (typeof value === 'number') {
            if (unit === "years") return Math.round(value);
            if (unit === "g/dL" || unit === "mmol/L") return value.toFixed(2);
            if (unit === "mL/min/1.73m2") return Math.round(value);
            if (unit === "10?/L") return value.toFixed(2);
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
        // Build HTML string first to avoid repeated DOM reparsing (memory leak fix)
        let tableHtml = '';

        if (scoreComponentData && scoreComponentData.length > 0) {
            scoreComponentData.forEach(item => {
                // Skip Base Score - don't display it
                if (item.parameter && item.parameter.includes("Base Score")) {
                    return;
                }

                const cleanParameterName = translateParameterName(item.parameter || 'Unnamed Criterion');
                // Escape values for XSS prevention
                const safeParameterName = escapeHtml(cleanParameterName);
                const safeParameter = escapeHtml(item.parameter);
                let valueControl = '';
                const unit = getUnitForParameter(item.parameter);
                const safeUnit = escapeHtml(unit);

                // Check if this is missing data
                const isMissingData = (item.value === 'Not available' || item.value === 'N/A' ||
                    (item.raw_value === null && item.is_present === null));

                // Create an input for numbers, a checkbox for booleans, or manual input for missing data
                if (item.raw_value !== null && typeof item.raw_value === 'number') {
                    const formattedValue = formatValueWithUnit(item.raw_value, unit);
                    const step = unit === "years" ? "1" : "0.01";

                    // Add unit toggle button for Hemoglobin
                    const unitToggleBtn = item.parameter.includes("Hemoglobin") ?
                        `<button type="button" class="unit-toggle-btn" title="Toggle Unit">?</button>` : '';

                    valueControl = `
                        <div class="input-group input-group-lg-text">
                            <input type="number"
                                   class="form-control input-number-lg"
                                   id="input-${safeParameter}"
                                   value="${escapeHtml(formattedValue)}"
                                   step="${step}">
                            ${safeUnit ? `<span class="input-group-text input-unit-lg">${safeUnit}</span>` : ''}
                            ${unitToggleBtn}
                        </div>
                    `;
                } else if (item.is_present !== null && typeof item.is_present === 'boolean') {
                    const checked = item.is_present ? 'checked' : '';
                    // Check if this is an ARC-HBR element (should not have editable score)
                    const isArcElement = item.is_arc_hbr_element === true;
                    const safeValue = escapeHtml(item.value);
                    valueControl = `
                        <div class="form-check form-switch">
                            <input class="form-check-input form-switch-lg"
                                   type="checkbox"
                                   id="input-${safeParameter}"
                                   ${checked}
                                   data-is-arc-element="${isArcElement}">
                            <label class="form-check-label form-check-label-lg"
                                   for="input-${safeParameter}">
                                ${safeValue}
                            </label>
                        </div>
                    `;
                } else if (isMissingData) {
                    // Missing data - provide manual input option
                    missingDataItems.push(cleanParameterName);
                    const step = unit === "years" ? "1" : "0.01";
                    const placeholder = unit ? `Enter value in ${safeUnit}` : "Enter value";

                    // Add unit toggle button for Hemoglobin
                    const unitToggleBtn = item.parameter.includes("Hemoglobin") ?
                        `<button type="button" class="unit-toggle-btn" title="Toggle Unit">?</button>` : '';

                    valueControl = `
                        <div class="input-group input-group-lg-text">
                            <input type="number"
                                   class="form-control input-missing"
                                   id="input-${safeParameter}"
                                   placeholder="${escapeHtml(placeholder)}"
                                   step="${step}"
                                   data-missing="true">
                            ${safeUnit ? `<span class="input-group-text unit-missing">${safeUnit}</span>` : ''}
                            <span class="input-group-text icon-missing">
                                <i class="fas fa-exclamation-triangle text-warning" title="Missing data - please enter manually if available"></i>
                            </span>
                            ${unitToggleBtn}
                        </div>
                    `;
                } else {
                    valueControl = `<span class="font-weight-500 font-lg">${escapeHtml(item.value)}</span>`; // Fallback for base score or others
                }

                // Generate score badge cell - hide for ARC-HBR elements
                let scoreBadgeHtml = '';
                if (item.is_arc_hbr_element === true) {
                    // Don't show score for ARC-HBR elements
                    scoreBadgeHtml = '<span class="text-muted arc-badge-placeholder">X</span>';
                } else {
                    scoreBadgeHtml = `<span class="badge bg-primary score-badge" id="score-${safeParameter}">${escapeHtml(item.score)}</span>`;
                }

                // Generate tooltip for clinical information
                const tooltipKey = cleanParameterName.split('(')[0].trim();
                const tooltipHtml = generateTooltip(tooltipKey);

                const safeDate = escapeHtml(item.date || 'N/A');
                tableHtml += `
                    <tr>
                        <td class="table-cell-lg">
                            ${safeParameterName}
                            ${tooltipHtml}
                        </td>
                        <td>${valueControl}</td>
                        <td>${scoreBadgeHtml}</td>
                        <td class="table-cell-lg ${item.is_outdated ? 'text-danger' : ''}">
                            ${safeDate}
                            ${item.is_outdated ? '<br><small><i class="fas fa-exclamation-circle"></i> Please Retest</small>' : ''}
                        </td>
                    </tr>
                `;
            });

            // Assign all HTML at once (prevents repeated DOM reparsing)
            componentsBody.innerHTML = tableHtml;

            // Display missing data warning if any
            displayMissingDataWarning(missingDataItems);
        } else {
            componentsBody.innerHTML = '<tr><td colspan="4" class="text-center">No risk components available for editing.</td></tr>';
        }
    }

    function displayMissingDataWarning(missingItems) {
        const warningDiv = document.getElementById('missing-data-warning');
        const missingList = document.getElementById('missing-data-list');

        if (missingItems && missingItems.length > 0) {
            // Build the list of missing items
            missingList.innerHTML = '';
            missingItems.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                li.className = 'missing-list-item';
                missingList.appendChild(li);
            });

            // Show the warning
            warningDiv.classList.remove('d-none');
        } else {
            // Hide the warning if no missing data
            warningDiv.classList.add('d-none');
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
            // Show warning message instead of risk score
            document.getElementById('total-score').innerHTML = `
                <i class="fas fa-exclamation-triangle text-warning"></i>
            `;
            document.getElementById('risk-level').innerHTML = `
                <span class="text-warning">Incomplete Data</span>
            `;
            document.getElementById('recommendation').innerHTML = `
                <div class="alert alert-warning mb-0" role="alert">
                    <strong><i class="fas fa-edit"></i> Please enter the following missing data:</strong>
                    <ul class="mb-0 mt-2">
                        ${missingCriticalData.map(param => {
                let displayName = param;
                if (param === 'Age') displayName = 'Age';
                if (param === 'Hemoglobin') displayName = 'Hemoglobin';
                if (param === 'eGFR') displayName = 'eGFR (Glomerular Filtration Rate)';
                if (param === 'White Blood Cell') displayName = 'White Blood Cell Count';
                return `<li><strong>${escapeHtml(displayName)}</strong></li>`;
            }).join('')}
                    </ul>
                    <p class="mb-0 mt-2"><small>Once complete data is entered, the risk score will be calculated automatically.</small></p>
                </div>
            `;

            // Hide CCD export button when data is incomplete
            document.getElementById('copyResultBtn').classList.add('d-none');

            return; // Stop calculation but keep UI visible
        }

        // === NEW: Check for validation errors that should block calculation ===
        const validationErrors = hasValidationErrors();
        if (validationErrors.length > 0) {
            // Show validation error message instead of risk score
            document.getElementById('total-score').innerHTML = `
                <i class="fas fa-times-circle text-danger"></i>
            `;
            document.getElementById('risk-level').innerHTML = `
                <span class="text-danger">Invalid Values</span>
            `;
            document.getElementById('recommendation').innerHTML = `
                <div class="alert alert-danger mb-0" role="alert">
                    <strong><i class="fas fa-exclamation-circle"></i> Cannot calculate risk score - Please correct the following errors:</strong>
                    <ul class="mb-0 mt-2">
                        ${validationErrors.map(err => {
                const cleanParam = err.parameter.replace('PRECISE-HBR - ', '');
                return `<li><strong>${escapeHtml(cleanParam)}:</strong> ${escapeHtml(err.message)}</li>`;
            }).join('')}
                    </ul>
                    <p class="mb-0 mt-2"><small>Please enter clinically valid values to calculate the risk score.</small></p>
                </div>
            `;

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

        // Determine risk level and colors
        // Replicate bleeding risk percentage and category logic from backend
        if (score <= 22) {
            riskPercent = 0.5 + (score / 22) * 3.0;
            riskCategory = `Not high bleeding risk (score ?22)`;
            colorClass = 'text-success';
            scoreColor = '#28a745'; // green
        } else if (score <= 26) {
            riskPercent = 3.5 + ((score - 22) / 4) * 2.0;
            riskCategory = `HBR (score 23-26)`;
            colorClass = 'text-warning';
            scoreColor = '#fd7e14'; // orange
        } else { // score >= 27
            riskPercent = 5.5 + ((score - 26) / 4) * 2.5;
            if (score > 30) riskPercent = 8.0 + ((score - 30) / 5) * 4.0;
            if (score > 35) riskPercent = 12.0 + ((score - 35) / 10) * 3.0;
            riskCategory = `Very HBR (score ?27)`;
            colorClass = 'text-danger';
            scoreColor = '#dc3545'; // red
        }
        riskPercent = Math.min(15.0, riskPercent);
        recommendation = `1-year risk of major bleeding: ${riskPercent.toFixed(2)}% (Bleeding Academic Research Consortium [BARC] type 3 or 5)`;

        // Apply color and bold to total score
        totalScoreEl.textContent = score;
        totalScoreEl.style.color = scoreColor; // Color is dynamic, hard to move to class without many classes
        totalScoreEl.className = 'display-3 font-weight-900';

        riskLevelEl.textContent = riskCategory;
        riskLevelEl.className = `h4 ${colorClass}`;
        document.getElementById('recommendation').textContent = recommendation;

        // Update currentPatientData with latest score and risk level
        if (currentPatientData) {
            currentPatientData.total_score = score;
            currentPatientData.risk_level = riskCategory;
            currentPatientData.recommendation = recommendation;
        }

        // --- NEW: Add/Remove Tradeoff Analysis Link ---
        const totalScoreCard = document.getElementById('risk-level').parentElement;
        // First, remove any existing tradeoff link to prevent duplicates
        const existingLink = totalScoreCard.querySelector('#tradeoff-link-container');
        if (existingLink) {
            existingLink.remove();
        }

        // Add the link only if the score is 23 or higher (HBR threshold)
        if (score >= 23) {
            const tradeoffDiv = document.createElement('div');
            tradeoffDiv.id = 'tradeoff-link-container'; // Add an ID for easy removal
            tradeoffDiv.className = 'alert alert-info mt-3';
            tradeoffDiv.innerHTML = `
                <strong>High Bleeding Risk Detected (PRECISE-HBR ?23).</strong>
                <br><br>
                <a href="/tradeoff_analysis" class="btn btn-info btn-sm mt-2" target="_blank" rel="noopener noreferrer">
                    <i class="fas fa-chart-line"></i> View Bleeding vs. Thrombosis Trade-off Analysis
                </a>`;
            totalScoreCard.appendChild(tradeoffDiv);
        }

        // --- NEW: Show/Hide HBR Recommendations Section ---
        const hbrRecommendationsSection = document.getElementById('hbr-recommendations-section');
        if (score >= 23) {
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

        // --- NEW: Outdated Data Warning ---
        // Add warning about outdated data
        const outdatedWarningId = 'outdated-data-warning';
        const existingOutdated = totalScoreCard.querySelector(`#${outdatedWarningId}`);
        if (existingOutdated) existingOutdated.remove();

        if (hasOutdatedData) {
            const outdatedDiv = document.createElement('div');
            outdatedDiv.id = outdatedWarningId;
            outdatedDiv.className = 'alert alert-danger mt-3 mb-0';
            outdatedDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Data Outdated (>3 months):</strong> Risk score may be unreliable. Please re-verify values.
            `;
            totalScoreCard.appendChild(outdatedDiv);
        }
    }

    function displayError(errorMessage) {
        document.getElementById('loading-container').classList.add('d-none');
        document.getElementById('error-container').classList.remove('d-none');
        document.getElementById('error-message').textContent = errorMessage;
    }

    function translateParameterName(parameterName) {
        // Clean up parameter names for better display
        const translations = {
            'PRECISE-HBR - Base Score': 'Base Score (fixed)',
            'PRECISE-HBR - Age': 'Age (truncated 30-80 years)',
            'PRECISE-HBR - Hemoglobin': 'Hemoglobin (truncated 5-15 g/dL)',
            'PRECISE-HBR - eGFR': 'eGFR (truncated above 100)',
            'PRECISE-HBR - White Blood Cell Count': 'White Blood Cell Count (truncated above 15103)',
            'PRECISE-HBR - Prior Bleeding': 'Previous bleeding',
            'PRECISE-HBR - Oral Anticoagulation': 'Long-term oral anticoagulation',
            'PRECISE-HBR - Platelet Count': 'Platelet count <100 10?/L',
            'PRECISE-HBR - Chronic Bleeding Diathesis': 'Chronic bleeding diathesis',
            'PRECISE-HBR - Liver Cirrhosis': 'Liver cirrhosis with portal hypertension',
            'PRECISE-HBR - Active Malignancy': 'Active malignancy',
            'PRECISE-HBR - NSAIDs/Corticosteroids': 'Chronic use of nsaids or corticosteroids',
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

    function submitComment() {
        if (!currentPatientData) {
            console.error('No patient data available for feedback');
            return;
        }

        const comment = document.getElementById('feedbackComment').value;

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
        document.getElementById('submitCommentBtn').disabled = true;
        document.getElementById('submitCommentBtn').innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>Submitting...';

        // Submit feedback via AJAX
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        fetch('/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(feedbackData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show success message
                    document.getElementById('feedbackMessage').textContent = data.message;
                    document.getElementById('feedbackSuccess').classList.remove('d-none');
                    document.getElementById('feedbackError').classList.add('d-none');

                    // Hide comment section and buttons
                    document.getElementById('commentSection').classList.add('d-none');
                    document.getElementById('thumbsUpBtn').classList.add('d-none');
                    document.getElementById('thumbsDownBtn').classList.add('d-none');

                    // Show a thank you message
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
                    // Show error message
                    document.getElementById('feedbackError').classList.remove('d-none');
                    document.getElementById('feedbackSuccess').classList.add('d-none');
                }
            })
            .catch(error => {
                console.error('Error submitting feedback:', error);
                document.getElementById('feedbackError').classList.remove('d-none');
                document.getElementById('feedbackSuccess').classList.add('d-none');
            })
            .finally(() => {
                // Reset button state
                document.getElementById('submitCommentBtn').disabled = false;
                document.getElementById('submitCommentBtn').innerHTML = '<i class="fas fa-paper-plane mr-1"></i>Submit Feedback';
            });
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

    // Helper function to calculate approximate birth date from age
    function calculateBirthDate(age) {
        if (!age || age === 'N/A') {
            return '1970-01-01';
        }
        const currentYear = new Date().getFullYear();
        const birthYear = currentYear - parseInt(age);
        return `${birthYear}-01-01`;
    }

    // Helper function to extract bleeding risk percentage from recommendation text
    function extractBleedingRiskPercent(recommendation) {
        if (!recommendation) return 'N/A';
        const match = recommendation.match(/(\d+\.?\d*)%/);
        return match ? match[1] : 'N/A';
    }

    // Helper function to get parameter value from current data
    function getParameterValue(parameterName) {
        if (!currentPatientData || !currentPatientData.score_components) {
            return 'Not available';
        }

        const component = currentPatientData.score_components.find(c =>
            c.parameter.includes(parameterName)
        );

        if (!component) {
            return 'Not available';
        }

        // For CCD export, return only the numeric raw_value (CCD generator adds units)
        if (component.raw_value !== null && component.raw_value !== undefined) {
            return component.raw_value;
        }

        // For boolean values, return the is_present status
        if (component.is_present !== null && component.is_present !== undefined) {
            return component.is_present ? 'Present' : 'Absent';
        }

        return component.value || 'Not available';
    }

    // Helper function to extract ARC-HBR factors
    function getARCHBRFactors() {
        const factors = [];

        if (!currentPatientData || !currentPatientData.score_components) {
            return factors;
        }

        // Check for prior bleeding
        const priorBleeding = currentPatientData.score_components.find(c =>
            c.parameter.includes('Prior Bleeding')
        );
        if (priorBleeding && priorBleeding.value === true) {
            factors.push('Prior spontaneous bleeding requiring hospitalization or transfusion');
        }

        // Check for oral anticoagulation
        const oralAnticoag = currentPatientData.score_components.find(c =>
            c.parameter.includes('Oral Anticoagulation')
        );
        if (oralAnticoag && oralAnticoag.value === true) {
            factors.push('Long-term oral anticoagulation therapy');
        }

        // Check for other ARC-HBR factors
        const arcHBR = currentPatientData.score_components.find(c =>
            c.parameter.includes('ARC-HBR')
        );
        if (arcHBR && arcHBR.value === true) {
            factors.push('One or more ARC-HBR major or minor criteria');
        }

        return factors;
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
            warningModal.className = 'modal fade show';
            warningModal.style.display = 'block';
            warningModal.style.backgroundColor = 'rgba(0,0,0,0.5)';
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
                resetInactivityTimer(); // Reset the timer as if user was active
            });

            document.getElementById('logout-now-btn').addEventListener('click', function () {
                performLogout();
            });
        } else {
            warningModal.style.display = 'block';
        }
    }

    function closeWarningModal() {
        if (warningModal) {
            warningModal.style.display = 'none';
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
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const headers = csrfMeta ? { 'X-CSRFToken': csrfMeta.getAttribute('content') } : {};

        fetch('/logout', {
            method: 'POST',
            credentials: 'same-origin',
            headers: headers
        }).catch(function (err) {
            console.error('Logout request failed:', err);
        });
    }

    // Attach activity listeners
    activityEvents.forEach(function (eventName) {
        document.addEventListener(eventName, resetInactivityTimer, { passive: true });
    });

    // Start the countdown on page load
    startCountdown();
})();