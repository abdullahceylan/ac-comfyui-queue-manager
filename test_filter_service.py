"""
Unit tests for the FilterService class.
"""

import unittest
from datetime import datetime, timezone

from filter_service import FilterService, FilterValidationError
from models import QueueFilter, QueueItem, QueueStatus


class TestFilterService(unittest.TestCase):
    """Test cases for the FilterService class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample queue items for testing
        self.items = [
            QueueItem(
                id="item1",
                workflow_name="Test Workflow 1",
                workflow_data={"node1": {"type": "input"}},
                status=QueueStatus.PENDING,
                created_at=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
                error_message=None
            ),
            QueueItem(
                id="item2",
                workflow_name="Production Workflow",
                workflow_data={"node1": {"type": "output"}},
                status=QueueStatus.COMPLETED,
                created_at=datetime(2024, 1, 2, 15, 30, 0, tzinfo=timezone.utc),
                error_message=None
            ),
            QueueItem(
                id="item3",
                workflow_name="Failed Test",
                workflow_data={"node1": {"type": "process"}},
                status=QueueStatus.FAILED,
                created_at=datetime(2024, 1, 3, 9, 15, 0, tzinfo=timezone.utc),
                error_message="Connection timeout"
            ),
            QueueItem(
                id="item4",
                workflow_name="Archive Workflow",
                workflow_data={"node1": {"type": "archive"}},
                status=QueueStatus.ARCHIVED,
                created_at=datetime(2024, 1, 4, 14, 45, 0, tzinfo=timezone.utc),
                error_message=None
            )
        ]

    def test_validate_filter_valid(self):
        """Test filter validation with valid filter."""
        filter_criteria = QueueFilter(
            status=[QueueStatus.PENDING, QueueStatus.COMPLETED],
            workflow_name="Test",
            date_range=(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 31, tzinfo=timezone.utc)
            ),
            search_term="workflow"
        )
        
        result = FilterService.validate_filter(filter_criteria)
        self.assertTrue(result)

    def test_validate_filter_invalid_status(self):
        """Test filter validation with invalid status."""
        filter_criteria = QueueFilter(status=["invalid_status"])
        
        with self.assertRaises(FilterValidationError):
            FilterService.validate_filter(filter_criteria)

    def test_validate_filter_invalid_date_range(self):
        """Test filter validation with invalid date range."""
        filter_criteria = QueueFilter(
            date_range=(
                datetime(2024, 1, 31, tzinfo=timezone.utc),
                datetime(2024, 1, 1, tzinfo=timezone.utc)  # End before start
            )
        )
        
        with self.assertRaises(FilterValidationError):
            FilterService.validate_filter(filter_criteria)

    def test_validate_filter_invalid_workflow_name(self):
        """Test filter validation with invalid workflow name."""
        filter_criteria = QueueFilter(workflow_name=123)
        
        with self.assertRaises(FilterValidationError):
            FilterService.validate_filter(filter_criteria)

    def test_parse_search_query_status(self):
        """Test parsing search query with status filter."""
        query = "status:pending status:completed"
        parsed = FilterService.parse_search_query(query)
        
        self.assertEqual(len(parsed["status"]), 2)
        self.assertIn(QueueStatus.PENDING, parsed["status"])
        self.assertIn(QueueStatus.COMPLETED, parsed["status"])

    def test_parse_search_query_name_quoted(self):
        """Test parsing search query with quoted name."""
        query = 'name:"My Test Workflow"'
        parsed = FilterService.parse_search_query(query)
        
        self.assertEqual(parsed["workflow_name"], "My Test Workflow")

    def test_parse_search_query_name_unquoted(self):
        """Test parsing search query with unquoted name."""
        query = "name:TestWorkflow"
        parsed = FilterService.parse_search_query(query)
        
        self.assertEqual(parsed["workflow_name"], "TestWorkflow")

    def test_parse_search_query_date(self):
        """Test parsing search query with date filter."""
        query = "created:>2024-01-01 created:<2024-01-31"
        parsed = FilterService.parse_search_query(query)
        
        self.assertIn(">", parsed["date_filters"])
        self.assertIn("<", parsed["date_filters"])
        self.assertEqual(
            parsed["date_filters"][">"],
            datetime(2024, 1, 1, tzinfo=timezone.utc)
        )

    def test_parse_search_query_error(self):
        """Test parsing search query with error filter."""
        query = "error:true"
        parsed = FilterService.parse_search_query(query)
        
        self.assertTrue(parsed["has_error"])

    def test_parse_search_query_text_search(self):
        """Test parsing search query with text search terms."""
        query = "workflow test status:pending some other terms"
        parsed = FilterService.parse_search_query(query)
        
        self.assertIn("workflow", parsed["text_search"])
        self.assertIn("test", parsed["text_search"])
        self.assertIn("some", parsed["text_search"])
        self.assertIn("other", parsed["text_search"])
        self.assertIn("terms", parsed["text_search"])

    def test_parse_search_query_empty(self):
        """Test parsing empty search query."""
        query = ""
        parsed = FilterService.parse_search_query(query)
        
        self.assertEqual(parsed, {})

    def test_build_filter_from_query(self):
        """Test building filter from search query."""
        query = "status:pending name:TestWorkflow created:>2024-01-01 workflow test"
        filter_criteria = FilterService.build_filter_from_query(query)
        
        self.assertEqual(filter_criteria.status, [QueueStatus.PENDING])
        self.assertEqual(filter_criteria.workflow_name, "TestWorkflow")
        self.assertIsNotNone(filter_criteria.date_range)
        self.assertEqual(filter_criteria.search_term, "workflow test")

    def test_apply_client_side_filter_status(self):
        """Test client-side filtering by status."""
        filter_criteria = QueueFilter(status=[QueueStatus.PENDING, QueueStatus.COMPLETED])
        filtered = FilterService.apply_client_side_filter(self.items, filter_criteria)
        
        self.assertEqual(len(filtered), 2)
        statuses = [item.status for item in filtered]
        self.assertIn(QueueStatus.PENDING, statuses)
        self.assertIn(QueueStatus.COMPLETED, statuses)

    def test_apply_client_side_filter_workflow_name(self):
        """Test client-side filtering by workflow name."""
        filter_criteria = QueueFilter(workflow_name="Test")
        filtered = FilterService.apply_client_side_filter(self.items, filter_criteria)
        
        self.assertEqual(len(filtered), 2)  # "Test Workflow 1" and "Failed Test"
        names = [item.workflow_name for item in filtered]
        self.assertIn("Test Workflow 1", names)
        self.assertIn("Failed Test", names)

    def test_apply_client_side_filter_date_range(self):
        """Test client-side filtering by date range."""
        filter_criteria = QueueFilter(
            date_range=(
                datetime(2024, 1, 2, tzinfo=timezone.utc),
                datetime(2024, 1, 3, 23, 59, 59, tzinfo=timezone.utc)
            )
        )
        filtered = FilterService.apply_client_side_filter(self.items, filter_criteria)
        
        self.assertEqual(len(filtered), 2)  # Items from Jan 2 and Jan 3

    def test_apply_client_side_filter_search_term(self):
        """Test client-side filtering by search term."""
        filter_criteria = QueueFilter(search_term="timeout")
        filtered = FilterService.apply_client_side_filter(self.items, filter_criteria)
        
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].id, "item3")  # Item with "timeout" in error message

    def test_apply_client_side_filter_empty_list(self):
        """Test client-side filtering with empty item list."""
        filter_criteria = QueueFilter(status=[QueueStatus.PENDING])
        filtered = FilterService.apply_client_side_filter([], filter_criteria)
        
        self.assertEqual(len(filtered), 0)

    def test_apply_client_side_filter_no_matches(self):
        """Test client-side filtering with no matches."""
        filter_criteria = QueueFilter(workflow_name="NonExistent")
        filtered = FilterService.apply_client_side_filter(self.items, filter_criteria)
        
        self.assertEqual(len(filtered), 0)

    def test_item_matches_search_term_workflow_name(self):
        """Test search term matching in workflow name."""
        item = self.items[0]  # "Test Workflow 1"
        
        self.assertTrue(FilterService._item_matches_search_term(item, "test"))
        self.assertTrue(FilterService._item_matches_search_term(item, "workflow"))
        self.assertFalse(FilterService._item_matches_search_term(item, "production"))

    def test_item_matches_search_term_error_message(self):
        """Test search term matching in error message."""
        item = self.items[2]  # Has "Connection timeout" error
        
        self.assertTrue(FilterService._item_matches_search_term(item, "timeout"))
        self.assertTrue(FilterService._item_matches_search_term(item, "connection"))
        self.assertFalse(FilterService._item_matches_search_term(item, "success"))

    def test_item_matches_search_term_workflow_data(self):
        """Test search term matching in workflow data."""
        item = self.items[0]  # Has {"node1": {"type": "input"}}
        
        self.assertTrue(FilterService._item_matches_search_term(item, "input"))
        self.assertTrue(FilterService._item_matches_search_term(item, "node1"))
        self.assertFalse(FilterService._item_matches_search_term(item, "output"))

    def test_create_status_filter(self):
        """Test creating status filter."""
        filter_obj = FilterService.create_status_filter(["pending", "completed", QueueStatus.FAILED])
        
        self.assertEqual(len(filter_obj.status), 3)
        self.assertIn(QueueStatus.PENDING, filter_obj.status)
        self.assertIn(QueueStatus.COMPLETED, filter_obj.status)
        self.assertIn(QueueStatus.FAILED, filter_obj.status)

    def test_create_status_filter_invalid(self):
        """Test creating status filter with invalid statuses."""
        filter_obj = FilterService.create_status_filter(["pending", "invalid", "completed"])
        
        self.assertEqual(len(filter_obj.status), 2)  # Invalid status should be skipped
        self.assertIn(QueueStatus.PENDING, filter_obj.status)
        self.assertIn(QueueStatus.COMPLETED, filter_obj.status)

    def test_create_date_range_filter(self):
        """Test creating date range filter."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        filter_obj = FilterService.create_date_range_filter(start_date, end_date)
        
        self.assertEqual(filter_obj.date_range, (start_date, end_date))

    def test_create_date_range_filter_partial(self):
        """Test creating date range filter with only start date."""
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        filter_obj = FilterService.create_date_range_filter(start_date=start_date)
        
        self.assertEqual(filter_obj.date_range[0], start_date)
        self.assertEqual(filter_obj.date_range[1], datetime.max.replace(tzinfo=timezone.utc))

    def test_create_date_range_filter_none(self):
        """Test creating date range filter with no dates."""
        filter_obj = FilterService.create_date_range_filter()
        
        self.assertIsNone(filter_obj.date_range)

    def test_create_text_search_filter(self):
        """Test creating text search filter."""
        filter_obj = FilterService.create_text_search_filter("  test workflow  ")
        
        self.assertEqual(filter_obj.search_term, "test workflow")

    def test_create_text_search_filter_empty(self):
        """Test creating text search filter with empty string."""
        filter_obj = FilterService.create_text_search_filter("")
        
        self.assertIsNone(filter_obj.search_term)

    def test_combine_filters_status(self):
        """Test combining filters with status."""
        filter1 = QueueFilter(status=[QueueStatus.PENDING])
        filter2 = QueueFilter(status=[QueueStatus.COMPLETED, QueueStatus.FAILED])
        
        combined = FilterService.combine_filters(filter1, filter2)
        
        self.assertEqual(len(combined.status), 3)
        self.assertIn(QueueStatus.PENDING, combined.status)
        self.assertIn(QueueStatus.COMPLETED, combined.status)
        self.assertIn(QueueStatus.FAILED, combined.status)

    def test_combine_filters_workflow_name(self):
        """Test combining filters with workflow name."""
        filter1 = QueueFilter(workflow_name="First")
        filter2 = QueueFilter(workflow_name="Second")
        
        combined = FilterService.combine_filters(filter1, filter2)
        
        self.assertEqual(combined.workflow_name, "Second")  # Last non-None value

    def test_combine_filters_date_range(self):
        """Test combining filters with date range."""
        filter1 = QueueFilter(
            date_range=(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                datetime(2024, 1, 31, tzinfo=timezone.utc)
            )
        )
        filter2 = QueueFilter(
            date_range=(
                datetime(2024, 1, 15, tzinfo=timezone.utc),
                datetime(2024, 2, 15, tzinfo=timezone.utc)
            )
        )
        
        combined = FilterService.combine_filters(filter1, filter2)
        
        # Should use intersection (latest start, earliest end)
        expected_start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        expected_end = datetime(2024, 1, 31, tzinfo=timezone.utc)
        self.assertEqual(combined.date_range, (expected_start, expected_end))

    def test_combine_filters_search_term(self):
        """Test combining filters with search terms."""
        filter1 = QueueFilter(search_term="first term")
        filter2 = QueueFilter(search_term="second term")
        
        combined = FilterService.combine_filters(filter1, filter2)
        
        self.assertEqual(combined.search_term, "first term second term")

    def test_combine_filters_empty(self):
        """Test combining empty filters."""
        filter1 = QueueFilter()
        filter2 = QueueFilter()
        
        combined = FilterService.combine_filters(filter1, filter2)
        
        self.assertIsNone(combined.status)
        self.assertIsNone(combined.workflow_name)
        self.assertIsNone(combined.date_range)
        self.assertIsNone(combined.search_term)


if __name__ == "__main__":
    unittest.main()