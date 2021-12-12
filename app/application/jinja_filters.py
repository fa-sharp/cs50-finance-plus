from jinja2 import Markup

def commas(value):
    """Add commas to a numeric value"""
    return f"{value:,}"


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


def cash_flow(value):
    """Format cash flow (highlighting positive or negative amount)"""
    if value < 0:
        return Markup(f"<span class='negative'>${value:,.2f}</span>")
    else:
        return Markup(f"<span class='positive'>${value:,.2f}</span>")


def percent(value):
    """Format percentage (highlighting positive/negative)"""
    if value < 0:
        return Markup(f"<span class='negative'>{value:.2%}</span>")
    else:
        return Markup(f"<span class='positive'>+{value:.2%}</span>")