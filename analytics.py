"""Deterministic sales analytics backed by SQLite."""
import sqlite3
import os
import json
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "sales_data.csv"
DB_PATH = BASE_DIR / "sales.db"

REQUIRED_COLUMNS = [
    "Transaction_Id", "Order_date", "Product", "Category", "Region",
    "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
]

def initialize_database(csv_path=CSV_PATH, db_path=DB_PATH):
    """Load CSV into SQLite, normalizing dates and numeric fields."""
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")

    for col in ["Quantity", "Unit_price", "Discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Order_date"] = pd.to_datetime(df["Order_date"], format="%d-%m-%Y", errors="coerce")
    for col in ["Transaction_Id", "Product", "Category", "Region", "Sales_channel", "Status"]:
        df[col] = df[col].astype("string").str.strip()

    # Keep rows with an ID and a parseable date; invalid numeric values remain NULL
    # so they can be excluded and transparently counted by the analytics layer.
    df = df.dropna(subset=["Transaction_Id", "Order_date"])
    df["Order_date"] = df["Order_date"].dt.strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        df.to_sql("sales", conn, if_exists="replace", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(Order_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(Product)")
    return len(df)

def connection():
    if not DB_PATH.exists():
        initialize_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def data_quality():
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
        missing_price = conn.execute("SELECT COUNT(*) FROM sales WHERE Unit_price IS NULL OR Unit_price < 0").fetchone()[0]
        invalid_quantity = conn.execute("SELECT COUNT(*) FROM sales WHERE Quantity IS NULL OR Quantity < 0").fetchone()[0]
        returned = conn.execute("SELECT COUNT(*) FROM sales WHERE lower(Status) = 'returned'").fetchone()[0]
        zero_quantity = conn.execute("SELECT COUNT(*) FROM sales WHERE Quantity = 0").fetchone()[0]
    return {"total_rows": total, "missing_or_invalid_price": missing_price,
            "missing_or_invalid_quantity": invalid_quantity, "returned_rows": returned,
            "zero_quantity_rows": zero_quantity}

# Analytics include completed transactions with valid non-negative quantity and price.
# Revenue = quantity * unit price - transaction discount.
BASE_FILTER = """lower(Status) = 'completed'
AND Quantity IS NOT NULL AND Quantity > 0
AND Unit_price IS NOT NULL AND Unit_price >= 0
AND Discount_amount IS NOT NULL AND Discount_amount >= 0"""

def query_df(sql, params=()):
    with connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def _answer_question_rules(question):
    """Fallback intent interpreter; all figures still come from predefined SQL."""
    q = " ".join((question or "").lower().strip().split())
    if not q:
        return {"ok": False, "answer": "Please enter a question.", "data": [], "columns": [], "intent": "invalid"}
    if len(q) > 500:
        return {"ok": False, "answer": "Question is too long. Please keep it under 500 characters.", "data": [], "columns": [], "intent": "invalid"}

    # Only predefined, read-only SQL templates are used; user text is never executed as SQL.
    if any(x in q for x in ["total revenue", "overall revenue", "revenue overall", "revenue generated", "total sales", "overall sales", "how much revenue"]):
        df = query_df(f"""SELECT ROUND(SUM(Quantity * Unit_price - Discount_amount), 2) AS total_revenue,
            COUNT(*) AS qualifying_transactions FROM sales WHERE {BASE_FILTER}""")
        val = df.iloc[0]["total_revenue"]
        val = 0 if pd.isna(val) else val
        return _result("total_revenue", f"Total revenue is ₹{val:,.2f} across {int(df.iloc[0]['qualifying_transactions'])} qualifying completed transactions.", df)

    if any(x in q for x in ["highest revenue product", "product generated", "top product", "best selling product", "product has the highest", "which product", "revenue by product"]):
        df = query_df(f"""SELECT Product, ROUND(SUM(Quantity * Unit_price - Discount_amount), 2) AS revenue,
            SUM(Quantity) AS units_sold FROM sales WHERE {BASE_FILTER}
            GROUP BY Product ORDER BY revenue DESC, Product ASC""")
        if df.empty:
            return _result("product_revenue", "No qualifying sales records were found.", df)
        top = df.iloc[0]
        return _result("product_revenue", f"{top['Product']} generated the highest revenue: ₹{top['revenue']:,.2f} ({int(top['units_sold'])} units).", df)

    if any(x in q for x in ["monthly revenue", "revenue trend", "month-wise", "monthly sales", "revenue each month", "revenue by month"]):
        df = query_df(f"""SELECT substr(Order_date, 1, 7) AS month,
            ROUND(SUM(Quantity * Unit_price - Discount_amount), 2) AS revenue
            FROM sales WHERE {BASE_FILTER} GROUP BY month ORDER BY month""")
        return _result("monthly_revenue", "Monthly revenue trend (completed transactions only):", df)

    if any(x in q for x in ["highest sales region", "top region", "best region", "region generated", "sales by region", "revenue by region", "which region"]):
        df = query_df(f"""SELECT Region, ROUND(SUM(Quantity * Unit_price - Discount_amount), 2) AS revenue,
            SUM(Quantity) AS units_sold FROM sales WHERE {BASE_FILTER}
            GROUP BY Region ORDER BY revenue DESC, Region ASC""")
        if df.empty:
            return _result("region_revenue", "No qualifying sales records were found.", df)
        top = df.iloc[0]
        return _result("region_revenue", f"{top['Region']} generated the highest sales revenue: ₹{top['revenue']:,.2f}.", df)

    if any(x in q for x in ["compare", "change between", "difference between", "month to month", "between two months", "revenue change"]):
        months = ["january","february","march","april","may","june","july","august","september","october","november","december"]
        found = [i+1 for i,m in enumerate(months) if m in q]
        if len(found) >= 2:
            m1, m2 = found[0], found[1]
            y = "2026"
            labels = [f"{y}-{m1:02d}", f"{y}-{m2:02d}"]
            df = query_df(f"""SELECT substr(Order_date,1,7) AS month,
                ROUND(SUM(Quantity * Unit_price - Discount_amount),2) AS revenue
                FROM sales WHERE {BASE_FILTER} AND substr(Order_date,1,7) IN (?,?)
                GROUP BY month ORDER BY month""", labels)
            vals = {r["month"]: float(r["revenue"] or 0) for _,r in df.iterrows()}
            a, b = vals.get(labels[0], 0), vals.get(labels[1], 0)
            diff = b-a
            pct = (diff/a*100) if a else None
            pct_text = f"{pct:.2f}%" if pct is not None else "not available (first month revenue is zero)"
            msg = f"Revenue changed from ₹{a:,.2f} in {months[m1-1].title()} to ₹{b:,.2f} in {months[m2-1].title()}. Difference: {'increase' if diff >= 0 else 'decrease'} of ₹{abs(diff):,.2f} ({pct_text})."
            return _result("month_comparison", msg, df)
        return {"ok": False, "answer": "Please name two months, for example: How did revenue change between January and February?", "data": [], "columns": [], "intent": "month_comparison"}

    if any(x in q for x in ["data quality", "missing records", "invalid records", "returned transactions"]):
        dq = data_quality()
        df = pd.DataFrame([{"metric": k, "count": v} for k,v in dq.items()])
        return _result("data_quality", "Data-quality summary. Rows with missing prices, zero quantities, and returned status are excluded from revenue calculations.", df)

    return {"ok": False,
            "answer": "I couldn't match that to a supported sales question. Try total revenue, highest-revenue product, monthly revenue trend, highest-sales region, or compare two months.",
            "data": [], "columns": [], "intent": "unsupported"}


# Gemini is used only to classify the user's request into a small allowlisted intent.
# It never writes SQL, and its output is validated before any query is selected.
ALLOWED_INTENTS = {
    "total_revenue", "product_revenue", "monthly_revenue",
    "region_revenue", "month_comparison", "data_quality", "unsupported"
}
MONTH_NAMES = ["january", "february", "march", "april", "may", "june",
               "july", "august", "september", "october", "november", "december"]


def _gemini_classify(question):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        schema = {
            "type": "OBJECT",
            "properties": {
                "intent": {"type": "STRING", "enum": sorted(ALLOWED_INTENTS)},
                "months": {"type": "ARRAY", "items": {"type": "STRING", "enum": MONTH_NAMES}}
            },
            "required": ["intent", "months"]
        }
        prompt = (
            "Classify the user's question about a sales dataset. Return only JSON matching the schema. "
            "Allowed intents: total_revenue (overall revenue/total sales), product_revenue (product with highest revenue), "
            "monthly_revenue (monthly trend), region_revenue (region with highest revenue), "
            "month_comparison (compare revenue between two named months), data_quality (missing/invalid/returned data), "
            "unsupported (anything else). Extract month names only when explicitly mentioned. "
            "Do not answer the question and do not create SQL. User question: " + question
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json", "response_schema": schema, "temperature": 0},
        )
        parsed = json.loads(response.text or "{}")
        intent = parsed.get("intent")
        months = parsed.get("months", [])
        if intent not in ALLOWED_INTENTS or not isinstance(months, list):
            return None
        months = [m.lower() for m in months if isinstance(m, str) and m.lower() in MONTH_NAMES]
        # A month comparison must contain exactly two valid month names.
        if intent == "month_comparison" and len(months) < 2:
            return {"intent": "month_comparison", "months": []}
        return {"intent": intent, "months": months[:2]}
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None


def answer_question(question):
    """Use Gemini to interpret the request, then answer with allowlisted read-only SQL."""
    q = (question or "").strip()
    if not q:
        return {"ok": False, "answer": "Please enter a question.", "data": [], "columns": [], "intent": "invalid"}
    if len(q) > 500:
        return {"ok": False, "answer": "Question is too long. Please keep it under 500 characters.", "data": [], "columns": [], "intent": "invalid"}

    classification = _gemini_classify(q)
    if classification is None:
        return _answer_question_rules(q)

    intent = classification["intent"]
    months = classification["months"]
    canonical = {
        "total_revenue": "What is the total revenue?",
        "product_revenue": "Which product generated the highest revenue?",
        "monthly_revenue": "What is the monthly revenue trend?",
        "region_revenue": "Which region generated the highest sales?",
        "data_quality": "Show data quality summary.",
        "unsupported": "unsupported request"
    }
    if intent == "month_comparison":
        if len(months) < 2:
            return {"ok": False, "answer": "Please name two months, for example: How did revenue change between January and February?", "data": [], "columns": [], "intent": "month_comparison", "method": "Gemini intent classification + predefined read-only SQL"}
        canonical_question = f"How did revenue change between {months[0]} and {months[1]}?"
    else:
        canonical_question = canonical[intent]

    result = _answer_question_rules(canonical_question)
    result["method"] = "Gemini intent classification + predefined read-only SQL" if result.get("ok") else "Gemini intent classification; unsupported request blocked"
    return result


def _result(intent, answer, df):
    # Convert NaN and numpy values to JSON-safe plain Python values.
    safe = df.astype(object).where(pd.notna(df), None)
    return {"ok": True, "intent": intent, "answer": answer,
            "columns": list(safe.columns), "data": safe.to_dict(orient="records"),
            "method": "Read-only predefined SQL query"}
