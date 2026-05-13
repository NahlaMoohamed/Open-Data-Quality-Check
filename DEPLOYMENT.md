# Deployment & Scheduling Guide

## Production Setup

### 1. Server Setup

```bash
# Create dedicated user
sudo useradd -m dataquality

# Create application directory
sudo mkdir -p /opt/open-data-quality-check
sudo chown dataquality:dataquality /opt/open-data-quality-check

# Clone repository
cd /opt/open-data-quality-check
sudo -u dataquality git clone <repo-url> .

# Setup virtual environment
sudo -u dataquality python3 -m venv venv
sudo -u dataquality venv/bin/pip install -r requirements.txt
```

### 2. Configuration

Create `/opt/open-data-quality-check/production_config.yaml`:

```yaml
api:
  base_url: "https://bayanat.ae/api/3"
  timeout: 30
  max_retries: 3

quality_checks:
  resource_validation:
    enabled: true
  language_check:
    enabled: true
  excel_validation:
    enabled: true
  metadata:
    enabled: true
  arabic_encoding:
    enabled: true
  time_period:
    enabled: true

reporting:
  output_formats: ["json", "csv", "html"]
  save_dir: "/var/reports/open-data-quality"
  include_summary: true

logging:
  level: "INFO"
  file: "/var/log/open-data-quality/quality_check.log"
```

### 3. Directory Permissions

```bash
# Create log directory
sudo mkdir -p /var/log/open-data-quality
sudo chown dataquality:dataquality /var/log/open-data-quality

# Create reports directory
sudo mkdir -p /var/reports/open-data-quality
sudo chown dataquality:dataquality /var/reports/open-data-quality

# Create data directory
sudo mkdir -p /var/data/open-data-quality
sudo chown dataquality:dataquality /var/data/open-data-quality
```

---

## Automated Scheduling

### Option 1: Linux Cron Jobs

Edit crontab:
```bash
sudo -u dataquality crontab -e
```

Add schedules:

```cron
# Daily check at 2 AM UTC
0 2 * * * cd /opt/open-data-quality-check && venv/bin/python quality_check.py --config production_config.yaml --all-orgs --limit 100 >> /var/log/open-data-quality/cron.log 2>&1

# Weekly full audit every Sunday at 3 AM
0 3 * * 0 cd /opt/open-data-quality-check && venv/bin/python quality_check.py --config production_config.yaml --all-orgs --limit 500 >> /var/log/open-data-quality/cron.log 2>&1

# Hourly quick check during business hours
0 9-17 * * 1-5 cd /opt/open-data-quality-check && venv/bin/python quality_check.py --config production_config.yaml --limit 50 >> /var/log/open-data-quality/cron.log 2>&1
```

### Option 2: Windows Task Scheduler

Create batch file `check_quality.bat`:
```batch
@echo off
cd C:\Open-Data-Quality-Check
C:\Open-Data-Quality-Check\venv\Scripts\python.exe quality_check.py ^
  --config production_config.yaml ^
  --all-orgs ^
  --output-dir C:\Reports\open-data-quality ^
  >> C:\Logs\quality_check.log 2>&1
```

Schedule in Task Scheduler:
- **Trigger:** Daily at 2:00 AM
- **Action:** Run `check_quality.bat`
- **User:** Service account with read permissions

### Option 3: Kubernetes Cronjob

Create `cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: bayanat-quality-check
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: quality-checker
            image: open-data-quality-check:latest
            args:
            - python
            - quality_check.py
            - --config
            - /etc/config/production_config.yaml
            - --all-orgs
            volumeMounts:
            - name: config
              mountPath: /etc/config
            - name: reports
              mountPath: /var/reports
          volumes:
          - name: config
            configMap:
              name: quality-check-config
          - name: reports
            persistentVolumeClaim:
              claimName: quality-check-reports
          restartPolicy: OnFailure
```

Deploy:
```bash
kubectl apply -f cronjob.yaml
```

---

## Monitoring & Alerting

### 1. Log Monitoring

Monitor key log events:

```bash
# Watch for failures
tail -f /var/log/open-data-quality/quality_check.log | grep -i "error\|fail"

# Check latest run
tail -20 /var/log/open-data-quality/quality_check.log
```

### 2. Report Monitoring

Script to track quality trends:

```python
# monitor_trends.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

reports_dir = Path("/var/reports/open-data-quality")

# Find latest reports
reports = sorted(reports_dir.glob("quality_check_report_*.json"), 
                key=os.path.getmtime, reverse=True)

if len(reports) >= 2:
    latest = json.load(open(reports[0]))
    previous = json.load(open(reports[1]))
    
    latest_pass = latest['summary']['pass_percentage']
    prev_pass = previous['summary']['pass_percentage']
    
    change = latest_pass - prev_pass
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    
    print(f"Pass Rate: {latest_pass}% {arrow} ({change:+.1f}%)")
    
    if change < -5:
        print("⚠️ WARNING: Quality decreased by more than 5%")
```

### 3. Email Alerts

Script `send_alerts.py`:

```python
import json
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

def send_alert(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'dataquality@bayanat.ae'
    msg['To'] = 'admin@bayanat.ae'
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)

# Check latest report
latest_report = sorted(
    Path("/var/reports/open-data-quality").glob("*.json"),
    reverse=True
)[0]

with open(latest_report) as f:
    data = json.load(f)

if data['summary']['failed'] > 10:
    send_alert(
        "⚠️ Quality Check Alert",
        f"Failed datasets: {data['summary']['failed']}\n"
        f"Pass rate: {data['summary']['pass_percentage']}%"
    )
```

Add to cron:
```cron
0 3 * * * cd /opt/open-data-quality-check && venv/bin/python send_alerts.py
```

---

## Backup Strategy

### 1. Backup Reports

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/var/backups/quality-reports"
REPORTS_DIR="/var/reports/open-data-quality"

mkdir -p "$BACKUP_DIR/$(date +%Y-%m-%d)"
cp -r "$REPORTS_DIR"/* "$BACKUP_DIR/$(date +%Y-%m-%d)/"

# Keep only last 30 days
find "$BACKUP_DIR" -mtime +30 -delete
```

### 2. Archive Old Reports

```bash
# Monthly archive
#!/bin/bash
ARCHIVE_DIR="/var/archive/quality-reports"
REPORTS_DIR="/var/reports/open-data-quality"

# Archive reports older than 90 days
find "$REPORTS_DIR" -mtime +90 -exec tar -czf "$ARCHIVE_DIR/reports_$(date +%Y%m%d).tar.gz" {} \;
```

---

## Performance Optimization

### 1. Parallel Processing

For large organizations, modify `quality_check.py`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_datasets_parallel(datasets, max_workers=4):
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_dataset, dataset): dataset 
            for dataset in datasets
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error: {e}")
    
    return results
```

### 2. Incremental Checks

```bash
# Check only datasets modified in last 24 hours
python quality_check.py --since 2024-05-12
```

Requires modification to Bayanat API integration.

### 3. Resource Limits

Docker compose file `docker-compose.yml`:

```yaml
version: '3'
services:
  quality-checker:
    image: open-data-quality-check:latest
    environment:
      PYTHONUNBUFFERED: 1
    volumes:
      - /var/reports:/var/reports
      - /var/logs:/var/logs
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 512M
```

---

## Disaster Recovery

### 1. Failure Recovery

```bash
# Retry failed dataset checks
python quality_check.py --retry-failed --config production_config.yaml

# Check specific dataset by ID
python quality_check.py --dataset-id <dataset-id>
```

### 2. Data Recovery

```bash
# Restore from backup
cp /var/backups/quality-reports/2024-05-10/* /var/reports/open-data-quality/

# Verify integrity
python -m json.tool /var/reports/open-data-quality/*.json > /dev/null
```

---

## Health Checks

Monitoring endpoint `health_check.py`:

```python
from flask import Flask, jsonify
import json
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)

@app.route('/health')
def health():
    reports_dir = Path("/var/reports/open-data-quality")
    
    # Check if recent report exists
    recent = sorted(
        reports_dir.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not recent:
        return jsonify({"status": "unhealthy", "reason": "No reports"}), 503
    
    age_hours = (datetime.now() - datetime.fromtimestamp(
        recent[0].stat().st_mtime
    )).total_seconds() / 3600
    
    if age_hours > 25:
        return jsonify({"status": "unhealthy", "reason": "Report too old"}), 503
    
    # Load report
    with open(recent[0]) as f:
        report = json.load(f)
    
    status = "healthy" if report['summary']['pass_percentage'] > 50 else "degraded"
    
    return jsonify({
        "status": status,
        "pass_rate": report['summary']['pass_percentage'],
        "last_check": recent[0].stat().st_mtime,
        "datasets_checked": report['summary']['total_datasets']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Deploy and monitor:
```bash
curl http://localhost:5000/health
```

---

## Troubleshooting Production Issues

### Issue: Out of Memory
**Solution:**
- Process organizations separately
- Reduce `--limit` parameter
- Increase server RAM

### Issue: API Rate Limiting
**Solution:**
- Add delay between requests: `--delay 1` (second)
- Use smaller batch sizes
- Contact Bayanat API team for higher limits

### Issue: Disk Space Full
**Solution:**
```bash
# Check disk usage
du -sh /var/reports/
du -sh /var/log/

# Archive old reports
tar -czf /archive/reports_2024_q1.tar.gz /var/reports/2024-01*
rm -rf /var/reports/2024-01*
```

### Issue: Network Timeout
**Solution:**
- Increase timeout in config
- Use retry logic
- Check network connectivity: `ping bayanat.ae`

---

## Capacity Planning

Estimate resources needed:

```
Datasets to check: 1000
Average check time: 5 seconds
Total time: 5000 seconds = 1.4 hours

Memory usage:
- Per dataset: ~500 KB
- Total: 500 MB

Storage:
- JSON report: ~1 MB per 10 datasets
- HTML report: ~2 MB per 10 datasets
- Total for 1000: ~300 MB per run
- 30-day retention: ~9 GB
```

---

## Support & Maintenance

### Update Schedule
- Monthly: Update dependencies
- Quarterly: Feature updates
- As needed: Security patches

### Maintenance Windows
- Preferred: 2 AM - 6 AM UTC
- Duration: 30 minutes
- Impact: Quality checks will be interrupted

### Version Control
```bash
# Tag releases
git tag -a v1.1.0 -m "Production release"
git push origin v1.1.0

# Rollback if needed
git checkout v1.0.0
```
