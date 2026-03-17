// PRECISE-HBR Standalone Calculator
// Reuses the SAME scoring config, validation ranges, unit conversion,
// and clinical tooltips as main.js to ensure consistency.
// All coefficients are loaded from /api/config/scoring (cdss_config.json).
(function () {
    'use strict';

    // ======================================================================
    // Shared state — mirrors main.js
    // ======================================================================
    let scoringConfig = null;

    let unitSettings = {
        hemoglobin: 'g/dL' // or 'mmol/L'
    };

    // Complementary log-log calibration curve (from risk_classifier.py)
    const CLOGLOG_A = -5.3945;
    const CLOGLOG_B = 0.09725;

    // ======================================================================
    // Scoring config — IDENTICAL to main.js
    // ======================================================================
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

    function validateScoringConfigResponse(data) {
        if (!data || typeof data !== 'object') return false;
        if (!data.coefficients || typeof data.coefficients !== 'object') return false;
        if (!data.binary_scores || typeof data.binary_scores !== 'object') return false;
        const requiredCoeffs = ['age', 'hemoglobin', 'egfr', 'wbc'];
        for (const key of requiredCoeffs) {
            const c = data.coefficients[key];
            if (!c || typeof c.coefficient !== 'number' || typeof c.threshold !== 'number') return false;
        }
        return true;
    }

    async function fetchScoringConfig() {
        try {
            const response = await fetch('/api/config/scoring');
            if (!response.ok) {
                scoringConfig = getDefaultScoringConfig();
                return scoringConfig;
            }
            const configData = await response.json();
            if (!validateScoringConfigResponse(configData)) {
                scoringConfig = getDefaultScoringConfig();
                return scoringConfig;
            }
            scoringConfig = configData;
            updateTooltipsWithConfig();
            return scoringConfig;
        } catch (error) {
            scoringConfig = getDefaultScoringConfig();
            return scoringConfig;
        }
    }

    // ======================================================================
    // Clinical tooltips — IDENTICAL to main.js
    // ======================================================================
    const clinicalTooltips = {
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
            content: 'History of spontaneous bleeding is the strongest predictor of future bleeding.',
            normalRange: 'No history of bleeding',
            riskFactors: 'Significant risk increase (+7 points)'
        },
        'Long-term oral anticoagulation': {
            title: 'Long-term Oral Anticoagulation',
            content: 'Long-term use of oral anticoagulants (e.g., Warfarin, DOACs) significantly increases bleeding risk.',
            normalRange: 'Not used',
            riskFactors: 'ARC-HBR Major Criterion (+5 points)'
        },
        'ARC-HBR Factors': {
            title: 'ARC-HBR Additional Factors',
            content: 'Presence of at least one of the remaining ARC-HBR elements: thrombocytopenia, bleeding diathesis, active malignancy, liver cirrhosis with portal hypertension, recent major surgery/trauma, chronic NSAIDs/corticosteroids.',
            normalRange: 'None present',
            riskFactors: '+3 points if \u22651 factor present'
        }
    };

    function updateTooltipsWithConfig() {
        if (!scoringConfig) return;
        const c = scoringConfig.coefficients;
        if (clinicalTooltips['Age'] && c.age) {
            clinicalTooltips['Age'].riskFactors =
                `Score Weight: +${c.age.coefficient} points per year increase`;
            clinicalTooltips['Age'].normalRange =
                `Calculation Range: ${c.age.truncation_min}-${c.age.truncation_max} years`;
        }
        if (clinicalTooltips['Hemoglobin'] && c.hemoglobin) {
            clinicalTooltips['Hemoglobin'].riskFactors =
                `Score Weight: +${c.hemoglobin.coefficient} points per 1 g/dL decrease`;
            clinicalTooltips['Hemoglobin'].normalRange =
                `Calculation Range: ${c.hemoglobin.truncation_min}-${c.hemoglobin.truncation_max} g/dL`;
        }
        if (clinicalTooltips['eGFR'] && c.egfr) {
            clinicalTooltips['eGFR'].riskFactors =
                `Score Weight: +${c.egfr.coefficient} points per 1 mL/min decrease`;
        }
        if (clinicalTooltips['White Blood Cell Count'] && c.wbc) {
            clinicalTooltips['White Blood Cell Count'].riskFactors =
                `Score Weight: +${c.wbc.coefficient} points per 1 \u00d710\u00b3/\u00b5L increase`;
        }
    }

    // ======================================================================
    // Validation ranges — IDENTICAL to main.js
    // ======================================================================
    const VALIDATION_RANGES = {
        Age: { min: 18, max: 120, warnMax: 100 },
        Hemoglobin: { min: 3, max: 22, warnMin: 7, warnMax: 18 },
        eGFR: { min: 0, max: 200, warnMax: 150 },
        WBC: { min: 0.1, max: 50, warnMin: 4, warnMax: 20 }
    };

    const RISK_THRESHOLDS = {
        NOT_HIGH: 22,
        HBR: 23,
        VERY_HBR: 27
    };

    // validateValue — IDENTICAL to main.js
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
                result.message = 'Elderly patient (\u226575 years) - increased bleeding risk';
            }
        } else if (parameterName.includes("Hemoglobin")) {
            const range = VALIDATION_RANGES.Hemoglobin;
            const unit = unitSettings.hemoglobin || 'g/dL';
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
        } else if (parameterName.includes("WBC") || parameterName.includes("White Blood Cell")) {
            const range = VALIDATION_RANGES.WBC;
            if (numValue < range.min || numValue > range.max) {
                result.level = 'error';
                result.message = `WBC must be between ${range.min} and ${range.max} \u00d710\u00b3/\u00b5L`;
                result.blockCalculation = true;
            } else if (numValue < range.warnMin) {
                result.level = 'warning';
                result.message = 'Low WBC (<4 \u00d710\u00b3/\u00b5L) - Leukopenia';
            } else if (numValue > range.warnMax) {
                result.level = 'warning';
                result.message = 'Elevated WBC (>20 \u00d710\u00b3/\u00b5L) - Leukocytosis';
            }
        }

        return result;
    }

    // applyValidationStyling — IDENTICAL to main.js
    function applyValidationStyling(inputElement, validation) {
        inputElement.classList.remove('value-normal', 'value-warning', 'value-error');

        if (validation.level === 'error') {
            inputElement.classList.add('value-error');
        } else if (validation.level === 'warning') {
            inputElement.classList.add('value-warning');
        } else {
            inputElement.classList.add('value-normal');
        }

        const inputGroup = inputElement.closest('.input-group') || inputElement.parentElement;
        const container = inputGroup.parentElement;

        const existingMessages = container.querySelectorAll('.validation-message');
        existingMessages.forEach(msg => msg.remove());

        if (validation.message) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'validation-message';
            messageDiv.textContent = validation.message;
            if (validation.level === 'error') messageDiv.classList.add('text-danger');
            if (validation.level === 'warning') messageDiv.classList.add('text-warning');
            container.appendChild(messageDiv);
        }
    }

    // ======================================================================
    // Hemoglobin unit conversion — IDENTICAL to main.js
    // ======================================================================
    function convertHemoglobin(value, fromUnit, toUnit) {
        if (fromUnit === toUnit) return value;
        if (fromUnit === 'g/dL' && toUnit === 'mmol/L') return value * 0.6206;
        if (fromUnit === 'mmol/L' && toUnit === 'g/dL') return value / 0.6206;
        return value;
    }

    function toggleHemoglobinUnit() {
        const input = document.getElementById('input-hb');
        const currentValue = parseFloat(input.value);
        const currentUnit = unitSettings.hemoglobin;
        const newUnit = currentUnit === 'g/dL' ? 'mmol/L' : 'g/dL';

        if (!isNaN(currentValue)) {
            const newValue = convertHemoglobin(currentValue, currentUnit, newUnit);
            input.value = newValue.toFixed(2);
        }

        unitSettings.hemoglobin = newUnit;

        // Update unit displays
        const unitSpan = document.getElementById('hb-unit-display');
        if (unitSpan) unitSpan.textContent = newUnit;
        const unitLabel = document.getElementById('hb-unit-label');
        if (unitLabel) unitLabel.textContent = '(' + newUnit + ')';

        recalculate();
    }

    // ======================================================================
    // Tooltip rendering
    // ======================================================================
    function renderTooltip(key) {
        const tip = clinicalTooltips[key];
        if (!tip) return '';
        return ` <span class="text-muted" tabindex="0" role="button"
            data-bs-toggle="popover" data-bs-trigger="hover focus"
            data-bs-html="true" data-bs-placement="right"
            title="${escapeHtml(tip.title)}"
            data-bs-content="<p>${escapeHtml(tip.content)}</p><p><strong>Normal:</strong> ${escapeHtml(tip.normalRange)}</p><p><strong>Risk:</strong> ${escapeHtml(tip.riskFactors)}</p>">
            <i class="fas fa-info-circle"></i></span>`;
    }

    function initPopovers() {
        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        popoverTriggerList.forEach(el => {
            new bootstrap.Popover(el);
        });
    }

    // ======================================================================
    // Score calculation — uses scoringConfig from /api/config/scoring
    // ======================================================================
    function recalculate() {
        const cfg = scoringConfig;
        if (!cfg) return;

        const c = cfg.coefficients;
        const b = cfg.binary_scores;

        // Validate all inputs first
        let blocked = false;
        const inputs = [
            { id: 'input-age', param: 'Age' },
            { id: 'input-hb', param: 'Hemoglobin' },
            { id: 'input-egfr', param: 'eGFR' },
            { id: 'input-wbc', param: 'White Blood Cell Count' }
        ];

        inputs.forEach(function (item) {
            const el = document.getElementById(item.id);
            if (el && el.value) {
                const v = validateValue(item.param, el.value);
                applyValidationStyling(el, v);
                if (v.blockCalculation) blocked = true;
            } else if (el) {
                // Clear validation when empty
                applyValidationStyling(el, { level: 'normal', message: '' });
            }
        });

        let total = cfg.base_score;

        // Age
        const ageRaw = parseFloat(document.getElementById('input-age').value);
        let ageScore = 0;
        if (!isNaN(ageRaw)) {
            const ageCfg = c.age;
            const eff = Math.max(ageCfg.truncation_min, Math.min(ageCfg.truncation_max, ageRaw));
            if (eff > ageCfg.threshold) {
                ageScore = (eff - ageCfg.threshold) * ageCfg.coefficient;
            }
        }
        total += ageScore;
        document.getElementById('score-age').textContent = ageScore.toFixed(1);

        // Hemoglobin (convert to g/dL if in mmol/L)
        const hbRaw = parseFloat(document.getElementById('input-hb').value);
        let hbScore = 0;
        if (!isNaN(hbRaw)) {
            let hbGdl = hbRaw;
            if (unitSettings.hemoglobin === 'mmol/L') {
                hbGdl = convertHemoglobin(hbRaw, 'mmol/L', 'g/dL');
            }
            const hbCfg = c.hemoglobin;
            const eff = Math.max(hbCfg.truncation_min, Math.min(hbCfg.truncation_max, hbGdl));
            if (eff < hbCfg.threshold) {
                hbScore = (hbCfg.threshold - eff) * hbCfg.coefficient;
            }
        }
        total += hbScore;
        document.getElementById('score-hb').textContent = hbScore.toFixed(1);

        // eGFR
        const egfrRaw = parseFloat(document.getElementById('input-egfr').value);
        let egfrScore = 0;
        if (!isNaN(egfrRaw)) {
            const egfrCfg = c.egfr;
            const eff = Math.max(egfrCfg.truncation_min, Math.min(egfrCfg.truncation_max, egfrRaw));
            if (eff < egfrCfg.threshold) {
                egfrScore = (egfrCfg.threshold - eff) * egfrCfg.coefficient;
            }
        }
        total += egfrScore;
        document.getElementById('score-egfr').textContent = egfrScore.toFixed(1);

        // WBC
        const wbcRaw = parseFloat(document.getElementById('input-wbc').value);
        let wbcScore = 0;
        if (!isNaN(wbcRaw)) {
            const wbcCfg = c.wbc;
            const eff = Math.max(wbcCfg.truncation_min, Math.min(wbcCfg.truncation_max, wbcRaw));
            if (eff > wbcCfg.threshold) {
                wbcScore = (eff - wbcCfg.threshold) * wbcCfg.coefficient;
            }
        }
        total += wbcScore;
        document.getElementById('score-wbc').textContent = wbcScore.toFixed(1);

        // Binary factors
        const bleedingScore = document.getElementById('input-bleeding').checked ? b.prior_bleeding : 0;
        const oacScore = document.getElementById('input-oac').checked ? b.oral_anticoagulation : 0;
        const arcScore = document.getElementById('input-arc').checked ? b.arc_hbr : 0;

        total += bleedingScore + oacScore + arcScore;

        document.getElementById('score-bleeding').textContent = bleedingScore;
        document.getElementById('score-oac').textContent = oacScore;
        document.getElementById('score-arc').textContent = arcScore;

        // Round (same as main.js: Math.round)
        const finalScore = Math.round(total);

        if (blocked) {
            document.getElementById('total-score').textContent = '--';
            document.getElementById('total-score').className = 'display-3 fw-bold text-muted';
            document.getElementById('risk-level').innerHTML =
                '<span class="badge bg-secondary">Invalid input</span>';
            document.getElementById('risk-percent').textContent = '';
            document.getElementById('recommendation').textContent =
                'Please correct the highlighted values above.';
            document.getElementById('hbr-recommendations-section').classList.add('d-none');
            return;
        }

        updateScoreDisplay(finalScore);
    }

    // ======================================================================
    // Risk % — cloglog from risk_classifier.py
    // ======================================================================
    function calculateRiskPercent(score) {
        const lp = CLOGLOG_A + CLOGLOG_B * score;
        const risk = 1.0 - Math.exp(-Math.exp(lp));
        return (risk * 100).toFixed(2);
    }

    // ======================================================================
    // UI update — mirrors updateTotalScoreUI from main.js
    // ======================================================================
    function updateScoreDisplay(score) {
        const totalEl = document.getElementById('total-score');
        const riskEl = document.getElementById('risk-level');
        const riskPctEl = document.getElementById('risk-percent');
        const recommendEl = document.getElementById('recommendation');
        const hbrSection = document.getElementById('hbr-recommendations-section');

        totalEl.textContent = score;

        const riskPct = calculateRiskPercent(score);

        let category, colorClass, scoreRange, scoreColor;
        if (score <= RISK_THRESHOLDS.NOT_HIGH) {
            category = 'Not high bleeding risk';
            colorClass = 'bg-success';
            scoreRange = `(score \u2264${RISK_THRESHOLDS.NOT_HIGH})`;
            scoreColor = 'text-success';
        } else if (score < RISK_THRESHOLDS.VERY_HBR) {
            category = 'High bleeding risk (HBR)';
            colorClass = 'bg-warning text-dark';
            scoreRange = `(score ${RISK_THRESHOLDS.HBR}\u2013${RISK_THRESHOLDS.VERY_HBR - 1})`;
            scoreColor = 'text-warning';
        } else {
            category = 'Very high bleeding risk';
            colorClass = 'bg-danger';
            scoreRange = `(score \u2265${RISK_THRESHOLDS.VERY_HBR})`;
            scoreColor = 'text-danger';
        }

        riskEl.innerHTML = '<span class="badge ' + colorClass + '">' +
            escapeHtml(category) + '</span> <small class="text-muted">' +
            escapeHtml(scoreRange) + '</small>';

        riskPctEl.textContent = '1-year risk of major bleeding (BARC 3/5): ' + riskPct + '%';

        recommendEl.textContent = score <= RISK_THRESHOLDS.NOT_HIGH
            ? 'Standard DAPT duration per guidelines.'
            : 'Consider abbreviated DAPT or de-escalation strategy.';

        // Show/hide HBR recommendations
        if (score >= RISK_THRESHOLDS.HBR) {
            hbrSection.classList.remove('d-none');
        } else {
            hbrSection.classList.add('d-none');
        }

        totalEl.className = 'display-3 fw-bold ' + scoreColor;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // ======================================================================
    // Initialisation
    // ======================================================================
    async function init() {
        await fetchScoringConfig();

        // Add tooltips to parameter labels
        const tooltipTargets = {
            'input-age': 'Age',
            'input-hb': 'Hemoglobin',
            'input-egfr': 'eGFR',
            'input-wbc': 'White Blood Cell Count',
            'input-bleeding': 'Previous bleeding',
            'input-oac': 'Long-term oral anticoagulation',
            'input-arc': 'ARC-HBR Factors'
        };

        Object.entries(tooltipTargets).forEach(([inputId, tooltipKey]) => {
            const input = document.getElementById(inputId);
            if (input) {
                const td = input.closest('tr').querySelector('td:first-child');
                if (td) {
                    td.insertAdjacentHTML('beforeend', renderTooltip(tooltipKey));
                }
            }
        });

        initPopovers();

        // Update base score display from config
        const baseScoreEl = document.getElementById('score-base');
        if (baseScoreEl && scoringConfig) {
            baseScoreEl.textContent = scoringConfig.base_score;
        }

        // Bind input listeners — 'input' for number fields, 'change' for checkboxes
        document.querySelectorAll('#score-components input').forEach(function (input) {
            if (input.type === 'checkbox') {
                input.addEventListener('change', recalculate);
            } else {
                input.addEventListener('input', recalculate);
            }
        });

        // Bind Hb unit toggle
        const toggleBtn = document.getElementById('hb-unit-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleHemoglobinUnit);
        }

        // Initial calculation
        recalculate();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
