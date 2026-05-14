"""Main quality check orchestrator and CLI"""

import logging
import re
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.api import BayanatClient
from src.checks import (
    ResourceValidator,
    ExcelValidator,
    LanguageValidator,
    MetadataValidator,
    ArabicValidator,
    TimePeriodValidator,
)
from src.reporting import ReportGenerator
from src.utils import load_config, setup_logging

logger = logging.getLogger(__name__)


class DataQualityChecker:
    """Main orchestrator for data quality checks"""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the quality checker
        
        Args:
            config_path: Path to configuration file
        """
        self.config = load_config(config_path)
        
        # Setup logging
        log_config = self.config.get("logging", {})
        setup_logging(
            log_level=log_config.get("level", "INFO"),
            log_file=log_config.get("file"),
        )
        logger.info(f"Loaded configuration from {config_path}")
        
        # Initialize API client
        api_config = self.config.get("api", {})
        self.client = BayanatClient(
            base_url=api_config.get("base_url", "https://bayanat.ae/api/3"),
            site_base_url=api_config.get("site_base_url", "https://bayanat.ae"),
            timeout=api_config.get("timeout", 30),
        )
        logger.info(f"Initialized BayanatClient with base_url={self.client.base_url}")
        logger.info(f"Website scraping base URL: {self.client.site_base_url}")

    def check_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all quality checks on a single dataset
        
        Args:
            dataset: Dataset object from API
            
        Returns:
            Comprehensive quality check result
        """
        dataset = self.client.attach_resource_guids_to_dataset(dataset)

        organization = dataset.get("organization")
        if isinstance(organization, dict):
            organization_name = organization.get("title", "N/A")
        else:
            organization_name = organization or "N/A"

        result = {
            "dataset_id": dataset.get("id"),
            "dataset_name": dataset.get("title", "N/A"),
            "dataset_description": dataset.get("description", ""),
            "organization": organization_name,
            "resource_count": len(dataset.get("resources", [])),
            "resource_guids": dataset.get("resource_guids", []),
            "resources": dataset.get("resources", []),
            "years_found": self.extract_years(dataset),
            "checks": {},
            "issues": [],
            "overall_status": "pass",
        }

        quality_checks = self.config.get("quality_checks", {})
        logger.info(
            f"Starting quality checks for dataset_id={result['dataset_id']} "
            f"title={result['dataset_name']} resource_count={result['resource_count']}"
        )

        # Resource validation
        if quality_checks.get("resource_validation", {}).get("enabled", True):
            try:
                logger.info("Starting resource validation")
                resource_result = ResourceValidator.validate_all_resources(dataset)
                result["checks"]["resources"] = resource_result
                logger.info(f"Resource validation completed: {resource_result.get('overall_status')}")

                if resource_result.get("overall_status") == "fail":
                    result["issues"].append("Resource validation failed")
                    result["overall_status"] = "fail"
                elif resource_result.get("overall_status") == "warning":
                    if result["overall_status"] != "fail":
                        result["overall_status"] = "warning"
            except Exception as e:
                logger.error(f"Error in resource validation: {e}")
                result["checks"]["resources"] = {"error": str(e)}

        # Metadata validation
        if quality_checks.get("metadata", {}).get("enabled", True):
            try:
                logger.info("Starting metadata validation")
                metadata_result = MetadataValidator.validate_metadata(dataset)
                result["checks"]["metadata"] = metadata_result
                logger.info(f"Metadata validation completed: {metadata_result.get('overall_status')}")
                
                if metadata_result.get("overall_status") == "fail":
                    result["issues"].append("Metadata validation failed")
                    result["overall_status"] = "fail"
                elif metadata_result.get("overall_status") == "warning":
                    if result["overall_status"] != "fail":
                        result["overall_status"] = "warning"
            except Exception as e:
                logger.error(f"Error in metadata validation: {e}")
                result["checks"]["metadata"] = {"error": str(e)}

        # Language validation
        if quality_checks.get("language_check", {}).get("enabled", True):
            try:
                logger.info("Starting language validation")
                language_result = LanguageValidator.validate_languages(dataset)
                result["checks"]["language"] = language_result
                logger.info(f"Language validation completed: {language_result.get('overall_status')}")
                
                # Check if bilingual
                lang_checks = language_result.get("language_checks", [])
                bilingual_check = next(
                    (c for c in lang_checks if c.get("check") == "bilingual_content"),
                    None,
                )
                result["bilingual"] = (
                    bilingual_check.get("status") == "pass"
                    if bilingual_check
                    else False
                )
                
                if language_result.get("overall_status") == "fail":
                    result["issues"].append("Language validation failed")
                    result["overall_status"] = "fail"
                elif language_result.get("overall_status") == "warning":
                    if result["overall_status"] != "fail":
                        result["overall_status"] = "warning"
            except Exception as e:
                logger.error(f"Error in language validation: {e}")
                result["checks"]["language"] = {"error": str(e)}

        # Arabic validation
        if quality_checks.get("arabic_encoding", {}).get("enabled", True):
            try:
                logger.info("Starting Arabic validation")
                arabic_result = ArabicValidator.validate_arabic_content(dataset)
                result["checks"]["arabic"] = arabic_result
                logger.info(f"Arabic validation completed: {arabic_result.get('overall_status')}")
                
                if arabic_result.get("overall_status") == "warning":
                    if result["overall_status"] != "fail":
                        result["overall_status"] = "warning"
            except Exception as e:
                logger.error(f"Error in Arabic validation: {e}")
                result["checks"]["arabic"] = {"error": str(e)}

        # Time period validation
        if quality_checks.get("time_period", {}).get("enabled", True):
            try:
                logger.info("Starting time period validation")
                time_result = TimePeriodValidator.validate_time_period(dataset)
                result["checks"]["time_period"] = time_result
                logger.info(f"Time period validation completed: {time_result.get('overall_status')}")
            except Exception as e:
                logger.error(f"Error in time period validation: {e}")
                result["checks"]["time_period"] = {"error": str(e)}

        return result

    def extract_years(self, dataset: Dict[str, Any]) -> List[str]:
        year_pattern = re.compile(r"\b(?:19|20)\d{2}\b")
        years = set()

        def scan(value: Any):
            if isinstance(value, dict):
                for k, v in value.items():
                    scan(k)
                    scan(v)
            elif isinstance(value, list):
                for item in value:
                    scan(item)
            else:
                try:
                    text = str(value)
                except Exception:
                    return
                for match in year_pattern.findall(text):
                    years.add(match)

        scan(dataset)

        # If metadata does not reveal year values, inspect resource content previews.
        if not years:
            for resource in dataset.get("resources", []):
                preview = self._get_resource_preview_text(resource)
                if preview:
                    for match in year_pattern.findall(preview):
                        years.add(match)
                if years:
                    break

        return sorted(years)

    def _get_resource_preview_text(self, resource: Dict[str, Any], max_bytes: int = 200000) -> str:
        if resource.get("resource_guid"):
            return self.client.fetch_resource_preview_by_guid(resource["resource_guid"], max_bytes=max_bytes)
        if resource.get("url"):
            return self.client.fetch_resource_preview_by_url(resource["url"], max_bytes=max_bytes)
        return ""

    def check_dataset_by_id(self, dataset_id: str) -> Dict[str, Any]:
        logger.info(f"Scraping dataset page for dataset_id={dataset_id}")
        dataset = self.client.scrape_dataset_page(dataset_id)
        logger.info(
            f"Dataset scraped: {dataset.get('title') or dataset.get('name') or dataset_id}"
        )
        return self.check_dataset(dataset)

    def check_dataset_by_url(self, dataset_url: str) -> Dict[str, Any]:
        logger.info(f"Scraping dataset page for dataset_url={dataset_url}")
        dataset = self.client.scrape_dataset_page(dataset_url)
        logger.info(
            f"Dataset scraped: {dataset.get('title') or dataset.get('name') or dataset_url}"
        )
        return self.check_dataset(dataset)

    def check_datasets_by_organization(
        self,
        organization_id: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Check all datasets for an organization
        
        Args:
            organization_id: Organization ID to check (if None, checks all)
            limit: Maximum number of datasets to check
            
        Returns:
            List of quality check results
        """
        results = []

        try:
            if organization_id:
                logger.info(f"Fetching datasets for organization: {organization_id}")
                org_data = self.client.get_organization_datasets(organization_id)
                datasets = org_data.get("result", {}).get("packages", [])
            else:
                logger.info(f"Fetching first {limit} datasets from portal")
                data = self.client.get_datasets(limit=limit)
                datasets = data.get("result", {}).get("results", [])

            total = len(datasets)
            logger.info(f"Found {total} dataset(s) to check")

            for idx, dataset in enumerate(datasets, 1):
                logger.info(f"Checking dataset {idx}/{total}: {dataset.get('id')}")
                try:
                    result = self.check_dataset(dataset)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error checking dataset {dataset.get('id')}: {e}")
                    results.append({
                        "dataset_id": dataset.get("id"),
                        "dataset_name": dataset.get("title"),
                        "organization": dataset.get("organization", {}).get("title"),
                        "overall_status": "error",
                        "error": str(e),
                    })

        except Exception as e:
            logger.error(f"Error fetching datasets: {e}")
            return results

        return results

    def check_all_organizations(self, limit_per_org: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Check datasets for all organizations
        
        Args:
            limit_per_org: Maximum datasets per organization
            
        Returns:
            Dictionary mapping organization name to results
        """
        all_results = {}

        try:
            org_data = self.client.get_organizations()
            organizations = org_data.get("result", [])
            
            logger.info(f"Found {len(organizations)} organizations")

            for org in organizations:
                org_name = org.get("title", org.get("name"))
                org_id = org.get("id")
                
                logger.info(f"Processing organization: {org_name}")
                
                org_results = self.check_datasets_by_organization(
                    organization_id=org_id,
                    limit=limit_per_org,
                )
                
                all_results[org_name] = org_results

        except Exception as e:
            logger.error(f"Error fetching organizations: {e}")

        return all_results

    def generate_reports(
        self,
        results: List[Dict[str, Any]],
        output_dir: str = "./reports",
        formats: List[str] = None,
    ) -> Dict[str, str]:
        """
        Generate quality check reports
        
        Args:
            results: List of quality check results
            output_dir: Directory to save reports
            formats: Report formats (json, csv, html)
            
        Returns:
            Dictionary of generated report files
        """
        if formats is None:
            formats = self.config.get("reporting", {}).get("output_formats", ["json", "csv", "html"])

        logger.info(f"Generating reports in {output_dir} for formats: {formats}")
        files = ReportGenerator.save_report(
            results,
            output_dir=output_dir,
            formats=formats,
            include_summary=self.config.get("reporting", {}).get("include_summary", True),
        )
        logger.info(f"Reports generated: {files}")
        return files

    def close(self):
        """Close the API client"""
        logger.info("Closing DataQualityChecker and Bayanat API client")
        self.client.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bayanat Open Data Portal Quality Checker"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--organization",
        help="Specific organization ID to check",
    )
    parser.add_argument(
        "--dataset-id",
        help="Dataset ID to scrape and check from the public website",
    )
    parser.add_argument(
        "--dataset-url",
        help="Dataset page URL to scrape and check from the public website",
    )
    parser.add_argument(
        "--all-orgs",
        action="store_true",
        help="Check all organizations",
    )
    parser.add_argument(
        "--output-dir",
        default="./reports",
        help="Output directory for reports (default: ./reports)",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["json", "csv", "html"],
        help="Report formats to generate (default: json csv html)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of datasets to check (default: 1000)",
    )

    args = parser.parse_args()

    try:
        # Initialize checker
        checker = DataQualityChecker(config_path=args.config)
        logger.info("Data Quality Checker initialized")

        # Run checks
        if args.dataset_url:
            logger.info(f"Checking single dataset URL: {args.dataset_url}")
            results = [checker.check_dataset_by_url(args.dataset_url)]
            logger.info("Generating reports")
            files = checker.generate_reports(results, args.output_dir, args.formats)
            for fmt, path in files.items():
                print(f"✓ {fmt.upper()} report saved to: {path}")
        elif args.dataset_id:
            logger.info(f"Checking single dataset ID: {args.dataset_id}")
            results = [checker.check_dataset_by_id(args.dataset_id)]
            logger.info("Generating reports")
            files = checker.generate_reports(results, args.output_dir, args.formats)
            for fmt, path in files.items():
                print(f"✓ {fmt.upper()} report saved to: {path}")
        elif args.all_orgs:
            logger.info("Checking all organizations")
            all_results = checker.check_all_organizations(limit_per_org=args.limit)

            # Generate reports for each organization
            for org_name, results in all_results.items():
                org_output_dir = str(Path(args.output_dir) / org_name.replace(" ", "_"))
                logger.info(f"Generating reports for {org_name}")
                files = checker.generate_reports(results, org_output_dir, args.formats)

                for fmt, path in files.items():
                    print(f"✓ {org_name} - {fmt.upper()} report: {path}")
        else:
            # Check specific organization or all datasets
            results = checker.check_datasets_by_organization(
                organization_id=args.organization,
                limit=args.limit,
            )

            # Generate reports
            logger.info("Generating reports")
            files = checker.generate_reports(results, args.output_dir, args.formats)

            for fmt, path in files.items():
                print(f"✓ {fmt.upper()} report saved to: {path}")

        # Print summary
        summary = ReportGenerator.generate_summary(results if not args.all_orgs else [r for results_list in all_results.values() for r in results_list])
        
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Total Datasets: {summary['total_datasets']}")
        print(f"Passed: {summary['passed']} ({summary['pass_percentage']}%)")
        print(f"Warnings: {summary['warnings']}")
        print(f"Failed: {summary['failed']}")
        print("="*50)

        checker.close()

    except KeyboardInterrupt:
        logger.info("Quality check interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
