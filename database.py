import psycopg2
import psycopg2.extras
import config

def get_db():
    """
    Opens and returns a fresh database connection.
    Every route that needs the database calls this function.
    We always close the connection after we are done to avoid leaks.
    """
    conn = psycopg2.connect(**config.DB_CONFIG)
    return conn

def init_db():
    """
    Creates all three tables if they do not already exist.
    Called once when the Flask app starts.
    IF NOT EXISTS means running it again never breaks anything.
    """
    conn   = get_db()
    cursor = conn.cursor()

    # Users table
    # Stores every registered user
    # password is stored as a hash, never plain text
    # UNIQUE on username and email means no duplicates allowed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email    VARCHAR(200) NOT NULL UNIQUE,
            password TEXT        NOT NULL
        )
    """)

    # Products table
    # Stores every product a user is tracking
    # user_id links back to the users table so we know who owns this product
    # current_price is updated every time the scheduler re-checks
    # NUMERIC(10,2) means up to 10 digits with 2 decimal places, perfect for prices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id            SERIAL        PRIMARY KEY,
            user_id       INTEGER       NOT NULL REFERENCES users(id),
            url           TEXT          NOT NULL,
            name          TEXT          NOT NULL,
            current_price NUMERIC(10,2) NOT NULL,
            date_added    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Price history table
    # Every single price check creates one new row here
    # This is how we build the price chart over time
    # product_id links back to the products table
    # checked_at records exactly when this price was seen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id         SERIAL        PRIMARY KEY,
            product_id INTEGER       NOT NULL REFERENCES products(id),
            price      NUMERIC(10,2) NOT NULL,
            checked_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()  # saves all the CREATE TABLE commands permanently
    cursor.close()
    conn.close()
    print("Database initialized successfully")