from flask import Flask, render_template, redirect, url_for, request, flash
import sqlite3
from datetime import datetime
import prediction

app = Flask(__name__)
app.secret_key = "gym_supplement_store_secret"

DATABASE = "store.db"


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# INITIALIZE DATABASE
# =========================================================

def init_db():

    conn = get_db()
    cursor = conn.cursor()

    # PRODUCTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            image TEXT,
            stock INTEGER DEFAULT 10
        )
    """)

    # Add stock column if old database does not have it
    cursor.execute("PRAGMA table_info(products)")
    columns = [row["name"] for row in cursor.fetchall()]

    if "stock" not in columns:
        cursor.execute("""
            ALTER TABLE products
            ADD COLUMN stock INTEGER DEFAULT 10
        """)

    # CART
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER DEFAULT 1
        )
    """)

    # ORDERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            address TEXT NOT NULL,
            total_amount REAL NOT NULL,
            order_date TEXT NOT NULL
        )
    """)

    # ORDER ITEMS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        )
    """)

    # -----------------------------------------------------
    # INSERT PRODUCTS IF EMPTY
    # -----------------------------------------------------

    cursor.execute("SELECT COUNT(*) AS count FROM products")
    count = cursor.fetchone()["count"]

    if count == 0:

        products = [
            (
                "Whey Protein",
                2999,
                "High quality whey protein for muscle growth.",
                "whey.jpg",
                20
            ),
            (
                "Creatine Monohydrate",
                999,
                "Creatine supplement for strength and performance.",
                "creatine.jpg",
                25
            ),
            (
                "Mass Gainer",
                2499,
                "Mass gainer for healthy weight and muscle gain.",
                "massgainer.jpg",
                15
            ),
            (
                "Pre Workout",
                1499,
                "Pre workout supplement for energy and performance.",
                "preworkout.jpg",
                20
            ),
            (
                "BCAA",
                1199,
                "BCAA supplement for recovery and muscle support.",
                "bcaa.jpg",
                20
            ),
            (
                "Glutamine",
                899,
                "Glutamine supplement for recovery.",
                "glutamine.jpg",
                20
            )
        ]

        cursor.executemany("""
            INSERT INTO products
            (name, price, description, image, stock)
            VALUES (?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    search = request.args.get("search", "").strip()

    conn = get_db()

    if search:

        products = conn.execute("""
            SELECT *
            FROM products
            WHERE name LIKE ?
               OR description LIKE ?
            ORDER BY id
        """, (
            "%" + search + "%",
            "%" + search + "%"
        )).fetchall()

    else:

        products = conn.execute("""
            SELECT *
            FROM products
            ORDER BY id
        """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        products=products,
        search=search
    )


# =========================================================
# PRODUCT DETAILS
# =========================================================

@app.route("/product/<int:product_id>")
def product_details(product_id):

    conn = get_db()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    conn.close()

    if product is None:
        return "Product not found"

    return render_template(
        "product.html",
        product=product
    )


# =========================================================
# ADD TO CART
# =========================================================

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    conn = get_db()

    product = conn.execute("""
        SELECT *
        FROM products
        WHERE id = ?
    """, (product_id,)).fetchone()

    if product is None:

        conn.close()
        return "Product not found"

    if product["stock"] <= 0:

        conn.close()

        flash("This product is out of stock.")

        return redirect(url_for("home"))

    existing = conn.execute("""
        SELECT *
        FROM cart
        WHERE product_id = ?
    """, (product_id,)).fetchone()

    if existing:

        if existing["quantity"] >= product["stock"]:

            conn.close()

            flash("Maximum available stock already added.")

            return redirect(url_for("cart"))

        conn.execute("""
            UPDATE cart
            SET quantity = quantity + 1
            WHERE product_id = ?
        """, (product_id,))

    else:

        conn.execute("""
            INSERT INTO cart
            (
                product_id,
                product_name,
                price,
                quantity
            )
            VALUES (?, ?, ?, ?)
        """, (
            product["id"],
            product["name"],
            product["price"],
            1
        ))

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CART
# =========================================================

@app.route("/cart")
def cart():

    conn = get_db()

    items = conn.execute("""
        SELECT *
        FROM cart
        ORDER BY id
    """).fetchall()

    conn.close()

    total = 0

    for item in items:
        total += item["price"] * item["quantity"]

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


# =========================================================
# INCREASE
# =========================================================

@app.route("/increase/<int:cart_id>")
def increase(cart_id):

    conn = get_db()

    item = conn.execute("""
        SELECT *
        FROM cart
        WHERE id = ?
    """, (cart_id,)).fetchone()

    if item:

        product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
        """, (item["product_id"],)).fetchone()

        if product and item["quantity"] < product["stock"]:

            conn.execute("""
                UPDATE cart
                SET quantity = quantity + 1
                WHERE id = ?
            """, (cart_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# =========================================================
# DECREASE
# =========================================================

@app.route("/decrease/<int:cart_id>")
def decrease(cart_id):

    conn = get_db()

    item = conn.execute("""
        SELECT quantity
        FROM cart
        WHERE id = ?
    """, (cart_id,)).fetchone()

    if item:

        if item["quantity"] > 1:

            conn.execute("""
                UPDATE cart
                SET quantity = quantity - 1
                WHERE id = ?
            """, (cart_id,))

        else:

            conn.execute("""
                DELETE FROM cart
                WHERE id = ?
            """, (cart_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# =========================================================
# REMOVE
# =========================================================

@app.route("/remove/<int:cart_id>")
def remove(cart_id):

    conn = get_db()

    conn.execute("""
        DELETE FROM cart
        WHERE id = ?
    """, (cart_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CLEAR CART
# =========================================================

@app.route("/clear_cart")
def clear_cart():

    conn = get_db()

    conn.execute("DELETE FROM cart")

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    conn = get_db()

    items = conn.execute("""
        SELECT *
        FROM cart
        ORDER BY id
    """).fetchall()

    if not items:

        conn.close()

        return redirect(url_for("cart"))

    total = 0

    # Check stock and calculate total
    for item in items:

        product = conn.execute("""
            SELECT *
            FROM products
            WHERE id = ?
        """, (item["product_id"],)).fetchone()

        if product is None:

            conn.close()

            return "Product not found"

        if item["quantity"] > product["stock"]:

            conn.close()

            flash(
                f"Not enough stock for {product['name']}."
            )

            return redirect(url_for("cart"))

        total += item["price"] * item["quantity"]

    # -----------------------------------------------------
    # PLACE ORDER
    # -----------------------------------------------------

    if request.method == "POST":

        customer_name = request.form.get(
            "customer_name",
            ""
        ).strip()

        customer_mobile = request.form.get(
            "customer_mobile",
            ""
        ).strip()

        customer_address = request.form.get(
            "customer_address",
            ""
        ).strip()

        if (
            not customer_name
            or not customer_mobile
            or not customer_address
        ):

            conn.close()

            flash("Please fill all customer details.")

            return redirect(url_for("checkout"))

        # Check stock again before saving order
        for item in items:

            product = conn.execute("""
                SELECT *
                FROM products
                WHERE id = ?
            """, (
                item["product_id"],
            )).fetchone()

            if product is None:

                conn.close()

                flash(
                    f"Product {item['product_name']} not found."
                )

                return redirect(url_for("cart"))

            if item["quantity"] > product["stock"]:

                conn.close()

                flash(
                    f"Not enough stock for "
                    f"{product['name']}."
                )

                return redirect(url_for("cart"))

        order_date = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        cursor = conn.cursor()

        # Save order
        cursor.execute("""
            INSERT INTO orders
            (
                customer_name,
                mobile,
                address,
                total_amount,
                order_date
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            customer_name,
            customer_mobile,
            customer_address,
            total,
            order_date
        ))

        order_id = cursor.lastrowid

        # Save order items + reduce stock
        for item in items:

            cursor.execute("""
                INSERT INTO order_items
                (
                    order_id,
                    product_id,
                    product_name,
                    price,
                    quantity
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                item["product_id"],
                item["product_name"],
                item["price"],
                item["quantity"]
            ))

            cursor.execute("""
                UPDATE products
                SET stock = stock - ?
                WHERE id = ?
            """, (
                item["quantity"],
                item["product_id"]
            ))

        # Empty cart
        cursor.execute("""
            DELETE FROM cart
        """)

        conn.commit()
        conn.close()

        return redirect(
            url_for(
                "success",
                order_id=order_id
            )
        )

    # GET request
    conn.close()

    return render_template(
        "checkout.html",
        items=items,
        total=total
    )


# =========================================================
# SUCCESS
# =========================================================

@app.route("/success/<int:order_id>")
def success(order_id):

    conn = get_db()

    order = conn.execute("""
        SELECT *
        FROM orders
        WHERE id = ?
    """, (
        order_id,
    )).fetchone()

    items = conn.execute("""
        SELECT *
        FROM order_items
        WHERE order_id = ?
    """, (
        order_id,
    )).fetchall()

    conn.close()

    if order is None:

        return "Order not found"

    return render_template(
        "success.html",
        order=order,
        items=items
    )


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    conn = get_db()

    # =====================================================
    # ORDERS + PRODUCTS ORDERED
    # =====================================================

    order_data = conn.execute("""
        SELECT
            o.id AS order_id,
            o.customer_name,
            o.mobile,
            o.address,
            o.total_amount,
            o.order_date,
            oi.product_name,
            oi.quantity
        FROM orders o
        LEFT JOIN order_items oi
            ON o.id = oi.order_id
        ORDER BY o.id DESC
    """).fetchall()


    # =====================================================
    # ALL PRODUCTS
    # =====================================================

    products = conn.execute("""
        SELECT *
        FROM products
        ORDER BY id
    """).fetchall()


    # =====================================================
    # TOTAL SALES
    # =====================================================

    total_sales = conn.execute("""
        SELECT COALESCE(
            SUM(total_amount), 0
        ) AS total
        FROM orders
    """).fetchone()["total"]


    # =====================================================
    # TOTAL ORDERS
    # =====================================================

    order_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """).fetchone()["count"]


    # =====================================================
    # TOTAL CUSTOMERS
    # =====================================================

    customer_count = conn.execute("""
        SELECT COUNT(
            DISTINCT mobile
        ) AS count
        FROM orders
    """).fetchone()["count"]


    # =====================================================
    # TOTAL PRODUCTS
    # =====================================================

    product_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM products
    """).fetchone()["count"]


    conn.close()


    return render_template(
        "admin.html",

        order_data=order_data,

        products=products,

        total_sales=total_sales,

        order_count=order_count,

        customer_count=customer_count,

        product_count=product_count
    )
# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    conn = get_db()

    # Total sales money
    total_sales = conn.execute("""
        SELECT COALESCE(
            SUM(total_amount), 0
        ) AS total
        FROM orders
    """).fetchone()["total"]

    # Total orders
    total_orders = conn.execute("""
        SELECT COUNT(*) AS count
        FROM orders
    """).fetchone()["count"]

    # Unique customers
    total_customers = conn.execute("""
        SELECT COUNT(
            DISTINCT mobile
        ) AS count
        FROM orders
    """).fetchone()["count"]

    # -----------------------------------------------------
    # EVERY PRODUCT + ACTUAL UNITS SOLD
    # -----------------------------------------------------

    product_sales_rows = conn.execute("""
        SELECT
            p.id,
            p.name,
            COALESCE(
                SUM(oi.quantity), 0
            ) AS units_sold
        FROM products p
        LEFT JOIN order_items oi
            ON p.id = oi.product_id
        GROUP BY
            p.id,
            p.name
        ORDER BY p.id
    """).fetchall()

    product_sales = []

    for row in product_sales_rows:

        product_sales.append({
            "name": row["name"],
            "units_sold": int(row["units_sold"])
        })

    # -----------------------------------------------------
    # SALES PREDICTION
    # -----------------------------------------------------

    predicted_sales = prediction.predict_sales()

    conn.close()

    return render_template(
        "dashboard.html",
        total_sales=total_sales,
        total_orders=total_orders,
        total_customers=total_customers,
        product_sales=product_sales,
        predicted_sales=predicted_sales
    )


# =========================================================
# DELETE ORDER
# =========================================================

@app.route("/admin/delete_order/<int:order_id>")
def delete_order(order_id):

    conn = get_db()

    conn.execute("""
        DELETE FROM order_items
        WHERE order_id = ?
    """, (order_id,))

    conn.execute("""
        DELETE FROM orders
        WHERE id = ?
    """, (order_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)