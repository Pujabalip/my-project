"""
Daily Data Analysis Reporter
Reads CSV/Excel file, analyzes it, sends a beautiful HTML email report automatically.
"""
import gevent.monkey
gevent.monkey.patch_all()

import os
import smtplib
import schedule
import time
import threading
import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# ── State ──────────────────────────────────────────────────────────────────────
report_log = []
stats = {'sent': 0, 'failed': 0, 'next_run': 'Not scheduled', 'last_run': 'Never'}


def log(tag, message):
    entry = {'tag': tag, 'message': message, 'time': datetime.now().strftime('%H:%M:%S')}
    report_log.insert(0, entry)
    if len(report_log) > 100:
        report_log.pop()
    socketio.emit('log', entry)
    socketio.emit('stats', stats)
    print(f"[{tag.upper()}] {message}")


# ── Data Analysis ──────────────────────────────────────────────────────────────

def analyze_file(filepath):
    """Read CSV or Excel and return summary stats + HTML table."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(filepath)
    elif ext in ['.xlsx', '.xls']:
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    rows, cols = df.shape
    numeric_cols = df.select_dtypes(include='number').columns.tolist()

    summary = {}
    for col in numeric_cols:
        summary[col] = {
            'total':   round(df[col].sum(), 2),
            'average': round(df[col].mean(), 2),
            'max':     round(df[col].max(), 2),
            'min':     round(df[col].min(), 2),
        }

    preview_html = df.head(10).to_html(
        index=False, border=0,
        classes='data-table',
        na_rep='-'
    )

    return {
        'rows': rows,
        'cols': cols,
        'columns': list(df.columns),
        'numeric_cols': numeric_cols,
        'summary': summary,
        'preview_html': preview_html,
        'filename': os.path.basename(filepath),
    }


def build_html_report(data):
    """Build a beautiful HTML email report."""
    date_str = datetime.now().strftime('%B %d, %Y')
    time_str = datetime.now().strftime('%H:%M')

    cards_html = ''
    for col, s in data['summary'].items():
        cards_html += f"""
        <div class="card">
            <div class="card-title">{col}</div>
            <div class="card-row"><span>Total</span><strong>{s['total']:,}</strong></div>
            <div class="card-row"><span>Average</span><strong>{s['average']:,}</strong></div>
            <div class="card-row"><span>Max</span><strong>{s['max']:,}</strong></div>
            <div class="card-row"><span>Min</span><strong>{s['min']:,}</strong></div>
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"/>
<style>
  body {{ font-family: Arial, sans-serif; background: #f5f5f3; margin: 0; padding: 20px; color: #1a1a18; }}
  .wrapper {{ max-width: 700px; margin: 0 auto; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ background: #1a1a18; padding: 28px 32px; }}
  .header h1 {{ color: #fff; margin: 0; font-size: 22px; }}
  .header p {{ color: #999; margin: 6px 0 0; font-size: 13px; }}
  .body {{ padding: 28px 32px; }}
  .meta {{ background: #f9f9f8; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px; color: #5a5a56; display: flex; gap: 24px; }}
  .meta span {{ font-weight: 600; color: #1a1a18; }}
  .section-title {{ font-size: 14px; font-weight: 700; color: #1a1a18; margin: 24px 0 12px; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 2px solid #f0f0ee; padding-bottom: 6px; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #f9f9f8; border-radius: 8px; padding: 14px 16px; border: 1px solid #e3e2de; }}
  .card-title {{ font-size: 12px; font-weight: 700; color: #1a6ef5; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px; }}
  .card-row {{ display: flex; justify-content: space-between; font-size: 13px; padding: 3px 0; color: #5a5a56; border-bottom: 1px solid #f0f0ee; }}
  .card-row:last-child {{ border-bottom: none; }}
  .card-row strong {{ color: #1a1a18; }}
  .data-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .data-table th {{ background: #1a1a18; color: #fff; padding: 8px 12px; text-align: left; font-weight: 600; }}
  .data-table td {{ padding: 7px 12px; border-bottom: 1px solid #f0f0ee; color: #3a3a38; }}
  .data-table tr:nth-child(even) td {{ background: #f9f9f8; }}
  .footer {{ background: #f9f9f8; padding: 16px 32px; font-size: 12px; color: #9a9a94; border-top: 1px solid #e3e2de; }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <h1>Daily Data Report</h1>
    <p>Automated analysis for {date_str} at {time_str}</p>
  </div>
  <div class="body">
    <div class="meta">
      File: <span>{data['filename']}</span>
      &nbsp;|&nbsp; Rows: <span>{data['rows']:,}</span>
      &nbsp;|&nbsp; Columns: <span>{data['cols']}</span>
      &nbsp;|&nbsp; Generated: <span>{time_str}</span>
    </div>

    <div class="section-title">Column Summary</div>
    <div class="cards">{cards_html}</div>

    <div class="section-title">Data Preview (first 10 rows)</div>
    {data['preview_html']}
  </div>
  <div class="footer">
    This report was automatically generated and sent by your SMTP Server.
    Do not reply to this email.
  </div>
</div>
</body>
</html>
"""
    return html


# ── Email Sending ──────────────────────────────────────────────────────────────

def send_report():
    """Main function — analyze file and send report email."""
    host      = os.getenv('SMTP_HOST', '').strip()
    port      = int(os.getenv('SMTP_PORT', 587))
    user      = os.getenv('SMTP_USER', '').strip()
    password  = os.getenv('SMTP_PASSWORD', '').strip()
    to_emails = os.getenv('REPORT_TO', '').strip()
    filepath  = os.getenv('DATA_FILE', '').strip()

    stats['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    if not filepath:
        log('error', 'DATA_FILE not set in .env — set the path to your CSV/Excel file')
        return
    if not os.path.exists(filepath):
        log('error', f'File not found: {filepath}')
        return
    if not to_emails:
        log('error', 'REPORT_TO not set in .env — add recipient emails')
        return

    try:
        log('info', f'Reading file: {os.path.basename(filepath)}')
        data = analyze_file(filepath)
        log('info', f'Analyzed {data["rows"]} rows x {data["cols"]} columns')

        log('info', 'Building HTML report...')
        html_content = build_html_report(data)

        log('info', f'Connecting to {host}:{port}...')

        recipients = [e.strip() for e in to_emails.split(',')]

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            log('success', '[235] Authentication successful')

            for recipient in recipients:
                msg = MIMEMultipart('alternative')
                msg['From']    = user
                msg['To']      = recipient
                msg['Subject'] = f'Daily Data Report — {datetime.now().strftime("%B %d, %Y")}'
                msg.attach(MIMEText('Your email client does not support HTML.', 'plain'))
                msg.attach(MIMEText(html_content, 'html'))
                server.sendmail(user, recipient, msg.as_string())
                log('success', f'Report sent to {recipient}')

        stats['sent'] += 1
        socketio.emit('stats', stats)

    except smtplib.SMTPAuthenticationError:
        log('error', '[535] Authentication failed — check SMTP credentials in .env')
        stats['failed'] += 1

    except Exception as e:
        log('error', f'Error: {str(e)}')
        stats['failed'] += 1


# ── Scheduler ──────────────────────────────────────────────────────────────────

def run_scheduler():
    schedule_time = os.getenv('SEND_TIME', '08:00')
    schedule.every().day.at(schedule_time).do(send_report)
    stats['next_run'] = f'Daily at {schedule_time}'
    log('info', f'Scheduler started — report will send daily at {schedule_time}')
    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/send-now', methods=['POST'])
def send_now():
    thread = threading.Thread(target=send_report, daemon=True)
    thread.start()
    return jsonify({'ok': True, 'message': 'Report sending started'})


@app.route('/api/stats')
def api_stats():
    return jsonify(stats)


@app.route('/api/log')
def api_log():
    return jsonify(report_log[:50])


@app.route('/api/config')
def api_config():
    return jsonify({
        'smtp_host':  os.getenv('SMTP_HOST', 'not set'),
        'smtp_user':  os.getenv('SMTP_USER', 'not set'),
        'send_time':  os.getenv('SEND_TIME', '08:00'),
        'report_to':  os.getenv('REPORT_TO', 'not set'),
        'data_file':  os.getenv('DATA_FILE', 'not set'),
    })


@socketio.on('connect')
def on_connect():
    emit('stats', stats)
    for entry in report_log[:20]:
        emit('log', entry)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    flask_port = int(os.getenv('FLASK_PORT', 5001))

    print(f'\n  Daily Report Server at http://localhost:{flask_port}')
    print(f'  SMTP Host  : {os.getenv("SMTP_HOST", "NOT SET")}')
    print(f'  SMTP User  : {os.getenv("SMTP_USER", "NOT SET")}')
    print(f'  Data File  : {os.getenv("DATA_FILE", "NOT SET")}')
    print(f'  Report To  : {os.getenv("REPORT_TO", "NOT SET")}')
    print(f'  Send Time  : {os.getenv("SEND_TIME", "08:00")}\n')

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    socketio.run(app, host='0.0.0.0', port=flask_port, debug=False)