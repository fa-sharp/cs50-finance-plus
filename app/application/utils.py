from typing import Tuple
import requests
import urllib.parse

from flask import redirect, render_template, session, current_app
from functools import wraps

req = requests.Session()
"""Requests Session object. We can use this to make multiple calls to the same URL, with keep-alive"""

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = current_app.config["API_KEY"]
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={urllib.parse.quote_plus(symbol)}&token={api_key}"
        quote_response = req.get(quote_url)
        quote_response.raise_for_status()
        company_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={urllib.parse.quote_plus(symbol)}&token={api_key}"
        company_response = req.get(company_url)
        company_response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = quote_response.json()
        company = company_response.json()
        data = {
            "name": company["name"],
            "price": float(quote["c"]),
            "symbol": company["ticker"],
            "priceChange": quote['d'],
            "percentChange": quote['dp'] / 100,
            "open": quote['o'],
            "low": quote['l'],
            "high": quote['h'],
            "lastUpdate": quote['t']
        }
        if "logo" in company:
            data["logoUrl"] = company['logo']
        if "weburl" in company:
            data['url'] = company['weburl']

        return data
    except (KeyError, TypeError, ValueError):
        return None


def check_valid_password(password: str) -> Tuple[bool, str]:
    '''Check if a password is valid (has 8 characters, has at least one lowercase, uppercase, and digit,
    and no spaces). Returns a tuple: first element is a boolean of whether this is a valid password. Second
    element is a user-friendly message'''
    if len(password) < 8:
        return (False, "Password must be at least 8 characters!")

    lower, upper, digits, spaces = 0, 0, 0, 0
    for c in password:
        if c.islower():  # count lowercase letters
            lower += 1
        elif c.isupper():  # count uppercase letters
            upper += 1
        elif c.isspace(): # count spaces
            spaces += 1
        elif c.isdigit():  # count digits
            digits+=1
    
    if spaces > 0:
        return (False, "No spaces allowed in password!")
    elif lower < 1:
        return (False, "Password must have at least one lowercase letter!")
    elif upper < 1:
        return (False, "Password must have at least one uppercase letter!")
    elif digits < 1:
        return (False, "Password must have at least one digit!")
    else:
        return (True, "Valid password!")
