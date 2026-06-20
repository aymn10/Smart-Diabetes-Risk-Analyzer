from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from database import create_user_record, get_user_by_email, get_user_by_id, update_user_profile


class User(UserMixin):
    def __init__(self, row: dict):
        self.id = row["id"]
        self.email = row["email"]
        self.full_name = row.get("full_name") or ""
        self.gender = row.get("gender") or ""
        self.date_of_birth = row.get("date_of_birth") or ""
        self.height_cm = row.get("height_cm")
        self.weight_kg = row.get("weight_kg")
        self.created_at = row.get("created_at", "")

    @property
    def display_name(self):
        return self.full_name or self.email.split("@")[0]

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        try:
            dob = datetime.strptime(self.date_of_birth, "%Y-%m-%d").date()
            today = date.today()
            return today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
        except ValueError:
            return None

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg and self.height_cm > 0:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def profile_completion(self):
        fields = [
            self.full_name,
            self.gender,
            self.date_of_birth,
            self.height_cm,
            self.weight_kg,
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)

    def to_profile_dict(self):
        return {
            "full_name": self.full_name,
            "email": self.email,
            "gender": self.gender,
            "date_of_birth": self.date_of_birth,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "age": self.age,
            "bmi": self.bmi,
            "profile_completion": self.profile_completion,
        }


def load_user(user_id):
    row = get_user_by_id(int(user_id))
    return User(row) if row else None


def register_user(email: str, password: str, full_name: str = ""):
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if get_user_by_email(email):
        raise ValueError("An account with this email already exists.")

    password_hash = generate_password_hash(password)
    user_id = create_user_record(email, password_hash, full_name.strip())
    return user_id


def authenticate_user(email: str, password: str):
    email = email.strip().lower()
    row = get_user_by_email(email)
    if not row or not check_password_hash(row["password_hash"], password):
        return None
    return User(row)


def save_profile(user_id: int, data: dict):
    update_user_profile(user_id, data)
    row = get_user_by_id(user_id)
    return User(row) if row else None
