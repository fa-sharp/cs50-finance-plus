from flask import Blueprint, render_template, request, session, redirect, current_app, flash
from werkzeug.security import check_password_hash, generate_password_hash

from application import db
from application.models import Transaction, User
from application.utils import apology, check_valid_password


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
    hash_password = generate_password_hash(password)
    try:
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
