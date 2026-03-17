// ARC-HBR Standalone Tradeoff Calculator
// Client-side Cox-PH calculation without FHIR/patient context
(function () {
    'use strict';

    // Baseline 1-year event rate (validated against official ARC-HBR app)
    var BASELINE_RATE = 0.014; // 1.4%
    var BASELINE_HAZARD = -Math.log(1 - BASELINE_RATE);

    // Mortality weighting ratio (bleeding mortality ~1.9x ischemia mortality)
    var MORTALITY_RATIO = 1.9;

    // ARC-HBR model predictors (from Urban et al. JAMA Cardiol 2021, Table 3)
    var BLEEDING_PREDICTORS = [
        { factor: 'age_ge_65',           hr: 1.50, label: 'Age \u226565 (HR 1.50)' },
        { factor: 'liver_cancer_surgery', hr: 1.63, label: 'Liver disease/cancer/surgery (HR 1.63)' },
        { factor: 'copd',                hr: 1.39, label: 'COPD (HR 1.39)' },
        { factor: 'smoker',              hr: 1.47, label: 'Current smoker (HR 1.47)' },
        { factor: 'hemoglobin_11_12.9',  hr: 1.69, label: 'Hb 11\u201312.9 g/dL (HR 1.69)' },
        { factor: 'hemoglobin_lt_11',    hr: 3.99, label: 'Hb <11 g/dL (HR 3.99)' },
        { factor: 'egfr_lt_30',          hr: 1.43, label: 'eGFR <30 (HR 1.43)' },
        { factor: 'complex_pci',         hr: 1.32, label: 'Complex PCI (HR 1.32)' },
        { factor: 'oac_discharge',       hr: 2.00, label: 'OAC at discharge (HR 2.00)' }
    ];

    var THROMBOTIC_PREDICTORS = [
        { factor: 'diabetes',            hr: 1.56, label: 'Diabetes (HR 1.56)' },
        { factor: 'prior_mi',            hr: 1.89, label: 'Prior MI (HR 1.89)' },
        { factor: 'smoker',              hr: 1.48, label: 'Current smoker (HR 1.48)' },
        { factor: 'nstemi_stemi',        hr: 1.82, label: 'NSTEMI/STEMI (HR 1.82)' },
        { factor: 'hemoglobin_11_12.9',  hr: 1.27, label: 'Hb 11\u201312.9 g/dL (HR 1.27)' },
        { factor: 'hemoglobin_lt_11',    hr: 1.50, label: 'Hb <11 g/dL (HR 1.50)' },
        { factor: 'egfr_30_59',          hr: 1.30, label: 'eGFR 30\u201359 (HR 1.30)' },
        { factor: 'egfr_lt_30',          hr: 1.69, label: 'eGFR <30 (HR 1.69)' },
        { factor: 'complex_pci',         hr: 1.50, label: 'Complex PCI (HR 1.50)' },
        { factor: 'bms',                 hr: 1.53, label: 'Bare metal stent (HR 1.53)' }
    ];

    function getActiveFactors() {
        var factors = {};

        // Checkboxes
        var checkboxIds = [
            'age_ge_65', 'diabetes', 'prior_mi', 'smoker', 'nstemi_stemi',
            'copd', 'liver_cancer_surgery', 'complex_pci', 'bms', 'oac_discharge'
        ];
        checkboxIds.forEach(function (id) {
            var el = document.getElementById('tf-' + id);
            if (el && el.checked) {
                factors[id] = true;
            }
        });

        // Hb select
        var hbSelect = document.getElementById('tf-hb-select');
        if (hbSelect && hbSelect.value !== 'normal') {
            factors[hbSelect.value] = true;
        }

        // eGFR select
        var egfrSelect = document.getElementById('tf-egfr-select');
        if (egfrSelect && egfrSelect.value !== 'normal') {
            factors[egfrSelect.value] = true;
        }

        return factors;
    }

    function calculateRisk(predictors, activeFactors) {
        var hrProduct = 1.0;
        var activeList = [];

        predictors.forEach(function (p) {
            if (activeFactors[p.factor]) {
                hrProduct *= p.hr;
                activeList.push(p.label);
            }
        });

        var risk = (1 - Math.exp(-BASELINE_HAZARD * hrProduct)) * 100;
        return { risk: Math.round(risk * 100) / 100, factors: activeList };
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function recalculate() {
        var factors = getActiveFactors();

        var blResult = calculateRisk(BLEEDING_PREDICTORS, factors);
        var thResult = calculateRisk(THROMBOTIC_PREDICTORS, factors);

        // Update numbers
        document.getElementById('result-bleeding').textContent = blResult.risk.toFixed(2) + '%';
        document.getElementById('result-thrombotic').textContent = thResult.risk.toFixed(2) + '%';

        // Update progress bar
        var total = blResult.risk + thResult.risk;
        if (total > 0) {
            var blPct = (blResult.risk / total) * 100;
            document.getElementById('risk-bar-bleeding').style.width = blPct + '%';
            document.getElementById('risk-bar-thrombotic').style.width = (100 - blPct) + '%';
        }

        // Update factor lists
        var blList = document.getElementById('active-bleeding-factors');
        var thList = document.getElementById('active-thrombotic-factors');

        if (blResult.factors.length > 0) {
            blList.innerHTML = blResult.factors.map(function (f) {
                return '<li>' + escapeHtml(f) + '</li>';
            }).join('');
        } else {
            blList.innerHTML = '<li class="text-muted">None</li>';
        }

        if (thResult.factors.length > 0) {
            thList.innerHTML = thResult.factors.map(function (f) {
                return '<li>' + escapeHtml(f) + '</li>';
            }).join('');
        } else {
            thList.innerHTML = '<li class="text-muted">None</li>';
        }

        // Interpretation
        var interpEl = document.getElementById('interpretation');
        var interpText = document.getElementById('interpretation-text');

        // Mortality-weighted comparison
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

    function init() {
        // Bind all factor inputs
        document.querySelectorAll('.tradeoff-factor').forEach(function (el) {
            el.addEventListener('change', recalculate);
        });

        // Initial calculation
        recalculate();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
