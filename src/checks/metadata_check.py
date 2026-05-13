"""Metadata validation checks"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validates dataset metadata completeness and quality"""

    REQUIRED_FIELDS = [
        "title",
        "description",
        "organization",
        "resources",
    ]

    IMPORTANT_FIELDS = [
        "author",
        "author_email",
        "license_title",
        "license_id",
        "tags",
        "issued",
        "modified",
    ]

    @staticmethod
    def check_required_fields(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has all required metadata fields
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "required_metadata_fields",
            "status": "pass",
            "required_fields": MetadataValidator.REQUIRED_FIELDS,
            "missing_fields": [],
            "present_fields": [],
        }

        for field in MetadataValidator.REQUIRED_FIELDS:
            if field not in dataset or not dataset[field]:
                result["missing_fields"].append(field)
            else:
                result["present_fields"].append(field)

        if result["missing_fields"]:
            result["status"] = "fail"

        return result

    @staticmethod
    def check_important_fields(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has important optional metadata fields
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "important_metadata_fields",
            "status": "pass",
            "important_fields": MetadataValidator.IMPORTANT_FIELDS,
            "missing_fields": [],
            "present_fields": [],
        }

        for field in MetadataValidator.IMPORTANT_FIELDS:
            if field not in dataset or not dataset[field]:
                result["missing_fields"].append(field)
            else:
                result["present_fields"].append(field)

        # This is a warning, not a failure
        if result["missing_fields"]:
            result["status"] = "warning"

        return result

    @staticmethod
    def check_data_dictionary(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has a data dictionary or metadata file
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "data_dictionary",
            "status": "fail",
            "has_dictionary": False,
            "dictionary_resources": [],
            "issues": [],
        }

        dictionary_keywords = [
            "data dictionary",
            "metadata",
            "documentation",
            "codebook",
            "schema",
            "قاموس",
            "بيانات وصفية",
            "توثيق",
        ]

        for resource in dataset.get("resources", []):
            name = resource.get("name", "").lower()
            description = resource.get("description", "").lower()
            
            for keyword in dictionary_keywords:
                if keyword in name or keyword in description:
                    result["dictionary_resources"].append(resource.get("name"))
                    result["has_dictionary"] = True
                    break

        if result["has_dictionary"]:
            result["status"] = "pass"
        else:
            result["issues"].append(
                "No data dictionary or metadata file found in resources"
            )

        return result

    @staticmethod
    def check_description_quality(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check quality of dataset description
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "description_quality",
            "status": "pass",
            "description_length": 0,
            "issues": [],
        }

        description = dataset.get("description", "").strip()
        result["description_length"] = len(description)

        if not description:
            result["status"] = "fail"
            result["issues"].append("Dataset description is missing")
        elif len(description) < 50:
            result["status"] = "warning"
            result["issues"].append(
                f"Description is too short ({len(description)} characters). "
                "Recommended: at least 50 characters."
            )

        return result

    @staticmethod
    def check_tags(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has tags for categorization
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "tags",
            "status": "pass",
            "tag_count": 0,
            "tags": [],
            "issues": [],
        }

        tags = dataset.get("tags", [])
        result["tags"] = [tag.get("name", tag) if isinstance(tag, dict) else tag 
                         for tag in tags]
        result["tag_count"] = len(tags)

        if result["tag_count"] == 0:
            result["status"] = "warning"
            result["issues"].append("Dataset has no tags")
        elif result["tag_count"] < 3:
            result["status"] = "warning"
            result["issues"].append(
                f"Dataset has only {result['tag_count']} tags. "
                "Recommended: at least 3 tags."
            )

        return result

    @staticmethod
    def validate_metadata(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all metadata validation checks on a dataset
        
        Args:
            dataset: Dataset object
            
        Returns:
            Comprehensive validation result
        """
        checks = [
            MetadataValidator.check_required_fields(dataset),
            MetadataValidator.check_important_fields(dataset),
            MetadataValidator.check_data_dictionary(dataset),
            MetadataValidator.check_description_quality(dataset),
            MetadataValidator.check_tags(dataset),
        ]

        all_pass = all(check.get("status") == "pass" for check in checks)
        overall_status = "pass" if all_pass else (
            "fail" if any(check.get("status") == "fail" for check in checks)
            else "warning"
        )

        return {
            "metadata_checks": checks,
            "overall_status": overall_status,
        }
