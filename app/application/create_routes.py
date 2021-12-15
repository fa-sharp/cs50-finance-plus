from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError

from flask import current_app as app
from application.utils import apology

from application.routes.auth import auth_pages
from application.routes.home import home_page
from application.routes.quote import quote_page
from application.routes.transaction import transaction_pages
from application.routes.history import history_page


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Register routes
app.register_blueprint(auth_pages)
app.register_blueprint(home_page)
app.register_blueprint(quote_page)
app.register_blueprint(transaction_pages)
app.register_blueprint(history_page)


# Define error handler
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
