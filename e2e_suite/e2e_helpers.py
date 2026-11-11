"""Shared E2E helpers: session-based client that mimics a real browser."""
import json, re, time, requests

import os
BASE = os.environ.get("CC_BASE", "http://127.0.0.1:8010")
SERVER_LOG = os.environ.get("CC_SERVER_LOG", "/tmp/ccserver.log")


class E2E:
    def __init__(self):
        self.s = requests.Session()
        self.csrf = None

    def _refresh_csrf(self, path="/auth/login/"):
        r = self.s.get(BASE + path, allow_redirects=True)
        self.csrf = self.s.cookies.get("csrftoken")
        return r

    def get(self, path, **kw):
        kw.setdefault("allow_redirects", True)
        r = self.s.get(BASE + path, **kw)
        self.csrf = self.s.cookies.get("csrftoken") or self.csrf
        return r

    def post_form(self, path, data, csrf_required=True, follow=True):
        for attempt in range(2):
            if csrf_required:
                if attempt == 0 and not self.csrf:
                    self._refresh_csrf(path)
                elif attempt == 1:
                    self._refresh_csrf(path)  # token may have rotated (login)
                data = dict(data)
                data["csrfmiddlewaretoken"] = self.csrf
            r = self.s.post(BASE + path, data=data, allow_redirects=follow)
            if r.status_code != 403:
                return r
        return r

    def post_json(self, path, payload, csrf_required=True):
        for attempt in range(2):
            if csrf_required:
                if attempt == 0 and not self.csrf:
                    self._refresh_csrf(path)
                elif attempt == 1:
                    self._refresh_csrf(path)
                headers = {"X-CSRFToken": self.csrf, "Content-Type": "application/json"}
            else:
                headers = {"Content-Type": "application/json"}
            r = self.s.post(BASE + path, data=json.dumps(payload), headers=headers)
            if r.status_code != 403:
                return r
        return r

    def post_multipart(self, path, data=None, files=None, csrf_required=True):
        """Mirror the chat UI: FormData POST with X-CSRFToken header."""
        for attempt in range(2):
            if csrf_required:
                if attempt == 0 and not self.csrf:
                    self._refresh_csrf(path)
                elif attempt == 1:
                    self._refresh_csrf(path)
            headers = {"X-CSRFToken": self.csrf} if csrf_required else {}
            r = self.s.post(BASE + path, data=data, files=files, headers=headers,
                            allow_redirects=False)
            if r.status_code != 403:
                return r
        return r

    def log_otp(self, email):
        """Read the most recent console-email OTP addressed to email."""
        txt = open(SERVER_LOG, encoding="utf-8", errors="ignore").read()
        matches = re.findall(
            r"To:\s*%s\n.*?verification code is\s+([A-Z0-9]{6})" % re.escape(email),
            txt, re.S,
        )
        if not matches:
            raise RuntimeError(f"No OTP found in server log for {email}")
        return matches[-1]


# ---- signup + onboarding pipeline --------------------------------
USER_ANSWERS = {}  # user key -> {question_idx: chosen option idx}


def answer_pattern(key):
    return USER_ANSWERS[key]


def signup_and_onboard(e2e, key, full_name, email, interests, university, city,
                       major="Computer Science", year="3rd Year",
                       bio="Student exploring new connections.",
                       age=20, gender=None,
                       languages=("English", "Hindi")):
    """Full signup: signup form -> email OTP -> profile setup -> questionnaire -> complete."""
    if gender is None:
        gender = "Female" if key == "divya" else "Male"
    steps = []

    def step(name, ok, detail=""):
        steps.append((name, ok, detail))
        mark = "PASS" if ok else "FAIL"
        print(f"    [{mark}] {name}" + (f" -- {detail}" if detail and not ok else ""))
        if not ok:
            raise AssertionError(f"step failed: {name} {detail}")

    r = e2e.post_form("/auth/signup/", {
        "full_name": full_name, "email": email,
        "password1": "Str0ng!Pass9x", "password2": "Str0ng!Pass9x", "terms": "on",
    }, follow=False)
    step("signup form submitted", r.status_code in (302, 303) and "/verify-email/" in r.headers.get("Location", ""),
         f"status={r.status_code} loc={r.headers.get('Location')}")
    r = e2e.get("/auth/verify-email/")
    step("verify-email page reachable", r.status_code == 200 and "verification code" in r.text.lower())

    wrong = "000000"
    r = e2e.post_form("/auth/verify-email/", {"code": wrong}, follow=False)
    step("wrong OTP rejected", ("incorre" in r.text.lower() or "attempt" in r.text.lower()),
         f"status={r.status_code}")
    code = e2e.log_otp(email)
    step(f"OTP found in console log ({code})", bool(code))

    r = e2e.post_form("/auth/verify-email/", {"code": code}, follow=False)
    step("correct OTP -> redirected to profile setup", "/profiles/setup/" in r.headers.get("Location", ""),
         f"loc={r.headers.get('Location')} status={r.status_code}")

    r = e2e.post_form("/profiles/setup/", {
        "display_name": full_name.split()[0], "age": age, "gender": gender,
        "languages": languages, "city": city, "university": university,
        "major": major, "year": year, "bio": bio, "interests": interests,
    }, follow=False)
    step("profile setup saved", r.status_code in (302, 303), f"status={r.status_code}")

    r = e2e.post_form("/questionnaire/intro/", {"ai_consent": "yes"}, follow=False)
    step("questionnaire intro consent saved", "/questionnaire/hub/" in r.headers.get("Location", ""),
         f"loc={r.headers.get('Location')}")

    r = e2e.get("/api/questionnaire/questions/")
    qs = r.json()
    step(f"fetched {len(qs)} questionnaire questions", r.status_code == 200 and len(qs) == 24,
         f"got {len(qs)} status={r.status_code}")

    my_picks = []
    for i, q in enumerate(qs):
        opts = q.get("options") or []
        if not opts:
            continue
        n = len(opts)
        pattern = answer_pattern(key)
        pick_idx = pattern[i] % n if i in pattern else i % n
        chosen = opts[pick_idx]
        payload = {
            "question": q["id"],
            "value": chosen.get("option_value", ""),
            "selected_option_ids": [chosen["id"]],
            "importance": "NEUTRAL",
        }
        rr = e2e.post_json("/api/questionnaire/responses/", payload)
        if rr.status_code not in (200, 201):
            step(f"answer q#{i} ({q.get('category')})", False, rr.text[:200])
            return {"key": key, "email": email, "client": e2e, "steps": steps, "failed": True}
        my_picks.append((i, q["id"], pick_idx, chosen.get("option_value")))
    step(f"answered all {len(my_picks)} questions", len(my_picks) == len(qs))
    USER_ANSWERS[key] = {i: p[2] for p in my_picks}

    r = e2e.post_json("/api/questionnaire/complete/", {})
    data = r.json() if r.status_code in (200, 400) else {}
    step("questionnaire marked complete", r.status_code == 200 and data.get("completed") is True, str(data)[:200])

    r = e2e.get("/api/questionnaire/progress/")
    p = r.json()
    step("progress shows 100% complete", p.get("completion_percentage") == 100 and p.get("is_complete") is True, str(p)[:200])

    return {"key": key, "email": email, "client": e2e, "steps": steps, "failed": False}


def login(e2e, email, password="Str0ng!Pass9x"):
    e2e.get("/auth/logout/")
    r = e2e.post_form("/auth/login/", {"username": email, "password": password}, follow=False)
    ok = r.status_code in (302, 303) and "/home/" in r.headers.get("Location", "")
    print(f"    [{'PASS' if ok else 'FAIL'}] login as {email}")
    if not ok:
        raise AssertionError(f"login failed for {email}: status={r.status_code}")
    return True


def dump_user_ids():
    """Refresh /tmp/user_ids.json with all current users (post-signup).

    Inherits the caller's environment (PYTHONPATH, DJANGO_SETTINGS_MODULE, etc.)
    and runs `manage.py shell` from the CC_PROJECT directory (default: cwd).
    """
    import subprocess, os, json
    cwd = os.environ.get("CC_PROJECT", os.getcwd())
    env = dict(os.environ)
    cmd = [
        "python3", "manage.py", "shell", "-c",
        "import json;from django.contrib.auth import get_user_model;U=get_user_model();"
        "open('/tmp/user_ids.json','w').write(json.dumps({u.email:str(u.id) for u in U.objects.all()}))",
    ]
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not os.path.exists("/tmp/user_ids.json"):
        raise RuntimeError(f"dump_user_ids failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}")
    return json.load(open("/tmp/user_ids.json"))
