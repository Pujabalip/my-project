# SMTP Server Model

A real-time SMTP email server built with Flask + Flask-SocketIO.
Shows the live SMTP protocol handshake as emails are sent.

---

## Features

- Send real emails via any SMTP provider (Gmail, Outlook, SendGrid, Mailgun)
- Live protocol log — watch every SMTP command in real time (220, EHLO, AUTH, MAIL FROM, RCPT TO, DATA, 250, QUIT)
- Real-time metrics (sent, failed, queue, active connections)
- WebSocket-powered dashboard (no page refresh needed)
- TLS/STARTTLS support

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your SMTP provider

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your SMTP settings.

**Gmail setup** (recommended):
1. Go to https://myaccount.google.com/security
2. Enable 2-Factor Authentication
3. Search "App passwords" → create one for "Mail"
4. Use that 16-character app password (not your real password)

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
```

### 3. Run the server

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## Project structure

```
smtp_server/
├── app.py              # Flask application + SMTP logic
├── requirements.txt    # Python dependencies
├── .env.example        # Config template (copy to .env)
├── README.md
└── templates/
    └── index.html      # Web UI (real-time dashboard)
```

---

## API endpoints

| Method | Path         | Description                   |
|--------|--------------|-------------------------------|
| GET    | /            | Web dashboard                 |
| POST   | /api/send    | Send email (JSON body)        |
| GET    | /api/stats   | Server statistics             |
| GET    | /api/log     | Last 50 log entries           |
| GET    | /api/config  | Server config (no passwords)  |

### POST /api/send — example

```bash
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "from": "you@gmail.com",
    "to": "friend@example.com",
    "subject": "Hello",
    "body": "This is a test email."
  }'
```

---

## Supported SMTP providers

| Provider   | Host                    | Port |
|------------|-------------------------|------|
| Gmail      | smtp.gmail.com          | 587  |
| Outlook    | smtp.office365.com      | 587  |
| SendGrid   | smtp.sendgrid.net       | 587  |
| Mailgun    | smtp.mailgun.org        | 587  |
| Yahoo      | smtp.mail.yahoo.com     | 587  |

---

## Requirements

- Python 3.8+
- pip
