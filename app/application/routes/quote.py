from flask import Blueprint, render_template, request

from application.utils import login_required, apology, lookup


quote_page = Blueprint('quote_page', __name__)


@quote_page.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # If GET, we'll display the quote form
    if request.method == "GET":
        return render_template("quote.html")

    # If POST, we'll look up the stock and render the 'quote' template with the updated stock info
    symbol = request.form.get("symbol", default="").upper().strip()
    if symbol == "":
        return apology("must provide stock symbol", 400)

    stockData = lookup(symbol)
    if not stockData:
        return apology("error getting stock price", 400)
    else:
        price = stockData.get("price")
        name = stockData.get("name")
        logoUrl = stockData.get("logoUrl")
        url = stockData.get("url")

    return render_template("quote.html", symbol=symbol, price=price, name=name, logoUrl=logoUrl, url=url)
