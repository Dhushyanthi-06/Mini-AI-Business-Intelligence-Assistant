# AI-assisted development notes

Please personalize this document before submission so it accurately describes what you did.

## AI tools used
ChatGPT was used to help structure the prototype and draft code, documentation, and tests.

## How AI was used
The challenge requirements were translated into a small Streamlit interface, a FastAPI endpoint, SQLite-backed deterministic analytics, and automated tests. Review every file and make sure you can explain and modify the code.

## Problems encountered / debugging checklist
- Confirmed the CSV schema and found one missing unit price.
- Defined a consistent revenue formula: quantity × unit price − discount amount.
- Excluded returned, zero-quantity, and invalid-price records from revenue totals.
- Added supported-intent checks so unsupported questions do not receive fabricated answers.
- Added tests for the five requested analytics examples and invalid/edge-case questions.

## Improvements with another day
- Add an optional LLM for more flexible language interpretation while keeping numeric calculations in SQL.
- Add richer date filters, downloadable reports, and role-based access.
- Add tests for all data-quality scenarios and compare outputs against independently computed expected values.
- Deploy the API and UI with environment-based configuration.

## Gemini integration added
- Gemini is used to classify natural-language questions into a fixed set of supported analytics intents.
- The app validates the returned intent and maps it to a predefined SQL query; it does not execute generated SQL.
- If the API key is missing or a request fails, the local rule-based interpreter keeps the app usable.
- Before submission, test with a configured API key, test with no key, and verify unsupported questions are blocked. Never commit `.env`.
