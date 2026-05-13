"""Time period validation checks"""

import logging
from typing import Dict, Any, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class TimePeriodValidator:
    """Validates time period information in datasets"""

    TIME_PERIOD_KEYWORDS = [
        "temporal_start",
        "temporal_end",
        "start_date",
        "end_date",
        "date",
        "period",
        "year",
        "from_date",
        "to_date",
        "begin",
        "end",
        "temporal_coverage",
        "date_start",
        "date_end",
    ]

    @staticmethod
    def extract_date(value: Any) -> Optional[str]:
        """
        Extract and normalize date from various formats
        
        Args:
            value: Value that might contain a date
            
        Returns:
            Normalized date string or None
        """
        if not value:
            return None

        value_str = str(value).strip()

        # Try common date formats
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m",
            "%Y/%m",
            "%Y",
            "%m/%d/%Y",
            "%m-%d-%Y",
        ]

        for fmt in date_formats:
            try:
                parsed = datetime.strptime(value_str, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    @staticmethod
    def check_time_period_in_metadata(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has time period information in metadata
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "time_period_metadata",
            "status": "pass",
            "has_time_period": False,
            "time_period_fields": [],
            "extracted_dates": {},
            "issues": [],
        }

        # Check for time period in various metadata fields
        for key, value in dataset.items():
            if key.lower() in TimePeriodValidator.TIME_PERIOD_KEYWORDS:
                result["time_period_fields"].append(key)
                
                # Try to extract date
                extracted = TimePeriodValidator.extract_date(value)
                if extracted:
                    result["extracted_dates"][key] = extracted
                    result["has_time_period"] = True

        if not result["has_time_period"]:
            result["status"] = "warning"
            result["issues"].append(
                "No explicit time period information found in dataset metadata. "
                f"Searched fields: {', '.join(TimePeriodValidator.TIME_PERIOD_KEYWORDS[:5])}..."
            )

        return result

    @staticmethod
    def check_time_period_in_resources(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if resources have time period information
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "time_period_resources",
            "status": "pass",
            "resources_with_period": [],
            "resources_without_period": [],
            "issues": [],
        }

        resources = dataset.get("resources", [])
        
        for idx, resource in enumerate(resources):
            has_period = False
            period_info = {}
            
            for key, value in resource.items():
                if key.lower() in TimePeriodValidator.TIME_PERIOD_KEYWORDS:
                    extracted = TimePeriodValidator.extract_date(value)
                    if extracted:
                        has_period = True
                        period_info[key] = extracted

            resource_name = resource.get("name", f"resource_{idx}")
            
            if has_period:
                result["resources_with_period"].append({
                    "name": resource_name,
                    "period_info": period_info,
                })
            else:
                result["resources_without_period"].append(resource_name)

        if len(result["resources_without_period"]) > 0:
            result["status"] = "warning"
            result["issues"].append(
                f"{len(result['resources_without_period'])} resource(s) do not have "
                "explicit time period information"
            )

        return result

    @staticmethod
    def check_time_period_in_description(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset description mentions time period
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "time_period_description",
            "status": "pass",
            "mentions_time_period": False,
            "extracted_years": [],
            "issues": [],
        }

        description = dataset.get("description", "")
        if isinstance(description, dict):
            description = description.get("en", "") + " " + description.get("ar", "")

        description_lower = str(description).lower()

        # Check for time period keywords
        time_keywords = [
            "period",
            "from",
            "to",
            "since",
            "year",
            "time",
            "date",
            "coverage",
            "data collected",
            "spanning",
        ]

        if any(keyword in description_lower for keyword in time_keywords):
            result["mentions_time_period"] = True

        # Extract years (4-digit numbers that look like years)
        year_pattern = r"\b(19|20)\d{2}\b"
        years = re.findall(year_pattern, description)
        if years:
            result["extracted_years"] = sorted(list(set(years)))
            result["mentions_time_period"] = True

        return result

    @staticmethod
    def validate_time_period(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all time period validation checks on a dataset
        
        Args:
            dataset: Dataset object
            
        Returns:
            Comprehensive validation result
        """
        checks = [
            TimePeriodValidator.check_time_period_in_metadata(dataset),
            TimePeriodValidator.check_time_period_in_resources(dataset),
            TimePeriodValidator.check_time_period_in_description(dataset),
        ]

        # Count how many passed
        passed = sum(1 for check in checks if check.get("status") == "pass")
        
        # Overall status based on multiple sources
        if passed >= 2:
            overall_status = "pass"
        elif passed == 1:
            overall_status = "warning"
        else:
            overall_status = "warning"  # Time period is helpful but not critical

        return {
            "time_period_checks": checks,
            "overall_status": overall_status,
        }
