from decimal import Decimal
from jinja2 import Markup


def commas(value):
    """Add commas to a numeric value"""
    try:
        return f"{value:,}"
    except:
        return value


def usd(value):
    """Format value as USD."""
    try:
        return f"${value:,.2f}"
    except:
        return value


def cash_flow(value):
    """Format cash flow (highlighting positive or negative amount)"""
    try:
        if value < 0:
            return Markup(f"<span class='negative'>${value:,.2f}</span>")
        else:
            return Markup(f"<span class='positive'>${value:,.2f}</span>")
    except:
        return value


def percent(value):
    """Format percentage (highlighting positive/negative)"""
    try:
        if value < 0:
            return Markup(f"<span class='negative'>{value:.2%}</span>")
        else:
            return Markup(f"<span class='positive'>+{value:.2%}</span>")
    except:
        return value


filters = (commas, usd, cash_flow, percent)
