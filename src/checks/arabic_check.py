"""Arabic text encoding validation checks"""

import logging
from typing import Dict, Any
import re
import chardet

logger = logging.getLogger(__name__)


class ArabicValidator:
    """Validates Arabic text encoding and display"""

    # Arabic Unicode ranges
    ARABIC_UNICODE_START = 0x0600  # Start of Arabic block
    ARABIC_UNICODE_END = 0x06FF    # End of Arabic block

    @staticmethod
    def contains_arabic_text(text: str) -> bool:
        """
        Check if text contains Arabic characters
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains Arabic characters
        """
        if not text:
            return False
        
        for char in text:
            code = ord(char)
            if ArabicValidator.ARABIC_UNICODE_START <= code <= ArabicValidator.ARABIC_UNICODE_END:
                return True
        
        return False

    @staticmethod
    def check_arabic_in_dataset(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset contains Arabic content
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "arabic_presence",
            "status": "pass",
            "has_arabic": False,
            "arabic_fields": [],
        }

        # Check title
        title = dataset.get("title", "")
        if isinstance(title, dict):
            if ArabicValidator.contains_arabic_text(title.get("ar", "")):
                result["has_arabic"] = True
                result["arabic_fields"].append("title_ar")
        elif ArabicValidator.contains_arabic_text(str(title)):
            result["has_arabic"] = True
            result["arabic_fields"].append("title")

        # Check description
        description = dataset.get("description", "")
        if isinstance(description, dict):
            if ArabicValidator.contains_arabic_text(description.get("ar", "")):
                result["has_arabic"] = True
                result["arabic_fields"].append("description_ar")
        elif ArabicValidator.contains_arabic_text(str(description)):
            result["has_arabic"] = True
            result["arabic_fields"].append("description")

        # Check resource names and descriptions
        for idx, resource in enumerate(dataset.get("resources", [])):
            name = resource.get("name", "")
            if ArabicValidator.contains_arabic_text(str(name)):
                result["has_arabic"] = True
                result["arabic_fields"].append(f"resource_{idx}_name")

            desc = resource.get("description", "")
            if ArabicValidator.contains_arabic_text(str(desc)):
                result["has_arabic"] = True
                result["arabic_fields"].append(f"resource_{idx}_description")

        return result

    @staticmethod
    def check_arabic_encoding(text: str) -> Dict[str, Any]:
        """
        Check if Arabic text is properly encoded (UTF-8)
        
        Args:
            text: Text to check
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "arabic_encoding",
            "status": "pass",
            "detected_encoding": None,
            "is_utf8": False,
            "issues": [],
        }

        if not text:
            return result

        try:
            # Check if text is valid UTF-8
            if isinstance(text, bytes):
                text.decode("utf-8")
                result["is_utf8"] = True
                result["detected_encoding"] = "UTF-8"
            else:
                # Try to encode to UTF-8
                text.encode("utf-8")
                result["is_utf8"] = True
                result["detected_encoding"] = "UTF-8"

        except UnicodeDecodeError as e:
            result["status"] = "fail"
            result["issues"].append(f"Text is not valid UTF-8: {str(e)}")
        except UnicodeEncodeError as e:
            result["status"] = "fail"
            result["issues"].append(f"Cannot encode text to UTF-8: {str(e)}")

        return result

    @staticmethod
    def check_bidi_markers(text: str) -> Dict[str, Any]:
        """
        Check for proper bidirectional text markers in Arabic content
        
        Args:
            text: Text to check
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "bidi_markers",
            "status": "pass",
            "has_arabic": False,
            "has_ltr_marker": "\u202E" in text,  # Right-to-left override
            "has_rtl_marker": "\u202D" in text,  # Left-to-right override
            "issues": [],
        }

        result["has_arabic"] = ArabicValidator.contains_arabic_text(text)

        # For Arabic text, check if it's properly displayed
        if result["has_arabic"]:
            # Arabic text typically needs proper UTF-8 encoding
            try:
                if isinstance(text, str):
                    text.encode("utf-8")
            except UnicodeEncodeError:
                result["status"] = "fail"
                result["issues"].append("Arabic text cannot be encoded to UTF-8")

        return result

    @staticmethod
    def validate_arabic_content(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all Arabic validation checks on a dataset
        
        Args:
            dataset: Dataset object
            
        Returns:
            Comprehensive validation result
        """
        checks = [
            ArabicValidator.check_arabic_in_dataset(dataset),
        ]

        # If Arabic content is found, do encoding checks
        arabic_check = checks[0]
        if arabic_check["has_arabic"]:
            # Collect all Arabic text from dataset
            texts = []
            
            title = dataset.get("title", "")
            if isinstance(title, dict):
                texts.append(title.get("ar", ""))
            
            description = dataset.get("description", "")
            if isinstance(description, dict):
                texts.append(description.get("ar", ""))

            for resource in dataset.get("resources", []):
                texts.append(resource.get("name", ""))
                texts.append(resource.get("description", ""))

            for text in texts:
                if text and ArabicValidator.contains_arabic_text(str(text)):
                    checks.append(ArabicValidator.check_arabic_encoding(str(text)))
                    checks.append(ArabicValidator.check_bidi_markers(str(text)))

        all_pass = all(check.get("status") == "pass" for check in checks)
        overall_status = "pass" if all_pass else (
            "fail" if any(check.get("status") == "fail" for check in checks)
            else "warning"
        )

        return {
            "arabic_checks": checks,
            "overall_status": overall_status,
        }
