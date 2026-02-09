import os
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    session,
    g,
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from models import db, User, Task
from forms import RegistrationForm, LoginForm, TaskForm, SearchForm


def create_app():
    """
    Application factory to create and configure the Flask app.

    This pattern is beginner-friendly and also good practice for
    larger projects and deployments.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # In a real deployment, keep the secret key in environment variables.
    # For college / learning purposes, this hard-coded key is acceptable.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # SQLite database configuration - stored in local file todo.db
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Session lifetime (used when session.permanent = True)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

    # Initialize database and CSRF protection
    db.init_app(app)
    CSRFProtect(app)

    # -----------------------------
    # Authentication helpers
    # -----------------------------

    def login_required(view_func):
        """
        Simple decorator to protect routes.

        It checks whether 'user_id' is stored in the Flask session.
        If not, the user is redirected to the login page.
        """

        from functools import wraps

        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not session.get("user_id"):
                # 401: Unauthorized - we redirect to login page
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped_view

    @app.before_request
    def load_logged_in_user_and_check_timeout():
        """
        Runs before every request.

        - Loads the currently logged-in user into `g.user` (global request object)
        - Implements auto-logout after a period of inactivity
        """
        user_id = session.get("user_id")
        g.user = None

        if user_id is not None:
            g.user = User.query.get(user_id)

        # Auto-logout after 20 minutes of inactivity
        idle_timeout_minutes = 20
        now = datetime.utcnow()
        last_activity = session.get("last_activity")

        if user_id and last_activity:
            try:
                last_activity_dt = datetime.fromisoformat(last_activity)
            except ValueError:
                last_activity_dt = now

            if now - last_activity_dt > timedelta(minutes=idle_timeout_minutes):
                # Clear session and require login again
                session.clear()
                flash("You have been logged out due to inactivity.", "info")
                return redirect(url_for("login"))

        # Update last activity timestamp for next request
        if user_id:
            session["last_activity"] = now.isoformat()

    # -----------------------------
    # Routes
    # -----------------------------

    @app.route("/")
    def index():
        """
        Simple landing route.
        If already logged in, redirect to dashboard.
        Otherwise, show a basic welcome page (login/register links).
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """
        User registration.

        Multiple users are supported. Each user will only see
        their own tasks, because tasks are linked to the user_id
        in the Task model.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        form = RegistrationForm()
        if form.validate_on_submit():
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash("Username already taken. Please choose another one.", "danger")
                return redirect(url_for("register"))

            user = User(
                username=form.username.data,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))  # PRG pattern: avoids resubmission

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Login route using username and password.

        Stores user_id in Flask session on successful login.
        Passwords are hashed using Werkzeug utilities.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                session.clear()
                session["user_id"] = user.id
                session["last_activity"] = datetime.utcnow().isoformat()

                # Optional: remember-me like behaviour using permanent sessions
                if form.remember_me.data:
                    session.permanent = True
                else:
                    session.permanent = False

                flash(f"Welcome, {user.username}!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid username or password.", "danger")

        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        """
        Logout route.
        Clears the session so the user is fully logged out.
        """
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        """
        Main dashboard page.

        Shows:
        - Task list (with filters, search, and pagination)
        - Task statistics (total, completed, pending)
        """
        search_form = SearchForm(request.args)

        # Basic query: only tasks for the logged-in user
        query = Task.query.filter_by(user_id=g.user.id)

        # Filtering by status
        status_filter = request.args.get("status", "all")
        if status_filter == "completed":
            query = query.filter_by(is_completed=True)
        elif status_filter == "incomplete":
            query = query.filter_by(is_completed=False)

        # Search by title (case-insensitive)
        if search_form.search.data:
            search_term = f"%{search_form.search.data.strip()}%"
            query = query.filter(Task.title.ilike(search_term))

        # Sorting: newest first
        query = query.order_by(Task.created_at.desc())

        # Pagination (simple, 5 tasks per page)
        page = request.args.get("page", 1, type=int)
        per_page = 5
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        tasks = pagination.items

        # Task statistics for the current user
        total_tasks = Task.query.filter_by(user_id=g.user.id).count()
        completed_tasks = Task.query.filter_by(user_id=g.user.id, is_completed=True).count()
        pending_tasks = total_tasks - completed_tasks

        return render_template(
            "dashboard.html",
            tasks=tasks,
            pagination=pagination,
            status_filter=status_filter,
            search_form=search_form,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
        )

    @app.route("/tasks/create", methods=["GET", "POST"])
    @login_required
    def create_task():
        """
        Create a new task.

        - All new tasks are INCOMPLETE by default (enforced both in the model and here).
        """
        form = TaskForm()
        if form.validate_on_submit():
            task = Task(
                title=form.title.data,
                description=form.description.data,
                priority=form.priority.data,
                due_date=form.due_date.data,
                user_id=g.user.id,
                is_completed=False,  # Explicitly mark as incomplete for clarity
            )
            db.session.add(task)
            db.session.commit()
            flash("Task created successfully.", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_task.html", form=form, mode="create")

    @app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_task(task_id):
        """
        Edit an existing task that belongs to the logged-in user.
        """
        task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
        form = TaskForm(obj=task)

        if form.validate_on_submit():
            task.title = form.title.data
            task.description = form.description.data
            task.priority = form.priority.data
            task.due_date = form.due_date.data

            # Allow manually marking the task as completed/incomplete from the edit page.
            previously_completed = task.is_completed
            task.is_completed = form.is_completed.data
            if task.is_completed and not previously_completed:
                # Just transitioned to completed
                task.completed_at = datetime.utcnow()
            elif not task.is_completed:
                # If user unchecks completion, clear timestamp
                task.completed_at = None

            db.session.commit()
            flash("Task updated successfully.", "success")
            return redirect(url_for("dashboard"))

        return render_template("edit_task.html", form=form, mode="edit", task=task)

    @app.route("/tasks/<int:task_id>/toggle_complete", methods=["POST"])
    @login_required
    def toggle_complete(task_id):
        """
        Mark a task as complete or incomplete.

        When marking as complete, we also set the completion timestamp.
        When marking as incomplete again, we clear the completion timestamp.
        """
        task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
        task.is_completed = not task.is_completed
        if task.is_completed:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None
        db.session.commit()
        flash("Task status updated.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/tasks/<int:task_id>/delete", methods=["POST"])
    @login_required
    def delete_task(task_id):
        """
        Delete a task.

        The front-end will ask for a JavaScript confirmation
        before submitting the delete form.
        """
        task = Task.query.filter_by(id=task_id, user_id=g.user.id).first_or_404()
        db.session.delete(task)
        db.session.commit()
        flash("Task deleted.", "info")
        return redirect(url_for("dashboard"))

    # -----------------------------
    # Error handlers
    # -----------------------------

    @app.errorhandler(401)
    def unauthorized(error):
        # Custom 401 page
        return render_template("401.html"), 401

    @app.errorhandler(404)
    def not_found(error):
        # Custom 404 page
        return render_template("404.html"), 404

    return app


app = create_app()


if __name__ == "__main__":
    # Running in development mode. For production (e.g., Google Cloud),
    # a production server such as gunicorn is recommended.
    with app.app_context():
        db.create_all()
    app.run(debug=True)

