import sqlite3
from datetime import datetime, timedelta

import numpy as np
from sklearn.linear_model import LinearRegression


DATABASE = "store.db"


def predict_sales():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    # =====================================================
    # GET DAILY SALES REVENUE
    # =====================================================

    rows = conn.execute("""
        SELECT
            DATE(order_date) AS sale_date,
            SUM(total_amount) AS daily_sales
        FROM orders
        GROUP BY DATE(order_date)
        ORDER BY DATE(order_date)
    """).fetchall()

    conn.close()


    # =====================================================
    # IF THERE IS NO SALES DATA
    # =====================================================

    if not rows:

        today = datetime.now().date()

        dates = []

        predicted = []

        for i in range(30):

            future_date = today + timedelta(days=i + 1)

            dates.append(
                future_date.strftime("%Y-%m-%d")
            )

            predicted.append(0)


        return {
            "dates": dates,
            "predicted": predicted
        }


    # =====================================================
    # PREPARE SALES DATA
    # =====================================================

    sales = []

    for row in rows:

        sales.append(
            float(row["daily_sales"])
        )


    # =====================================================
    # LINEAR REGRESSION
    # =====================================================

    X = np.array(
        range(len(sales))
    ).reshape(-1, 1)

    y = np.array(sales)


    # If only one order/day exists,
    # use the average instead of regression.

    if len(sales) < 2:

        average_sales = float(
            np.mean(sales)
        )

        future_predictions = [
            round(average_sales, 2)
            for _ in range(30)
        ]

    else:

        model = LinearRegression()

        model.fit(X, y)


        # =================================================
        # PREDICT NEXT 30 DAYS
        # =================================================

        future_X = np.array(
            range(
                len(sales),
                len(sales) + 30
            )
        ).reshape(-1, 1)


        predictions = model.predict(
            future_X
        )


        # Do not allow negative sales.

        future_predictions = [
            round(max(0, float(value)), 2)
            for value in predictions
        ]


    # =====================================================
    # FUTURE DATES
    # =====================================================

    last_date = datetime.strptime(
        rows[-1]["sale_date"],
        "%Y-%m-%d"
    ).date()


    dates = []

    for i in range(30):

        future_date = (
            last_date +
            timedelta(days=i + 1)
        )

        dates.append(
            future_date.strftime("%Y-%m-%d")
        )


    # =====================================================
    # RETURN DATA TO DASHBOARD
    # =====================================================

    return {

        "dates": dates,

        "predicted": future_predictions

    }