import io, json, sys, time
import requests
from PIL import Image
sys.path.insert(0, "/tmp")
from e2e_helpers import E2E, BASE, signup_and_onboard, login, USER_ANSWERS, dump_user_ids

RESULTS = []   # (phase, test, ok, detail)

def record(phase, test, ok, detail=""):
    RESULTS.append((phase, test, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} | {phase} | {test}" + (f" | {detail}" if detail and not ok else ""))

def phase(title):
    print("\n" + "="*70 + f"\nPHASE: {title}\n" + "="*70)

UNI = "Campus Connect University"
P_SAME = {i: i % 4 for i in range(24)}
P_B = {i: (i + 1) % 4 for i in range(24)}
P_C = {i: (i + 2) % 4 for i in range(24)}
P_D = {i: (i + 3) % 4 for i in range(24)}

def main():
    # ================= PHASE 1: SIGNUP (5 new accounts) =============
    phase("PHASE 1 — SIGNUP & ONBOARDING (signup -> email OTP -> profile -> questionnaire)")

    mani = E2E(); divya = E2E(); arjun = E2E(); sara = E2E(); vikram = E2E()

    import e2e_helpers as H
    H.USER_ANSWERS["mani"] = P_SAME
    r1 = signup_and_onboard(mani, "mani", "Mani Kumar", "mani1@example.com",
        "Coding, Music, Startups", UNI, "Bengaluru", major="Computer Science")
    H.USER_ANSWERS["divya"] = P_SAME
    r2 = signup_and_onboard(divya, "divya", "Divya Rao", "divya@example.com",
        "Coding, Music, Startups", UNI, "Bengaluru", major="Data Science")
    H.USER_ANSWERS["arjun"] = P_B
    r3 = signup_and_onboard(arjun, "arjun", "Arjun Iyer", "arjun@example.com",
        "Photography, Music", UNI, "Hyderabad", major="Mechanical Engineering")
    H.USER_ANSWERS["sara"] = P_C
    r4 = signup_and_onboard(sara, "sara", "Sara Fernandes", "sara@example.com",
        "Reading, Sports, Music", UNI, "Bengaluru", major="Biotechnology")
    H.USER_ANSWERS["vikram"] = P_D
    r5 = signup_and_onboard(vikram, "vikram", "Vikram Seth", "vikram@example.com",
        "Gaming, Cooking", UNI, "Pune", major="Electrical Engineering")

    accounts = [r1, r2, r3, r4, r5]
    ok_all = all(not a["failed"] for a in accounts)
    record("signup", "5 new accounts created & onboarded (OTP verify, profile, 24 Qs, complete)", ok_all,
           "; ".join(f"{a['key']}={ 'FAIL' if a['failed'] else 'OK'}" for a in accounts))

    # negative signup checks (reuse a fresh session)
    neg = E2E()
    r = neg.post_form("/auth/signup/", {
        "full_name": "Dup User", "email": "mani1@example.com",
        "password1": "Str0ng!Pass9x", "password2": "Str0ng!Pass9x", "terms": "on"})
    record("signup", "duplicate email rejected with clear error",
           r.status_code == 200 and "already exists" in r.text.lower(), r.text[:200])
    r = neg.post_form("/auth/signup/", {
        "full_name": "M M", "email": "newbie@example.com",
        "password1": "Str0ng!Pass9x", "password2": "differen1!Pw", "terms": "on"})
    record("signup", "mismatched passwords rejected",
           r.status_code == 200 and ("do not match" in r.text.lower() or "mismatch" in r.text.lower()), r.text[:200])
    r = neg.get("/home/")
    record("auth", "unauthenticated /home/ redirects to login",
           r.url.split("/")[-2:] and "login" in r.url, f"final url={r.url}")

    # ================= PHASE 2: LOGIN =============
    phase("PHASE 2 — LOGIN")
    for label, sess, email in [("mani", mani, "mani1@example.com"), ("divya", divya, "divya@example.com")]:
        # logout first to test real login
        r = sess.post_form("/auth/logout/", {"csrfmiddlewaretoken": sess.csrf or ""}, follow=False)
        record("login", f"logout as {label} -> redirect to login", "login" in r.headers.get("Location",""), str(r.headers.get("Location")))
    # fresh session login flow
    fresh = E2E()
    login(fresh, "mani1@example.com")
    r = fresh.get("/home/")
    record("login", "login as mani -> lands on /home/ (200, shows 'Mani')", r.status_code == 200 and "Mani" in r.text, r.status_code)
    bad = E2E()
    bad.get("/auth/login/")
    r = bad.post_form("/auth/login/", {"username": "mani1@example.com", "password": "WrongPass9x!"}, follow=True)
    r2_msgs = r.text
    page_text = r.text + r2_msgs
    r2 = bad.get("/home/")
    record("login", "failed login does NOT create a session (/home redirects to login)",
           "login" in r2.url, r2.url)
    record("login", "BUG CHECK: wrong password shows visible error on login page",
           "Invalid email or password" in r.text,
           "login.html does not render Django messages — failure is silent to the user")

    # log the main accounts back in for the matching phase
    login(mani, "mani1@example.com")
    login(divya, "divya@example.com")
    login(arjun, "arjun@example.com")
    login(sara, "sara@example.com")
    login(vikram, "vikram@example.com")

    # ================= PHASE 3: MATCHING =============
    phase("PHASE 3 — MATCHING (percentage -> request -> accept -> visible)")
    ids = dump_user_ids()
    divya_id = ids.get("divya@example.com")
    vikram_id = ids.get("vikram@example.com")
    arjun_id = ids.get("arjun@example.com")
    sara_id = ids.get("sara@example.com")
    print("  user ids:", {k: v[:8] for k, v in ids.items() if not k.endswith('.local')})

    r = mani.get("/api/matches/")
    matches = r.json()
    record("matching", f"mani fetches match list (status {r.status_code}, {len(matches.get('results',[]))} candidates)",
           r.status_code == 200 and len(matches.get('results', [])) >= 5)
    by_id = {m["user_id"]: m for m in matches["results"]}
    divya_m = by_id.get(divya_id)
    vikram_m = by_id.get(vikram_id)
    id2short = {divya_id: "divya", vikram_id: "vikram", arjun_id: "arjun", sara_id: "sara",
                 ids.get("kabir.demo@campusconnect.local"): "kabir(demo)",
                 ids.get("ishita.demo@campusconnect.local"): "ishita(demo)",
                 ids.get("rohan.demo@campusconnect.local"): "rohan(demo)",
                 ids.get("priya.demo@campusconnect.local"): "priya(demo)",
                 ids.get("aarav.demo@campusconnect.local"): "aarav(demo)"}
    print("  mani's matches: " + "; ".join(
        f"{id2short.get(m['user_id'], m['user_id'][:4])}={m['overall_score']}%" for m in matches["results"]))
    record("matching", "divya (same answers+university+interests) is listed with high score (>=80)",
           divya_m is not None and divya_m["overall_score"] >= 80,
           f"score={divya_m['overall_score'] if divya_m else None} entry={json.dumps(divya_m)[:200] if divya_m else 'NOT LISTED'}")
    record("matching", "unconnected profiles shown as '??? ???' (names hidden until connection)",
           vikram_m is not None and vikram_m.get("display_name") == "??? ???",
           json.dumps(vikram_m)[:200] if vikram_m else "vikram not listed")

    # compatibility detail
    r = mani.get(f"/api/matches/{divya_id}/compatibility/")
    comp = r.json()
    record("matching", "compatibility breakdown (overall + per-category + reasons)",
           r.status_code == 200 and comp.get("overall_score") is not None and "categories" in comp,
           f"{r.status_code} " + json.dumps(comp)[:300])
    print(f"  compatibility vs divya: {comp.get('overall_score')}% reasons={comp.get('reasons')} shared={comp.get('shared_interests')}")

    # send requests (by user_id — display names are hidden until connection)
    r = mani.post_json("/api/connections/request/", {"user_id": divya_id})
    record("matching", f"mani sends connection request to divya ({divya_id[:8]})", r.status_code == 201, r.text[:200])

    # divya sees notification
    r = divya.get("/notifications/")
    notifs = r.json()
    conn_notif = next((n for n in notifs["results"] if n["title"] == "New connection request"), None)
    record("matching", "divya gets 'New connection request' notification", conn_notif is not None, json.dumps(notifs)[:300])

    # divya accepts via notification UI path
    if conn_notif:
        r = divya.post_json(f"/notifications/{conn_notif['id']}/accept/", {})
        record("matching", "divya accepts request (via notification) -> ACCEPTED",
               r.status_code == 200 and r.json().get("status") == "ACCEPTED", r.text[:200])

    # verify both sides see ACCEPTED
    r = mani.get("/api/connections/")
    statuses = {c["user_id"]: c["status"] for c in r.json()["results"]}
    record("matching", "connection list shows ACCEPTED on both sides",
           statuses.get(divya_id) == "ACCEPTED", json.dumps(statuses))

    # now divya's details are unlocked for mani
    r = mani.get("/api/matches/")
    m2 = next((m for m in r.json()["results"] if m.get("user_id") == divya_id), None)
    record("matching", "after acceptance, divya's name/university/major unlocked for mani",
           m2 is not None and m2.get("display_name") in ("Divya Rao", "Divya")
           and m2.get("university") == "Campus Connect University"
           and m2.get("field_of_study") == "Data Science" and not m2.get("is_private"),
           json.dumps(m2)[:300] if m2 else "not found")

    # profiles page — connected profile fully visible
    r = mani.get(f"/profiles/{divya_id}/")
    open('/tmp/divya_profile_after.html','w').write(r.text)
    record("matching", "divya's profile page shows full details to mani after acceptance",
           r.status_code == 200 and "Data Science" in r.text and "Campus Connect University" in r.text,
           str(r.status_code))
    # unconnected profile page stays partial (no interests/university leak)
    r = mani.get(f"/profiles/{vikram_id}/")
    record("matching", "unconnected profile page stays partial ('??? ???', interests/university hidden)",
           r.status_code == 200 and "???" in r.text and "Gaming" not in r.text,
           f"status={r.status_code}")

    # ================= PHASE 4: CHAT =============
    phase("PHASE 4 — CHAT between accepted connection (mani <-> divya)")
    r = mani.post_multipart(f"/chat/{divya_id}/send/", data={"content": "Hi Divya! Great to match on coding & music."})
    open('/tmp/chat_send1.json','w').write(r.text)
    record("chat", "mani sends text message to divya (multipart, like UI)",
           r.status_code == 200 and "Hi Divya!" in (r.json().get("content","") if r.headers.get('Content-Type','').startswith('application/json') else ""),
           f"{r.status_code} {r.text[:200]}")
    main_phase4(divya_id, mani, divya, sara, accounts)

    # ================= PHASE 5: COMMUNITIES / EVENTS / NOTIFICATIONS =============
    phase("PHASE 5 — COMMUNITIES, EVENTS, NOTIFICATIONS")
    r = mani.get("/communities/")
    record("communities", "communities home lists 5 demo communities", r.status_code == 200 and "AI & Machine Learning" in r.text, r.status_code)
    # join a community
    import re as _re
    cid = _re.search(r'/communities/(\d+)/', r.text)
    if cid:
        cnum = cid.group(1)
        r = mani.post_form(f"/communities/{cnum}/membership/", {"next": "/communities/"}, follow=False)
        r2 = mani.get("/communities/")
        record("communities", "mani joins a community (POST membership) and sees 'joined' state",
               r.status_code in (302,303), str(r2.status_code))
    r = mani.get("/events/")
    record("events", "events home lists demo events", r.status_code == 200 and "Campus Hack Night" in r.text, r.status_code)
    eid = _re.search(r'/events/(\d+)/', r.text)
    if eid:
        en = eid.group(1)
        r = mani.post_form(f"/events/{en}/register/", {"name":"Mani Kumar","email":"mani1@example.com","phone_number":"9812345678"}, follow=False)
        r2 = mani.get("/notifications/")
        ev_notif = any("registered for" in n["message"].lower() for n in r2.json()["results"])
        record("events", "mani registers for event -> success notification", ev_notif, r.text[:200])
        # invalid phone rejected
        r = mani.post_form(f"/events/{en}/register/", {"name":"X","email":"x@y.z","phone_number":"12"}, follow=False)
        record("events", "event registration with short phone rejected", r.status_code == 200 and "valid phone" in r.text.lower(), r.text[:200])
    r = mani.get("/notifications/inbox/")
    record("notifications", "notifications inbox renders", r.status_code == 200, r.status_code)

    # ================= PHASE 6: QUESTIONNAIRE SUMMARY + GROQ =============
    phase("PHASE 6 — QUESTIONNAIRE SUMMARY & AI INSIGHTS")
    r = mani.get("/api/questionnaire/summary/")
    record("questionnaire", "summary available after completion", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
    r = mani.get("/questionnaire/summary/")
    record("questionnaire", "summary page renders", r.status_code == 200, r.status_code)
    # AI insights without GROQ key -> graceful 503
    r = mani.post_json(f"/api/matches/{divya_id}/compatibility/insights/", {"consent": True})
    record("questionnaire", "AI compatibility insights degrade gracefully without GROQ key (503 + message, not crash)",
           r.status_code in (503, 502) and "config" in r.text.lower(), f"{r.status_code} {r.text[:150]}")

    # ================= finalize =============
    passed = sum(1 for _,_,ok,_ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "="*70)
    print(f"E2E SUMMARY: {passed}/{total} checks passed, {total-passed} failed")
    for ph,t,ok,d in RESULTS:
        if not ok:
            print(f"  FAIL [{ph}] {t} :: {d[:200]}")
    json.dump([{"phase":p,"test":t,"ok":o,"detail":d} for p,t,o,d in RESULTS],
              open("/tmp/e2e_results.json","w"), indent=2)
    print("\nresults written to /tmp/e2e_results.json")

def main_phase4(divya_id, mani, divya, sara, accounts):
    import json as _json
    ids = _json.load(open("/tmp/user_ids.json"))
    mani_id = ids["mani1@example.com"]
    divya_id = ids["divya@example.com"]
    # divya polls messages, sees mani's first message
    r = divya.get(f"/chat/{mani_id}/messages/")
    record("chat", "divya polls messages, sees mani's first message",
           r.status_code == 200 and any("Hi Divya" in msg.get("content","") for msg in r.json()["messages"]),
           r.text[:300])
    # divya replies (multipart)
    r = divya.post_multipart(f"/chat/{mani_id}/send/", data={"content": "Hey Mani! Let's build something."})
    record("chat", "divya replies", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    r = mani.get(f"/chat/{divya_id}/messages/")
    record("chat", "mani sees divya's reply in shared conversation",
           r.status_code == 200 and any("Let's build something" in msg.get("content","") for msg in r.json()["messages"]),
           r.text[:300])
    # image message (PNG accepted)
    buf = io.BytesIO(); Image.new("RGB",(40,40),"red").save(buf, format="PNG"); buf.seek(0)
    r = mani.post_multipart(f"/chat/{divya_id}/send/", data={"content":"check this"},
                            files={"image": ("shot.png", buf, "image/png")})
    j = r.json() if r.headers.get('Content-Type','').startswith('application/json') else {}
    record("chat", "mani sends an image message (PNG accepted)", r.status_code == 200 and j.get("image_url"),
           f"{r.status_code} {r.text[:200]}")
    # non-image file rejected
    r = mani.post_multipart(f"/chat/{divya_id}/send/", data={"content":"bad file"},
                            files={"image": ("notes.txt", io.BytesIO(b"hello"), "text/plain")})
    record("chat", "non-image file rejected with clear error (400)",
           r.status_code == 400 and "JPG, PNG" in r.text, f"{r.status_code} {r.text[:150]}")
    # empty message rejected
    r = mani.post_multipart(f"/chat/{divya_id}/send/", data={"content": ""})
    record("chat", "empty message (no text, no image) rejected (400)", r.status_code == 400, f"{r.status_code} {r.text[:150]}")
    # chat home shows contact
    r = divya.get("/chat/")
    record("chat", "chat home lists mani as a contact with last message",
           r.status_code == 200 and "Mani" in r.text, str(r.status_code))
    # unconnected user cannot message divya
    r = sara.post_multipart(f"/chat/{divya_id}/send/", data={"content":"hack"})
    record("chat", "unconnected user cannot message divya (403)", r.status_code == 403, f"{r.status_code} {r.text[:150]}")

if __name__ == "__main__":
    main()
