import unittest

from app import normalize_plan


class CategoryNormalizationTests(unittest.TestCase):
    def test_not_closed_work_orders_keeps_inequality(self) -> None:
        plan = normalize_plan(
            {
                "filters": [
                    {"field": "status", "op": "neq", "value": "Closed"}
                ]
            },
            "work orders that are not closed",
            "work_orders",
        )

        self.assertEqual(
            plan["filters"],
            [{"field": "status", "op": "neq", "value": "Closed"}],
        )

    def test_exclude_failed_inspections_keeps_inequality(self) -> None:
        plan = normalize_plan(
            {
                "filters": [
                    {"field": "result", "op": "neq", "value": "Failed"}
                ]
            },
            "exclude failed inspections",
            "site_inspections",
        )

        self.assertEqual(
            plan["filters"],
            [{"field": "result", "op": "neq", "value": "Failed"}],
        )


if __name__ == "__main__":
    unittest.main()
