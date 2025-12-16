# **Medical Calculator Verification & Validation (V\&V) Protocol**

Compliance Standard: FDA SaMD / IEC 62304 / IMDRF  
Target Audience: Clinical Engineers, QA Teams, AI Assistants  
Reference Example: Fractional Excretion of Sodium (FeNa)

## ---

**1\. Introduction & Scope**

This protocol defines the standardized workflow for the **Verification (Technical Correctness)** and **Validation (Clinical Utility)** of medical calculators intended for clinical use. All calculators must be treated as **Software as a Medical Device (SaMD)**.

**Definitions:**

* **Verification ("Building the product right"):** Ensuring the software algorithm matches the mathematical specifications and handles all inputs correctly (e.g., Unit conversions, Edge cases).  
* **Validation ("Building the right product"):** Ensuring the calculator provides clinically meaningful and accurate results for the intended patient population (e.g., Sensitivity, Specificity, AUC).

## ---

**Phase 1: Physiological & Mathematical Deconstruction (Design Input)**

**Objective:** Establish a "Valid Clinical Association" and define the "Ground Truth" formula.

### **1.1 Source Deconstruction**

* **Action:** Retrieve the primary derivation study.  
  * *FeNa Example:* Espinel CH (1976) for formula derivation; Miller TR (1978) for diagnostic cutoffs.1  
* **Action:** Extract the exact mathematical logic.  
  * **Formula:** $\\text{FeNa} \= \\frac{U\_{Na} \\times P\_{Cr}}{P\_{Na} \\times U\_{Cr}} \\times 100$  
  * *Note:* Confirm if variables like Urine Flow Rate ($V$) cancel out. For FeNa, they do, allowing the use of Spot Urine samples.

### **1.2 Variable & Unit Definition Table**

Define all inputs, allowed ranges, and required unit conversions.

| Variable | Symbol | Standard Unit (US) | SI Unit | Conversion Factor (SI to US) | Physiological Range (Guardrails) |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Serum Sodium | $P\_{Na}$ | mEq/L | mmol/L | 1.0 | 100 \- 200 |
| Urine Sodium | $U\_{Na}$ | mEq/L | mmol/L | 1.0 | 0 \- 200 |
| Serum Creatinine | $P\_{Cr}$ | **mg/dL** | **$\\mu$mol/L** | $\\div 88.4$ | 0.1 \- 25.0 |
| Urine Creatinine | $U\_{Cr}$ | **mg/dL** | **$\\mu$mol/L** | $\\div 88.4$ | 5 \- 500 |

**Critical Checkpoint:** Identify variables that require mandatory unit standardization before calculation (e.g., Creatinine). Failure to normalize units is a Critical Failure Mode.

## ---

**Phase 2: Technical Verification (The "Build It Right" Phase)**

**Objective:** Prove mathematically that the software implementation is error-free using **Parallel Testing**.

### **2.1 The "Golden Dataset" Strategy**

Do not rely on ad-hoc testing. Create a synthetic dataset to serve as the "Source of Truth."

1. **Generate Data:** Create a CSV/Excel file with N=100 rows of random integers/floats representing clinical variables.  
   * Include **Normal values** (Healthy ranges).  
   * Include **Pathological values** (e.g., high Creatinine, low Urine Na).  
   * Include **Boundary values** (Near 0, Max reasonable value).  
2. **Calculate Reference Results:** Use a trusted external tool (e.g., Excel or a validated Python library) to calculate the expected result for each row.  
   * *Excel Formula:* \=(U\_Na \* P\_Cr \* 100\) / (P\_Na \* U\_Cr)  
3. **Execute Parallel Test:** Run the software/code against this dataset and compare results.

### **2.2 Boundary Value Analysis (Edge Cases)**

The calculator must pass the following stress tests:

| Test Case ID | Scenario | Input Example | Expected Behavior |
| :---- | :---- | :---- | :---- |
| **TC-001** | Standard Calculation | Normal physiological values | Result matches Golden Dataset ($\\pm 0.0001$) |
| **TC-002** | Unit Mismatch | $P\_{Cr}$ in mg/dL, $U\_{Cr}$ in $\\mu$mol/L | System auto-converts or prompts user |
| **TC-003** | Zero Divisor | $P\_{Na} \= 0$ or $U\_{Cr} \= 0$ | Error Message: "Invalid Input" (No Crash) |
| **TC-004** | Impossible Negative | $U\_{Na} \= \-10$ | Error Message: "Value must be positive" |
| **TC-005** | Extreme High Value | $P\_{Cr} \= 50$ mg/dL | Warning: "Value outside typical range" |
| **TC-006** | Null Input | Missing $U\_{Na}$ | Button Disabled / "Required Field" alert |

## ---

**Phase 3: Clinical Validation (The "Build The Right Thing" Phase)**

**Objective:** Verify the clinical utility and accuracy using real-world or literature-derived performance metrics.

### **3.1 Diagnostic Accuracy Assessment (ROC Analysis)**

Evaluate the calculator's ability to distinguish between conditions (e.g., Prerenal vs. ATN).

* **Metric 1: AUC (Area Under the Receiver Operating Characteristic Curve)**  
  * *Target:* AUC \> 0.80 for clinical utility.3  
  * *Action:* Plot Sensitivity vs. (1 \- Specificity).  
* **Metric 2: Sensitivity & Specificity at Cutoff**  
  * *FeNa Example:* Verify performance at cutoff \< 1%.  
  * *Expected Standard:* Sensitivity \> 90% for Prerenal Azotemia (in oliguric patients off diuretics).1

### **3.2 Calibration Testing (Hosmer-Lemeshow)**

Does the predicted probability match the observed frequency?

* **Test:** **Hosmer-Lemeshow Goodness-of-Fit Test**.6  
* **Procedure:**  
  1. Divide patients into deciles of risk based on the calculator score.  
  2. Compare expected event rate vs. observed event rate in each decile.  
  3. *Pass:* p-value \> 0.05 (Indicates no significant difference between predicted and observed).

### **3.3 Confounder Analysis**

Identify and test clinical scenarios where the calculator fails.

* **FeNa Exclusion Criteria (Must be flagged in UI):**  
  * \[x\] Patients on **Diuretics** (Loop/Thiazide) \-\> *Action: Suggest FEUrea*.8  
  * \[x\] Non-oliguric states.  
  * \[x\] Chronic Kidney Disease (CKD).  
  * \[x\] Glomerulonephritis.

## ---

**Phase 4: Risk Management & Usability (ISO 14971\)**

**Objective:** Identify potential failure modes and implement mitigations.

### **4.1 FMEA (Failure Mode and Effects Analysis)**

| Failure Mode | Severity (1-5) | Cause | Mitigation Strategy |
| :---- | :---- | :---- | :---- |
| **Wrong Unit Entry** | 5 (Critical) | User enters $\\mu$mol/L value into mg/dL field. | **UI Design:** Explicit unit toggles next to input fields. Default to common local units. |
| **Interpretation Error** | 4 (High) | User misinterprets FeNa \< 1% in a patient on Lasix. | **Algorithm:** Add logic check "Is patient on diuretics?" If Yes $\\to$ Display warning or switch to FEUrea. |
| **Data Entry Error** | 3 (Moderate) | User types "1400" instead of "140" for Sodium. | **Validation:** Input masking and "Sanity Check" warnings for values $\> 3\\sigma$. |

## ---

**Phase 5: Reporting & Documentation (TRIPOD)**

**Objective:** Ensure transparency and reproducibility for regulatory review or publication.

Adhere to the **TRIPOD Statement** (Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis).10

**Checklist for Final Report:**

* \[ \] **Title/Abstract:** Clearly state if this is Development or Validation.  
* \[ \] **Methods:** Describe the "Golden Standard" used for comparison.  
* \[ \] **Participants:** Define inclusion/exclusion criteria (e.g., "Oliguric patients only").  
* \[ \] **Model Specification:** Provide the full formula and unit requirements.  
* \[ \] **Model Performance:** Report AUC (with 95% CI), Calibration slope, Sensitivity, Specificity.  
* \[ \] **Limitations:** Explicitly list confounders (e.g., "Not valid for patients on diuretics").  
* \[ \] **Code Availability:** Link to the verification script or repository.

### ---

**Execution Instructions for AI Agent:**

1. **Step 1:** Ingest the physiological formula and variable constraints defined in **Phase 1**.  
2. **Step 2:** Generate a **Python script** to perform the "Golden Dataset" verification as outlined in **Phase 2**. Output the test results.  
3. **Step 3:** Review the provided clinical literature snippets and summarize the **Sensitivity/Specificity** data for the target calculator (**Phase 3**).  
4. **Step 4:** Draft a **Risk Assessment** table based on **Phase 4**, specifically looking for "unit confusion" and "patient exclusion" risks.  
5. **Step 5:** Compile all findings into a final report following the **TRIPOD** structure (**Phase 5**).

#### **引用的著作**

1. Fractional Excretion of Sodium (FENa) \[Updated\] | Published in Evidence to Action: Official Journal of MDCalc, 檢索日期：12月 16, 2025， [https://mdcalc.scholasticahq.com/article/143123-fractional-excretion-of-sodium-fena-updated](https://mdcalc.scholasticahq.com/article/143123-fractional-excretion-of-sodium-fena-updated)  
2. Fractional Excretion of Sodium and Urea in Differentiating Acute Kidney Injury Phenotypes in Decompensated Cirrhosis \- PMC \- NIH, 檢索日期：12月 16, 2025， [https://pmc.ncbi.nlm.nih.gov/articles/PMC9168716/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9168716/)  
3. Receiver operating characteristic curve analysis in diagnostic accuracy studies: A guide to interpreting the area under the curve value \- Turkish Journal of Emergency Medicine, 檢索日期：12月 16, 2025， [https://turkjemergmed.com/full-text/851](https://turkjemergmed.com/full-text/851)  
4. The clinical meaning of the area under a receiver operating characteristic curve for the evaluation of the performance of disease markers \- Epidemiology and Health, 檢索日期：12月 16, 2025， [https://www.e-epih.org/journal/view.php?doi=10.4178/epih.e2022088](https://www.e-epih.org/journal/view.php?doi=10.4178/epih.e2022088)  
5. Diagnostic Performance of Fractional Excretion of Sodium for the Differential Diagnosis of Acute Kidney Injury: A Systematic Review and Meta-Analysis \- PubMed Central, 檢索日期：12月 16, 2025， [https://pmc.ncbi.nlm.nih.gov/articles/PMC9269645/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9269645/)  
6. Hosmer–Lemeshow Test (Logistic Regression Calibration) \- MetricGate Calculator, 檢索日期：12月 16, 2025， [https://metricgate.com/docs/hosmer-lemeshow-test/](https://metricgate.com/docs/hosmer-lemeshow-test/)  
7. Function for calibration plot and Hosmer-Lemeshow goodness of... \- R, 檢索日期：12月 16, 2025， [https://search.r-project.org/CRAN/refmans/PredictABEL/html/plotCalibration.html](https://search.r-project.org/CRAN/refmans/PredictABEL/html/plotCalibration.html)  
8. What do fractional excretion of sodium (FeNa) values indicate about the type and management of acute kidney injury (AKI)? \- Dr.Oracle, 檢索日期：12月 16, 2025， [https://www.droracle.ai/articles/307658/what-do-fractional-excretion-of-sodium-fena-values-indicate](https://www.droracle.ai/articles/307658/what-do-fractional-excretion-of-sodium-fena-values-indicate)  
9. Fractional Excretion of Sodium and Urea are Useful Tools in the Evaluation of AKI \- NIH, 檢索日期：12月 16, 2025， [https://pmc.ncbi.nlm.nih.gov/articles/PMC10371367/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10371367/)  
10. Tripod statement, 檢索日期：12月 16, 2025， [https://www.tripod-statement.org/](https://www.tripod-statement.org/)