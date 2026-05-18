"""Language validation checks"""

import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class LanguageValidator:
    """Validates language coverage in datasets"""

    @staticmethod
    def extract_language_codes(dataset: Dict[str, Any]) -> List[str]:
        """
        Extract language codes from dataset metadata
        
        Args:
            dataset: Dataset object
            
        Returns:
            List of language codes found
        """
        languages = set()
        
        # Check explicit language field
        if "language" in dataset:
            lang = dataset["language"]
            if isinstance(lang, list):
                languages.update(lang)
            elif isinstance(lang, str):
                languages.add(lang)

        # Check if dataset has multilingual content
        if "multilingual_resources" in dataset:
            languages.update(dataset["multilingual_resources"])

        # Normalize language codes to lowercase ISO 639-1
        normalized = set()
        for lang in languages:
            if isinstance(lang, str):
                # Extract 2-letter language code
                code = lang.lower().split("-")[0][:2]
                if len(code) == 2:
                    normalized.add(code)

        return list(normalized)

    @staticmethod
    def has_arabic_text(text: str) -> bool:
        return bool(re.search(r"[\u0600-\u06FF]", str(text)))

    @staticmethod
    def has_english_text(text: str) -> bool:
        return bool(re.search(r"[A-Za-z]", str(text)))

    @staticmethod
    def check_bilingual_content(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset is available in both Arabic and English
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "bilingual_content",
            "status": "pass",
            "languages_found": [],
            "issues": [],
        }

        languages = LanguageValidator.extract_language_codes(dataset)
        ar_resources = []
        en_resources = []

        for resource in dataset.get("resources", []):
            combined_text = " ".join(
                [str(resource.get("name", "")), str(resource.get("description", ""))]
            )

            if LanguageValidator.has_arabic_text(combined_text):
                ar_resources.append(resource.get("name"))
            if LanguageValidator.has_english_text(combined_text):
                en_resources.append(resource.get("name"))

            resource_lang = str(resource.get("language", "")).lower()
            if "ar" in resource_lang:
                ar_resources.append(resource.get("name"))
            if "en" in resource_lang:
                en_resources.append(resource.get("name"))

        dataset_text = ""
        if isinstance(dataset.get("title"), dict):
            dataset_text = " ".join(str(v) for v in dataset["title"].values() if v)
        else:
            dataset_text = str(dataset.get("title", ""))
        dataset_text += " " + str(dataset.get("description", ""))

        if LanguageValidator.has_arabic_text(dataset_text):
            ar_resources.append("dataset_text")
        if LanguageValidator.has_english_text(dataset_text):
            en_resources.append("dataset_text")

        result["en_resources"] = list(set(en_resources))
        result["ar_resources"] = list(set(ar_resources))
        result["languages_found"] = list(
            set(languages + (["ar"] if ar_resources else []) + (["en"] if en_resources else []))
        )
        has_ar = len(ar_resources) > 0
        has_en = len(en_resources) > 0

        if not has_ar:
            result["issues"].append("No Arabic resources found")
        if not has_en:
            result["issues"].append("No English resources found")

        if not (has_ar and has_en):
            result["status"] = "fail"
        elif result["issues"]:
            result["status"] = "warning"

        return result

    @staticmethod
    def check_title_translation(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if dataset title is available in both languages
        
        Args:
            dataset: Dataset object
            
        Returns:
            Result dictionary with check status
        """
        result = {
            "check": "title_translation",
            "status": "pass",
            "has_ar_title": False,
            "has_en_title": False,
            "issues": [],
        }

        title = dataset.get("title", "")
        
        if isinstance(title, dict):
            result["has_en_title"] = bool(title.get("en"))
            result["has_ar_title"] = bool(title.get("ar"))
            
            if not result["has_en_title"]:
                result["issues"].append("Dataset title missing in English")
            if not result["has_ar_title"]:
                result["issues"].append("Dataset title missing in Arabic")
        else:
            # Single language title
            result["issues"].append("Title should be available in both languages")

        if result["issues"]:
            result["status"] = "fail" if len(result["issues"]) > 1 else "warning"

        return result

    @staticmethod
    def validate_languages(dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all language validation checks on a dataset
        
        Args:
            dataset: Dataset object
            
        Returns:
            Comprehensive validation result
        """
        checks = [
            LanguageValidator.check_bilingual_content(dataset),
            LanguageValidator.check_title_translation(dataset),
        ]

        all_pass = all(check.get("status") == "pass" for check in checks)
        overall_status = "pass" if all_pass else (
            "fail" if any(check.get("status") == "fail" for check in checks)
            else "warning"
        )

        return {
            "language_checks": checks,
            "overall_status": overall_status,
        }
