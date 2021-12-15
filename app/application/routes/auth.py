from flask import Blueprint, render_template, request, session, redirect, current_app, flash
from werkzeug.security import check_password_hash, generate_password_hash

from application import db
from application.models import Transaction, User
from application.utils import apology, check_valid_password, login_required


auth_pages = Blueprint('auth_pages', __name__)


@auth_pages.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    INITIAL_DEPOSIT = 10000 # The initial deposit for all users

    # GET: display registration page
    if request.method == "GET":
        return render_template("register.html")

    # POST: Register a new user
    username = request.form.get("username")
    password = request.form.get("password")

    # Ensure username was submitted
    if not username:
        return apology("must provide username", 400)
    
    # Check if username already exists
    user_exists = db.session.query(
        User.query.filter(User.username == username).exists()).scalar()
    if user_exists:
        return apology("username already exists!", 400)

    # Ensure password was submitted
    if not password:
        return apology("must provide password", 400)

    # Check if password is valid
    valid, password_message = check_valid_password(password)
    if not valid:
        return apology(password_message, 400)

    # Ensure password == confirmation
    if not password == request.form.get("confirmation"):
        return apology("passwords must match", 400)

    # If all is good, hash the password and create a new user!
    try:
        hash_password = generate_password_hash(password)
        new_user = User(username=username,
                        hash=hash_password, cash=INITIAL_DEPOSIT)

        db.session.add(new_user)
        db.session.flush() # Flush in order to generate the new user id

        initial_deposit = Transaction("", 0, INITIAL_DEPOSIT, new_user.id)
        db.session.add(initial_deposit)
        
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception("Error adding user to DB")
        return apology("Server error registering user!", 500)

    # If successful, redirect to login page and display a friendly message
    flash("You're successfully registered! Login and start trading!!")
    return render_template("login.html")


@auth_pages.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.pop("user_id", None)

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 403)

        # Query database for username
        existing_user = User.query.filter(User.username == username).first()

        # Ensure username exists and password is correct
        if existing_user and check_password_hash(existing_user.hash, password):
            # Save user in Flask Session
            session["user_id"] = existing_user.id
            return redirect("/")

        else:
            return apology("invalid username and/or password", 403)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@auth_pages.route("/logout")
def logout():
    """Log user out"""

    # Forget session data
    session.pop("user_id", None)
    session.pop("start_balances", None)

    # Redirect user to login form
    return redirect("/")



@auth_pages.route("/profile")
@login_required
def profile():
    """A profile page where users can change their password and delete their profile"""

    return render_template("profile.html")


@auth_pages.route("/profile/changePassword", methods=["POST"])
@login_required
def change_password():
    """Change the user's password"""

    user_id = session.get("user_id")
    old_password = request.form.get("oldPassword", "")
    new_password = request.form.get("newPassword", "")
    confirmation = request.form.get("confirmation", "")

    user: User = User.query.filter(User.id == user_id).first()

    # Ensure old password is correct
    if not check_password_hash(user.hash, old_password):
        return apology("Incorrect password!", 400)
    
    # Ensure new password is valid
    valid, password_message = check_valid_password(new_password)
    if not valid:
        return apology(password_message, 400)
    
    # Ensure new password = confirmation
    if not new_password == confirmation:
        return apology("Passwords don't match!", 400)

    # Hash and save the new password
    try:
        current_app.logger.warn(f"Changing password of User {user}")
        hash_password = generate_password_hash(new_password)
        user.hash = hash_password
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception(f"Error changing password of User {user}")
        return apology("Server error while changing password!", 500)
    
    # Return to home page with confirmation message
    flash("Successfully changed password!")
    return redirect("/")


@auth_pages.route("/profile/deleteProfile", methods=["POST"])
@login_required
def delete_user():
    """Delete user profile and data"""

    confirm_yes = request.form.get("confirmCheck", "")
    confirm_delete = request.form.get("confirmText", "")

    # Check if user meant to delete their profile
    if confirm_yes != "yes" or confirm_delete != "DELETE":
        flash("Oops! Profile not deleted!")
        return redirect("/profile")

    user_id = session.get("user_id")
    user: User = User.query.filter(User.id == user_id).first()
    
    # Delete all user data in DB
    try:
        current_app.logger.warn(f"Deleting User {user}!!")
        db.session.delete(user)
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception(f"Error deleting User {user}")
        return apology("Server error while deleting user!", 500)

    # Clear session
    session.pop("user_id", None)
    session.pop("start_balances", None)

    return redirect("/")