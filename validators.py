"""Server-side validation for sign-up and log-in."""
import re

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 128


def validate_signup(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    confirm = form.get("confirm", "")
    if email == "":
        errors["email"] = "Email is required."
    elif len(email) > MAX_EMAIL_LENGTH or not EMAIL.fullmatch(email):
        errors["email"] = "Enter a valid email address."
    if password == "":
        errors["password"] = "Password is required."
    elif len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = "Password is too long."
    if len(confirm) > MAX_PASSWORD_LENGTH:
        errors["confirm"] = "Password confirmation is too long."
    elif confirm != "" and confirm != password:
        errors["confirm"] = "Passwords do not match."
    return errors, email


def validate_login(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    if email == "":
        errors["email"] = "Email is required."
    elif len(email) > MAX_EMAIL_LENGTH:
        errors["email"] = "Email is too long."
    if password == "":
        errors["password"] = "Password is required."
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = "Password is too long."
    return errors, email
