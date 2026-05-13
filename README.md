# Open Data Quality Check - Bayanat Portal Validator

Comprehensive data quality validation tool for the Bayanat open data portal (https://bayanat.ae/). This tool performs automated quality checks on datasets to ensure compliance with data standards and best practices.

## Features

### Quality Checks Implemented

1. **Resource Validation**
   - Verifies dataset has resources
   - Checks resource accessibility and validity
   - Validates resource format and metadata
   - Detects corrupted resources

2. **Excel File Validation**
   - Ensures each Excel resource has only 1 sheet
   - Detects and flags pivot tables
   - Validates data integrity (row/column counts, headers)

3. **Language & Bilingual Content**
   - Verifies dataset is available in both Arabic (AR) and English (EN)
   - Checks title translations
   - Detects multilingual resources

4. **Metadata Validation**
   - Checks for required metadata fields (title, description, organization, resources)
   - Validates optional important fields (author, license, tags)
   - Verifies description quality
   - Confirms presence of data dictionary/metadata files

5. **Arabic Content Validation**
   - Detects Arabic text presence
   - Validates UTF-8 encoding
   - Ensures proper bidirectional text handling
   - Flags encoding issues

6. **Time Period Information**
   - Checks for temporal data coverage
   - Extracts date ranges from metadata
   - Validates time period documentation

7. **Organization-Based Management**
   - Check datasets by specific organization
   - Batch check all organizations
   - Organization-segregated reporting

## Project Structure

```
Open-Data-Quality-Check/
├── src/
│   ├── api/
│   │   └── bayanat_client.py       # Bayanat API client
│   ├── checks/
│   │   ├── resource_check.py       # Resource validation
│   │   ├── excel_check.py          # Excel file validation
│   │   ├── language_check.py       # Language & bilingual checks
│   │   ├── metadata_check.py       # Metadata validation
│   │   ├── arabic_check.py         # Arabic encoding validation
│   │   └── timeperiod_check.py     # Time period validation
│   ├── reporting/
│   │   └── report_generator.py     # Report generation (JSON, CSV, HTML)
│   └── utils/
│       └── __init__.py             # Configuration and utilities
├── data/                           # Downloaded datasets
├── reports/                        # Generated reports
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
├── quality_check.py                # Main entry point
└── README.md                       # This file
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Open-Data-Quality-Check
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.yaml` to customize checks:

```yaml
api:
  base_url: "https://bayanat.ae/api/3"
  timeout: 30

quality_checks:
  resource_validation:
    enabled: true
    max_file_size_mb: 500
  
  language_check:
    enabled: true
    required_languages: ["en", "ar"]
  
  excel_validation:
    enabled: true
    max_sheets: 1
    check_pivot_tables: true
  
  metadata:
    enabled: true
  
  arabic_encoding:
    enabled: true
  
  time_period:
    enabled: true

reporting:
  output_formats: ["json", "csv", "html"]
  save_dir: "./reports"
```

## Usage

### Basic Usage

```bash
# Check all datasets (first 1000)
python quality_check.py

# Check specific organization
python quality_check.py --organization <org-id>

# Check all organizations
python quality_check.py --all-orgs

# Custom output directory and formats
python quality_check.py --output-dir ./my_reports --formats json html

# Limit number of datasets
python quality_check.py --limit 500
```

### Command Line Options

```
--config           Path to config file (default: config.yaml)
--organization     Specific organization ID to check
--all-orgs         Check all organizations
--output-dir       Output directory for reports (default: ./reports)
--formats          Report formats: json csv html (default: all)
--limit            Max datasets to check (default: 1000)
```

### Example Commands

```bash
# Check Ministry of Health datasets
python quality_check.py --organization ministry-of-health --formats json html

# Check all organizations with detailed reports
python quality_check.py --all-orgs

# Check 100 datasets and save as CSV
python quality_check.py --limit 100 --formats csv

# Use custom config
python quality_check.py --config my_config.yaml
```

## Output Reports

Reports are generated in three formats:

### JSON Report
- Complete check results with all details
- Structured format for programmatic processing
- Includes overall summary statistics

### CSV Report
- Tabular summary format
- One row per dataset
- Quick overview of status across datasets

### HTML Report
- Bilingual (AR/EN) visual report
- Interactive table with status indicators
- Includes summary cards
- Styled for easy viewing

## Understanding Results

### Status Levels

- **PASS**: Dataset meets all quality requirements
- **WARNING**: Dataset has minor issues or missing optional fields
- **FAIL**: Dataset has critical issues requiring attention

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| No resources | Dataset has no attached files | Add resources (Excel, CSV, etc.) |
| Multiple sheets | Excel has more than 1 sheet | Consolidate into single sheet |
| Missing metadata | Required fields empty | Fill title, description, organization |
| Not bilingual | No Arabic or English content | Provide translations |
| Arabic encoding error | Invalid UTF-8 encoding | Re-save with UTF-8 encoding |
| No data dictionary | Missing documentation | Add metadata/documentation resource |

## Python API Usage

```python
from src.api import BayanatClient
from src.checks import ResourceValidator, LanguageValidator
from src.reporting import ReportGenerator

# Initialize client
client = BayanatClient()

# Get datasets
data = client.get_datasets(limit=10)
datasets = data['result']['results']

# Check a dataset
results = []
for dataset in datasets:
    resource_check = ResourceValidator.validate_all_resources(dataset)
    language_check = LanguageValidator.validate_languages(dataset)
    
    result = {
        'dataset_id': dataset['id'],
        'resource_check': resource_check,
        'language_check': language_check,
    }
    results.append(result)

# Generate reports
ReportGenerator.save_report(results, output_dir='./reports')
```

## API Reference

### BayanatClient

```python
client = BayanatClient(base_url, timeout)

# Get datasets
client.get_datasets(organization=None, limit=1000, offset=0)

# Get dataset details
client.get_dataset_details(dataset_id)

# Get organizations
client.get_organizations()

# Get organization datasets
client.get_organization_datasets(org_id, limit=1000)

# Download resource
client.download_resource(resource_url, save_path)
```

### Quality Validators

Each validator has `validate_*` methods:

```python
# Resource validation
ResourceValidator.validate_all_resources(dataset)

# Excel validation
ExcelValidator.validate_excel_file(file_path)

# Language validation
LanguageValidator.validate_languages(dataset)

# Metadata validation
MetadataValidator.validate_metadata(dataset)

# Arabic validation
ArabicValidator.validate_arabic_content(dataset)

# Time period validation
TimePeriodValidator.validate_time_period(dataset)
```

## Logging

Logs are saved to `logs/quality_check.log`. Configure logging level in `config.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/quality_check.log"
```

## Development

### Adding New Checks

1. Create new validator in `src/checks/`
2. Implement check methods returning dict with `check`, `status`, and `issues`
3. Add to `DataQualityChecker.check_dataset()`
4. Add configuration option in `config.yaml`

### Running Tests

```bash
# Run specific check
python -c "from src.checks import ResourceValidator; print(ResourceValidator.check_has_resources(dataset))"
```

## Performance Considerations

- API timeout: 30 seconds (configurable)
- Batch size: Up to 1000 datasets per request
- Rate limiting: Respect Bayanat API rate limits
- Memory: Streaming for large file downloads

## Troubleshooting

### Connection Issues

```bash
# Check API connectivity
python -c "from src.api import BayanatClient; c = BayanatClient(); print(c.get_organizations())"
```

### Excel Validation Errors

- Ensure openpyxl is installed: `pip install openpyxl`
- Some complex Excel files may not be readable

### Arabic Encoding Issues

- Verify UTF-8 encoding in source files
- Use chardet for encoding detection: included in requirements

## Contributing

Contributions welcome! Areas for enhancement:

- Additional file format validation (CSV, JSON, XML)
- Data profile generation
- Duplicate detection
- Schema validation
- Performance optimizations

## License

[Add your license here]

## Support

For issues and questions:
- Check existing GitHub issues
- Review logs in `logs/quality_check.log`
- Consult Bayanat API documentation at https://bayanat.ae/

## Related Resources

- [Bayanat Open Data Portal](https://bayanat.ae/)
- [CKAN API Documentation](https://docs.ckan.org/en/latest/api/)
- [Open Data Standards](https://opendatahandbook.org/)