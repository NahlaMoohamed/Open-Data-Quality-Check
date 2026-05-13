"""
Example usage of the Data Quality Checker

This script demonstrates various ways to use the quality check tool
"""

from quality_check import DataQualityChecker
from src.reporting import ReportGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_check_all_datasets():
    """Example: Check all datasets (first 100)"""
    logger.info("Example 1: Checking all datasets")
    
    checker = DataQualityChecker()
    
    # Get first 100 datasets
    results = checker.check_datasets_by_organization(limit=100)
    
    # Generate reports
    files = checker.generate_reports(results, output_dir="./reports/all_datasets")
    
    print("Reports generated:")
    for fmt, path in files.items():
        print(f"  {fmt}: {path}")
    
    checker.close()


def example_check_organization():
    """Example: Check specific organization"""
    logger.info("Example 2: Checking specific organization")
    
    checker = DataQualityChecker()
    
    # Replace with actual organization ID
    org_id = "ministry-of-health"
    results = checker.check_datasets_by_organization(organization_id=org_id, limit=50)
    
    # Generate reports
    files = checker.generate_reports(
        results, 
        output_dir=f"./reports/{org_id}",
        formats=["json", "html"]
    )
    
    print(f"Reports for {org_id}:")
    for fmt, path in files.items():
        print(f"  {fmt}: {path}")
    
    checker.close()


def example_check_all_organizations():
    """Example: Check all organizations"""
    logger.info("Example 3: Checking all organizations")
    
    checker = DataQualityChecker()
    
    # This will take a while - checking all organizations
    all_results = checker.check_all_organizations(limit_per_org=50)
    
    # Generate individual organization reports
    for org_name, results in all_results.items():
        org_dir = org_name.replace(" ", "_")
        files = checker.generate_reports(
            results,
            output_dir=f"./reports/by_organization/{org_dir}"
        )
        print(f"{org_name}: {len(results)} datasets checked")
    
    checker.close()


def example_custom_checks():
    """Example: Run custom checks on specific dataset"""
    logger.info("Example 4: Custom checks on specific dataset")
    
    from src.api import BayanatClient
    from src.checks import (
        ResourceValidator,
        LanguageValidator,
        MetadataValidator,
        ArabicValidator,
    )
    
    # Get a dataset
    client = BayanatClient()
    datasets = client.get_datasets(limit=1)["result"]["results"]
    dataset = datasets[0]
    
    print(f"\nDataset: {dataset.get('title')}")
    print("=" * 50)
    
    # Run individual checks
    print("\n1. Resource Checks:")
    resource_result = ResourceValidator.validate_all_resources(dataset)
    print(f"   Status: {resource_result['overall_status']}")
    print(f"   Resources: {resource_result['resource_checks'][0]['resource_count']}")
    
    print("\n2. Metadata Checks:")
    metadata_result = MetadataValidator.validate_metadata(dataset)
    print(f"   Status: {metadata_result['overall_status']}")
    for check in metadata_result['metadata_checks']:
        if check.get('issues'):
            print(f"   Issues: {check['issues']}")
    
    print("\n3. Language Checks:")
    language_result = LanguageValidator.validate_languages(dataset)
    print(f"   Status: {language_result['overall_status']}")
    lang_check = language_result['language_checks'][0]
    print(f"   Languages: {lang_check.get('languages_found')}")
    
    print("\n4. Arabic Checks:")
    arabic_result = ArabicValidator.validate_arabic_content(dataset)
    print(f"   Status: {arabic_result['overall_status']}")
    arabic_check = arabic_result['arabic_checks'][0]
    print(f"   Has Arabic: {arabic_check.get('has_arabic')}")
    
    client.close()


def example_filter_by_status():
    """Example: Filter results by status"""
    logger.info("Example 5: Filter results by status")
    
    checker = DataQualityChecker()
    
    results = checker.check_datasets_by_organization(limit=50)
    
    # Filter by status
    passed = [r for r in results if r['overall_status'] == 'pass']
    warnings = [r for r in results if r['overall_status'] == 'warning']
    failed = [r for r in results if r['overall_status'] == 'fail']
    
    print(f"\nResults Summary:")
    print(f"  Passed: {len(passed)}")
    print(f"  Warnings: {len(warnings)}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print(f"\nFailed datasets:")
        for result in failed:
            print(f"  - {result['dataset_name']}")
            print(f"    Issues: {result.get('issues')}")
    
    checker.close()


def example_export_summary():
    """Example: Export summary statistics"""
    logger.info("Example 6: Export summary statistics")
    
    checker = DataQualityChecker()
    
    results = checker.check_datasets_by_organization(limit=100)
    
    # Generate summary
    summary = ReportGenerator.generate_summary(results)
    
    print(f"\nQuality Check Summary:")
    print(f"  Total Datasets: {summary['total_datasets']}")
    print(f"  Passed: {summary['passed']} ({summary['pass_percentage']}%)")
    print(f"  Warnings: {summary['warnings']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Timestamp: {summary['timestamp']}")
    
    checker.close()


if __name__ == "__main__":
    # Run examples (uncomment to execute)
    
    # example_check_all_datasets()
    # example_check_organization()
    # example_check_all_organizations()
    example_custom_checks()
    # example_filter_by_status()
    # example_export_summary()
