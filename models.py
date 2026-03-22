from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# users table
class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    # one user can have many products
    products = db.relationship('Product', backref='owner', lazy=True)

    def set_password(self, raw):
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)


# products table - stores every product a user is tracking
class Product(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url           = db.Column(db.Text, nullable=False)
    name          = db.Column(db.String(500), nullable=True)
    current_price = db.Column(db.Float, nullable=True)
    lowest_price  = db.Column(db.Float, nullable=True)
    highest_price = db.Column(db.Float, nullable=True)
    site_name     = db.Column(db.String(100), nullable=True)
    currency      = db.Column(db.String(10), default="USD")
    image_url     = db.Column(db.Text, nullable=True)
    available     = db.Column(db.Boolean, default=True)
    alerts_on     = db.Column(db.Boolean, default=True)
    added_at      = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked  = db.Column(db.DateTime, nullable=True)

    # one product can have many price records
    price_history = db.relationship('PriceHistory', backref='product', lazy=True, cascade='all, delete-orphan')


# price_history table - every time we check a price we save it here
class PriceHistory(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    price      = db.Column(db.Float, nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)