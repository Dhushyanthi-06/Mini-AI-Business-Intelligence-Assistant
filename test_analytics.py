import unittest
from analytics import initialize_database, answer_question, data_quality

class TestSalesAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_total_revenue(self):
        result = answer_question("What is the total revenue?")
        self.assertTrue(result["ok"])
        self.assertIn("total_revenue", result["intent"])

    def test_top_product(self):
        result = answer_question("Which product generated the highest revenue?")
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"])

    def test_monthly_trend(self):
        result = answer_question("What is the monthly revenue trend?")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["data"]), 6)

    def test_top_region(self):
        result = answer_question("Which region generated the highest sales?")
        self.assertTrue(result["ok"])
        self.assertIn("Region", result["columns"])

    def test_month_comparison(self):
        result = answer_question("How did revenue change between January and February?")
        self.assertTrue(result["ok"])
        self.assertIn("Difference", result["answer"])

    def test_unsupported_question(self):
        result = answer_question("Tell me a joke")
        self.assertFalse(result["ok"])

    def test_empty_question_edge_case(self):
        result = answer_question("")
        self.assertFalse(result["ok"])

    def test_data_quality_counts(self):
        dq = data_quality()
        self.assertEqual(dq["total_rows"], 51)
        self.assertGreaterEqual(dq["missing_or_invalid_price"], 1)

if __name__ == "__main__":
    unittest.main()
