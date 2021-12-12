from decimal import Decimal
import os
import json
from cs50 import SQL
from flask import flash, redirect, render_template, request, session
from sqlalchemy import func
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from flask import current_app as app
from application.models import Stock, Transaction, User
from application.helpers import apology, login_required, lookup
from application.jinja_filters import usd, cash_flow, commas, percent

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom Jinja filters
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["cash_flow"] = cash_flow
app.jinja_env.filters["commas"] = commas
app.jinja_env.filters["percent"] = percent

# Get Postgres connection string
postgres_url = os.environ.get("POSTGRES_URL")
if postgres_url is None:
    raise RuntimeError("POSTGRES_URL not set")

# Configure CS50 Library to use Postgres database
# db = SQL(postgres_url)

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user = User.query.filter(User.id == session.get("user_id")).first()
    
    # Calculate the initial cash basis for this user (sum of all DEPOSIT transactions)
    initialCashBasis = Transaction.query.\
                    with_entities(func.sum(Transaction.price)).\
                    filter(Transaction.user_id == user.id, Transaction.shares == 0).\
                    scalar()

    # To calculate portfolio's current total market value, we start with the user's cash balance, and add all stock values below
    pfTotalMarketValue = user.cash
    
    returned_portfolio = []
    for stock_row in user.portfolio:
        # Create a dict which will hold updated stock data
        stock = vars(stock_row)
        stockData = lookup(stock['symbol'])
        stock.update(stockData)

        # Calculate total current value (price * shares)
        stock['value'] = Decimal(stockData['price'] * stock['shares'])
        pfTotalMarketValue += stock['value'] # Add stock value to the total market value calculation

        # Calculate day change (price day change * shares)
        stock['dayChange'] = stockData['priceChange'] * stock['shares']
        returned_portfolio.append(stock)

    # Total Gain/loss = Portfolio current value - initial cash basis
    totalGL = pfTotalMarketValue - initialCashBasis

    # Pass portfolio, cash, and totals to Jinja
    return render_template("index.html", portfolio=returned_portfolio, cash=user.cash, totalMarketValue=pfTotalMarketValue, totalGainLoss=totalGL)


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
    if session.get("user_id") is not None:
        session.pop("user_id")

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


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.pop("user_id")

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
            # Create new user and initial deposit transaction
            new_user = User(username=username, hash=hashPassword, cash=INITIAL_DEPOSIT)
            initial_deposit = Transaction("", 0, INITIAL_DEPOSIT)
            new_user.transactions.append(initial_deposit)

            db.session.add(new_user)
            db.session.commit()

        except:
            db.session.rollback()
            return apology("username already exists!", 400)

        return render_template("login.html")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_id = session.get("user_id")
    user = User.query.filter(User.id == user_id).first()

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
        
        # Check if user has enough of the stock to sell
        current_stock = next((stock for stock in user.portfolio if stock.symbol == symbol), False)
        if not current_stock or current_stock.shares < shares:
            return apology("you don't have enough of that stock to sell :(", 400)

        subtotal = Decimal(stockData["price"] * shares)

        # TRADE THE STOCK
        try:
            # Adjust user's cash balance
            user.cash += subtotal

            # If we're selling all existing shares, delete the current stock
            # Otherwise, update the current stock with new quantity of shares.
            # Also insert row in transaction table (with negative value of shares to indicate SELL)
            if current_stock.shares == shares:
                sell_transaction = Transaction(symbol, -shares, stockData["price"], user_id)
                db.session.add(sell_transaction)
                db.session.delete(current_stock)
            
            else:
                sell_transaction = Transaction(symbol, -shares, stockData["price"], user_id, current_stock.id)
                db.session.add(sell_transaction)
                current_stock.shares -= shares
            
            db.session.commit()
        
        except:
            db.session.rollback()
            app.logger.exception("Selling stock failed :(")
            return apology("server error while selling stock!", 500)

        # Fingers crossed! If we made it this far, we're done! Put together a nice message for the user.
        flash(f"Sold {shares} {'shares' if shares > 1 else 'share'} of {symbol} at ${stockData['price']:,.2f} for a total of ${subtotal:,.2f}!")
        return redirect("/")

    else:
        symbol = request.args.get("symbol", "")

        # Pass user's portfolio to Jinja
        return render_template("sell.html", portfolio=user.portfolio, symbol=symbol)


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit money in cash account"""

    if request.method == "POST":
        user_id = session.get("user_id")
        amount = request.form.get("amount", type=float)

        # Validation
        if not amount or amount <= 0:
            return apology("must enter a positive number for amount to deposit", 400)

        # Get user's cash balance
        user = User.query.filter(User.id == user_id).first()

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
