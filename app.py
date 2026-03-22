import os
from datetime import datetime
from urllib.parse import quote_plus
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Product, PriceHistory
from collections import defaultdict

load_dotenv()

app = Flask(__name__)

# ── settings ──────────────────────────────────────────────────────────────────

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-later')

_pw = quote_plus(os.getenv('DB_PASSWORD', ''))
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://postgres:{_pw}@localhost/pricetracker'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── setup ─────────────────────────────────────────────────────────────────────

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in first.'

# Fixed: replaced legacy User.query.get() with db.session.get()
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ── routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            flash("Login Successful ! Redirecting...")
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Wrong username or password.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

# ── dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    products = Product.query.filter_by(
        user_id=current_user.id
    ).order_by(Product.added_at.desc()).all()

    # Most recently added product shown in the overview card
    last_product = products[0] if products else None

    # Stats for the last product overview card
    last_product_stats = {}
    if last_product:
        history = PriceHistory.query.filter_by(product_id=last_product.id).all()
        prices  = [h.price for h in history]
        last_product_stats = {
            'lowest':      min(prices) if prices else last_product.current_price,
            'highest':     max(prices) if prices else last_product.current_price,
            'average':     round(sum(prices) / len(prices), 2) if prices else last_product.current_price,
            'price_drops': sum(1 for i in range(1, len(prices)) if prices[i] < prices[i - 1]),
        }

    # Total saved = sum of (first recorded price - current price) for each product
    total_saved = 0
    for p in products:
        first_entry = PriceHistory.query.filter_by(
            product_id=p.id
        ).order_by(PriceHistory.checked_at).first()
        if first_entry and p.current_price:
            diff = first_entry.price - p.current_price
            if diff > 0:
                total_saved += diff

    # Count how many products dropped in price today
    price_drops_today = sum(
        1 for p in products
        if p.current_price and p.lowest_price and p.current_price <= p.lowest_price
    )

    # Last checked time — most recently updated product
    last_check = "Never"
    if products:
        last_checked_product = max(
            (p for p in products if p.last_checked),
            key=lambda p: p.last_checked,
            default=None
        )
        if last_checked_product:
            last_check = last_checked_product.last_checked.strftime("%I:%M %p")

    # stats dict — used by home_tab.html quick stats section
    stats = {
        'total_products':    len(products),
        'total_saved':       round(total_saved, 2),
        'price_drops_today': price_drops_today,
        'last_check':        last_check,
    }

    # ── Insights tab data ─────────────────────────────────────────────────────

    # Find the product with the biggest price drop
    best_deal        = None
    best_deal_saving = 0

    for p in products:
        first_entry = PriceHistory.query.filter_by(
            product_id=p.id
        ).order_by(PriceHistory.checked_at.asc()).first()

        if first_entry and p.current_price:
            saving = first_entry.price - p.current_price
            if saving > best_deal_saving:
                best_deal_saving = saving
                best_deal        = p

    # Count how many products dropped in price at least once
    deals_found = 0
    for p in products:
        if p.lowest_price and p.highest_price:
            if p.lowest_price < p.highest_price:
                deals_found += 1

    savings = {
        'total_saved':    round(total_saved, 2),
        'total_products': len(products),
        'deals_found':    deals_found,
        'best_deal':      best_deal,
        'best_deal_drop': round(best_deal_saving, 2),
    }

    # Group products by site and calculate performance
    site_stats = {}

    for p in products:
        site = p.site_name or 'unknown'

        if site not in site_stats:
            site_stats[site] = {
                'site':       site,
                'count':      0,
                'total_drop': 0.0,
                'drops':      0,
            }

        site_stats[site]['count'] += 1

        first_entry = PriceHistory.query.filter_by(
            product_id=p.id
        ).order_by(PriceHistory.checked_at.asc()).first()

        if first_entry and p.current_price:
            drop = first_entry.price - p.current_price
            if drop > 0:
                site_stats[site]['total_drop'] += drop
                site_stats[site]['drops']      += 1

    # Build site performance list
    site_performance = []
    for site, data in site_stats.items():
        avg_drop = round(data['total_drop'] / data['drops'], 2) if data['drops'] > 0 else 0
        site_performance.append({
            'site':     data['site'],
            'count':    data['count'],
            'avg_drop': avg_drop,
            'drops':    data['drops'],
        })

    # Sort best performing site first
    site_performance.sort(key=lambda x: x['avg_drop'], reverse=True)

    # Alerts tab data
    alerts=[]
    
    for p in products:
        
        if not p.alerts_on:
            continue
        
        # Get the first recorded price
        first_entry=PriceHistory.query.filter_by(
            product_id=p.id
        ).order_by(PriceHistory.checked_at.asc()).first()
        
        if not first_entry or not p.current_price:
            continue
        
        # Calculate the drop
        drop_amount=round(first_entry.price-p.current_price,2)
        drop_percent=round((drop_amount/first_entry.price)*100,2)
        
        # Only alert if price actually dropped
        if drop_amount>0:
            alerts.append({
                'product':       p,
                'first_price':   first_entry.price,
                'current_price': p.current_price,
                'drop_amount':   drop_amount,
                'drop_percent':  drop_percent,
            })
            
    # Sort biggest drop first
    alerts.sort(key=lambda x: x['drop_amount'],reverse=True)
    return render_template(
        'dash.html',
        products           = products,
        last_product       = last_product,
        last_product_stats = last_product_stats,
        stats              = stats,
        savings            = savings,
        site_performance   = site_performance,
        alerts             = alerts,
    )

# ── add product ───────────────────────────────────────────────────────────────

@app.route('/product/add', methods=['POST'])
@login_required
def add_product():
    from scraper import scrape_product

    url = request.form.get('url', '').strip()

    if not url:
        flash('Please enter a URL.', 'error')
        return redirect(url_for('dashboard'))

    # Don't add the same URL twice for the same user
    if Product.query.filter_by(user_id=current_user.id, url=url).first():
        flash('Already tracking this product.', 'warning')
        return redirect(url_for('dashboard'))

    # Run the scraper — takes 3–8 seconds depending on the site
    result = scrape_product(url)

    if not result['success']:
        flash(f"Could not scrape that URL: {result['error']}", 'error')
        return redirect(url_for('dashboard'))

    product = Product(
        user_id       = current_user.id,
        url           = url,
        name          = result['name'],
        site_name     = result['site'],
        current_price = result['price'],
        lowest_price  = result['price'],
        highest_price = result['price'],
        currency      = result['currency'],
        image_url     = result['image_url'],
        available     = result['available'],
        last_checked  = datetime.utcnow(),
    )
    db.session.add(product)
    db.session.flush()

    # Save the first price history entry
    history = PriceHistory(product_id=product.id, price=result['price'])
    db.session.add(history)
    db.session.commit()

    flash(f"Now tracking: {result['name']}", 'success')
    return redirect(url_for('dashboard'))

# ── delete product ────────────────────────────────────────────────────────────

@app.route('/product/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(
        id=product_id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(product)
    db.session.commit()
    flash('Product removed.', 'success')
    return redirect(url_for('dashboard'))

# Toggle alert
@app.route('/product/toggle-alert/<int:product_id>',methods=['POST'])
@login_required
def toggle_alert(product_id):
    product=Product.query.filter_by(
        id=product_id,user_id=current_user.id
    ).first_or_404()
    product.alerts_on=not product.alerts_on
    db.session.commit()
    return redirect(url_for('dashboard'))

# ── history API ───────────────────────────────────────────────────────────────

@app.route('/api/history/<int:product_id>')
@login_required
def get_history(product_id):
    import pandas as pd
    import numpy as np

    # Make sure the product belongs to the logged-in user
    product = Product.query.filter_by(
        id      = product_id,
        user_id = current_user.id
    ).first_or_404()

    # Fetch all price records oldest → newest
    records = PriceHistory.query.filter_by(
        product_id = product.id
    ).order_by(PriceHistory.checked_at.asc()).all()

    # ── Raw records for the table ─────────────────────────────────────────────
    raw = [
        {
            'price':      r.price,
            'checked_at': r.checked_at.strftime('%b %d, %Y %I:%M %p')
        }
        for r in records
    ]

    # ── Pandas + Numpy processing ─────────────────────────────────────────────
    chart_data = {}

    if len(records) >= 2:
        prices = [r.price for r in records]
        dates  = [r.checked_at.strftime('%b %d') for r in records]

        df = pd.DataFrame({'price': prices, 'date': dates})

        # Moving average — smooths the line (window of 3, min 1)
        df['moving_avg'] = df['price'].rolling(window=3, min_periods=1).mean().round(2)

        # Percentage change from first recorded price
        first_price         = df['price'].iloc[0]
        df['pct_change']    = ((df['price'] - first_price) / first_price * 100).round(2)

        # Trend — overall direction using numpy linear regression
        x           = np.arange(len(prices))
        slope, _    = np.polyfit(x, prices, 1)
        trend       = 'rising' if slope > 0.01 else 'falling' if slope < -0.01 else 'stable'

        # Stats
        avg_price   = round(float(df['price'].mean()), 2)
        volatility  = round(float(df['price'].std()), 2) if len(prices) > 1 else 0.0
        total_drop  = round(float(df['price'].iloc[0] - df['price'].iloc[-1]), 2)

        chart_data = {
            'labels':      df['date'].tolist(),
            'prices':      df['price'].tolist(),
            'moving_avg':  df['moving_avg'].tolist(),
            'pct_change':  df['pct_change'].tolist(),
            'trend':       trend,
            'avg_price':   avg_price,
            'volatility':  volatility,
            'total_drop':  total_drop,
        }

    return {
        'success':       True,
        'product_id':    product.id,
        'name':          product.name,
        'currency':      product.currency,
        'current_price': product.current_price,
        'lowest_price':  product.lowest_price,
        'highest_price': product.highest_price,
        'site_name':     product.site_name,
        'records':       raw,
        'chart_data':    chart_data,
    }
# ── run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Tables ready.')
    app.run(debug=True)