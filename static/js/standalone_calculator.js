// PRECISE-HBR Standalone Calculator
// Consumes shared logic from PreciseHBRCore (precise_hbr_core.js).
// All coefficients loaded from /api/config/scoring (cdss_config.json).
(function () {
    'use strict';

    var Core = window.PreciseHBRCore;
    if (!Core) {
        console.error('PreciseHBRCore not loaded — standalone calculator disabled');
        return;
    }

    // Module state
    var scoringConfig = null;
    var unitSettings = { hemoglobin: 'g/dL' };
    var clinicalTooltips = Core.createClinicalTooltips();

    // ------------------------------------------------------------------
    // Hemoglobin unit toggle
    // ------------------------------------------------------------------

    function toggleHemoglobinUnit() {
        var input = document.getElementById('input-hb');
        var currentValue = parseFloat(input.value);
        var currentUnit = unitSettings.hemoglobin;
        var newUnit = currentUnit === 'g/dL' ? 'mmol/L' : 'g/dL';

        if (!isNaN(currentValue)) {
            input.value = Core.convertHemoglobin(currentValue, currentUnit, newUnit).toFixed(2);
        }

        unitSettings.hemoglobin = newUnit;

        var unitSpan = document.getElementById('hb-unit-display');
        if (unitSpan) unitSpan.textContent = newUnit;
        var unitLabel = document.getElementById('hb-unit-label');
        if (unitLabel) unitLabel.textContent = '(' + newUnit + ')';

        recalculate();
    }

    // ------------------------------------------------------------------
    // Tooltip rendering
    // ------------------------------------------------------------------

    function renderTooltip(key) {
        var tip = clinicalTooltips[key];
        if (!tip) return '';
        return ' <span class="text-muted" tabindex="0" role="button"' +
            ' data-bs-toggle="popover" data-bs-trigger="hover focus"' +
            ' data-bs-html="true" data-bs-placement="right"' +
            ' title="' + Core.escapeHtml(tip.title) + '"' +
            ' data-bs-content="<p>' + Core.escapeHtml(tip.content) +
            '</p><p><strong>Normal:</strong> ' + Core.escapeHtml(tip.normalRange) +
            '</p><p><strong>Risk:</strong> ' + Core.escapeHtml(tip.riskFactors) +
            '</p>">' +
            '<i class="fas fa-info-circle"></i></span>';
    }

    function initPopovers() {
        document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
            new bootstrap.Popover(el);
        });
    }

    // ------------------------------------------------------------------
    // Score calculation — uses scoringConfig from /api/config/scoring
    // ------------------------------------------------------------------

    function recalculate() {
        var cfg = scoringConfig;
        if (!cfg) return;

        var c = cfg.coefficients;
        var b = cfg.binary_scores;

        // Validate all inputs
        var blocked = false;
        var inputs = [
            { id: 'input-age', param: 'Age' },
            { id: 'input-hb', param: 'Hemoglobin' },
            { id: 'input-egfr', param: 'eGFR' },
            { id: 'input-wbc', param: 'White Blood Cell Count' }
        ];

        inputs.forEach(function (item) {
            var el = document.getElementById(item.id);
            if (el && el.value) {
                var v = Core.validateValue(item.param, el.value, unitSettings);
                Core.applyValidationStyling(el, v);
                if (v.blockCalculation) blocked = true;
            } else if (el) {
                Core.applyValidationStyling(el, { level: 'normal', message: '' });
            }
        });

        var total = cfg.base_score;

        // Age
        var ageRaw = parseFloat(document.getElementById('input-age').value);
        var ageScore = 0;
        if (!isNaN(ageRaw)) {
            var eff = Math.max(c.age.truncation_min, Math.min(c.age.truncation_max, ageRaw));
            if (eff > c.age.threshold) ageScore = (eff - c.age.threshold) * c.age.coefficient;
        }
        total += ageScore;
        document.getElementById('score-age').textContent = ageScore.toFixed(1);

        // Hemoglobin (convert to g/dL if in mmol/L)
        var hbRaw = parseFloat(document.getElementById('input-hb').value);
        var hbScore = 0;
        if (!isNaN(hbRaw)) {
            var hbGdl = unitSettings.hemoglobin === 'mmol/L'
                ? Core.convertHemoglobin(hbRaw, 'mmol/L', 'g/dL') : hbRaw;
            var eff = Math.max(c.hemoglobin.truncation_min, Math.min(c.hemoglobin.truncation_max, hbGdl));
            if (eff < c.hemoglobin.threshold) hbScore = (c.hemoglobin.threshold - eff) * c.hemoglobin.coefficient;
        }
        total += hbScore;
        document.getElementById('score-hb').textContent = hbScore.toFixed(1);

        // eGFR
        var egfrRaw = parseFloat(document.getElementById('input-egfr').value);
        var egfrScore = 0;
        if (!isNaN(egfrRaw)) {
            var eff = Math.max(c.egfr.truncation_min, Math.min(c.egfr.truncation_max, egfrRaw));
            if (eff < c.egfr.threshold) egfrScore = (c.egfr.threshold - eff) * c.egfr.coefficient;
        }
        total += egfrScore;
        document.getElementById('score-egfr').textContent = egfrScore.toFixed(1);

        // WBC
        var wbcRaw = parseFloat(document.getElementById('input-wbc').value);
        var wbcScore = 0;
        if (!isNaN(wbcRaw)) {
            var eff = Math.max(c.wbc.truncation_min, Math.min(c.wbc.truncation_max, wbcRaw));
            if (eff > c.wbc.threshold) wbcScore = (eff - c.wbc.threshold) * c.wbc.coefficient;
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

        var finalScore = Math.round(total);

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

    // ------------------------------------------------------------------
    // UI update
    // ------------------------------------------------------------------

    function updateScoreDisplay(score) {
        var totalEl = document.getElementById('total-score');
        var riskEl = document.getElementById('risk-level');
        var riskPctEl = document.getElementById('risk-percent');
        var recommendEl = document.getElementById('recommendation');
        var hbrSection = document.getElementById('hbr-recommendations-section');
        var T = Core.RISK_THRESHOLDS;

        totalEl.textContent = score;
        var riskPct = Core.calculateRiskPercent(score);

        var category, colorClass, scoreRange, scoreColor;
        if (score <= T.NOT_HIGH) {
            category = 'Not high bleeding risk';
            colorClass = 'bg-success';
            scoreRange = '(score \u2264' + T.NOT_HIGH + ')';
            scoreColor = 'text-success';
        } else if (score < T.VERY_HBR) {
            category = 'High bleeding risk (HBR)';
            colorClass = 'bg-warning text-dark';
            scoreRange = '(score ' + T.HBR + '\u2013' + (T.VERY_HBR - 1) + ')';
            scoreColor = 'text-warning';
        } else {
            category = 'Very high bleeding risk';
            colorClass = 'bg-danger';
            scoreRange = '(score \u2265' + T.VERY_HBR + ')';
            scoreColor = 'text-danger';
        }

        riskEl.innerHTML = '<span class="badge ' + colorClass + '">' +
            Core.escapeHtml(category) + '</span> <small class="text-muted">' +
            Core.escapeHtml(scoreRange) + '</small>';

        riskPctEl.textContent = '1-year risk of major bleeding (BARC 3/5): ' + riskPct + '%';
        recommendEl.textContent = score <= T.NOT_HIGH
            ? 'Standard DAPT duration per guidelines.'
            : 'Consider abbreviated DAPT or de-escalation strategy.';

        if (score >= T.HBR) {
            hbrSection.classList.remove('d-none');
        } else {
            hbrSection.classList.add('d-none');
        }

        totalEl.className = 'display-3 fw-bold ' + scoreColor;
    }

    // ------------------------------------------------------------------
    // Required field check
    // ------------------------------------------------------------------

    var REQUIRED_FIELDS = ['input-age', 'input-hb', 'input-egfr', 'input-wbc'];

    function getMissingRequired() {
        var missing = [];
        REQUIRED_FIELDS.forEach(function (id) {
            var el = document.getElementById(id);
            if (!el || !el.value || el.value.trim() === '') {
                missing.push(id);
            }
        });
        return missing;
    }

    function updateCalculateButton() {
        var btn = document.getElementById('btn-calculate');
        if (!btn) return;
        var missing = getMissingRequired();
        btn.disabled = missing.length > 0;
    }

    function handleCalculateClick() {
        var missing = getMissingRequired();
        if (missing.length > 0) {
            // Highlight missing fields
            missing.forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.classList.add('is-invalid');
            });
            return;
        }

        recalculate();

        // Show results, hide placeholder
        document.getElementById('score-placeholder').classList.add('d-none');
        document.getElementById('score-results').classList.remove('d-none');
    }

    function handleResetClick() {
        // Clear all inputs
        document.querySelectorAll('#score-components input').forEach(function (input) {
            if (input.type === 'checkbox') {
                input.checked = false;
            } else {
                input.value = '';
            }
            input.classList.remove('is-invalid', 'value-error', 'value-warning', 'value-normal');
        });

        // Clear validation messages
        document.querySelectorAll('.validation-message').forEach(function (msg) { msg.remove(); });

        // Reset score displays
        ['score-age', 'score-hb', 'score-egfr', 'score-wbc',
         'score-bleeding', 'score-oac', 'score-arc'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = '0';
        });

        // Hide results, show placeholder
        document.getElementById('score-results').classList.add('d-none');
        document.getElementById('score-placeholder').classList.remove('d-none');
        document.getElementById('hbr-recommendations-section').classList.add('d-none');

        updateCalculateButton();
    }

    // ------------------------------------------------------------------
    // Init
    // ------------------------------------------------------------------

    async function init() {
        scoringConfig = await Core.fetchScoringConfig();
        Core.updateTooltipsWithConfig(clinicalTooltips, scoringConfig);

        // Update base score display from config
        var baseScoreEl = document.getElementById('score-base');
        if (baseScoreEl && scoringConfig) {
            baseScoreEl.textContent = scoringConfig.base_score;
        }

        // Add tooltips to parameter labels
        var tooltipTargets = {
            'input-age': 'Age',
            'input-hb': 'Hemoglobin',
            'input-egfr': 'eGFR',
            'input-wbc': 'White Blood Cell Count',
            'input-bleeding': 'Previous bleeding',
            'input-oac': 'Long-term oral anticoagulation',
            'input-arc': 'ARC-HBR Factors'
        };
        Object.keys(tooltipTargets).forEach(function (inputId) {
            var input = document.getElementById(inputId);
            if (input) {
                var td = input.closest('tr').querySelector('td:first-child');
                if (td) td.insertAdjacentHTML('beforeend', renderTooltip(tooltipTargets[inputId]));
            }
        });
        initPopovers();

        // Bind input listeners — validate on input, but don't auto-calculate
        document.querySelectorAll('#score-components input[type="number"]').forEach(function (input) {
            input.addEventListener('input', function () {
                var paramMap = {
                    'input-age': 'Age', 'input-hb': 'Hemoglobin',
                    'input-egfr': 'eGFR', 'input-wbc': 'White Blood Cell Count'
                };
                var param = paramMap[input.id];
                if (param) {
                    var v = Core.validateValue(param, input.value, unitSettings);
                    Core.applyValidationStyling(input, v);
                }
                input.classList.remove('is-invalid');
                updateCalculateButton();
            });
        });

        // Bind Hb unit toggle
        var toggleBtn = document.getElementById('hb-unit-toggle');
        if (toggleBtn) toggleBtn.addEventListener('click', toggleHemoglobinUnit);

        // Bind Calculate and Reset buttons
        var calcBtn = document.getElementById('btn-calculate');
        if (calcBtn) calcBtn.addEventListener('click', handleCalculateClick);

        var resetBtn = document.getElementById('btn-reset');
        if (resetBtn) resetBtn.addEventListener('click', handleResetClick);

        updateCalculateButton();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
