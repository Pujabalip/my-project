"""
Public IP Port Checker
Checks if your public IP has any open inbound ports.
Run: python check_ports.py
"""

import socket
import urllib.request
import threading
from datetime import datetime

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
BLUE   = '\033[94m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

def ok(msg):   print(f"  {GREEN}✅ OPEN    {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ BLOCKED {msg}{RESET}")
def info(msg): print(f"  {BLUE}ℹ️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{BLUE}{'─'*60}{RESET}\n{BOLD}  {msg}{RESET}\n{'─'*60}")

# ── Get Public IP ───────────────────────────────────────────────────────────────
def get_public_ip():
    try:
        req = urllib.request.Request(
            'https://api.ipify.org',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.read().decode().strip()
    except:
        return None

# ── Check Single Port ───────────────────────────────────────────────────────────
def check_port(ip, port, results, label=''):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, port))
        sock.close()
        if result == 0:
            results[port] = 'open'
        else:
            results[port] = 'closed'
    except:
        results[port] = 'closed'

# ── All ports to check ──────────────────────────────────────────────────────────
ALL_PORTS = {
    # Web
    80:    'HTTP',
    443:   'HTTPS',
    8080:  'HTTP Alt',
    8443:  'HTTPS Alt',
    3000:  'Node.js / React',
    5000:  'Flask App',
    5001:  'Flask App 2',
    5002:  'Flask App 3',
    8000:  'Django / Python',
    # Email
    25:    'SMTP (email receive)',
    465:   'SMTP SSL',
    587:   'SMTP TLS',
    110:   'POP3',
    143:   'IMAP',
    993:   'IMAP SSL',
    995:   'POP3 SSL',
    # Remote Access
    22:    'SSH',
    23:    'Telnet',
    3389:  'RDP (Remote Desktop)',
    5900:  'VNC',
    # Database
    3306:  'MySQL',
    5432:  'PostgreSQL',
    27017: 'MongoDB',
    6379:  'Redis',
    # Other
    21:    'FTP',
    53:    'DNS',
    1433:  'SQL Server',
    8888:  'Jupyter Notebook',
}


# ── Main ────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*60}{RESET}")
print(f"{BOLD}   PUBLIC IP PORT CHECKER{RESET}")
print(f"{BOLD}{'='*60}{RESET}")
print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Get public IP
header("GETTING YOUR PUBLIC IP")
public_ip = get_public_ip()
if not public_ip:
    print(f"  {RED}Could not get public IP — check internet connection{RESET}")
    exit()

print(f"  {GREEN}Public IP: {BOLD}{public_ip}{RESET}")
info(f"Scanning {len(ALL_PORTS)} ports on {public_ip}...")
info("This may take 30-60 seconds...")

# Scan all ports using threads
header(f"SCANNING ALL PORTS ON {public_ip}")
results = {}
threads = []

for port in ALL_PORTS:
    t = threading.Thread(
        target=check_port,
        args=(public_ip, port, results),
        daemon=True
    )
    threads.append(t)
    t.start()

# Wait for all threads
for t in threads:
    t.join(timeout=5)

# ── Results by category ─────────────────────────────────────────────────────────
categories = {
    'Web Ports': [80, 443, 8080, 8443, 3000, 5000, 5001, 5002, 8000],
    'Email Ports': [25, 465, 587, 110, 143, 993, 995],
    'Remote Access': [22, 23, 3389, 5900],
    'Database Ports': [3306, 5432, 27017, 6379],
    'Other Ports': [21, 53, 1433, 8888],
}

open_ports = []

for category, ports in categories.items():
    header(f"{category.upper()}")
    for port in ports:
        label = ALL_PORTS.get(port, '')
        status = results.get(port, 'closed')
        msg = f"Port {port:<6} {label}"
        if status == 'open':
            ok(msg)
            open_ports.append((port, label))
        else:
            fail(msg)

# ── Final Summary ───────────────────────────────────────────────────────────────
header("FINAL SUMMARY")

print(f"  Public IP scanned : {BOLD}{public_ip}{RESET}")
print(f"  Total ports checked: {len(ALL_PORTS)}")
print(f"  Open ports found  : {len(open_ports)}")
print()

if open_ports:
    print(f"  {GREEN}{BOLD}OPEN PORTS:{RESET}")
    for port, label in open_ports:
        print(f"  {GREEN}  → Port {port} ({label}) is OPEN on internet{RESET}")
    print()
    print(f"  {YELLOW}⚠️  Your ISP allows some inbound ports!{RESET}")
    print(f"  {BLUE}You can host your app on these open ports.{RESET}")
else:
    print(f"  {RED}{BOLD}NO OPEN PORTS FOUND{RESET}")
    print()
    print(f"  {YELLOW}Your ISP blocks ALL inbound traffic.{RESET}")
    print(f"  {YELLOW}This is normal for home/office internet plans.{RESET}")
    print()
    print(f"  {BLUE}To share your app on internet, use:{RESET}")
    print(f"  {BLUE}  Option 1 → Ngrok  : pip install pyngrok && ngrok http 5002{RESET}")
    print(f"  {BLUE}  Option 2 → Railway: https://railway.app (free cloud){RESET}")
    print(f"  {BLUE}  Option 3 → Router : Port forwarding on http://192.168.1.1{RESET}")

print(f"\n  {'─'*50}")
print(f"  {GREEN}{BOLD}Scan complete!{RESET}\n")