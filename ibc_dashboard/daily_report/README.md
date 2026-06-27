# Daily Data Report Scheduler

Automatically analyzes your CSV/Excel file and emails a beautiful HTML report every day.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```bash
copy .env.example .env
```

Edit `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

REPORT_TO=recipient@gmail.com
DATA_FILE=C:\Users\puja\Documents\your_data.csv
SEND_TIME=08:00
```

### 3. Run
```bash
python reporter.py
```

Open: **http://localhost:5001**

---

## Supported file types
- `.csv` — comma separated
- `.xlsx` — Excel 2007+
- `.xls`  — Excel 97-2003

## Multiple recipients
```env
REPORT_TO=boss@company.com,manager@company.com,team@company.com
```

## Send time examples
```env
SEND_TIME=08:00   # 8:00 AM
SEND_TIME=13:30   # 1:30 PM
SEND_TIME=18:00   # 6:00 PM
```

## Test instantly
Click **"Send Report Now"** on the dashboard to send immediately without waiting.
