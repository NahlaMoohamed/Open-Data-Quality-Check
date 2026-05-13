"""Main quality check orchestrator and CLI"""

import logging
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
        
        # Initialize API client
        api_config = self.config.get("api", {})
        self.client = BayanatClient(
            base_url=api_config.get("base_url", "https://bayanat.ae/api/3"),
            timeout=api_config.get("timeout", 30),
        )

    def check_dataset(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all quality checks on a single dataset
        
        Args:
            dataset: Dataset object from API
            
        Returns:
            Comprehensive quality check result
        """
        result = {
            "dataset_id": dataset.get("id"),
            "dataset_name": dataset.get("title", "N/A"),
            "organization": dataset.get("organization", {}).get("title", "N/A"),
            "resource_count": len(dataset.get("resources", [])),
            "checks": {},
            "issues": [],
            "overall_status": "pass",
        }

        quality_checks = self.config.get("quality_checks", {})

        # Resource validation
        if quality_checks.get("resource_validation", {}).get("enabled", True):
            try:
                resource_result = ResourceValidator.validate_all_resources(dataset)
                result["checks"]["resources"] = resource_result
                
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
                metadata_result = MetadataValidator.validate_metadata(dataset)
                result["checks"]["metadata"] = metadata_result
                
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
                language_result = LanguageValidator.validate_languages(dataset)
                result["checks"]["language"] = language_result
                
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
                arabic_result = ArabicValidator.validate_arabic_content(dataset)
                result["checks"]["arabic"] = arabic_result
                
                if arabic_result.get("overall_status") == "warning":
                    if result["overall_status"] != "fail":
                        result["overall_status"] = "warning"
            except Exception as e:
                logger.error(f"Error in Arabic validation: {e}")
                result["checks"]["arabic"] = {"error": str(e)}

        # Time period validation
        if quality_checks.get("time_period", {}).get("enabled", True):
            try:
                time_result = TimePeriodValidator.validate_time_period(dataset)
                result["checks"]["time_period"] = time_result
            except Exception as e:
                logger.error(f"Error in time period validation: {e}")
                result["checks"]["time_period"] = {"error": str(e)}

        return result

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

        return ReportGenerator.save_report(
            results,
            output_dir=output_dir,
            formats=formats,
            include_summary=self.config.get("reporting", {}).get("include_summary", True),
        )

    def close(self):
        """Close the API client"""
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
        if args.all_orgs:
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
