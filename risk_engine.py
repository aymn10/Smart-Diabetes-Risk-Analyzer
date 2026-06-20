"""
Diabetes risk assessment engine based on standard clinical thresholds
aligned with Pima Indians Diabetes Dataset factors and ADA guidelines.
"""

FACTOR_DEFINITIONS = {
    "glucose": {
        "label": "Blood Glucose",
        "unit": "mg/dL",
        "weight": 0.25,
        "ranges": [
            (0, 99, "normal", 0, "Fasting glucose within healthy range."),
            (100, 125, "prediabetes", 45, "Elevated — prediabetes range (100–125 mg/dL)."),
            (126, 200, "high", 75, "High — meets diabetes diagnostic threshold (≥126 mg/dL)."),
            (201, 999, "critical", 95, "Critically high — seek immediate medical attention."),
        ],
    },
    "bmi": {
        "label": "Body Mass Index",
        "unit": "kg/m²",
        "weight": 0.18,
        "ranges": [
            (0, 18.4, "underweight", 15, "Below healthy weight range."),
            (18.5, 24.9, "normal", 0, "Healthy BMI range."),
            (25, 29.9, "overweight", 40, "Overweight — increased diabetes risk."),
            (30, 34.9, "obese", 65, "Obese Class I — significantly elevated risk."),
            (35, 999, "critical", 85, "Obese Class II+ — very high metabolic risk."),
        ],
    },
    "blood_pressure": {
        "label": "Blood Pressure",
        "unit": "mmHg (systolic)",
        "weight": 0.12,
        "ranges": [
            (0, 119, "normal", 0, "Normal blood pressure."),
            (120, 129, "elevated", 25, "Elevated — monitor regularly."),
            (130, 139, "high", 50, "Stage 1 hypertension — lifestyle changes recommended."),
            (140, 999, "critical", 75, "Stage 2 hypertension — consult a physician."),
        ],
    },
    "age": {
        "label": "Age",
        "unit": "years",
        "weight": 0.10,
        "ranges": [
            (0, 34, "normal", 0, "Lower age-related risk."),
            (35, 44, "moderate", 20, "Moderate age-related risk."),
            (45, 59, "high", 45, "Increased risk after age 45."),
            (60, 999, "critical", 65, "Significantly elevated age-related risk."),
        ],
    },
    "insulin": {
        "label": "Insulin Level",
        "unit": "μU/mL",
        "weight": 0.10,
        "ranges": [
            (0, 16, "normal", 0, "Insulin within reference range."),
            (17, 25, "elevated", 30, "Slightly elevated insulin — possible insulin resistance."),
            (26, 50, "high", 55, "High insulin — insulin resistance likely."),
            (51, 999, "critical", 80, "Very high insulin — strong insulin resistance indicator."),
        ],
    },
    "skin_thickness": {
        "label": "Skin Fold Thickness",
        "unit": "mm",
        "weight": 0.05,
        "ranges": [
            (0, 20, "normal", 0, "Within typical range."),
            (21, 30, "elevated", 25, "Above average — may indicate higher body fat."),
            (31, 999, "high", 50, "High skin fold thickness."),
        ],
    },
    "diabetes_pedigree": {
        "label": "Diabetes Pedigree Function",
        "unit": "score",
        "weight": 0.12,
        "ranges": [
            (0, 0.35, "normal", 0, "Low genetic predisposition."),
            (0.36, 0.55, "moderate", 35, "Moderate family history influence."),
            (0.56, 0.75, "high", 60, "Strong family history of diabetes."),
            (0.76, 999, "critical", 85, "Very strong genetic predisposition."),
        ],
    },
    "pregnancies": {
        "label": "Pregnancies",
        "unit": "count",
        "weight": 0.08,
        "ranges": [
            (0, 2, "normal", 0, "Low gestational history factor."),
            (3, 5, "moderate", 30, "Multiple pregnancies — moderate gestational risk."),
            (6, 999, "high", 55, "High number of pregnancies — elevated gestational diabetes history risk."),
        ],
    },
}

RISK_CATEGORIES = [
    (0, 24, "Low", "Your overall diabetes risk appears low. Maintain healthy habits."),
    (25, 49, "Moderate", "Moderate risk detected. Lifestyle improvements are recommended."),
    (50, 74, "High", "High risk — consult a healthcare provider for screening."),
    (75, 100, "Very High", "Very high risk — schedule medical evaluation promptly."),
]

RECOMMENDATIONS = {
    "glucose": {
        "normal": "Continue balanced meals and regular activity.",
        "prediabetes": "Reduce refined carbs; consider HbA1c testing.",
        "high": "Seek fasting glucose confirmation and physician guidance.",
        "critical": "Urgent medical review for hyperglycemia management.",
    },
    "bmi": {
        "underweight": "Ensure adequate nutrition; discuss healthy weight gain.",
        "normal": "Maintain current weight through diet and exercise.",
        "overweight": "Aim for 5–7% weight loss through calorie control and activity.",
        "obese": "Structured weight management program recommended.",
        "critical": "Medical weight management consultation advised.",
    },
    "blood_pressure": {
        "normal": "Keep sodium moderate and stay physically active.",
        "elevated": "Reduce salt intake and increase daily movement.",
        "high": "DASH diet and regular BP monitoring recommended.",
        "critical": "Physician evaluation for hypertension management.",
    },
    "age": {
        "normal": "Annual wellness checks are sufficient.",
        "moderate": "Consider glucose screening every 1–3 years.",
        "high": "Annual diabetes screening recommended.",
        "critical": "Comprehensive metabolic panel yearly.",
    },
    "insulin": {
        "normal": "No insulin-specific action needed.",
        "elevated": "Reduce added sugars; increase fiber intake.",
        "high": "Focus on low-glycemic diet and resistance training.",
        "critical": "Medical evaluation for insulin resistance (HOMA-IR).",
    },
    "skin_thickness": {
        "normal": "No action required.",
        "elevated": "Track body composition changes over time.",
        "high": "Correlate with BMI and waist circumference.",
    },
    "diabetes_pedigree": {
        "normal": "General prevention strategies apply.",
        "moderate": "Family history noted — prioritize prevention.",
        "high": "Early screening and lifestyle intervention essential.",
        "critical": "Genetic counseling and aggressive prevention advised.",
    },
    "pregnancies": {
        "normal": "Standard screening guidelines apply.",
        "moderate": "Discuss gestational diabetes history with your doctor.",
        "high": "Enhanced glucose monitoring if planning pregnancy.",
    },
}


def _evaluate_factor(key: str, value: float | None) -> dict:
    definition = FACTOR_DEFINITIONS[key]
    if value is None or (key in ("skin_thickness", "insulin") and value == 0):
        return {
            "key": key,
            "label": definition["label"],
            "value": value,
            "unit": definition["unit"],
            "status": "not_provided",
            "score": 0,
            "weight": definition["weight"],
            "weighted_score": 0,
            "message": "Not provided — excluded from weighted calculation.",
            "recommendation": "Provide this value for a more accurate assessment.",
            "included": False,
        }

    status = "normal"
    score = 0
    message = ""
    for low, high, stat, pts, msg in definition["ranges"]:
        if low <= value <= high:
            status = stat
            score = pts
            message = msg
            break

    weighted = round(score * definition["weight"], 2)
    rec = RECOMMENDATIONS.get(key, {}).get(status, "Consult your healthcare provider.")

    return {
        "key": key,
        "label": definition["label"],
        "value": value,
        "unit": definition["unit"],
        "status": status,
        "score": score,
        "weight": definition["weight"],
        "weighted_score": weighted,
        "message": message,
        "recommendation": rec,
        "included": True,
    }


def _categorize_risk(score: float) -> tuple[str, str]:
    for low, high, category, description in RISK_CATEGORIES:
        if low <= score <= high:
            return category, description
    return "Very High", RISK_CATEGORIES[-1][3]


def _build_summary(factors: list[dict]) -> list[str]:
    included = [f for f in factors if f["included"]]
    elevated = [f for f in included if f["score"] >= 45]
    moderate = [f for f in included if 20 <= f["score"] < 45]

    summary = []
    if not included:
        summary.append("Insufficient data for a complete assessment.")
        return summary

    if elevated:
        names = ", ".join(f["label"] for f in elevated)
        summary.append(f"Primary risk drivers: {names}.")
    elif moderate:
        names = ", ".join(f["label"] for f in moderate)
        summary.append(f"Moderate concerns in: {names}.")
    else:
        summary.append("All provided factors are within acceptable ranges.")

    top = sorted(included, key=lambda x: x["weighted_score"], reverse=True)[:3]
    if top and top[0]["weighted_score"] > 0:
        summary.append(
            f"Highest weighted contributor: {top[0]['label']} "
            f"({top[0]['weighted_score']} pts)."
        )
    return summary


def assess_patient(data: dict) -> dict:
    factor_keys = [
        "glucose", "bmi", "blood_pressure", "age",
        "insulin", "skin_thickness", "diabetes_pedigree", "pregnancies",
    ]
    factors = [_evaluate_factor(key, data.get(key)) for key in factor_keys]

    included = [f for f in factors if f["included"]]
    if not included:
        raise ValueError("At least glucose, BMI, blood pressure, and age are required.")

    total_weight = sum(f["weight"] for f in included)
    raw_score = sum(f["weighted_score"] for f in included)
    normalized = round((raw_score / total_weight) * (100 / 95), 1) if total_weight else 0
    risk_score = min(100, max(0, normalized))

    category, category_desc = _categorize_risk(risk_score)
    summary = _build_summary(factors)

    action_items = []
    for f in sorted(included, key=lambda x: x["score"], reverse=True):
        if f["score"] >= 20:
            action_items.append({
                "factor": f["label"],
                "priority": "high" if f["score"] >= 45 else "medium",
                "action": f["recommendation"],
            })

    if not action_items:
        action_items.append({
            "factor": "General",
            "priority": "low",
            "action": "Continue regular exercise, balanced diet, and annual checkups.",
        })

    return {
        "patient_name": data.get("patient_name", "Anonymous"),
        "risk_score": risk_score,
        "risk_category": category,
        "category_description": category_desc,
        "summary": summary,
        "factors": factors,
        "action_items": action_items[:5],
        "chart_data": {
            "labels": [f["label"] for f in included],
            "scores": [f["score"] for f in included],
            "weighted": [f["weighted_score"] for f in included],
        },
        "disclaimer": (
            "This report is an educational risk screening tool, not a medical diagnosis. "
            "Always consult a qualified healthcare professional for clinical decisions."
        ),
    }
