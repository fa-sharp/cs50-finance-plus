from decimal import Decimal
from flask import Blueprint, render_template, request, session

from application.models import Transaction
from application.utils import login_required


history_page = Blueprint('history_page', __name__)


@history_page.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions"""

    DEFAULT_LIMIT = 10
    requested_page = request.form.get("page", type=int, default=1)

    # Determine starting balance(s) for each page
    start_balances = session.get("start_balances")
    if requested_page == 1 or start_balances is None or type(start_balances) is not list:
        start_balances = [Decimal(0)]
        requested_page = 1

    # Determine direction and starting running balance for the current page
    if len(start_balances) == requested_page:
        direction = "next"
        running_balance = Decimal(start_balances[-1])
    elif len(start_balances) == requested_page + 2:
        direction = "prev"
        running_balance = Decimal(start_balances[-3])
    else:
        requested_page = 1
        direction = "next"
        running_balance = Decimal(0)

    # Get user's transaction history from database
    user_id = session.get("user_id")
    transaction_page = Transaction.query.\
        filter(Transaction.user_id == user_id).\
        order_by(Transaction.timestamp).\
        paginate(page=requested_page, per_page=DEFAULT_LIMIT)
    formatted_transactions = get_formatted_transactions(transaction_page, running_balance)

    # If we're going forwards, save the balance as of the last transaction for pagination
    if direction == 'next':
        start_balances.append(formatted_transactions[-1]['cashBalance'])
    # If going backwards, slice the last element of the starting balances
    else:
        start_balances = start_balances[:-1]

    # Save starting balances in session
    session["start_balances"] = start_balances

    # Pass transaction history and pagination data to Jinja
    return render_template("history.html", transactions=formatted_transactions, currentPage=requested_page,
                           hasNextPage=transaction_page.has_next, hasPreviousPage=transaction_page.has_prev)


def get_formatted_transactions(transaction_page, running_balance: Decimal):
    '''Make a formatted list of transactions (with time, date, action, etc.)'''
    transactions = []
    
    for transaction_item in transaction_page.items:
        
        # Make a dict from the transaction data
        tx = vars(transaction_item)
        
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
        running_balance += tx['total']
        tx['cashBalance'] = running_balance

        transactions.append(tx)
    
    return transactions
