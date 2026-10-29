import unittest
from analyzer import calculate_metrics

class TestMetrics(unittest.TestCase):
    def test_metrics(self):
        events = [{'customers_affected': 10, 'duration_minutes': 30},
                  {'customers_affected': 20, 'duration_minutes': 60}]
        m = calculate_metrics(events, 100)
        self.assertAlmostEqual(m['saifi'], 0.3)
        self.assertAlmostEqual(m['saidi_minutes'], 15)
        self.assertAlmostEqual(m['caidi_minutes'], 50)

    def test_no_outages(self):
        m = calculate_metrics([], 100)
        self.assertEqual(m['caidi_minutes'], 0)

    def test_invalid_population(self):
        with self.assertRaises(ValueError):
            calculate_metrics([], 0)

if __name__ == '__main__':
    unittest.main()
