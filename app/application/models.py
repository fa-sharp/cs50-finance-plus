from . import db
from sqlalchemy import Integer, String, Text, Float, ForeignKey


class User(db.Model):
    id = db.Column(Integer, primary_key=True, nullable=False)

    username = db.Column(String(80), unique=True, nullable=False)

    hash = db.Column(Text(), nullable=False)

    cash = db.Column(Float(precision=3), nullable=False)

    portfolio = db.relationship(
        'Stock', backref='user', lazy=True, cascade="all, delete", passive_deletes=True)

    def __repr__(self):
        return '<User %i: %r>' % self.id % self.username


class Stock(db.Model):
    id = db.Column(Integer, primary_key=True, nullable=False)

    symbol = db.Column(String(10), nullable=False)

    shares = db.Column(Integer(), nullable=False)

    user_id = db.Column(Integer, ForeignKey(
        'user.id', ondelete="CASCADE"), nullable=False)

    def __repr__(self):
        return '<Stock %i: %i shares of %r>' % self.id % self.shares % self.symbol
