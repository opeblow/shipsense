import urllib.request, json, sys, time

HOST = "http://localhost:8000"

def post(path, data):
    req = urllib.request.Request(
        f"{HOST}{path}",
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())

def get(path):
    return json.loads(urllib.request.urlopen(f"{HOST}{path}").read())

passed = 0
failed = 0

def test(name, ok, detail=""):
    global passed, failed
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

# ====== TEST 1: ONBOARDING ======
print("\n=== TEST 1: ONBOARDING ===")
resp = post("/api/onboard", {
    "url": "https://mysaas.app",
    "product_type": "consumers",
    "core_action": "create account",
    "user_id": "user_tester",
})
pid = resp["product_id"]
test("Product created with ID", bool(pid), f"pid={pid}")
test("Initial insights generated", bool(resp.get("initial_insights")), f"len={len(resp['initial_insights'])}")
print(f"  Insights summary:\n{resp['initial_insights']}")

# ====== TEST 2: BEHAVIOR INGESTION ======
print("\n=== TEST 2: BEHAVIOR INGESTION ===")
events = []
for i in range(20):
    user = f"user_{['alice','bob','charlie','dave','eve'][i%5]}"
    actions = ["visit page", "click signup", "enter email", "upload photo", "set profile", "click api keys", "run test", "invite team", "create project", "view dashboard"]
    events.append({"action": actions[i % len(actions)], "user_id": user, "timestamp": f"2026-06-{10+i:02d}T12:00:0{i%10}Z"})

resp2 = post("/api/behavior/ingest", {"product_id": pid, "events": events})
test("All events ingested", resp2.get("ingested") == True, f"count={resp2.get('count')}")
test("Correct count (20)", resp2.get("count") == 20)

# ====== TEST 3: DROP-OFF / INSIGHTS ======
print("\n=== TEST 3: DROP-OFF & INSIGHTS ===")
time.sleep(0.5)
resp3 = get(f"/api/insights/{pid}")
test("Insights returned", bool(resp3.get("summary")))
actions_list = resp3.get("recommended_actions", [])
test("Has recommended actions", len(actions_list) > 0, f"count={len(actions_list)}")
for a in actions_list:
    has_effort = bool(a.get("effort"))
    has_impact = bool(a.get("impact"))
    test(f"  Action '{a['title'][:40]}' has effort+impact", has_effort and has_impact, f"E:{a.get('effort')} I:{a.get('impact')}")

# Also check behavior for drop-offs
beh = get(f"/api/behavior/{pid}")
test("Drop-off points identified", len(beh.get("drop_off_points", [])) > 0, f"points={len(beh['drop_off_points'])}")
print(f"  Drop-off points: {json.dumps(beh['drop_off_points'], indent=2)}")

# ====== TEST 4: AGENT CHAT ======
print("\n=== TEST 4: AGENT CHAT ===")
try:
    resp4 = post("/api/agent/chat", {"product_id": pid, "user_id": "user_tester", "message": "Why are users leaving?"})
    test("Chat reply received", bool(resp4.get("reply")), f"len={len(resp4['reply'])}")
    test("Has data point", bool(resp4.get("data_point")))
    test("Has confidence score", resp4.get("confidence", 0) > 0, f"confidence={resp4['confidence']}")
    print(f"  Reply: {resp4['reply']}")
    print(f"  Data point: {resp4.get('data_point', 'N/A')}")
except Exception as e:
    test("Chat endpoint works", False, str(e))

# ====== TEST 5: METRICS ======
print("\n=== TEST 5: METRICS ===")
resp5 = get(f"/api/metrics/{pid}")
test("active_users populated", resp5.get("active_users", -1) >= 0, f"value={resp5['active_users']}")
test("avg_session populated", bool(resp5.get("avg_session")), f"value={resp5['avg_session']}")
test("drop_off_rate populated", bool(resp5.get("drop_off_rate")), f"value={resp5['drop_off_rate']}")
test("top_action populated", resp5.get("top_action") != "N/A", f"value={resp5['top_action']}")

# ====== TEST 6: EMPTY STATE ======
print("\n=== TEST 6: EMPTY STATE ===")
resp6 = post("/api/onboard", {
    "url": "https://freshproduct.io",
    "product_type": "consumers",
    "core_action": "start trial",
    "user_id": "user_empty",
})
empty_pid = resp6["product_id"]
test("Empty product created", bool(empty_pid))
time.sleep(0.5)
try:
    resp6b = get(f"/api/insights/{empty_pid}")
    summary = resp6b.get("summary", "")
    test("Insights returned without crash", bool(summary))
    not_a_crash = not any(phrase in summary.lower() for phrase in ["internal server error", "traceback"])
    has_graceful_language = any(phrase in summary.lower() for phrase in ["no active", "no engagement", "no data", "not enough", "fly blind", "zero"])
    test("Graceful empty-state message (no crash, graceful language)", has_graceful_language, f"graceful={has_graceful_language}")
    print(f"  Empty-state insight:\n{summary}")
except Exception as e:
    test("Empty product insights endpoint", False, str(e))

# ====== SUMMARY ======
print(f"\n{'='*40}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{failed} TEST(S) FAILED")
    sys.exit(1)
