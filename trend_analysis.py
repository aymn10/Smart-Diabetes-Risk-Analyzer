from datetime import datetime, timedelta


def _parse_date(date_str: str):
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")


def _filter_by_days(assessments: list[dict], days: int) -> list[dict]:
    if not assessments:
        return []
    cutoff = datetime.utcnow() - timedelta(days=days)
    return [a for a in assessments if _parse_date(a["created_at"]) >= cutoff]


def _trend_direction(scores: list[float]) -> str:
    if len(scores) < 2:
        return "stable"
    first_half = scores[: len(scores) // 2]
    second_half = scores[len(scores) // 2 :]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    diff = avg_second - avg_first
    if diff <= -5:
        return "improving"
    if diff >= 5:
        return "worsening"
    return "stable"


def _build_period_conclusion(period_name: str, records: list[dict]) -> dict:
    if not records:
        return {
            "period": period_name,
            "count": 0,
            "available": False,
            "message": f"No assessments in the last {period_name}. Complete an assessment to track your progress.",
        }

    scores = [r["risk_score"] for r in records]
    categories = [r["risk_category"] for r in records]
    avg = round(sum(scores) / len(scores), 1)
    latest = records[0]
    oldest = records[-1]
    direction = _trend_direction(list(reversed(scores)))
    change = round(latest["risk_score"] - oldest["risk_score"], 1)

    messages = []
    if direction == "improving":
        messages.append(
            f"Your risk score has decreased by {abs(change)}% over this period — keep up your healthy habits."
        )
    elif direction == "worsening":
        messages.append(
            f"Your risk score has increased by {change}% over this period. Review your action items and consult a doctor if needed."
        )
    else:
        messages.append(
            f"Your risk has remained relatively stable (avg {avg}%) over this period."
        )

    high_count = sum(1 for c in categories if c in ("High", "Very High"))
    if high_count >= len(categories) * 0.6:
        messages.append(
            "Most readings in this window are High or Very High — prioritize medical follow-up."
        )
    elif avg < 25:
        messages.append("Overall readings suggest low risk — maintain your current lifestyle.")
    elif avg < 50:
        messages.append("Moderate risk pattern — focus on diet, activity, and regular screening.")

    latest_cat = latest["risk_category"]
    if latest_cat in ("High", "Very High"):
        messages.append(f"Your most recent assessment ({latest['created_at'][:10]}) was {latest_cat} risk ({latest['risk_score']}%).")

    return {
        "period": period_name,
        "count": len(records),
        "available": True,
        "average_risk": avg,
        "min_risk": round(min(scores), 1),
        "max_risk": round(max(scores), 1),
        "latest_risk": latest["risk_score"],
        "latest_category": latest_cat,
        "direction": direction,
        "change": change,
        "message": " ".join(messages),
        "scores": scores,
        "dates": [r["created_at"][:10] for r in reversed(records)],
    }


def analyze_user_trends(assessments: list[dict]) -> dict:
    week = _filter_by_days(assessments, 7)
    ten_days = _filter_by_days(assessments, 10)
    overall = assessments

    week_analysis = _build_period_conclusion("7 days", week)
    ten_day_analysis = _build_period_conclusion("10 days", ten_days)
    overall_analysis = _build_period_conclusion("overall", overall)

    headline = "Start your first assessment to unlock personalized health insights."
    if overall:
        direction = overall_analysis["direction"]
        if direction == "improving":
            headline = "Great progress — your diabetes risk trend is improving."
        elif direction == "worsening":
            headline = "Your risk trend needs attention — review recent assessments."
        else:
            headline = f"Your overall risk is stable at around {overall_analysis['average_risk']}%."

    return {
        "headline": headline,
        "week": week_analysis,
        "ten_days": ten_day_analysis,
        "overall": overall_analysis,
    }
