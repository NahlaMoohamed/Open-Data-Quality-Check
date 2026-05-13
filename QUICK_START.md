# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run First Check
```bash
# Check first 50 datasets
python quality_check.py --limit 50

# Check specific organization
python quality_check.py --organization <org-id> --limit 100

# Check all organizations
python quality_check.py --all-orgs --limit 50
```

### 3. Find Reports
Reports are saved in `./reports/` by default:
- `quality_check_report_*.json` - Complete detailed results
- `quality_check_report_*.csv` - Summary table
- `quality_check_report_*.html` - Visual bilingual report

## Common Use Cases

### Use Case 1: Review Datasets from Ministry of Health
```bash
python quality_check.py --organization ministry-of-health --formats html csv
```
Then open the HTML report in a browser.

### Use Case 2: Audit All Organizations
```bash
python quality_check.py --all-orgs --limit 100
```
Reports will be organized by organization name in `./reports/by_organization/`

### Use Case 3: Deep Dive into a Single Dataset
```python
from examples import example_custom_checks
example_custom_checks()
```

## Understanding the Checks

| Check | What It Does | Why It Matters |
|-------|-------------|-----------------|
| **Resource Validation** | Verifies files exist and are accessible | Broken links = useless data |
| **Excel Sheets** | Ensures 1 sheet per file | Multiple sheets = confusion |
| **Languages (AR/EN)** | Confirms bilingual content | UAE citizens need both languages |
| **Metadata** | Checks title, description, tags | Missing metadata = hard to find data |
| **Arabic Encoding** | Validates UTF-8 Arabic text | Corrupted Arabic = unreadable |
| **Data Dictionary** | Looks for documentation files | Users need to understand the data |
| **Time Period** | Finds date range info | Users need to know data currency |

## Output Files

After running checks, you'll find:

```
reports/
├── quality_check_report_20240513_143022.json
├── quality_check_report_20240513_143022.csv
└── quality_check_report_20240513_143022.html
```

### JSON Format (for processing)
```json
{
  "summary": {
    "total_datasets": 50,
    "passed": 35,
    "warnings": 10,
    "failed": 5,
    "pass_percentage": 70.0
  },
  "results": [
    {
      "dataset_id": "...",
      "dataset_name": "...",
      "overall_status": "pass|warning|fail",
      "checks": { ... },
      "issues": [ ... ]
    }
  ]
}
```

### CSV Format (for spreadsheets)
```
Dataset ID, Dataset Name, Organization, Status, Resources, Issues
dataset-1, Ministry Health Data, Ministry of Health, PASS, 3, 
dataset-2, Education Stats, Ministry of Education, FAIL, 1, Missing Arabic content
```

### HTML Format (for viewing)
Bilingual Arabic/English visual report with:
- Summary statistics
- Color-coded status indicators
- Interactive table
- Print-friendly styling

## Configuration

Edit `config.yaml` to:
- Enable/disable specific checks
- Set file size limits
- Configure logging
- Change output formats

## Troubleshooting

### "Connection refused"
```
✗ API not responding
→ Check internet connection and https://bayanat.ae/ is accessible
```

### "No module named 'openpyxl'"
```
✗ Excel validation failing
→ pip install openpyxl
```

### "Empty results"
```
✗ No datasets found
→ Check organization ID is correct
→ Try without organization filter: python quality_check.py --limit 10
```

### "UTF-8 decode error"
```
✗ Arabic encoding issue
→ Check source files are UTF-8 encoded
→ Use a text editor that can convert encoding
```

## Next Steps

1. **Review HTML report** - Open the `.html` file in your browser
2. **Export for sharing** - CSV format works well for stakeholders
3. **Create organization reports** - Use `--all-orgs` for comprehensive audit
4. **Schedule regular checks** - Use cron (Linux/Mac) or Task Scheduler (Windows)

## API Development

Use the tool programmatically:

```python
from quality_check import DataQualityChecker

checker = DataQualityChecker()
results = checker.check_datasets_by_organization(
    organization_id="ministry-of-health",
    limit=100
)

for result in results:
    print(f"{result['dataset_name']}: {result['overall_status']}")

files = checker.generate_reports(results)
checker.close()
```

See `examples.py` for more patterns.

## Performance Tips

- **Large organizations**: Use `--limit 100` first, then increase
- **All orgs**: Run during off-hours (slower, many API calls)
- **Memory issues**: Process by organization, not all at once
- **Timeout issues**: Increase in `config.yaml` under `api.timeout`

## Need Help?

1. Check `logs/quality_check.log` for detailed errors
2. Review examples in `examples.py`
3. Read full documentation in `README.md`
4. Consult `config.yaml` for all options
