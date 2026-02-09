from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy instance is created here and initialized in app.create_app()
db = SQLAlchemy()


class User(db.Model):
    """
    Simple User model.

    This application supports MULTIPLE users.
    Each user will see only their own tasks because tasks are linked
    to the user's id (user_id foreign key) and all queries are filtered
    by the currently logged-in user.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    tasks = db.relationship("Task", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        """Hash and store the password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check the provided password against the stored hash."""
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    """
    Task model.

    Fields:
    - id: primary key
    - title: short title for the task (required)
    - description: optional longer text
    - priority: Low / Medium / High (string)
    - is_completed: boolean status (INCOMPLETE by default)
    - created_at: timestamp of creation (UTC)
    - completed_at: optional timestamp when task was finished
    - due_date: optional due date for the task
    - user_id: foreign key to the User who owns the task
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Priority feature: Low / Medium / High
    priority = db.Column(db.String(10), nullable=False, default="Medium")

    # Status feature: incomplete by default
    is_completed = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Due date feature (optional)
    due_date = db.Column(db.Date, nullable=True)

    # Foreign key to User (each task belongs to a user)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

