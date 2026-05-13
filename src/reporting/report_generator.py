"""Report generation and formatting"""

import json
import csv
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates quality check reports in multiple formats"""

    @staticmethod
    def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of all quality checks
        
        Args:
            results: List of quality check results
            
        Returns:
            Summary dictionary
        """
        total_datasets = len(results)
        passed = sum(1 for r in results if r.get("overall_status") == "pass")
        warnings = sum(1 for r in results if r.get("overall_status") == "warning")
        failed = sum(1 for r in results if r.get("overall_status") == "fail")

        return {
            "total_datasets": total_datasets,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "pass_percentage": round((passed / total_datasets * 100) if total_datasets > 0 else 0, 2),
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def save_json_report(
        results: List[Dict[str, Any]],
        output_path: str,
        include_summary: bool = True,
    ) -> str:
        """
        Save results as JSON report
        
        Args:
            results: List of quality check results
            output_path: Path to save report
            include_summary: Whether to include summary
            
        Returns:
            Path to saved report
        """
        report = {
            "results": results,
        }

        if include_summary:
            report["summary"] = ReportGenerator.generate_summary(results)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON report saved to {output_file}")
        return str(output_file)

    @staticmethod
    def save_csv_report(
        results: List[Dict[str, Any]],
        output_path: str,
    ) -> str:
        """
        Save results as CSV report (summary view)
        
        Args:
            results: List of quality check results
            output_path: Path to save report
            
        Returns:
            Path to saved report
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for result in results:
            row = {
                "Dataset ID": result.get("dataset_id"),
                "Dataset Name": result.get("dataset_name"),
                "Organization": result.get("organization"),
                "Overall Status": result.get("overall_status"),
                "Resources": result.get("resource_count", 0),
                "Has Resources": "Yes" if result.get("resource_count", 0) > 0 else "No",
                "Bilingual": result.get("bilingual", "Unknown"),
                "Issues": "|".join(result.get("issues", [])),
            }
            rows.append(row)

        if rows:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)

            logger.info(f"CSV report saved to {output_file}")

        return str(output_file)

    @staticmethod
    def save_html_report(
        results: List[Dict[str, Any]],
        output_path: str,
        include_summary: bool = True,
    ) -> str:
        """
        Save results as HTML report
        
        Args:
            results: List of quality check results
            output_path: Path to save report
            include_summary: Whether to include summary
            
        Returns:
            Path to saved report
        """
        summary = ReportGenerator.generate_summary(results) if include_summary else None

        html_content = """
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Open Data Quality Check Report</title>
    <style>
        body {
            font-family: Arial, Segoe UI, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
            direction: rtl;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: white;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
        }
        .summary-card .value {
            font-size: 28px;
            font-weight: bold;
            color: #3498db;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th {
            background-color: #34495e;
            color: white;
            padding: 12px;
            text-align: right;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .status-pass {
            color: #27ae60;
            font-weight: bold;
        }
        .status-warning {
            color: #f39c12;
            font-weight: bold;
        }
        .status-fail {
            color: #e74c3c;
            font-weight: bold;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>تقرير فحص جودة البيانات المفتوحة</h1>
        <p>Open Data Quality Check Report</p>
    </div>
"""

        if summary:
            html_content += f"""
    <div class="summary">
        <div class="summary-card">
            <h3>إجمالي مجموعات البيانات / Total Datasets</h3>
            <div class="value">{summary['total_datasets']}</div>
        </div>
        <div class="summary-card">
            <h3>نجح / Passed</h3>
            <div class="value" style="color: #27ae60;">{summary['passed']}</div>
        </div>
        <div class="summary-card">
            <h3>تحذيرات / Warnings</h3>
            <div class="value" style="color: #f39c12;">{summary['warnings']}</div>
        </div>
        <div class="summary-card">
            <h3>فشل / Failed</h3>
            <div class="value" style="color: #e74c3c;">{summary['failed']}</div>
        </div>
        <div class="summary-card">
            <h3>نسبة النجاح / Pass Rate</h3>
            <div class="value" style="color: #3498db;">{summary['pass_percentage']}%</div>
        </div>
    </div>
"""

        html_content += """
    <table>
        <thead>
            <tr>
                <th>معرّف مجموعة البيانات / Dataset ID</th>
                <th>اسم مجموعة البيانات / Dataset Name</th>
                <th>المنظمة / Organization</th>
                <th>الحالة / Status</th>
                <th>الموارد / Resources</th>
                <th>ثنائي اللغة / Bilingual</th>
            </tr>
        </thead>
        <tbody>
"""

        for result in results:
            status = result.get("overall_status", "unknown")
            status_class = f"status-{status}"
            bilingual = "نعم / Yes" if result.get("bilingual") else "لا / No"

            html_content += f"""
            <tr>
                <td>{result.get('dataset_id', 'N/A')}</td>
                <td>{result.get('dataset_name', 'N/A')}</td>
                <td>{result.get('organization', 'N/A')}</td>
                <td><span class="{status_class}">{status.upper()}</span></td>
                <td>{result.get('resource_count', 0)}</td>
                <td>{bilingual}</td>
            </tr>
"""

        html_content += """
        </tbody>
    </table>
    <div class="footer">
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    </div>
</body>
</html>
"""

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML report saved to {output_file}")
        return str(output_file)

    @staticmethod
    def save_report(
        results: List[Dict[str, Any]],
        output_dir: str = "./reports",
        formats: List[str] = None,
        include_summary: bool = True,
    ) -> Dict[str, str]:
        """
        Save report in multiple formats
        
        Args:
            results: List of quality check results
            output_dir: Directory to save reports
            formats: List of formats to save (json, csv, html)
            include_summary: Whether to include summary
            
        Returns:
            Dictionary of format -> file path
        """
        if formats is None:
            formats = ["json", "csv", "html"]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}

        for fmt in formats:
            if fmt.lower() == "json":
                path = Path(output_dir) / f"quality_check_report_{timestamp}.json"
                saved_files["json"] = ReportGenerator.save_json_report(
                    results, str(path), include_summary
                )
            elif fmt.lower() == "csv":
                path = Path(output_dir) / f"quality_check_report_{timestamp}.csv"
                saved_files["csv"] = ReportGenerator.save_csv_report(results, str(path))
            elif fmt.lower() == "html":
                path = Path(output_dir) / f"quality_check_report_{timestamp}.html"
                saved_files["html"] = ReportGenerator.save_html_report(
                    results, str(path), include_summary
                )

        return saved_files
