"""
Advanced filtering and search functionality for the ComfyUI Queue Manager.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from models import QueueFilter, QueueItem, QueueStatus


class FilterValidationError(Exception):
    """Exception raised when filter validation fails."""


class FilterService:
    """Service for advanced filtering and search operations."""

    @staticmethod
    def validate_filter(filter_criteria: QueueFilter) -> bool:
        """Validate filter criteria.
        
        Args:
            filter_criteria: The filter criteria to validate
            
        Returns:
            True if the filter is valid
            
        Raises:
            FilterValidationError: If the filter is invalid
        """
        if filter_criteria.status:
            # Validate status values
            for status in filter_criteria.status:
                if not isinstance(status, QueueStatus):
                    raise FilterValidationError(f"Invalid status: {status}")
        
        if filter_criteria.date_range:
            start_date, end_date = filter_criteria.date_range
            if not isinstance(start_date, datetime) or not isinstance(end_date, datetime):
                raise FilterValidationError("Date range must contain datetime objects")
            if start_date > end_date:
                raise FilterValidationError("Start date must be before end date")
        
        if filter_criteria.workflow_name is not None and not isinstance(filter_criteria.workflow_name, str):
            raise FilterValidationError("Workflow name must be a string")
        
        if filter_criteria.search_term is not None and not isinstance(filter_criteria.search_term, str):
            raise FilterValidationError("Search term must be a string")
        
        return True

    @staticmethod
    def parse_search_query(search_query: str) -> dict[str, Any]:
        """Parse a search query string into structured search parameters.
        
        Supports syntax like:
        - status:pending
        - name:"My Workflow"
        - created:>2024-01-01
        - error:true
        
        Args:
            search_query: The search query string
            
        Returns:
            Dictionary of parsed search parameters
        """
        if not search_query or not search_query.strip():
            return {}
        
        parsed = {
            "status": [],
            "workflow_name": None,
            "date_filters": {},
            "has_error": None,
            "text_search": []
        }
        
        # Regular expressions for different query patterns
        status_pattern = r'status:(\w+)'
        name_pattern = r'name:"([^"]+)"|name:(\S+)'
        date_pattern = r'created:([><=]+)(\d{4}-\d{2}-\d{2})'
        error_pattern = r'error:(true|false)'
        
        # Extract status filters
        status_matches = re.findall(status_pattern, search_query, re.IGNORECASE)
        for status_str in status_matches:
            try:
                status = QueueStatus(status_str.lower())
                parsed["status"].append(status)
            except ValueError:
                # Invalid status, ignore
                pass
        
        # Extract name filters
        name_matches = re.findall(name_pattern, search_query, re.IGNORECASE)
        for quoted_name, unquoted_name in name_matches:
            name = quoted_name or unquoted_name
            if name:
                parsed["workflow_name"] = name
                break  # Use first match
        
        # Extract date filters
        date_matches = re.findall(date_pattern, search_query, re.IGNORECASE)
        for operator, date_str in date_matches:
            try:
                date_obj = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
                parsed["date_filters"][operator] = date_obj
            except ValueError:
                # Invalid date, ignore
                pass
        
        # Extract error filters
        error_matches = re.findall(error_pattern, search_query, re.IGNORECASE)
        for error_str in error_matches:
            parsed["has_error"] = error_str.lower() == "true"
            break  # Use first match
        
        # Extract remaining text for general search
        # Remove all structured query parts
        remaining_text = search_query
        for pattern in [status_pattern, name_pattern, date_pattern, error_pattern]:
            remaining_text = re.sub(pattern, "", remaining_text, flags=re.IGNORECASE)
        
        # Split remaining text into search terms
        text_terms = [term.strip() for term in remaining_text.split() if term.strip()]
        parsed["text_search"] = text_terms
        
        return parsed

    @staticmethod
    def build_filter_from_query(search_query: str) -> QueueFilter:
        """Build a QueueFilter from a search query string.
        
        Args:
            search_query: The search query string
            
        Returns:
            QueueFilter object
        """
        parsed = FilterService.parse_search_query(search_query)
        
        filter_criteria = QueueFilter()
        
        # Set status filter
        if parsed["status"]:
            filter_criteria.status = parsed["status"]
        
        # Set workflow name filter
        if parsed["workflow_name"]:
            filter_criteria.workflow_name = parsed["workflow_name"]
        
        # Set date range filter
        if parsed["date_filters"]:
            start_date = None
            end_date = None
            
            for operator, date_obj in parsed["date_filters"].items():
                if operator == ">":
                    start_date = date_obj
                elif operator == "<":
                    end_date = date_obj
                elif operator == ">=":
                    start_date = date_obj
                elif operator == "<=":
                    end_date = date_obj
                elif operator == "=":
                    # For exact date, set both start and end to the same day
                    start_date = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            if start_date or end_date:
                filter_criteria.date_range = (
                    start_date or datetime.min.replace(tzinfo=timezone.utc),
                    end_date or datetime.max.replace(tzinfo=timezone.utc)
                )
        
        # Set search term for text search
        if parsed["text_search"]:
            filter_criteria.search_term = " ".join(parsed["text_search"])
        
        return filter_criteria

    @staticmethod
    def apply_client_side_filter(items: list[QueueItem], filter_criteria: QueueFilter) -> list[QueueItem]:
        """Apply additional client-side filtering that may not be supported by the database.
        
        Args:
            items: List of queue items to filter
            filter_criteria: Filter criteria to apply
            
        Returns:
            Filtered list of queue items
        """
        if not items:
            return items
        
        filtered_items = items
        
        # Apply status filter
        if filter_criteria.status:
            filtered_items = [
                item for item in filtered_items
                if item.status in filter_criteria.status
            ]
        
        # Apply workflow name filter (case-insensitive partial match)
        if filter_criteria.workflow_name:
            search_name = filter_criteria.workflow_name.lower()
            filtered_items = [
                item for item in filtered_items
                if search_name in item.workflow_name.lower()
            ]
        
        # Apply date range filter
        if filter_criteria.date_range:
            start_date, end_date = filter_criteria.date_range
            filtered_items = [
                item for item in filtered_items
                if start_date <= item.created_at <= end_date
            ]
        
        # Apply search term filter (searches in workflow name, data, and error message)
        if filter_criteria.search_term:
            search_term = filter_criteria.search_term.lower()
            filtered_items = [
                item for item in filtered_items
                if FilterService._item_matches_search_term(item, search_term)
            ]
        
        return filtered_items

    @staticmethod
    def _item_matches_search_term(item: QueueItem, search_term: str) -> bool:
        """Check if a queue item matches a search term.
        
        Args:
            item: The queue item to check
            search_term: The search term (already lowercased)
            
        Returns:
            True if the item matches the search term
        """
        # Search in workflow name
        if search_term in item.workflow_name.lower():
            return True
        
        # Search in error message
        if item.error_message and search_term in item.error_message.lower():
            return True
        
        # Search in workflow data (convert to string and search)
        try:
            workflow_data_str = str(item.workflow_data).lower()
            if search_term in workflow_data_str:
                return True
        except Exception:
            # If conversion fails, skip workflow data search
            pass
        
        # Search in result data
        if item.result_data:
            try:
                result_data_str = str(item.result_data).lower()
                if search_term in result_data_str:
                    return True
            except Exception:
                # If conversion fails, skip result data search
                pass
        
        return False

    @staticmethod
    def create_status_filter(statuses: list[str | QueueStatus]) -> QueueFilter:
        """Create a filter for specific statuses.
        
        Args:
            statuses: List of status strings or QueueStatus enums
            
        Returns:
            QueueFilter configured for the specified statuses
        """
        status_enums = []
        for status in statuses:
            if isinstance(status, str):
                try:
                    status_enums.append(QueueStatus(status.lower()))
                except ValueError:
                    # Invalid status, skip
                    continue
            elif isinstance(status, QueueStatus):
                status_enums.append(status)
        
        return QueueFilter(status=status_enums)

    @staticmethod
    def create_date_range_filter(
        start_date: datetime | None = None,
        end_date: datetime | None = None
    ) -> QueueFilter:
        """Create a filter for a date range.
        
        Args:
            start_date: Start of the date range (inclusive)
            end_date: End of the date range (inclusive)
            
        Returns:
            QueueFilter configured for the specified date range
        """
        if start_date is None and end_date is None:
            return QueueFilter()
        
        # Set default values if not provided
        if start_date is None:
            start_date = datetime.min.replace(tzinfo=timezone.utc)
        if end_date is None:
            end_date = datetime.max.replace(tzinfo=timezone.utc)
        
        return QueueFilter(date_range=(start_date, end_date))

    @staticmethod
    def create_text_search_filter(search_term: str) -> QueueFilter:
        """Create a filter for text search.
        
        Args:
            search_term: The text to search for
            
        Returns:
            QueueFilter configured for text search
        """
        return QueueFilter(search_term=search_term.strip() if search_term else None)

    @staticmethod
    def combine_filters(*filters: QueueFilter) -> QueueFilter:
        """Combine multiple filters into a single filter.
        
        Args:
            filters: Variable number of QueueFilter objects to combine
            
        Returns:
            Combined QueueFilter
        """
        combined = QueueFilter()
        
        # Combine status filters
        all_statuses = []
        for filter_obj in filters:
            if filter_obj.status:
                all_statuses.extend(filter_obj.status)
        if all_statuses:
            # Remove duplicates while preserving order
            seen = set()
            combined.status = [
                status for status in all_statuses
                if status not in seen and not seen.add(status)
            ]
        
        # Combine workflow name filters (use the last non-None value)
        for filter_obj in filters:
            if filter_obj.workflow_name:
                combined.workflow_name = filter_obj.workflow_name
        
        # Combine date range filters (use intersection of ranges)
        date_ranges = [f.date_range for f in filters if f.date_range]
        if date_ranges:
            start_dates = [dr[0] for dr in date_ranges]
            end_dates = [dr[1] for dr in date_ranges]
            combined.date_range = (max(start_dates), min(end_dates))
        
        # Combine search terms
        search_terms = [f.search_term for f in filters if f.search_term]
        if search_terms:
            combined.search_term = " ".join(search_terms)
        
        return combined