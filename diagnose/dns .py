"""
DNS & CNAME Checker
Checks DNS records, CNAME, A records, MX, TXT, NS for any domain.
Run: python dns_check.py
"""

import socket
import subprocess
import sys
import urllib.request
import json
from datetime import datetime

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN  = '\033[92m'
RED    = '\033[91m'
YELLOW = '\033[93m'
BLUE   = '\033[94m'
BOLD   = '\033[1m'
RESET  = '\033[0m'

def ok(msg):     print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):   print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):   print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):   print(f"  {BLUE}ℹ️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{BLUE}{'─'*60}{RESET}\n{BOLD}  {msg}{RESET}\n{'─'*60}")
def row(k, v):   print(f"  {BOLD}{k:<20}{RESET} {GREEN}{v}{RESET}")


# ── DNS Lookup using Google DNS API ────────────────────────────────────────────
def dns_lookup(domain, record_type):
    """Query Google Public DNS API for any record type."""
    try:
        url = f"https://dns.google/resolve?name={domain}&type={record_type}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            answers = data.get('Answer', [])
            return answers, data.get('Status', -1)
    except Exception as e:
        return [], -1


# ── nslookup via system ────────────────────────────────────────────────────────
def run_nslookup(domain):
    try:
        result = subprocess.run(
            ['nslookup', domain],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except:
        return None


# ── Check if domain resolves ───────────────────────────────────────────────────
def check_domain_resolves(domain):
    try:
        ip = socket.gethostbyname(domain)
        return ip
    except:
        return None


# ── Check HTTP/HTTPS reachable ─────────────────────────────────────────────────
def check_website(domain):
    results = {}
    for scheme in ['http', 'https']:
        try:
            url = f"{scheme}://{domain}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as r:
                results[scheme] = {'status': r.status, 'ok': True}
        except urllib.error.HTTPError as e:
            results[scheme] = {'status': e.code, 'ok': True}
        except Exception as e:
            results[scheme] = {'status': None, 'ok': False, 'error': str(e)}
    return results


# ── Main ────────────────────────────────────────────────────────────────────────
print(f"\n{BOLD}{'='*60}{RESET}")
print(f"{BOLD}   DNS & CNAME CHECKER{RESET}")
print(f"{BOLD}{'='*60}{RESET}")
print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Get domain from user
domain = input(f"  {BOLD}Enter domain to check (e.g. google.com): {RESET}").strip()
if not domain:
    print(f"  {RED}No domain entered. Exiting.{RESET}")
    exit()

# Remove http/https if user typed it
domain = domain.replace('https://', '').replace('http://', '').strip('/')
print()

# ── 1. Basic Resolution ────────────────────────────────────────────────────────
header(f"1. BASIC DNS RESOLUTION — {domain}")

ip = check_domain_resolves(domain)
if ip:
    ok(f"Domain resolves to IP: {ip}")
else:
    fail(f"Domain does NOT resolve — DNS not configured or domain doesn't exist")

# www version
www_domain = f"www.{domain}" if not domain.startswith('www.') else domain
www_ip = check_domain_resolves(www_domain)
if www_ip:
    ok(f"www.{domain} resolves to: {www_ip}")
else:
    warn(f"www.{domain} does NOT resolve")


# ── 2. A Records ──────────────────────────────────────────────────────────────
header(f"2. A RECORDS (IPv4 Address)")
info("A record maps domain → IP address")

answers, status = dns_lookup(domain, 'A')
if answers:
    for a in answers:
        row("Domain:", domain)
        row("Points to IP:", a['data'])
        row("TTL:", f"{a['TTL']} seconds")
        print()
    ok(f"Found {len(answers)} A record(s)")
else:
    fail(f"No A records found for {domain}")

# www A records
answers_www, _ = dns_lookup(f"www.{domain}", 'A')
if answers_www:
    print()
    info(f"www.{domain} A records:")
    for a in answers_www:
        row("  Points to IP:", a['data'])


# ── 3. CNAME Records ──────────────────────────────────────────────────────────
header(f"3. CNAME RECORDS (Alias)")
info("CNAME maps one domain name → another domain name")
info("Example: www.mysite.com → mysite.github.io")
print()

# Check www CNAME
cname_checks = [
    f"www.{domain}",
    domain,
    f"mail.{domain}",
    f"blog.{domain}",
    f"app.{domain}",
    f"api.{domain}",
]

found_any_cname = False
for subdomain in cname_checks:
    answers, status = dns_lookup(subdomain, 'CNAME')
    if answers:
        found_any_cname = True
        for a in answers:
            ok(f"CNAME found!")
            row("  Subdomain:", subdomain)
            row("  Points to:", a['data'])
            row("  TTL:", f"{a['TTL']} seconds")
            print()

if not found_any_cname:
    warn(f"No CNAME records found for common subdomains")
    info("This is normal if using A records directly instead of CNAME")


# ── 4. MX Records (Email) ─────────────────────────────────────────────────────
header(f"4. MX RECORDS (Email Server)")
info("MX records tell where to deliver emails for your domain")
print()

answers, status = dns_lookup(domain, 'MX')
if answers:
    ok(f"Found {len(answers)} MX record(s) — email is configured!")
    for a in answers:
        parts = a['data'].split(' ')
        priority = parts[0] if len(parts) > 1 else '?'
        mail_server = parts[1] if len(parts) > 1 else a['data']
        row("  Mail server:", mail_server)
        row("  Priority:", priority)
        print()
else:
    warn(f"No MX records — email not configured for {domain}")


# ── 5. NS Records (Nameservers) ───────────────────────────────────────────────
header(f"5. NS RECORDS (Nameservers)")
info("NS records show which DNS provider manages your domain")
print()

answers, status = dns_lookup(domain, 'NS')
if answers:
    ok(f"Found {len(answers)} nameserver(s):")
    for a in answers:
        ns = a['data']
        row("  Nameserver:", ns)
        # Identify DNS provider
        if 'cloudflare' in ns.lower():
            info("  → Using Cloudflare DNS ⚡")
        elif 'awsdns' in ns.lower():
            info("  → Using Amazon Route53 DNS")
        elif 'googledomains' in ns.lower() or 'google' in ns.lower():
            info("  → Using Google DNS")
        elif 'godaddy' in ns.lower():
            info("  → Using GoDaddy DNS")
        elif 'namecheap' in ns.lower():
            info("  → Using Namecheap DNS")
        elif 'bigrock' in ns.lower():
            info("  → Using BigRock DNS")
        elif 'hostinger' in ns.lower():
            info("  → Using Hostinger DNS")
    print()
else:
    fail(f"No NS records found")


# ── 6. TXT Records ────────────────────────────────────────────────────────────
header(f"6. TXT RECORDS (Verification & SPF)")
info("TXT records used for domain verification, SPF, DKIM")
print()

answers, status = dns_lookup(domain, 'TXT')
if answers:
    ok(f"Found {len(answers)} TXT record(s):")
    for a in answers:
        txt = a['data']
        row("  Record:", txt[:60] + ('...' if len(txt) > 60 else ''))
        if 'v=spf1' in txt:
            info("  → SPF record — email spam protection configured")
        if 'google-site-verification' in txt:
            info("  → Google Search Console verified")
        if 'v=DKIM1' in txt:
            info("  → DKIM email signing configured")
        if 'MS=' in txt:
            info("  → Microsoft/Office365 verified")
        print()
else:
    warn(f"No TXT records found")


# ── 7. Website Reachability ───────────────────────────────────────────────────
header(f"7. WEBSITE REACHABILITY")
info("Checking if website actually loads...")
print()

web = check_website(domain)
for scheme, result in web.items():
    if result['ok']:
        ok(f"{scheme.upper()} — reachable (status {result['status']})")
    else:
        fail(f"{scheme.upper()} — not reachable ({result.get('error', 'unknown')})")


# ── 8. Common Subdomains ──────────────────────────────────────────────────────
header(f"8. COMMON SUBDOMAINS CHECK")
info("Checking which subdomains exist...")
print()

subdomains = ['www', 'mail', 'smtp', 'pop', 'imap', 'ftp',
              'blog', 'api', 'app', 'dev', 'staging', 'cdn']

found_subs = []
for sub in subdomains:
    full = f"{sub}.{domain}"
    ip = check_domain_resolves(full)
    if ip:
        ok(f"{full:<35} → {ip}")
        found_subs.append(full)

if not found_subs:
    warn("No common subdomains found")


# ── 9. NSLOOKUP Output ────────────────────────────────────────────────────────
header(f"9. NSLOOKUP OUTPUT")
ns_out = run_nslookup(domain)
if ns_out:
    for line in ns_out.strip().split('\n'):
        if line.strip():
            info(line.strip())
else:
    warn("nslookup not available")


# ── Final Summary ─────────────────────────────────────────────────────────────
header("FINAL SUMMARY & RECOMMENDATIONS")

print(f"  Domain checked : {BOLD}{domain}{RESET}")
print(f"  Checked at     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

checks = {
    'A Record (domain → IP)':     ip is not None,
    'www resolves':                www_ip is not None,
    'CNAME configured':            found_any_cname,
    'Email (MX) configured':       len(dns_lookup(domain, 'MX')[0]) > 0,
    'Nameservers found':           len(dns_lookup(domain, 'NS')[0]) > 0,
    'Website reachable (HTTP)':    web.get('http', {}).get('ok', False),
    'Website reachable (HTTPS)':   web.get('https', {}).get('ok', False),
}

for check, passed in checks.items():
    if passed:
        ok(check)
    else:
        fail(check)

print(f"\n  {BLUE}{'─'*50}{RESET}")
print(f"\n  {BOLD}HOW TO SET UP DNS FOR YOUR OWN WEBSITE:{RESET}\n")
print(f"  {BLUE}Step 1{RESET} — Buy domain from GoDaddy/Namecheap/Hostinger")
print(f"  {BLUE}Step 2{RESET} — Go to DNS settings in your registrar")
print(f"  {BLUE}Step 3{RESET} — Add A record:")
print(f"           Type: A")
print(f"           Name: @")
print(f"           Value: YOUR_SERVER_IP")
print(f"  {BLUE}Step 4{RESET} — Add CNAME for www:")
print(f"           Type: CNAME")
print(f"           Name: www")
print(f"           Value: yourdomain.com")
print(f"  {BLUE}Step 5{RESET} — Wait 5-48 hours for DNS propagation")
print(f"\n  {GREEN}{BOLD}DNS Check Complete!{RESET}\n")