Mini AI Business Intelligence Assistant

A small Python application for asking natural-language questions about the provided sales CSV and getting answers supported by SQLite queries.

Features
- Loads `sales_data.csv` into a local SQLite database (`sales.db`).
- Streamlit user interface with example questions, answer text, supporting figures, and a monthly revenue chart.
- FastAPI backend with `POST /ask` and `GET /health`.
- Supports total revenue, highest-revenue product, monthly revenue trend, highest-sales region, month-to-month comparison, and a data-quality summary.
- Includes automated tests.

Technology
Python, Pandas, SQLite, Streamlit, FastAPI, Uvicorn, Google Gemini API, python-dotenv, and unittest.

Setup
Use Python 3.10 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
```

Enable Gemini AI (optional but recommended)
1. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/).
2. Copy `.env.example` to a new file named `.env` in this project folder.
3. Put your key after `GEMINI_API_KEY=` in `.env`. Do not share the key or commit `.env` to GitHub.
4. Install packages with `pip install -r requirements.txt`.

Gemini classifies the question into one of a small set of supported intents. The application validates that intent and then selects a predefined read-only SQL query. The model never generates SQL. If no key is configured or the API fails, the local rule-based interpreter is used.

The model name can be changed in `.env` using `GEMINI_MODEL` if your account does not have access to the default model. API availability and free-tier limits depend on Google's current terms.

Run the user interface
```bash
streamlit run app.py
```
The browser opens the assistant. Choose an example in the sidebar or type your own question.

Run the API
In a second terminal, activate the same environment and run:
```bash
uvicorn api:app --reload
```
API documentation: `http://127.0.0.1:8000/docs`

Example request:
```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is the total revenue?\"}"
```

Run tests
```bash
python -m unittest -v
```

How it works
1. `analytics.py` loads and normalizes the CSV and stores it in SQLite.
2. Gemini classifies the request into a fixed allowlist of supported intents (with a local rule-based fallback).
3. The application validates the intent and selects a predefined, read-only SQL query. Gemini never generates or executes SQL. User text is never concatenated into SQL, and destructive SQL is not accepted.
4. The API returns structured JSON (`ok`, `intent`, `answer`, `columns`, `data`, and calculation method); Streamlit renders the answer and supporting figures.

Revenue definition and data handling
Revenue is calculated as `Quantity * Unit_price - Discount_amount`. Only completed transactions with a positive quantity and valid non-negative unit price and discount are included. Returned transactions, zero-quantity rows, and rows with missing/invalid price are excluded from revenue totals. Invalid dates or missing transaction IDs are dropped during import. Data-quality counts are shown in the UI.

The supplied CSV has 51 rows and one missing `Unit_price` value. The app reports data quality rather than silently treating the missing price as a real price. Check the business's intended discount semantics before using the numbers for formal reporting.

AI integration and limitations
Gemini is used for natural-language intent classification only. The app accepts only a fixed allowlist of intents and uses predefined read-only SQL templates for calculations. It does not execute model-generated SQL. If the API key is missing or the API call fails, the local rule-based interpreter is used. Unsupported questions are blocked rather than answered with invented figures.

Tests
Tests cover the five core analytics questions, an unsupported question, an empty-question edge case, and data-quality counts.

Architecture
`User (Streamlit UI) -> Gemini intent classification (or local fallback) -> validated intent allowlist -> predefined read-only SQL -> SQLite database -> structured result -> UI`
`API client -> FastAPI (/ask) -> same analytics service -> SQLite`
AI-assisted development note (edit to reflect your actual work)
- AI tool used: ChatGPT (if this matches the tool you used).
- How it was used: to help draft the project structure, interpret the challenge requirements, and create a first implementation for review.
- Problems to check during debugging: CSV date/numeric parsing, handling missing prices and returned transactions, and matching different ways users phrase questions.
- Debugging approach: run the automated tests, compare results with manual SQL calculations, and inspect data-quality counts.
- Further improvements: add an optional LLM-based intent parser with strict validation, more date-range questions, deployment configuration, and additional tests.
