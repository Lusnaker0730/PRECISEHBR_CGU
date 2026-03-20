// ARC-HBR Standalone Tradeoff Calculator
// Loads model data from /api/config/tradeoff-model (arc-hbr-model.json + cdss_config.json).
// Consumes PreciseHBRCore for escapeHtml.
(function () {
    'use strict';

    var Core = window.PreciseHBRCore;
    if (!Core) {
        console.error('PreciseHBRCore not loaded — standalone tradeoff disabled');
        return;
    }

    // Model state — loaded from API, with hardcoded fallback
    var modelConfig = null;

    // Fallback defaults (used when API is unreachable)
    function getDefaultModelConfig() {
        return {
            baselineRatePercent: 1.4,
            mortalityRatio: 1.9,
            bleedingPredictors: [
                { factor: 'age_ge_65',            hazardRatio: 1.50, description: 'Age \u226565 years' },
                { factor: 'liver_cancer_surgery',  hazardRatio: 1.63, description: 'Liver disease, cancer, or surgery' },
                { factor: 'copd',                  hazardRatio: 1.39, description: 'COPD' },
                { factor: 'smoker',                hazardRatio: 1.47, description: 'Current smoker' },
                { factor: 'hemoglobin_11_12.9',    hazardRatio: 1.69, description: 'Hemoglobin 11\u201312.9 g/dL' },
                { factor: 'hemoglobin_lt_11',      hazardRatio: 3.99, description: 'Hemoglobin < 11 g/dL' },
                { factor: 'egfr_lt_30',            hazardRatio: 1.43, description: 'eGFR < 30 mL/min' },
                { factor: 'complex_pci',           hazardRatio: 1.32, description: 'Complex PCI procedure' },
                { factor: 'oac_discharge',         hazardRatio: 2.00, description: 'OAC at discharge' }
            ],
            thromboticPredictors: [
                { factor: 'diabetes',              hazardRatio: 1.56, description: 'Diabetes mellitus' },
                { factor: 'prior_mi',              hazardRatio: 1.89, description: 'Prior myocardial infarction' },
                { factor: 'smoker',                hazardRatio: 1.48, description: 'Current smoker' },
                { factor: 'nstemi_stemi',          hazardRatio: 1.82, description: 'NSTEMI or STEMI' },
                { factor: 'hemoglobin_11_12.9',    hazardRatio: 1.27, description: 'Hemoglobin 11\u201312.9 g/dL' },
                { factor: 'hemoglobin_lt_11',      hazardRatio: 1.50, description: 'Hemoglobin < 11 g/dL' },
                { factor: 'egfr_30_59',            hazardRatio: 1.30, description: 'eGFR 30\u201359 mL/min' },
                { factor: 'egfr_lt_30',            hazardRatio: 1.69, description: 'eGFR < 30 mL/min' },
                { factor: 'complex_pci',           hazardRatio: 1.50, description: 'Complex PCI procedure' },
                { factor: 'bms',                   hazardRatio: 1.53, description: 'Bare metal stent (BMS)' }
            ]
        };
    }

    async function fetchModelConfig() {
        try {
            var response = await fetch('/api/config/tradeoff-model');
            if (!response.ok) {
                console.warn('Tradeoff model API returned', response.status, '— using fallback');
                return getDefaultModelConfig();
            }
            var data = await response.json();
            if (!data.bleedingPredictors || !data.thromboticPredictors) {
                console.warn('Tradeoff model response invalid — using fallback');
                return getDefaultModelConfig();
            }
            return data;
        } catch (e) {
            console.warn('Tradeoff model fetch error — using fallback:', e.message);
            return getDefaultModelConfig();
        }
    }

    // ------------------------------------------------------------------
    // Factor detection from UI
    // ------------------------------------------------------------------

    function getActiveFactors() {
        var factors = {};
        var checkboxIds = [
            'age_ge_65', 'diabetes', 'prior_mi', 'smoker', 'nstemi_stemi',
            'copd', 'liver_cancer_surgery', 'complex_pci', 'bms', 'oac_discharge'
        ];
        checkboxIds.forEach(function (id) {
            var el = document.getElementById('tf-' + id);
            if (el && el.checked) factors[id] = true;
        });

        var hbSelect = document.getElementById('tf-hb-select');
        if (hbSelect && hbSelect.value !== 'normal') factors[hbSelect.value] = true;

        var egfrSelect = document.getElementById('tf-egfr-select');
        if (egfrSelect && egfrSelect.value !== 'normal') factors[egfrSelect.value] = true;

        return factors;
    }

    // ------------------------------------------------------------------
    // Risk calculation — Cox-PH with baseline from config
    // ------------------------------------------------------------------

    function calculateRisk(predictors, activeFactors) {
        var baselineRate = modelConfig.baselineRatePercent / 100;
        var baselineHazard = -Math.log(1 - baselineRate);
        var hrProduct = 1.0;
        var activeList = [];

        predictors.forEach(function (p) {
            if (activeFactors[p.factor]) {
                hrProduct *= p.hazardRatio;
                activeList.push(p.description + ' (HR: ' + p.hazardRatio + ')');
            }
        });

        var risk = (1 - Math.exp(-baselineHazard * hrProduct)) * 100;
        return { risk: Math.round(risk * 100) / 100, factors: activeList };
    }

    // ------------------------------------------------------------------
    // UI update
    // ------------------------------------------------------------------

    function recalculate() {
        if (!modelConfig) return;

        var factors = getActiveFactors();
        var blResult = calculateRisk(modelConfig.bleedingPredictors, factors);
        var thResult = calculateRisk(modelConfig.thromboticPredictors, factors);

        document.getElementById('result-bleeding').textContent = blResult.risk.toFixed(2) + '%';
        document.getElementById('result-thrombotic').textContent = thResult.risk.toFixed(2) + '%';

        // Progress bar
        var total = blResult.risk + thResult.risk;
        if (total > 0) {
            var blPct = (blResult.risk / total) * 100;
            if (window._cspSetBarWidths) {
                window._cspSetBarWidths('risk-bar-bleeding', blPct, 'risk-bar-thrombotic', 100 - blPct);
            }
        }

        // Factor lists
        var blList = document.getElementById('active-bleeding-factors');
        var thList = document.getElementById('active-thrombotic-factors');

        blList.innerHTML = blResult.factors.length > 0
            ? blResult.factors.map(function (f) { return '<li>' + Core.escapeHtml(f) + '</li>'; }).join('')
            : '<li class="text-muted">None</li>';
        thList.innerHTML = thResult.factors.length > 0
            ? thResult.factors.map(function (f) { return '<li>' + Core.escapeHtml(f) + '</li>'; }).join('')
            : '<li class="text-muted">None</li>';

        // Interpretation — uses mortality ratio from config
        var MORTALITY_RATIO = modelConfig.mortalityRatio;
        var interpEl = document.getElementById('interpretation');
        var interpText = document.getElementById('interpretation-text');
        var weightedBleeding = blResult.risk * MORTALITY_RATIO;

        if (thResult.risk > weightedBleeding * 1.1) {
            interpEl.className = 'alert alert-primary';
            interpText.textContent = 'Ischemic risk dominates (' + thResult.risk.toFixed(1) +
                '% MI/ST vs ' + blResult.risk.toFixed(1) +
                '% bleeding). Consider extending/intensifying antithrombotic therapy.';
        } else if (blResult.risk > thResult.risk * 1.1) {
            interpEl.className = 'alert alert-danger';
            interpText.textContent = 'Bleeding risk dominates (' + blResult.risk.toFixed(1) +
                '% bleeding vs ' + thResult.risk.toFixed(1) +
                '% MI/ST). Consider shortening/simplifying antithrombotic therapy.';
        } else {
            interpEl.className = 'alert alert-secondary';
            interpText.textContent = 'Bleeding and ischemic risks are comparable (' +
                blResult.risk.toFixed(1) + '% vs ' + thResult.risk.toFixed(1) +
                '%). Standard guideline-based DAPT duration recommended.';
        }
    }

    // ------------------------------------------------------------------
    // Init
    // ------------------------------------------------------------------

    async function init() {
        modelConfig = await fetchModelConfig();

        document.querySelectorAll('.tradeoff-factor').forEach(function (el) {
            el.addEventListener('change', recalculate);
        });

        recalculate();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
