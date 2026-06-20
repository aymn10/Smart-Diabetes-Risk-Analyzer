
from datetime import date

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from auth import User, load_user, register_user, authenticate_user, save_profile
from database import init_db, save_assessment, get_assessment, get_user_assessments, get_dashboard_stats
from risk_engine import assess_patient
from trend_analysis import analyze_user_trends
from field_guides import FIELD_GUIDES

app = Flask(__name__)
app.secret_key = "diasense-dev-key-change-in-production"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."

init_db()


@login_manager.user_loader
def user_loader(user_id):
    return load_user(user_id)


def parse_form_data(form, user: User = None) -> dict:
    def to_float(key, required=False):
        val = form.get(key, "").strip()
        if not val:
            return None if not required else 0.0
        return float(val)

    def to_int(key, default=0):
        val = form.get(key, "").strip()
        return int(val) if val else default

    height = to_float("height_cm")
    weight = to_float("weight_kg")
    bmi = to_float("bmi")
    if not bmi and height and weight and height > 0:
        bmi = round(weight / ((height / 100) ** 2), 1)

    age = to_float("age")
    if not age and user and user.age:
        age = float(user.age)

    gender = form.get("gender", "").strip() or (user.gender if user else "")
    pregnancies = 0
    if gender != "male":
        pregnancies = to_int("pregnancies")

    name = form.get("patient_name", "").strip()
    if not name and user:
        name = user.display_name

    return {
        "patient_name": name or "Anonymous",
        "age": age,
        "pregnancies": pregnancies,
        "glucose": to_float("glucose", required=True),
        "blood_pressure": to_float("blood_pressure", required=True),
        "skin_thickness": to_float("skin_thickness"),
        "insulin": to_float("insulin"),
        "bmi": bmi,
        "diabetes_pedigree": to_float("diabetes_pedigree") or 0.0,
        "height_cm": height,
        "weight_kg": weight,
        "gender": gender,
    }


# --- Auth routes ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        try:
            register_user(
                request.form.get("email", ""),
                request.form.get("password", ""),
                request.form.get("full_name", ""),
            )
            user = authenticate_user(
                request.form.get("email", ""),
                request.form.get("password", ""),
            )
            login_user(user)
            flash("Welcome to DiaSense AI! Complete your profile for faster assessments.", "success")
            return redirect(url_for("profile"))
        except ValueError as e:
            flash(str(e), "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        user = authenticate_user(
            request.form.get("email", ""),
            request.form.get("password", ""),
        )
        if user:
            login_user(user, remember=request.form.get("remember") == "on")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# --- Profile ---

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        try:
            height = request.form.get("height_cm", "").strip()
            weight = request.form.get("weight_kg", "").strip()
            save_profile(current_user.id, {
                "full_name": request.form.get("full_name", "").strip(),
                "gender": request.form.get("gender", "").strip(),
                "date_of_birth": request.form.get("date_of_birth", "").strip() or None,
                "height_cm": float(height) if height else None,
                "weight_kg": float(weight) if weight else None,
            })
            flash("Profile saved successfully.", "success")
            return redirect(url_for("profile"))
        except ValueError:
            flash("Please check your height and weight values.", "error")

    return render_template("profile.html", user=current_user, today=date.today().isoformat())


# --- Main app routes ---

@app.route("/")
@login_required
def dashboard():
    stats = get_dashboard_stats(current_user.id)
    assessments = get_user_assessments(current_user.id, limit=100)
    trends = analyze_user_trends(assessments)
    return render_template(
        "dashboard.html",
        stats=stats,
        trends=trends,
        user=current_user,
    )


@app.route("/assess", methods=["GET", "POST"])
@login_required
def assess():
    profile = current_user.to_profile_dict()

    if request.method == "GET":
        return render_template(
            "assess.html",
            profile=profile,
            guides=FIELD_GUIDES,
        )

    try:
        data = parse_form_data(request.form, current_user)
        if not data["bmi"]:
            raise ValueError("BMI is required. Enter height and weight, or provide BMI directly.")
        if not data["age"]:
            raise ValueError("Age is required. Add your date of birth in Profile, or enter age manually.")

        report = assess_patient(data)

        if request.form.get("save_report") == "on":
            assessment_id = save_assessment(data, report, current_user.id)
            flash("Report saved successfully.", "success")
            return redirect(url_for("view_report", assessment_id=assessment_id))

        return render_template("report.html", report=report, data=data, saved=False)

    except (ValueError, KeyError) as e:
        flash(str(e), "error")
        return render_template(
            "assess.html",
            profile=profile,
            guides=FIELD_GUIDES,
        )


@app.route("/api/assess", methods=["POST"])
@login_required
def api_assess():
    try:
        payload = request.get_json() or {}
        report = assess_patient(payload)
        if payload.get("save"):
            assessment_id = save_assessment(payload, report, current_user.id)
            report["id"] = assessment_id
            report["saved"] = True
        return jsonify(report)
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/report/<int:assessment_id>")
@login_required
def view_report(assessment_id):
    record = get_assessment(assessment_id, current_user.id)
    if not record:
        flash("Report not found.", "error")
        return redirect(url_for("history"))
    return render_template(
        "report.html",
        report=record["report"],
        data=record,
        saved=True,
        assessment_id=assessment_id,
    )


@app.route("/history")
@login_required
def history():
    assessments = get_user_assessments(current_user.id)
    return render_template("history.html", assessments=assessments)


@app.route("/api/stats")
@login_required
def api_stats():
    stats = get_dashboard_stats(current_user.id)
    assessments = get_user_assessments(current_user.id, limit=100)
    stats["trends"] = analyze_user_trends(assessments)
    return jsonify(stats)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
