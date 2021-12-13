from decimal import Decimal
from sqlalchemy.ext.hybrid import hybrid_property
from . import db
from sqlalchemy import Integer, String, Text, Numeric, ForeignKey, DateTime
from sqlalchemy.sql.functions import current_timestamp
from sqlalchemy.orm import relationship


class User(db.Model):

    def __init__(self, username: str, hash: str, cash: float):
        self.username = username
        self.hash = hash
        self.cash = cash

    id = db.Column(Integer, primary_key=True, nullable=False)

    username = db.Column(String(80), unique=True, nullable=False)

    hash = db.Column(Text(), nullable=False)

    cash = db.Column(Numeric(scale=4, precision=25), nullable=False)

    portfolio = relationship(
        'Stock', backref='user', lazy=True, cascade="all, delete", passive_deletes=True, order_by="Stock.symbol")

    transactions = relationship(
        'Transaction', backref='user', lazy=True, cascade="all, delete", passive_deletes=True)

    # @hybrid_property
    # def cash_basis(self):
    #     return sum(tx.price for tx in self.transactions)

    def __repr__(self):
        return '<User %i: %r>' % self.id % self.username


class Stock(db.Model):

    def __init__(self, symbol: str, shares: int, user_id: int = None):
        self.symbol = symbol
        self.shares = shares
        self.user_id = user_id

    id = db.Column(Integer, primary_key=True, nullable=False)

    symbol = db.Column(String(10), nullable=False)

    shares = db.Column(Integer(), nullable=False)

    user_id = db.Column(Integer, ForeignKey(
        'user.id', ondelete="CASCADE"), nullable=False)

    basis_transactions = db.relationship(
        'Transaction', lazy=True, passive_deletes=True)

    def __repr__(self):
        return '<Stock %i: %i shares of %r>' % self.id % self.shares % self.symbol


class Transaction(db.Model):

    def __init__(self, symbol: str, shares: int, price: Decimal, user_id: int = None, stock_id: int = None):
        self.symbol = symbol
        self.shares = shares
        self.price = price
        self.user_id = user_id
        self.stock_id = stock_id

    id = db.Column(Integer, primary_key=True, nullable=False)

    symbol = db.Column(String(10), nullable=False)

    shares = db.Column(Integer(), nullable=False)

    price = db.Column(Numeric(scale=4, precision=20), nullable=False)

    timestamp = db.Column(DateTime(), nullable=False,
                          server_default=current_timestamp())

    user_id = db.Column(Integer, ForeignKey(
        'user.id', ondelete="CASCADE"), nullable=False)

    stock_id = db.Column(Integer, ForeignKey(
        'stock.id', ondelete="SET NULL"), nullable=True)

    def __repr__(self):
        return '<Tx %i: %i shares of %r at %f>' % self.id % self.shares % self.symbol % self.price
