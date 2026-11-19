"""Server-side validation for sign-up and log-in."""
import re

EMAIL = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")

# Use the account schema's email limit and the same password limit on both forms.
MAX_EMAIL_LENGTH = 254
MAX_PASSWORD_LENGTH = 128


def validate_signup(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    confirm = form.get("confirm", "")
    if email == "":
        errors["email"] = "Email is required."
    # Enforce the email column's length before checking its format.
    elif len(email) > MAX_EMAIL_LENGTH:
        errors["email"] = f"Email must be at most {MAX_EMAIL_LENGTH} characters."
    elif not EMAIL.match(email):
        errors["email"] = "Enter a valid email address."
    if password == "":
        errors["password"] = "Password is required."
    elif len(password) < 6:
        errors["password"] = "Password must be at least 6 characters."
    # Bound both password fields before account creation.
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    if confirm == "":
        errors["confirm"] = "Please confirm your password."
    elif len(confirm) > MAX_PASSWORD_LENGTH:
        errors["confirm"] = f"Confirmation must be at most {MAX_PASSWORD_LENGTH} characters."
    elif confirm != password:
        errors["confirm"] = "Passwords do not match."
    return errors, email


def validate_login(form):
    errors = {}
    email = form.get("email", "").strip().lower()
    password = form.get("password", "")
    if email == "":
        errors["email"] = "Email is required."
    # Apply the signup field limits before looking up or verifying login credentials.
    elif len(email) > MAX_EMAIL_LENGTH:
        errors["email"] = f"Email must be at most {MAX_EMAIL_LENGTH} characters."
    if password == "":
        errors["password"] = "Password is required."
    elif len(password) > MAX_PASSWORD_LENGTH:
        errors["password"] = f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    return errors, email
