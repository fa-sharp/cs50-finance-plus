import os

import json
from dotenv import load_dotenv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from datetime import datetime
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup
from jinja_filters import usd, cash_flow, commas, percent

# Get environment variables from .env file, if there is one
load_dotenv()

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["cash_flow"] = cash_flow
app.jinja_env.filters["commas"] = commas
app.jinja_env.filters["percent"] = percent

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Get Postgres connection string
postgres_url = os.environ.get("POSTGRES_URL")
if postgres_url is None:
    raise RuntimeError("POSTGRES_URL not set")

# Configure CS50 Library to use Postgres database
db = SQL(postgres_url)

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    userId = session.get("user_id")

    # Get user's portfolio, cash balance
    try:
        db.execute("START TRANSACTION")
        portfolio = db.execute("SELECT * from portfolios WHERE user_id = ? ORDER BY symbol", userId)
        userCash = db.execute("SELECT cash from users WHERE id = ?", userId)[0]['cash']
        # Using the SUM command, we calculate the initial cash basis (sum of all DEPOSIT transactions)
        initialCashBasis = db.execute("SELECT SUM(price) from transactions WHERE shares = 0 AND user_id = ?", userId)[0]['sum']
    except:
        app.logger.exception(f"Error reading from database for user {userId}")
        return apology("Server error!", 500)
    finally:
        db.execute("COMMIT")

    # To calculate portfolio's current total market value, we start with the user's cash balance, and add all stock values below
    pfTotalMarketValue = userCash

    for stock in portfolio:
        # Get current stock data, and merge it into the stock dict
        stockData = lookup(stock['symbol'])
        stock.update(stockData)

        # Calculate total current value (price * shares)
        stock['value'] = stockData['price'] * stock['shares']
        pfTotalMarketValue += stock['value'] # Add stock value to the total market value calculation

        # Calculate day change (price day change * shares)
        stock['dayChange'] = stockData['priceChange'] * stock['shares']

    # Total Gain/loss = Portfolio current value - initial cash basis
    totalGL = pfTotalMarketValue - initialCashBasis

    # Pass portfolio, cash, and totals to Jinja
    return render_template("index.html", portfolio=portfolio, cash=userCash, totalMarketValue=pfTotalMarketValue, totalGainLoss=totalGL)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        userId = session.get("user_id")
        symbol = request.form.get("symbol", default="").upper().strip()
        shares = request.form.get("shares", type=int)

        # Validation
        if symbol == "":
            return apology("must provide stock symbol", 400)
        if not shares or shares <= 0:
            return apology("must enter a positive integer for # of shares", 400)

        # Lookup stock
        stockData = lookup(symbol)
        if not stockData:
            return apology("not a valid stock symbol", 400)

        try:
            db.execute("START TRANSACTION")

            # Get user balance and portfolio
            portfolio = db.execute("SELECT * from portfolios WHERE user_id = ?", userId)
            userCash = db.execute("SELECT cash from users WHERE id = ?", userId)[0]["cash"]

            # Check if user has enough money to buy the stock
            subtotal = stockData["price"] * shares
            if (userCash < subtotal):
                return apology("not enough cash yo!", 400)

            # Check if stock is already in user's portfolio
            existingStock = next((stock for stock in portfolio if stock["symbol"] == symbol), False)
            
            # TRADE THE STOCK: Update all 3 tables
            # Adjust balance in user table
            db.execute("UPDATE users SET cash = ? WHERE id = ?", userCash - subtotal, userId)
            # Update the transaction and portfolio tables
            if existingStock:
                newShares = existingStock['shares'] + shares
                db.execute("UPDATE portfolios SET shares = ? WHERE id = ?", newShares, existingStock['id'])
                db.execute("INSERT INTO transactions (shares, symbol, price, portfolio_id, user_id) VALUES (?, ?, ?, ?, ?)",
                            shares, symbol, stockData["price"], existingStock['id'], userId)   
            else:
                newPortfolioId = db.execute("INSERT INTO portfolios (shares, symbol, user_id) VALUES (?, ?, ?)", shares, symbol, userId)
                db.execute("INSERT INTO transactions (shares, symbol, price, portfolio_id, user_id) VALUES (?, ?, ?, ?, ?)",
                            shares, symbol, stockData["price"], newPortfolioId, userId)
            
            db.execute("COMMIT")
        
        except:
            db.execute("ROLLBACK")
            app.logger.exception("Buying stock failed :(")
            return apology("server error while buying stock!", 500)

        # Phew! If we made it this far, we're done! Put together a nice message for the user.
        flash(f"Bought {shares} {'shares' if shares > 1 else 'share'} of {symbol} at ${stockData['price']:,.2f} for a total of ${subtotal:,.2f}!")
        return redirect("/")

    else:
        symbol = request.args.get("symbol", "")
        return render_template("buy.html", symbol=symbol)


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""

    DEFAULT_LIMIT = 15
    requestedPage = request.form.get("page", type=int, default=1)
    unparsedStartBalances = request.form.get("startBalances")

    # Read starting balances
    try:
        if unparsedStartBalances:
            startBalances = json.loads(unparsedStartBalances)
        else:
            startBalances = [0]
        if type(startBalances) is not list:
            raise
    except:
        app.logger.exception("History: Error reading starting balances")
        return apology("Pagination error!", 500)

    # Determine the direction we're going, and the starting running balance
    if len(startBalances) == requestedPage:
        direction = "next"
        runningBalance = startBalances[-1]
    elif len(startBalances) == requestedPage + 2:
        direction = "prev"
        runningBalance = startBalances[-3]
    else:
        return apology("Pagination error!", 500)

    # Get user's transaction history from database
    userId = session.get("user_id")
    transactions = db.execute("SELECT * from transactions WHERE user_id = ? ORDER BY timestamp LIMIT ? OFFSET ?",
                                userId, DEFAULT_LIMIT + 1, (requestedPage - 1) * DEFAULT_LIMIT)

    # Booleans for whether there is a next/previous page
    nextPage = len(transactions) == DEFAULT_LIMIT + 1
    prevPage = requestedPage != 1

    # Slice the transaction list up to the limit
    transactions = transactions[:DEFAULT_LIMIT]

    for tx in transactions:
        # Add formatted time and date to each transaction
        tx['time'] = tx['timestamp'].strftime('%-I:%M %p')
        tx['date'] = tx['timestamp'].strftime('%b %-d, %Y')

        # Determine action and total cash flow based on positive, negative, or zero number of shares
        if tx['shares'] > 0:
            tx['action'] = 'BUY'
            tx['total'] = -(tx['price'] * tx['shares'])
        elif tx['shares'] == 0:
            tx['action'] = 'DEPOSIT'
            tx['total'] = tx['price']
        else:
            tx['action'] = 'SELL'
            tx['total'] = -(tx['price'] * tx['shares'])

        # Calculate and add to the running cash balance
        runningBalance += tx['total']
        tx['cashBalance'] = runningBalance


    # Save the balance as of the last transaction for pagination
    if direction == 'next':
        startBalances.append(transactions[-1]['cashBalance'])
    else:
        startBalances = startBalances[:-1]

    # Pass transaction history and pagination data to Jinja
    return render_template("history.html", transactions=transactions, startBalances=startBalances,
                            currentPage=requestedPage, hasNextPage=nextPage, hasPreviousPage=prevPage)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # If POST, we'll look up the stock and render the 'quote' template with the updated stock info
    if request.method == "POST":
        symbol = request.form.get("symbol", default="").upper().strip()
        if symbol == "":
            return apology("must provide stock symbol", 400)

        stockData = lookup(symbol)
        if not stockData:
            return apology("not a valid stock symbol", 400)
        else:
            price = stockData.get("price")
            name = stockData.get("name")

        return render_template("quote.html", symbol=symbol, price=price, name=name)

    # If GET, we'll just display the quote form
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)

        # Ensure password == confirmation
        elif not password == request.form.get("confirmation"):
            return apology("passwords must match", 400)

        hashPassword = generate_password_hash(password)
        INITIAL_DEPOSIT = 10000
        
        try:
            db.execute("START TRANSACTION")
            # Insert new user in users table
            userId = db.execute("INSERT INTO users (username, hash, cash) VALUES (?, ?, ?)",
                                username, hashPassword, INITIAL_DEPOSIT)
            # Insert row in transaction table to indicate the initial deposit (0 shares to indicate DEPOSIT)
            db.execute("INSERT INTO transactions (shares, symbol, price, user_id) VALUES (?, ?, ?, ?)",
                   0, '', INITIAL_DEPOSIT, userId)
            db.execute("COMMIT")
        except:
            db.execute("ROLLBACK")
            return apology("username already exists!", 400)

        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    userId = session.get("user_id")

    if request.method == "POST":
        symbol = request.form.get("symbol", default="").upper().strip()
        shares = request.form.get("shares", type=int)

        # Validation
        if symbol == "":
            return apology("must provide stock symbol", 400)
        if not shares or shares == 0:
            return apology("must enter a valid number of shares", 400)
        elif shares < 0:
            return apology("I told you not to do that. I am upset now.")

        # Lookup stock
        stockData = lookup(symbol)
        if not stockData:
            return apology("not a valid stock symbol", 400)

        try:
            db.execute("START TRANSACTION")

            # Get user's cash balance and portfolio
            portfolio = db.execute("SELECT * from portfolios WHERE user_id = ?", userId)
            userCash = db.execute("SELECT cash from users WHERE id = ?", userId)[0]['cash']

            # Check if user has enough of the stock to sell
            currentStock = next((stock for stock in portfolio if stock["symbol"] == symbol), False)
            if not currentStock or currentStock['shares'] < shares:
                return apology("you don't have enough of that stock to sell :(", 400)

            subtotal = stockData["price"] * shares

            # TRADE THE STOCK: Update all 3 tables
            # Adjust balance in user table
            db.execute("UPDATE users SET cash = ? WHERE id = ?", userCash + subtotal, userId)

            # If we're selling all existing shares, delete the portfolio row. Otherwise, update the row with new quantity of shares.
            # Insert row in transaction table (with negative value of shares to indicate SELL)
            if currentStock['shares'] == shares:
                db.execute("DELETE FROM portfolios WHERE id = ?", currentStock['id'])
                db.execute("INSERT INTO transactions (shares, symbol, price, user_id) VALUES (?, ?, ?, ?)",
                       -shares, symbol, stockData["price"], userId)
            else:
                newShares = currentStock['shares'] - shares
                db.execute("UPDATE portfolios SET shares = ? WHERE id = ?", newShares, currentStock['id'])
                db.execute("INSERT INTO transactions (shares, symbol, price, portfolio_id, user_id) VALUES (?, ?, ?, ?, ?)",
                       -shares, symbol, stockData["price"], currentStock["id"], userId)            
            
            db.execute("COMMIT")
        
        except:
            db.execute("ROLLBACK")
            app.logger.exception("Selling stock failed :(")
            return apology("server error while selling stock!", 500)

        # Fingers crossed! If we made it this far, we're done! Put together a nice message for the user.
        flash(f"Sold {shares} {'shares' if shares > 1 else 'share'} of {symbol} at ${stockData['price']:,.2f} for a total of ${subtotal:,.2f}!")
        return redirect("/")

    else:
        symbol = request.args.get("symbol", "")

        # Get user's portfolio, and pass to Jinja
        portfolio = db.execute("SELECT * from portfolios WHERE user_id = ? ORDER BY symbol", userId)
        return render_template("sell.html", portfolio=portfolio, symbol=symbol)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit money in cash account"""

    if request.method == "POST":
        userId = session.get("user_id")
        amount = request.form.get("amount", type=float)

        # Validation
        if not amount or amount <= 0:
            return apology("must enter a positive number for amount to deposit", 400)

        # Get user's cash balance
        userCash = db.execute("SELECT cash from users WHERE id = ?", userId)[0]['cash']

        try:
            db.execute("START TRANSACTION")
            # Insert row in transaction table (with 0 shares to indicate DEPOSIT)
            db.execute("INSERT INTO transactions (shares, symbol, price, user_id) VALUES (?, ?, ?, ?)",
                       0, '', amount, userId)
            # Adjust balance in user table
            db.execute("UPDATE users SET cash = ? WHERE id = ?", userCash + amount, userId)
            db.execute("COMMIT")

        except:
            db.execute("ROLLBACK")
            app.logger.exception("Error depositing cash!")
            return apology("server error while depositing cash!", 500)

        # Done!
        flash(f"Deposited ${amount:,.2f} into cash account!")
        return redirect("/")

    else:
        return render_template("deposit.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
