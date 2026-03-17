// PRECISE-HBR Standalone Calculator
// Client-side scoring without FHIR/patient context
(function () {
    'use strict';

    // Scoring configuration — loaded from backend, with local fallback
    var scoringConfig = null;

    // Current hemoglobin unit
    var hbUnit = 'g/dL';
    var HB_CONVERSION_FACTOR = 0.6206; // 1 g/dL = 0.6206 mmol/L

    // Complementary log-log calibration curve for 1-year BARC 3/5 risk
    var CLOGLOG_A = -5.3945;
    var CLOGLOG_B = 0.09725;

    // Risk thresholds
    var THRESHOLD_NON_HBR = 22;
    var THRESHOLD_HBR = 26;

    // Validation ranges (matching main.js)
    var VALIDATION_RANGES = {
        Age: { min: 18, max: 120, warnMax: 100 },
        Hemoglobin: { min: 3, max: 22, warnMin: 7, warnMax: 18 },  // g/dL
        eGFR: { min: 0, max: 200, warnMax: 150 },
        WBC: { min: 0.1, max: 50, warnMin: 4, warnMax: 20 }
    };

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

    async function fetchScoringConfig() {
        try {
            var response = await fetch('/api/config/scoring');
            if (response.ok) {
                scoringConfig = await response.json();
            } else {
                scoringConfig = getDefaultScoringConfig();
            }
        } catch (e) {
            scoringConfig = getDefaultScoringConfig();
        }
        return scoringConfig;
    }

    // === Validation ===

    function validateInput(inputId, paramName) {
        var el = document.getElementById(inputId);
        var value = parseFloat(el.value);
        var feedbackEl = el.closest('td').querySelector('.validation-feedback');

        // Clear previous feedback
        el.classList.remove('is-invalid', 'is-warning');
        if (feedbackEl) feedbackEl.remove();

        if (el.value === '' || isNaN(value)) {
            return { valid: true, blockCalculation: false };
        }

        var result = validateValue(paramName, value);

        if (result.level === 'error') {
            el.classList.add('is-invalid');
            addFeedback(el, result.message, 'text-danger');
        } else if (result.level === 'warning') {
            el.classList.add('is-warning');
            addFeedback(el, result.message, 'text-warning');
        }

        return result;
    }

    function validateValue(paramName, value) {
        var result = { valid: true, level: 'normal', message: '', blockCalculation: false };

        if (paramName === 'Age') {
            var r = VALIDATION_RANGES.Age;
            if (value < r.min || value > r.max) {
                result.level = 'error';
                result.message = 'Age must be between ' + r.min + ' and ' + r.max + ' years';
                result.blockCalculation = true;
            } else if (value > r.warnMax) {
                result.level = 'warning';
                result.message = 'Age exceeds typical range (>100 years)';
            } else if (value >= 75) {
                result.level = 'warning';
                result.message = 'Elderly patient (\u226575 years) \u2014 increased bleeding risk';
            }
        } else if (paramName === 'Hemoglobin') {
            var r = VALIDATION_RANGES.Hemoglobin;
            var factor = hbUnit === 'mmol/L' ? HB_CONVERSION_FACTOR : 1;
            var min = r.min * factor, max = r.max * factor;
            var warnMin = r.warnMin * factor, warnMax = r.warnMax * factor;
            if (value < min || value > max) {
                result.level = 'error';
                result.message = 'Hemoglobin must be between ' + min.toFixed(1) + ' and ' + max.toFixed(1) + ' ' + hbUnit;
                result.blockCalculation = true;
            } else if (value < warnMin) {
                result.level = 'warning';
                result.message = 'Low hemoglobin (<' + warnMin.toFixed(1) + ' ' + hbUnit + ') \u2014 Anemia';
            } else if (value > warnMax) {
                result.level = 'warning';
                result.message = 'Elevated hemoglobin (>' + warnMax.toFixed(1) + ' ' + hbUnit + ')';
            }
        } else if (paramName === 'eGFR') {
            var r = VALIDATION_RANGES.eGFR;
            if (value < r.min || value > r.max) {
                result.level = 'error';
                result.message = 'eGFR must be between ' + r.min + ' and ' + r.max + ' mL/min';
                result.blockCalculation = true;
            } else if (value < 15) {
                result.level = 'warning';
                result.message = 'Severe renal impairment (<15) \u2014 Very high risk';
            } else if (value < 30) {
                result.level = 'warning';
                result.message = 'Severe renal impairment (<30) \u2014 High risk';
            } else if (value < 60) {
                result.level = 'warning';
                result.message = 'Moderate renal impairment (30\u201360)';
            } else if (value > r.warnMax) {
                result.level = 'warning';
                result.message = 'eGFR unusually high (>150) \u2014 Please verify';
            }
        } else if (paramName === 'WBC') {
            var r = VALIDATION_RANGES.WBC;
            if (value < r.min || value > r.max) {
                result.level = 'error';
                result.message = 'WBC must be between ' + r.min + ' and ' + r.max + ' \u00d710\u00b3/\u00b5L';
                result.blockCalculation = true;
            } else if (value < r.warnMin) {
                result.level = 'warning';
                result.message = 'Low WBC (<4) \u2014 Leukopenia';
            } else if (value > r.warnMax) {
                result.level = 'warning';
                result.message = 'Elevated WBC (>20) \u2014 Leukocytosis';
            }
        }
        return result;
    }

    function addFeedback(inputEl, message, cssClass) {
        var div = document.createElement('div');
        div.className = 'validation-feedback small mt-1 ' + cssClass;
        div.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + escapeHtml(message);
        inputEl.closest('td').appendChild(div);
    }

    function hasValidationErrors() {
        var validations = [
            validateInput('input-age', 'Age'),
            validateInput('input-hb', 'Hemoglobin'),
            validateInput('input-egfr', 'eGFR'),
            validateInput('input-wbc', 'WBC')
        ];
        return validations.some(function (v) { return v.blockCalculation; });
    }

    // === Hemoglobin unit conversion ===

    function toggleHbUnit() {
        var input = document.getElementById('input-hb');
        var currentValue = parseFloat(input.value);
        var newUnit = hbUnit === 'g/dL' ? 'mmol/L' : 'g/dL';

        if (!isNaN(currentValue)) {
            if (hbUnit === 'g/dL' && newUnit === 'mmol/L') {
                input.value = (currentValue * HB_CONVERSION_FACTOR).toFixed(2);
            } else {
                input.value = (currentValue / HB_CONVERSION_FACTOR).toFixed(2);
            }
        }

        hbUnit = newUnit;
        document.getElementById('hb-unit-display').textContent = newUnit;
        document.getElementById('hb-unit-label').textContent = '(' + newUnit + ')';

        calculateScore();
    }

    // === Score calculation ===

    function calculateScore() {
        var cfg = scoringConfig;
        if (!cfg) return;

        // Run validation
        var blocked = hasValidationErrors();

        var c = cfg.coefficients;
        var b = cfg.binary_scores;
        var total = cfg.base_score;

        // Age
        var ageRaw = parseFloat(document.getElementById('input-age').value);
        var ageScore = 0;
        if (!isNaN(ageRaw)) {
            var eff = Math.max(c.age.truncation_min, Math.min(c.age.truncation_max, ageRaw));
            if (eff > c.age.threshold) {
                ageScore = (eff - c.age.threshold) * c.age.coefficient;
            }
        }
        total += ageScore;
        document.getElementById('score-age').textContent = ageScore.toFixed(1);

        // Hemoglobin (convert to g/dL if in mmol/L)
        var hbRaw = parseFloat(document.getElementById('input-hb').value);
        var hbScore = 0;
        if (!isNaN(hbRaw)) {
            var hbGdl = hbUnit === 'mmol/L' ? hbRaw / HB_CONVERSION_FACTOR : hbRaw;
            var eff = Math.max(c.hemoglobin.truncation_min, Math.min(c.hemoglobin.truncation_max, hbGdl));
            if (eff < c.hemoglobin.threshold) {
                hbScore = (c.hemoglobin.threshold - eff) * c.hemoglobin.coefficient;
            }
        }
        total += hbScore;
        document.getElementById('score-hb').textContent = hbScore.toFixed(1);

        // eGFR
        var egfrRaw = parseFloat(document.getElementById('input-egfr').value);
        var egfrScore = 0;
        if (!isNaN(egfrRaw)) {
            var eff = Math.max(c.egfr.truncation_min, Math.min(c.egfr.truncation_max, egfrRaw));
            if (eff < c.egfr.threshold) {
                egfrScore = (c.egfr.threshold - eff) * c.egfr.coefficient;
            }
        }
        total += egfrScore;
        document.getElementById('score-egfr').textContent = egfrScore.toFixed(1);

        // WBC
        var wbcRaw = parseFloat(document.getElementById('input-wbc').value);
        var wbcScore = 0;
        if (!isNaN(wbcRaw)) {
            var eff = Math.max(c.wbc.truncation_min, Math.min(c.wbc.truncation_max, wbcRaw));
            if (eff > c.wbc.threshold) {
                wbcScore = (eff - c.wbc.threshold) * c.wbc.coefficient;
            }
        }
        total += wbcScore;
        document.getElementById('score-wbc').textContent = wbcScore.toFixed(1);

        // Binary factors
        var bleedingScore = document.getElementById('input-bleeding').checked ? b.prior_bleeding : 0;
        var oacScore = document.getElementById('input-oac').checked ? b.oral_anticoagulation : 0;
        var arcScore = document.getElementById('input-arc').checked ? b.arc_hbr : 0;

        total += bleedingScore + oacScore + arcScore;

        document.getElementById('score-bleeding').textContent = bleedingScore;
        document.getElementById('score-oac').textContent = oacScore;
        document.getElementById('score-arc').textContent = arcScore;

        // Round total
        var roundedTotal = Math.floor(total + 0.5);

        if (blocked) {
            document.getElementById('total-score').textContent = '--';
            document.getElementById('total-score').className = 'display-3 fw-bold text-muted';
            document.getElementById('risk-level').innerHTML = '<span class="badge bg-secondary">Invalid input</span>';
            document.getElementById('risk-percent').textContent = '';
            document.getElementById('recommendation').textContent = 'Please correct the highlighted values above.';
            document.getElementById('hbr-recommendations-section').classList.add('d-none');
            return;
        }

        updateScoreDisplay(roundedTotal);
    }

    function calculateRiskPercent(score) {
        var lp = CLOGLOG_A + CLOGLOG_B * score;
        var risk = 1.0 - Math.exp(-Math.exp(lp));
        return (risk * 100).toFixed(2);
    }

    function updateScoreDisplay(score) {
        var totalEl = document.getElementById('total-score');
        var riskEl = document.getElementById('risk-level');
        var riskPctEl = document.getElementById('risk-percent');
        var recommendEl = document.getElementById('recommendation');
        var hbrSection = document.getElementById('hbr-recommendations-section');

        totalEl.textContent = score;

        var riskPct = calculateRiskPercent(score);

        var category, colorClass, scoreRange;
        if (score <= THRESHOLD_NON_HBR) {
            category = 'Not high bleeding risk';
            colorClass = 'bg-success';
            scoreRange = '(score \u226422)';
        } else if (score <= THRESHOLD_HBR) {
            category = 'High bleeding risk (HBR)';
            colorClass = 'bg-warning text-dark';
            scoreRange = '(score 23\u201326)';
        } else {
            category = 'Very high bleeding risk';
            colorClass = 'bg-danger';
            scoreRange = '(score \u226527)';
        }

        riskEl.innerHTML = '<span class="badge ' + colorClass + '">' +
            escapeHtml(category) + '</span> <small class="text-muted">' +
            escapeHtml(scoreRange) + '</small>';

        riskPctEl.textContent = '1-year risk of major bleeding (BARC 3/5): ' + riskPct + '%';

        recommendEl.textContent = score <= THRESHOLD_NON_HBR
            ? 'Standard DAPT duration per guidelines.'
            : 'Consider abbreviated DAPT or de-escalation strategy.';

        // Show/hide HBR recommendations
        if (score >= THRESHOLD_NON_HBR + 1) {
            hbrSection.classList.remove('d-none');
        } else {
            hbrSection.classList.add('d-none');
        }

        // Color the score number
        totalEl.className = 'display-3 fw-bold';
        if (score <= THRESHOLD_NON_HBR) {
            totalEl.classList.add('text-success');
        } else if (score <= THRESHOLD_HBR) {
            totalEl.classList.add('text-warning');
        } else {
            totalEl.classList.add('text-danger');
        }
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    // Initialisation
    async function init() {
        await fetchScoringConfig();

        // Bind input listeners
        document.querySelectorAll('#score-components input').forEach(function (input) {
            input.addEventListener('input', calculateScore);
            input.addEventListener('change', calculateScore);
        });

        // Bind Hb unit toggle
        var toggleBtn = document.getElementById('hb-unit-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleHbUnit);
        }

        // Initial calculation
        calculateScore();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
