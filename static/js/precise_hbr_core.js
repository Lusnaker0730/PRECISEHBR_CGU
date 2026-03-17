// ======================================================================
// PRECISE-HBR Core Utilities
// Single source of truth for scoring config, validation, unit conversion,
// clinical tooltips, and risk classification shared across all calculators.
//
// All clinical parameters are loaded from /api/config/scoring
// (backed by config/cdss_config.json). Hardcoded defaults serve as
// fallback only when the API is unreachable.
//
// IEC 62304 §5.3 — shared clinical calculation boundary
// ======================================================================
(function () {
    'use strict';

    // ------------------------------------------------------------------
    // Constants
    // ------------------------------------------------------------------

    // Complementary log-log calibration curve for 1-year BARC 3/5 risk
    // (from risk_classifier.py, validated against official calculator)
    var CLOGLOG_A = -5.3945;
    var CLOGLOG_B = 0.09725;

    // Clinical validation ranges (hard bounds that block calculation)
    var VALIDATION_RANGES = {
        Age: { min: 18, max: 120, warnMax: 100 },
        Hemoglobin: { min: 3, max: 22, warnMin: 7, warnMax: 18 },
        eGFR: { min: 0, max: 200, warnMax: 150 },
        WBC: { min: 0.1, max: 50, warnMin: 4, warnMax: 20 },
        Platelet: { min: 5, max: 1000, warnMin: 100, warnMax: 450 }
    };

    // PRECISE-HBR score thresholds for bleeding risk categorisation
    var RISK_THRESHOLDS = {
        NOT_HIGH: 22,
        HBR: 23,
        VERY_HBR: 27
    };

    // Hemoglobin conversion factor: 1 g/dL = 0.6206 mmol/L
    var HB_CONVERSION_FACTOR = 0.6206;

    // ------------------------------------------------------------------
    // Scoring config — default fallback
    // ------------------------------------------------------------------

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

    function validateScoringConfigResponse(config) {
        if (!config || typeof config !== 'object') return false;
        if (typeof config.base_score !== 'number') return false;
        if (!config.coefficients || typeof config.coefficients !== 'object') return false;
        var requiredCoefficients = ['age', 'hemoglobin', 'egfr', 'wbc'];
        for (var i = 0; i < requiredCoefficients.length; i++) {
            var key = requiredCoefficients[i];
            var coef = config.coefficients[key];
            if (!coef || typeof coef !== 'object') return false;
            if (typeof coef.threshold !== 'number' || typeof coef.coefficient !== 'number') return false;
        }
        if (!config.binary_scores || typeof config.binary_scores !== 'object') return false;
        return true;
    }

    /**
     * Fetch scoring config from /api/config/scoring.
     * Returns the config object (does NOT store it — consumers manage their own state).
     */
    async function fetchScoringConfig() {
        try {
            var response = await fetch('/api/config/scoring');
            if (!response.ok) {
                console.warn('PreciseHBRCore: scoring config API returned', response.status, '— using fallback');
                return getDefaultScoringConfig();
            }
            var configData = await response.json();
            if (!validateScoringConfigResponse(configData)) {
                console.warn('PreciseHBRCore: scoring config validation failed — using fallback');
                return getDefaultScoringConfig();
            }
            return configData;
        } catch (error) {
            console.warn('PreciseHBRCore: scoring config fetch error — using fallback:', error.message);
            return getDefaultScoringConfig();
        }
    }

    // ------------------------------------------------------------------
    // Clinical tooltips
    // ------------------------------------------------------------------

    function createClinicalTooltips() {
        return {
            'Age': {
                title: 'Age',
                content: 'Age is a continuous variable in the PRECISE-HBR model. It is truncated to the 30-80 years range during calculation; older age increases the score.',
                normalRange: 'Calculation Range: 30-80 years',
                riskFactors: 'Score Weight: +0.25 points per year increase'
            },
            'Hemoglobin': {
                title: 'Hemoglobin',
                content: 'Hemoglobin is a continuous variable in the PRECISE-HBR model. It is truncated to the 5-15 g/dL range during calculation; lower hemoglobin increases the score.',
                normalRange: 'Calculation Range: 5-15 g/dL',
                riskFactors: 'Score Weight: +2.5 points per 1 g/dL decrease'
            },
            'eGFR': {
                title: 'eGFR (Estimated Glomerular Filtration Rate)',
                content: 'eGFR is a continuous variable in the PRECISE-HBR model. It is truncated to the 5-100 mL/min range; lower kidney function increases the score.',
                normalRange: 'Calculation Range: 5-100 mL/min/1.73m\u00b2',
                riskFactors: 'Score Weight: +0.055 points per 1 mL/min decrease'
            },
            'White Blood Cell Count': {
                title: 'White Blood Cell Count',
                content: 'WBC count is a continuous variable in the PRECISE-HBR model. It is truncated to a maximum of 15 \u00d710\u00b3/\u00b5L; higher WBC increases the score.',
                normalRange: 'Calculation Range: 3-15 \u00d710\u00b3/\u00b5L',
                riskFactors: 'Score Weight: +0.8 points per 1 \u00d710\u00b3/\u00b5L increase'
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
                content: 'Platelets are key for coagulation. Low platelet count (<100\u00d710\u2079/L) impairs clotting ability, increasing risk of spontaneous and post-traumatic bleeding.',
                normalRange: '150-400 \u00d710\u2079/L',
                riskFactors: '<100 \u00d710\u2079/L is an ARC-HBR Major Criterion'
            },
            'Chronic bleeding diathesis': {
                title: 'Chronic Bleeding Diathesis',
                content: 'Refers to congenital or acquired coagulation disorders, such as Hemophilia, von Willebrand disease, etc.',
                normalRange: 'No coagulation disorder',
                riskFactors: 'ARC-HBR Major Criterion'
            },
            'Liver cirrhosis': {
                title: 'Liver Cirrhosis with Portal Hypertension',
                content: 'Cirrhosis reduces coagulation factor synthesis, while portal hypertension causes esophageal varices and hypersplenism.',
                normalRange: 'No cirrhosis',
                riskFactors: 'ARC-HBR Major Criterion'
            },
            'Active malignancy': {
                title: 'Active Malignancy',
                content: 'Active cancer (diagnosed or treated within past 12 months, excluding non-melanoma skin cancer) increases bleeding risk.',
                normalRange: 'No active malignancy',
                riskFactors: 'ARC-HBR Major Criterion'
            },
            'Chronic use of nsaids': {
                title: 'Chronic Use of NSAIDs or Corticosteroids',
                content: 'NSAIDs inhibit platelet function and damage gastric mucosa, increasing GI bleeding risk. Long-term steroids weaken vessel walls.',
                normalRange: 'No chronic use',
                riskFactors: 'ARC-HBR Minor Criterion'
            },
            'ARC-HBR Factors': {
                title: 'ARC-HBR Additional Factors',
                content: 'Presence of at least one of the remaining ARC-HBR elements: thrombocytopenia, bleeding diathesis, active malignancy, liver cirrhosis with portal hypertension, recent major surgery/trauma, chronic NSAIDs/corticosteroids.',
                normalRange: 'None present',
                riskFactors: '+3 points if \u22651 factor present'
            }
        };
    }

    /**
     * Update tooltip text with dynamic coefficient values from scoring config.
     * @param {Object} tooltips - mutable tooltips object (from createClinicalTooltips)
     * @param {Object} config - scoring config (from fetchScoringConfig)
     */
    function updateTooltipsWithConfig(tooltips, config) {
        if (!config || !config.coefficients) return;
        var c = config.coefficients;
        if (tooltips['Age'] && c.age) {
            tooltips['Age'].riskFactors =
                'Score Weight: +' + c.age.coefficient + ' points per year increase';
            tooltips['Age'].normalRange =
                'Calculation Range: ' + c.age.truncation_min + '-' + c.age.truncation_max + ' years';
        }
        if (tooltips['Hemoglobin'] && c.hemoglobin) {
            tooltips['Hemoglobin'].riskFactors =
                'Score Weight: +' + c.hemoglobin.coefficient + ' points per 1 g/dL decrease';
            tooltips['Hemoglobin'].normalRange =
                'Calculation Range: ' + c.hemoglobin.truncation_min + '-' + c.hemoglobin.truncation_max + ' g/dL';
        }
        if (tooltips['eGFR'] && c.egfr) {
            tooltips['eGFR'].riskFactors =
                'Score Weight: +' + c.egfr.coefficient + ' points per 1 mL/min decrease';
        }
        if (tooltips['White Blood Cell Count'] && c.wbc) {
            tooltips['White Blood Cell Count'].riskFactors =
                'Score Weight: +' + c.wbc.coefficient + ' points per 1 \u00d710\u00b3/\u00b5L increase';
        }
    }

    // ------------------------------------------------------------------
    // Validation — identical to main.js
    // ------------------------------------------------------------------

    /**
     * Validate a clinical input value.
     * @param {string} parameterName - parameter name (may use .includes() matching)
     * @param {*} value - raw input value
     * @param {Object} [unitSettings] - optional, e.g. { hemoglobin: 'mmol/L' }
     * @returns {{ valid: boolean, level: string, message: string, blockCalculation: boolean }}
     */
    function validateValue(parameterName, value, unitSettings) {
        var numValue = parseFloat(value);
        if (isNaN(numValue)) return { valid: true, level: 'normal', message: '', blockCalculation: false };

        var result = { valid: true, level: 'normal', message: '', blockCalculation: false };

        if (parameterName.includes('Age')) {
            var range = VALIDATION_RANGES.Age;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = 'Age must be between ' + range.min + ' and ' + range.max + ' years';
                result.blockCalculation = true;
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Age exceeds typical range (>100 years)';
            } else if (numValue >= 75) {
                result.level = 'warning';
                result.message = 'Elderly patient (\u226575 years) - increased bleeding risk';
            }
        } else if (parameterName.includes('Hemoglobin')) {
            var range = VALIDATION_RANGES.Hemoglobin;
            var unit = (unitSettings && unitSettings.hemoglobin) || 'g/dL';
            var factor = unit === 'mmol/L' ? HB_CONVERSION_FACTOR : 1;
            var min = range.min * factor;
            var max = range.max * factor;
            var warnMin = range.warnMin * factor;
            var warnMax = range.warnMax * factor;
            if (numValue < min || numValue > max) {
                result.level = 'error';
                result.message = 'Hemoglobin must be between ' + min.toFixed(1) + ' and ' + max.toFixed(1) + ' ' + unit;
                result.blockCalculation = true;
            } else if (numValue < warnMin) {
                result.level = 'warning';
                result.message = 'Low hemoglobin (<' + warnMin.toFixed(1) + ' ' + unit + ') - Anemia';
            } else if (numValue > warnMax) {
                result.level = 'warning';
                result.message = 'Elevated hemoglobin (>' + warnMax.toFixed(1) + ' ' + unit + ')';
            }
        } else if (parameterName.includes('eGFR')) {
            var range = VALIDATION_RANGES.eGFR;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = 'eGFR must be between ' + range.min + ' and ' + range.max + ' mL/min';
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
        } else if (parameterName.includes('White Blood Cell') || parameterName.includes('WBC')) {
            var range = VALIDATION_RANGES.WBC;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = 'WBC must be between ' + range.min + ' and ' + range.max + ' \u00d710\u00b3/\u00b5L';
                result.blockCalculation = true;
            } else if (numValue < range.warnMin) {
                result.level = 'warning';
                result.message = 'Low WBC (<4 \u00d710\u00b3/\u00b5L) - Leukopenia';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Elevated WBC (>20 \u00d710\u00b3/\u00b5L) - Leukocytosis';
            }
        } else if (parameterName.includes('Platelet')) {
            var range = VALIDATION_RANGES.Platelet;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = 'Platelet must be between ' + range.min + ' and ' + range.max + ' \u00d710\u2079/L';
                result.blockCalculation = true;
            } else if (numValue < range.warnMin) {
                result.level = 'warning';
                result.message = 'Thrombocytopenia (<100 \u00d710\u2079/L) - High bleeding risk';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Thrombocytosis (>450 \u00d710\u2079/L)';
            }
        }

        return result;
    }

    function applyValidationStyling(inputElement, validation) {
        inputElement.classList.remove('value-normal', 'value-warning', 'value-error');

        if (validation.level === 'error') {
            inputElement.classList.add('value-error');
        } else if (validation.level === 'warning') {
            inputElement.classList.add('value-warning');
        } else {
            inputElement.classList.add('value-normal');
        }

        // Always append the validation message inside the <td> containing the input
        var container = inputElement.closest('td') || inputElement.parentElement;

        var existingMessages = container.querySelectorAll('.validation-message');
        existingMessages.forEach(function (msg) { msg.remove(); });

        if (validation.message) {
            var messageDiv = document.createElement('div');
            messageDiv.className = 'validation-message small mt-1';
            messageDiv.textContent = validation.message;
            if (validation.level === 'error') messageDiv.classList.add('text-danger');
            if (validation.level === 'warning') messageDiv.classList.add('text-warning');
            container.appendChild(messageDiv);
        }
    }

    // ------------------------------------------------------------------
    // Unit conversion
    // ------------------------------------------------------------------

    function convertHemoglobin(value, fromUnit, toUnit) {
        if (fromUnit === toUnit) return value;
        if (fromUnit === 'g/dL' && toUnit === 'mmol/L') return value * HB_CONVERSION_FACTOR;
        if (fromUnit === 'mmol/L' && toUnit === 'g/dL') return value / HB_CONVERSION_FACTOR;
        return value;
    }

    // ------------------------------------------------------------------
    // Risk percentage (cloglog)
    // ------------------------------------------------------------------

    function calculateRiskPercent(score) {
        var lp = CLOGLOG_A + CLOGLOG_B * score;
        var risk = 1.0 - Math.exp(-Math.exp(lp));
        return (risk * 100).toFixed(2);
    }

    // ------------------------------------------------------------------
    // Security: HTML escape
    // ------------------------------------------------------------------

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        var div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    window.PreciseHBRCore = {
        // Constants
        CLOGLOG_A: CLOGLOG_A,
        CLOGLOG_B: CLOGLOG_B,
        VALIDATION_RANGES: VALIDATION_RANGES,
        RISK_THRESHOLDS: RISK_THRESHOLDS,
        HB_CONVERSION_FACTOR: HB_CONVERSION_FACTOR,

        // Config
        getDefaultScoringConfig: getDefaultScoringConfig,
        validateScoringConfigResponse: validateScoringConfigResponse,
        fetchScoringConfig: fetchScoringConfig,

        // Tooltips
        createClinicalTooltips: createClinicalTooltips,
        updateTooltipsWithConfig: updateTooltipsWithConfig,

        // Validation
        validateValue: validateValue,
        applyValidationStyling: applyValidationStyling,

        // Conversion & risk
        convertHemoglobin: convertHemoglobin,
        calculateRiskPercent: calculateRiskPercent,

        // Security
        escapeHtml: escapeHtml
    };
})();
