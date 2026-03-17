// PRECISE-HBR Standalone Calculator
// Client-side scoring without FHIR/patient context
(function () {
    'use strict';

    // Scoring configuration — loaded from backend, with local fallback
    let scoringConfig = null;

    // Complementary log-log calibration curve for 1-year BARC 3/5 risk
    const CLOGLOG_A = -5.3945;
    const CLOGLOG_B = 0.09725;

    // Risk thresholds
    const THRESHOLD_NON_HBR = 22;
    const THRESHOLD_HBR = 26;

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
            const response = await fetch('/api/config/scoring');
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

    function calculateScore() {
        const cfg = scoringConfig;
        if (!cfg) return;

        const c = cfg.coefficients;
        const b = cfg.binary_scores;
        let total = cfg.base_score;

        // Age
        const ageRaw = parseFloat(document.getElementById('input-age').value);
        let ageScore = 0;
        if (!isNaN(ageRaw)) {
            const eff = Math.max(c.age.truncation_min, Math.min(c.age.truncation_max, ageRaw));
            if (eff > c.age.threshold) {
                ageScore = (eff - c.age.threshold) * c.age.coefficient;
            }
        }
        total += ageScore;
        document.getElementById('score-age').textContent = ageScore.toFixed(1);

        // Hemoglobin
        const hbRaw = parseFloat(document.getElementById('input-hb').value);
        let hbScore = 0;
        if (!isNaN(hbRaw)) {
            const eff = Math.max(c.hemoglobin.truncation_min, Math.min(c.hemoglobin.truncation_max, hbRaw));
            if (eff < c.hemoglobin.threshold) {
                hbScore = (c.hemoglobin.threshold - eff) * c.hemoglobin.coefficient;
            }
        }
        total += hbScore;
        document.getElementById('score-hb').textContent = hbScore.toFixed(1);

        // eGFR
        const egfrRaw = parseFloat(document.getElementById('input-egfr').value);
        let egfrScore = 0;
        if (!isNaN(egfrRaw)) {
            const eff = Math.max(c.egfr.truncation_min, Math.min(c.egfr.truncation_max, egfrRaw));
            if (eff < c.egfr.threshold) {
                egfrScore = (c.egfr.threshold - eff) * c.egfr.coefficient;
            }
        }
        total += egfrScore;
        document.getElementById('score-egfr').textContent = egfrScore.toFixed(1);

        // WBC
        const wbcRaw = parseFloat(document.getElementById('input-wbc').value);
        let wbcScore = 0;
        if (!isNaN(wbcRaw)) {
            const eff = Math.max(c.wbc.truncation_min, Math.min(c.wbc.truncation_max, wbcRaw));
            if (eff > c.wbc.threshold) {
                wbcScore = (eff - c.wbc.threshold) * c.wbc.coefficient;
            }
        }
        total += wbcScore;
        document.getElementById('score-wbc').textContent = wbcScore.toFixed(1);

        // Binary factors
        const bleeding = document.getElementById('input-bleeding').checked;
        const oac = document.getElementById('input-oac').checked;
        const arc = document.getElementById('input-arc').checked;

        const bleedingScore = bleeding ? b.prior_bleeding : 0;
        const oacScore = oac ? b.oral_anticoagulation : 0;
        const arcScore = arc ? b.arc_hbr : 0;

        total += bleedingScore + oacScore + arcScore;

        document.getElementById('score-bleeding').textContent = bleedingScore;
        document.getElementById('score-oac').textContent = oacScore;
        document.getElementById('score-arc').textContent = arcScore;

        // Round total
        const roundedTotal = Math.floor(total + 0.5);

        // Update display
        updateScoreDisplay(roundedTotal);
    }

    function calculateRiskPercent(score) {
        const lp = CLOGLOG_A + CLOGLOG_B * score;
        const risk = 1.0 - Math.exp(-Math.exp(lp));
        return (risk * 100).toFixed(2);
    }

    function updateScoreDisplay(score) {
        const totalEl = document.getElementById('total-score');
        const riskEl = document.getElementById('risk-level');
        const riskPctEl = document.getElementById('risk-percent');
        const recommendEl = document.getElementById('recommendation');
        const hbrSection = document.getElementById('hbr-recommendations-section');

        totalEl.textContent = score;

        const riskPct = calculateRiskPercent(score);

        let category, colorClass, scoreRange;
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

        // Bind event listeners
        var inputs = document.querySelectorAll('#score-components input');
        inputs.forEach(function (input) {
            input.addEventListener('input', calculateScore);
            input.addEventListener('change', calculateScore);
        });

        // Initial calculation
        calculateScore();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
