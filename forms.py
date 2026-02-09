from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    SelectField,
    DateField,
    BooleanField,
)
from wtforms.validators import DataRequired, Length, EqualTo


class RegistrationForm(FlaskForm):
    """
    Registration form for new users.

    For simplicity, we require only a username and password.
    """

    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=25, message="Username must be between 3 and 25 characters."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=6, message="Password should be at least 6 characters long."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    """Login form for existing users."""

    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Login")


class TaskForm(FlaskForm):
    """
    Form for creating and editing tasks.

    New tasks are incomplete by default in the database, so we don't expose
    the "is_completed" flag directly to the user on creation.
    """

    title = StringField(
        "Title",
        validators=[
            DataRequired(message="Please provide a title for the task."),
            Length(max=120),
        ],
    )
    description = TextAreaField(
        "Description (optional)",
        validators=[Length(max=1000)],
    )
    priority = SelectField(
        "Priority",
        choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High")],
        default="Medium",
        validators=[DataRequired()],
    )
    due_date = DateField(
        "Due Date (optional)",
        format="%Y-%m-%d",
        validators=[],
        default=None,
    )
    # This checkbox will be used mainly on the EDIT page so users can
    # manually mark a task as completed. New tasks remain incomplete by
    # default in the database and in create_task().
    is_completed = BooleanField("Mark as completed")
    submit = SubmitField("Save")

    def validate(self, extra_validators=None):
        """
        Custom validation:
        Ensure the due date (if provided) is not far in the past.
        """
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.due_date.data and self.due_date.data < date(2000, 1, 1):
            self.due_date.errors.append("Please choose a realistic due date.")
            return False

        return True


class SearchForm(FlaskForm):
    """Simple search form used in the dashboard (GET parameters)."""

    search = StringField("Search by title")
    submit = SubmitField("Search")

