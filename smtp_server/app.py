"""
SMTP Server Model — Flask + Flask-SocketIO
Real-time email sending with live SMTP protocol log.
"""
import eventlet
eventlet.monkey_patch()
import os
import smtplib
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv

# Load .env from same folder as this file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ── In-memory stats ────────────────────────────────────────────────────────────
stats = {'sent': 0, 'failed': 0, 'queue': 0, 'connections': 0}
email_log = []


def log_event(tag: str, message: str, to: str = ''):
    entry = {
        'tag': tag,
        'message': message,
        'to': to,
        'time': datetime.now().strftime('%H:%M:%S'),
    }
    email_log.insert(0, entry)
    if len(email_log) > 100:
        email_log.pop()
    socketio.emit('log', entry)
    socketio.emit('stats', stats)


def send_email_task(from_addr, to_addr, subject, body):
    host     = os.getenv('SMTP_HOST', 'smtp.gmail.com').strip()
    port     = int(os.getenv('SMTP_PORT', 587))
    user     = os.getenv('SMTP_USER', '').strip()
    password = os.getenv('SMTP_PASSWORD', '').strip()

    # Debug print to terminal
    print(f"\n--- SMTP DEBUG ---")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"User: {user}")
    print(f"Password length: {len(password)} chars")
    print(f"Password preview: {password[:4]}****")
    print(f"------------------\n")

    stats['connections'] += 1
    socketio.emit('stats', stats)

    def step(delay, tag, msg, to=''):
        time.sleep(delay)
        log_event(tag, msg, to)

    try:
        step(0.0,  'info',    f'[220] {host} ESMTP ready')
        step(0.3,  'command', f'[EHLO] client hello → {host}')
        step(0.6,  'info',    '[250] Extensions: STARTTLS AUTH MIME8BIT SIZE')
        step(0.9,  'command', '[STARTTLS] Upgrading to TLS...')
        step(1.2,  'info',    '[220] TLS handshake complete')
        step(1.5,  'command', '[AUTH LOGIN] Authenticating...')

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.set_debuglevel(0)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)

            step(0.0,  'success', '[235] Authentication successful')
            step(0.3,  'command', f'[MAIL FROM] <{from_addr}>')
            step(0.5,  'info',    '[250] Sender OK')
            step(0.7,  'command', f'[RCPT TO] <{to_addr}>')
            step(0.9,  'info',    '[250] Recipient OK')
            step(1.1,  'command', '[DATA] Transmitting message body...')
            step(0.3,  'info',    f'[...] Subject: {subject}')

            msg = MIMEMultipart('alternative')
            msg['From']    = from_addr
            msg['To']      = to_addr
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(f'<p>{body}</p>', 'html'))

            server.sendmail(from_addr, to_addr, msg.as_string())

            import random, string
            msg_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            step(0.5, 'success', f'[250] Message queued as {msg_id}', to_addr)
            step(0.3, 'info',    '[QUIT] Connection closed')

        stats['sent'] += 1

    except smtplib.SMTPAuthenticationError as e:
        print(f"AUTH ERROR: {e}")
        log_event('error', f'[535] Authentication failed — {str(e)}')
        stats['failed'] += 1

    except smtplib.SMTPRecipientsRefused as e:
        print(f"RECIPIENT ERROR: {e}")
        log_event('error', f'[550] Recipient refused: {to_addr}', to_addr)
        stats['failed'] += 1
        stats['queue'] += 1

    except smtplib.SMTPException as e:
        print(f"SMTP ERROR: {e}")
        log_event('error', f'[SMTP Error] {str(e)}')
        stats['failed'] += 1

    except Exception as e:
        print(f"GENERAL ERROR: {e}")
        log_event('error', f'[Error] {str(e)}')
        stats['failed'] += 1

    finally:
        stats['connections'] = max(0, stats['connections'] - 1)
        socketio.emit('stats', stats)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/send', methods=['POST'])
def api_send():
    data = request.get_json()
    from_addr = data.get('from', '').strip()
    to_addr   = data.get('to', '').strip()
    subject   = data.get('subject', '(no subject)').strip()
    body      = data.get('body', '').strip()

    if not from_addr or not to_addr:
        return jsonify({'ok': False, 'error': 'From and To are required'}), 400

    thread = threading.Thread(
        target=send_email_task,
        args=(from_addr, to_addr, subject, body),
        daemon=True,
    )
    thread.start()

    return jsonify({'ok': True, 'message': 'SMTP session started'})


@app.route('/api/stats')
def api_stats():
    return jsonify(stats)


@app.route('/api/log')
def api_log():
    return jsonify(email_log[:50])


@app.route('/api/config')
def api_config():
    return jsonify({
        'host': os.getenv('SMTP_HOST', 'not set'),
        'port': os.getenv('SMTP_PORT', '587'),
        'user': os.getenv('SMTP_USER', 'not set'),
        'tls':  True,
    })


@socketio.on('connect')
def on_connect():
    emit('stats', stats)
    for entry in email_log[:20]:
        emit('log', entry)


if __name__ == '__main__':
    port  = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    print(f'\n  SMTP Server running at http://localhost:{port}\n')
    print(f'  Loaded config:')
    print(f'  SMTP_HOST = {os.getenv("SMTP_HOST", "NOT SET")}')
    print(f'  SMTP_USER = {os.getenv("SMTP_USER", "NOT SET")}')
    print(f'  SMTP_PASSWORD = {"SET (" + str(len(os.getenv("SMTP_PASSWORD",""))) + " chars)" if os.getenv("SMTP_PASSWORD") else "NOT SET"}')
    print()
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)