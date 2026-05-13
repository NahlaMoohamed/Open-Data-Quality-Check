"""Resource validation checks"""

import logging
import os
from typing import Dict, List, Any
import requests

logger = logging.getLogger(__name__)


class ResourceValidator:
    """Validates dataset resources"""

    @staticmethod
    def check_has_resources(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset has resources
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        resources = dataset.get("resources", [])
        has_resources = len(resources) > 0
        
        return {
            "check": "has_resources",
            "status": "pass" if has_resources else "fail",
            "message": f"Dataset has {len(resources)} resource(s)",
            "resource_count": len(resources),
            "details": resources,
        }

    @staticmethod
    def check_resource_validity(resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if resource is valid and accessible
        
        Args:
            resource: Resource object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "resource_validity",
            "resource_id": resource.get("id"),
            "resource_name": resource.get("name"),
            "status": "pass",
            "issues": [],
        }

        # Check resource URL
        url = resource.get("url")
        if not url:
            result["status"] = "fail"
            result["issues"].append("Resource URL is missing")
            return result

        # Try to access the resource
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            
            if response.status_code >= 400:
                result["status"] = "fail"
                result["issues"].append(
                    f"Resource URL returned status {response.status_code}"
                )
            
            # Check content length
            content_length = response.headers.get("content-length")
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                result["file_size_mb"] = round(size_mb, 2)
                
                if size_mb == 0:
                    result["status"] = "fail"
                    result["issues"].append("Resource file size is 0")
                    
        except requests.exceptions.RequestException as e:
            result["status"] = "fail"
            result["issues"].append(f"Cannot access resource: {str(e)}")

        return result

    @staticmethod
    def check_resource_format(resource: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check resource format and metadata
        
        Args:
            resource: Resource object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "resource_format",
            "resource_id": resource.get("id"),
            "resource_name": resource.get("name"),
            "format": resource.get("format", "unknown").upper(),
            "status": "pass",
            "issues": [],
        }

        # Supported formats
        supported_formats = ["CSV", "XLSX", "XLS", "JSON", "XML", "PDF"]
        
        resource_format = resource.get("format", "").upper()
        
        if not resource_format:
            result["status"] = "fail"
            result["issues"].append("Resource format is not specified")
        elif resource_format not in supported_formats:
            result["issues"].append(
                f"Format {resource_format} not in standard formats"
            )

        # Check for description
        if not resource.get("description"):
            result["issues"].append("Resource description is missing")

        if result["issues"]:
            result["status"] = "warning"

        return result

    @staticmethod
    def validate_all_resources(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all resource validation checks on a dataset
        
        Args:
            dataset: Dataset object
            
        Returns:
            Comprehensive validation result
        """
        has_resources = ResourceValidator.check_has_resources(dataset)
        
        if has_resources["status"] == "fail":
            return {
                "resource_checks": [has_resources],
                "overall_status": "fail",
            }

        resources = dataset.get("resources", [])
        checks = [has_resources]
        
        for resource in resources:
            checks.append(ResourceValidator.check_resource_validity(resource))
            checks.append(ResourceValidator.check_resource_format(resource))

        all_pass = all(check.get("status") == "pass" for check in checks)
        overall_status = "pass" if all_pass else (
            "fail" if any(check.get("status") == "fail" for check in checks)
            else "warning"
        )

        return {
            "resource_checks": checks,
            "overall_status": overall_status,
        }
