from decimal import Decimal
from flask import Blueprint, render_template, session
from sqlalchemy import func

from application.models import Transaction, User
from application.utils import login_required, lookup


home_page = Blueprint('home_page', __name__)


@home_page.route("/")
@login_required
def home():
    """User's home page: Show current portfolio of stocks"""

    # Get user
    user = User.query.filter(User.id == session.get("user_id")).first()

    # Calculate the initial cash basis for this user (sum of all DEPOSIT transactions)
    initialCashBasis = Transaction.query.\
        with_entities(func.sum(Transaction.price)).\
        filter(Transaction.user_id == user.id, Transaction.shares == 0).\
        scalar()

    # Fetch and calculate updated portfolio data
    returned_portfolio, total_market_value, total_gain_loss = get_portfolio_data(
        user, initialCashBasis)

    # Pass portfolio, cash, and totals to Jinja
    return render_template("index.html", portfolio=returned_portfolio,
                           cash=user.cash, totalMarketValue=total_market_value, totalGainLoss=total_gain_loss)


def get_portfolio_data(user, initialCashBasis):
    '''Fetch and calculate user's up-to-date portfolio data. Returns a tuple:
    (portfolio with updated data, total market value, total Gain/Loss)'''

    # To calculate portfolio's total market value, we start with the user's cash balance, and add all stock values below
    total_market_value = Decimal(user.cash)

    returned_portfolio = []
    for stock_row in user.portfolio:
        # Create a dict which will hold updated stock data
        stock = vars(stock_row)
        stockData = lookup(stock['symbol'])
        stock.update(stockData)

        # Calculate stock's current value (current price * shares)
        stock['value'] = Decimal(stockData['price'] * stock['shares'])
        # Add stock value to the total market value calculation
        total_market_value += stock['value']

        # Calculate day change (price day change * shares)
        stock['dayChange'] = stockData['priceChange'] * stock['shares']
        returned_portfolio.append(stock)

        # Total Gain/loss = Portfolio current value - initial cash basis
    total_gain_loss = Decimal(total_market_value - initialCashBasis)

    return returned_portfolio, total_market_value, total_gain_loss
