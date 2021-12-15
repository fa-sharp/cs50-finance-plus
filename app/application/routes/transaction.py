from decimal import Decimal
from flask import Blueprint, render_template, request, session, flash, redirect, current_app

from application import db
from application.models import Transaction, User, Stock
from application.utils import login_required, apology, lookup


transaction_pages = Blueprint('transaction_pages', __name__)


@transaction_pages.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "GET":
        symbol = request.args.get("symbol", "")
        return render_template("buy.html", symbol=symbol)

    user_id = session.get("user_id")
    symbol = request.form.get("symbol", default="").upper().strip()
    shares = request.form.get("shares", type=int, default=None)

    # Validation
    if symbol == "":
        return apology("must provide stock symbol", 400)
    if not shares or shares <= 0:
        return apology("must enter a positive integer for # of shares", 400)

    # Lookup stock
    stockData = lookup(symbol)
    if not stockData:
        return apology("not a valid stock symbol", 400)

    # Get user data
    user: User = User.query.filter(User.id == user_id).first()

    # Check if user has enough money to buy the stock
    subtotal = Decimal(stockData["price"] * shares)
    if (user.cash < subtotal):
        return apology("not enough cash yo!", 400)

    # TRADE THE STOCK
    try:
        perform_buy_transaction(user, symbol, shares, stockData, subtotal)
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception("Buying stock failed :(")
        return apology("server error while buying stock!", 500)

    # Phew! If we made it this far, we're done! Put together a nice message for the user.
    flash(f"Bought {shares} {'shares' if shares > 1 else 'share'} of {symbol} at \
            ${stockData['price']:,.2f} for a total of ${subtotal:,.2f}!")
    return redirect("/")


def perform_buy_transaction(user: User, symbol: str, shares: int, stockData: dict, subtotal: Decimal):
    # Adjust user's cash balance
    user.cash -= subtotal

    # Check if stock is already in user's portfolio
    existing_stock = next(
        (stock for stock in user.portfolio if stock.symbol == symbol), False)

    # Add transaction, and add/update the stock
    if existing_stock:
        buy_transaction = Transaction(
            symbol, shares, stockData["price"], user.id, existing_stock.id)
        existing_stock.shares += shares

        db.session.add(buy_transaction)
    
    else:
        buy_transaction = Transaction(
            symbol, shares, stockData["price"], user.id)
        new_stock = Stock(symbol, shares, user.id)
        new_stock.basis_transactions.append(buy_transaction)

        db.session.add(new_stock)


@transaction_pages.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    user_id = session.get("user_id")
    user = User.query.filter(User.id == user_id).first()

    # GET: Display user's current stocks, which they can select from
    if request.method == "GET":
        symbol = request.args.get("symbol", "")
        return render_template("sell.html", portfolio=user.portfolio, symbol=symbol)

    # POST: Sell a stock
    symbol = request.form.get("symbol", default="").upper().strip()
    shares = request.form.get("shares", type=int, default=None)

    # Validation
    if symbol == "":
        return apology("must provide stock symbol", 400)
    if not shares or shares == 0:
        return apology("must enter a valid number of shares", 400)
    elif shares < 0:
        return apology("I told you not to do that. I am upset now.")

    # Lookup stock
    stock_data = lookup(symbol)
    if not stock_data:
        return apology("not a valid stock symbol", 400)

    # Check if user has enough of the stock to sell
    current_stock = next(
        (stock for stock in user.portfolio if stock.symbol == symbol), False)
    if not current_stock or current_stock.shares < shares:
        return apology("you don't have enough of that stock to sell :(", 400)

    # TRADE THE STOCK
    try:
        subtotal = perform_sell_transaction(
            user, symbol, shares, stock_data, current_stock)
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception("Selling stock failed :(")
        return apology("server error while selling stock!", 500)

    # Fingers crossed! If we made it this far, we're done! Put together a nice message for the user.
    flash(
        f"Sold {shares} {'shares' if shares > 1 else 'share'} of {symbol} at ${stock_data['price']:,.2f} for a total of ${subtotal:,.2f}!")
    return redirect("/")


def perform_sell_transaction(user: User, symbol: str, shares: int, stock_data: dict, current_stock: Stock):

    subtotal = Decimal(stock_data["price"] * shares)

    # Adjust user's cash balance
    user.cash += subtotal

    # If we're selling all existing shares, delete the current stock. Otherwise, update the current stock with new quantity of shares.
    # Also insert row in transaction table (with negative value of shares to indicate SELL)
    if current_stock.shares == shares:
        sell_transaction = Transaction(
            symbol, -shares, stock_data["price"], user.id)
        db.session.add(sell_transaction)
        db.session.delete(current_stock)
    else:
        sell_transaction = Transaction(
            symbol, -shares, stock_data["price"], user.id, current_stock.id)
        db.session.add(sell_transaction)
        current_stock.shares -= shares

    return subtotal


@transaction_pages.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit money in cash account"""

    # GET: Display deposit page
    if request.method == "GET":
        return render_template("deposit.html")

    # POST: Deposit cash
    amount = request.form.get("amount", type=Decimal, default=None)

    # Validation
    if not amount or amount <= 0:
        return apology("must enter a positive number for amount to deposit", 400)

    # Get user
    user_id = session.get("user_id")
    user = User.query.filter(User.id == user_id).first()

    try:
        # Create new transaction (with 0 shares to indicate DEPOSIT)
        deposit_transaction = Transaction('', 0, amount, user.id)
        db.session.add(deposit_transaction)

        # Adjust user cash balance
        user.cash += amount
        db.session.commit()
    except:
        db.session.rollback()
        current_app.logger.exception("Error depositing cash!")
        return apology("server error while depositing cash!", 500)

    # Done!
    flash(f"Deposited ${amount:,.2f} into cash account!")
    return redirect("/")
