"""
HM2 End-to-End Verification Script
Run after Supabase tables have been created and dummy data has been inserted.

Usage:
    .\\venv\\Scripts\\python.exe tests\\e2e_verify.py
"""
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

# ── path fix so backend package resolves
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.supabase_client import get_supabase_client
from backend.agent import agent_executor, resume_workflow
from langchain_core.messages import HumanMessage, ToolMessage

PASS = "PASS"
FAIL = "FAIL"
BLOCKED = "BLOCKED"

results = {}

def sep(title):
    print(f"\n{'='*55}\n  {title}\n{'='*55}")

def log(key, status, detail=""):
    results[key] = status
    marker = "PASS" if status == PASS else ("FAIL" if status == FAIL else "WARN")
    print(f"  [{marker}] {key}: {status}  {detail}")

def is_429(e):
    return "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)

def block_all():
    global results
    for key in ["READ", "CREATE", "UPDATE", "HITL Interrupt", "HITL Approve", "HITL Decline", "HITL Add Details", "Ambiguity Handling", "Not Found", "History"]:
        if key not in results:
            log(key, BLOCKED, "Gemini Quota Exhausted")

def _print_final():
    sep("HM2 FINAL VERIFIED STATUS")
    order = [
        "Supabase Connection", "employees table", "operation_history table",
        "Dummy Data", "Gemini", "READ", "CREATE", "UPDATE",
        "HITL Interrupt", "HITL Approve", "HITL Decline", "HITL Add Details",
        "Ambiguity Handling", "Not Found", "History"
    ]
    for key in order:
        status = results.get(key, "NOT RUN")
        marker = "PASS" if status == PASS else ("FAIL" if status == FAIL else "WARN")
        print(f"  [{marker}] {key}: {status}")
    remaining = [k for k, v in results.items() if v != PASS and v != BLOCKED]
    if remaining:
        print(f"\n  Remaining issues: {', '.join(remaining)}")
    elif any(v == BLOCKED for v in results.values()):
        print("\n  TESTS BLOCKED — Gemini quota exhaustion.")
    else:
        print("\n  ALL TESTS PASSED — HM2 backend verified end-to-end.")

# ──────────────────────────────────────────────────────────────────────────────
# 1. SUPABASE CONNECTION + TABLES
# ──────────────────────────────────────────────────────────────────────────────
sep("1. SUPABASE CONNECTION & TABLES")
try:
    client = get_supabase_client()
    emp_res = client.table("employees").select("*").execute()
    hist_res = client.table("operation_history").select("*").execute()
    print(f"  employees rows: {len(emp_res.data)}")
    print(f"  operation_history rows: {len(hist_res.data)}")
    log("Supabase Connection", PASS)
    log("employees table", PASS, f"({len(emp_res.data)} rows)")
    log("operation_history table", PASS, f"({len(hist_res.data)} rows)")
except Exception as e:
    log("Supabase Connection", FAIL, str(e))
    log("employees table", BLOCKED)
    log("operation_history table", BLOCKED)
    print("\n  DATABASE SETUP REQUIRED — run SQL in projectBrain/SUPABASE_SETUP.md")
    print("\nStopping — cannot continue without database.")
    _print_final()
    sys.exit(1)


# ──────────────────────────────────────────────────────────────────────────────
# 2. DUMMY DATA
# ──────────────────────────────────────────────────────────────────────────────
sep("2. DUMMY DATA VERIFICATION")
EXPECTED = [
    ("Ali Ahmed", "HR"),
    ("Ali Raza", "IT"),
    ("Sara Khan", "IT"),
    ("Ahmed Raza", "Finance"),
    ("Hamza Malik", "HR"),
]
all_present = True
for name, dept in EXPECTED:
    row = client.table("employees").select("*").eq("name", name).eq("department", dept).execute()
    found = len(row.data) > 0
    print(f"  {'PASS' if found else 'FAIL'} {name} - {dept}")
    if not found:
        all_present = False
log("Dummy Data", PASS if all_present else FAIL, "5 expected records" if all_present else "Some records missing")

# ──────────────────────────────────────────────────────────────────────────────
# Cleanup helper — remove test records created by this script
# ──────────────────────────────────────────────────────────────────────────────
TEST_NAMES = ["Test Employee 01", "Test Decline Emp", "Test Ali"]

def cleanup_test_records():
    for name in TEST_NAMES:
        try:
            client.table("employees").delete().eq("name", name).execute()
        except Exception:
            pass
cleanup_test_records()

# ──────────────────────────────────────────────────────────────────────────────
# 3. READ
# ──────────────────────────────────────────────────────────────────────────────
sep("3. READ - Show all employees in HR")
try:
    config = {"configurable": {"thread_id": "verify_read"}}
    res = agent_executor.invoke({"messages": [HumanMessage(content="Show all employees in HR.")], "conversation_id": "verify_read"}, config)
    
    # Verify exact tool result
    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    if tool_msgs:
        parsed = json.loads(tool_msgs[-1].content)
        success = parsed.get("success", False)
        count = parsed.get("count", 0)
        print(f"  Tool returned success: {success}, count: {count}")
        if success and count > 0:
            log("READ", PASS)
            log("Gemini", PASS)
        else:
            log("READ", FAIL, "Tool returned success=false or count=0")
            log("Gemini", PASS)
    else:
        log("READ", FAIL, "No ToolMessage found")
        log("Gemini", PASS)
except Exception as e:
    if is_429(e):
        log("Gemini", BLOCKED, "Quota Exhausted")
        block_all()
        _print_final()
        sys.exit(0)
    else:
        log("Gemini", FAIL, str(e))
        log("READ", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 4. CREATE
# ──────────────────────────────────────────────────────────────────────────────
sep("4. CREATE - Test Employee 01")
try:
    config = {"configurable": {"thread_id": "verify_create"}}
    msg = "Create Test Employee 01 in IT with email test01@example.com, phone 03000000001, position Developer."
    res = agent_executor.invoke({"messages": [HumanMessage(content=msg)], "conversation_id": "verify_create"}, config)
    
    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    success = False
    if tool_msgs:
        parsed = json.loads(tool_msgs[-1].content)
        success = parsed.get("success", False)
    
    row = client.table("employees").select("*").eq("name", "Test Employee 01").execute()
    exists = len(row.data) > 0
    print(f"  Tool success: {success}, Row exists: {exists}")
    
    if success and exists:
        log("CREATE", PASS)
    else:
        log("CREATE", FAIL, "Either tool failed or row missing")
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("CREATE", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 5. UPDATE
# ──────────────────────────────────────────────────────────────────────────────
sep("5. UPDATE - Test Employee 01: IT -> Finance")
try:
    config = {"configurable": {"thread_id": "verify_update"}}
    msg = "Move Test Employee 01 from IT to Finance."
    res = agent_executor.invoke({"messages": [HumanMessage(content=msg)], "conversation_id": "verify_update"}, config)

    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    success = False
    if tool_msgs:
        parsed = json.loads(tool_msgs[-1].content)
        success = parsed.get("success", False)

    after = client.table("employees").select("*").eq("name", "Test Employee 01").execute()
    after_dept = after.data[0]["department"] if after.data else "MISSING"
    print(f"  Tool success: {success}, After dept: {after_dept}")
    if success and after_dept == "Finance":
        log("UPDATE", PASS)
    else:
        log("UPDATE", FAIL)
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("UPDATE", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 6. DELETE + HITL INTERRUPT + APPROVE
# ──────────────────────────────────────────────────────────────────────────────
sep("6. DELETE HITL INTERRUPT - Test Employee 01")
try:
    config = {"configurable": {"thread_id": "verify_delete_approve"}}
    msg = "Delete Test Employee 01 from Finance."
    res = agent_executor.invoke({"messages": [HumanMessage(content=msg)], "conversation_id": "verify_delete_approve"}, config)

    state = agent_executor.get_state(config)
    requires_approval = state.values.get("requires_approval", False)
    
    pre = client.table("employees").select("*").eq("name", "Test Employee 01").execute()
    still_exists = len(pre.data) > 0
    print(f"  requires_approval: {requires_approval}, Row still exists: {still_exists}")
    if requires_approval and still_exists:
        log("HITL Interrupt", PASS)
    else:
        log("HITL Interrupt", FAIL)

    # 7. APPROVE
    sep("7. HITL APPROVE")
    result = resume_workflow("verify_delete_approve", True)
    
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    success = False
    if tool_msgs:
        parsed = json.loads(tool_msgs[-1].content)
        success = parsed.get("success", False)

    post = client.table("employees").select("*").eq("name", "Test Employee 01").execute()
    deleted = len(post.data) == 0
    print(f"  Tool success: {success}, Row gone: {deleted}")
    if success and deleted:
        log("HITL Approve", PASS)
    else:
        log("HITL Approve", FAIL)
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("HITL Interrupt", FAIL, str(e))
    log("HITL Approve", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 8. HITL DECLINE
# ──────────────────────────────────────────────────────────────────────────────
sep("8. HITL DECLINE - Test Decline Emp")
try:
    client.table("employees").insert({
        "name": "Test Decline Emp", "department": "IT",
        "email": "decline@test.com", "phone": "0300000002", "position": "QA"
    }).execute()

    config = {"configurable": {"thread_id": "verify_decline"}}
    res = agent_executor.invoke({"messages": [HumanMessage(content="Delete Test Decline Emp from IT.")], "conversation_id": "verify_decline"}, config)
    state = agent_executor.get_state(config)
    
    if state.values.get("requires_approval"):
        res = resume_workflow("verify_decline", False)  # Decline
        
        tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
        err_msg = ""
        if tool_msgs:
            parsed = json.loads(tool_msgs[-1].content)
            err_msg = parsed.get("error", "")
            
        post = client.table("employees").select("*").eq("name", "Test Decline Emp").execute()
        still_exists = len(post.data) > 0
        print(f"  Row still exists: {still_exists}, Error: {err_msg}")
        
        if still_exists and "declined" in err_msg.lower():
            log("HITL Decline", PASS)
        else:
            log("HITL Decline", FAIL)
    else:
        log("HITL Decline", FAIL, "Did not pause for approval")
    
    client.table("employees").delete().eq("name", "Test Decline Emp").execute()
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("HITL Decline", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 9. AMBIGUITY
# ──────────────────────────────────────────────────────────────────────────────
sep("9. AMBIGUITY - Delete Ali (multiple matches)")
try:
    config = {"configurable": {"thread_id": "verify_ambiguous"}}
    res = agent_executor.invoke({"messages": [HumanMessage(content="Delete Ali.")], "conversation_id": "verify_ambiguous"}, config)
    state = agent_executor.get_state(config)
    
    # Assert multiple records existed beforehand (dummy data has Ali Ahmed HR and Ali Raza IT)
    ali_check = client.table("employees").select("*").ilike("name", "Ali%").execute()
    has_multiple_alis = len(ali_check.data) >= 2
    
    # Verify no delete_record tool was executed
    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    get_records_called = any("get_records" in m.content for m in tool_msgs)
    delete_called = any("delete_record" in m.content for m in tool_msgs)
    
    requires_approval = state.values.get("requires_approval", False)
    
    # Verify no Ali was deleted
    ali_check_after = client.table("employees").select("*").ilike("name", "Ali%").execute()
    rows_unchanged = len(ali_check_after.data) == len(ali_check.data)
    
    status_field = res.get("status", "completed")
    
    print(f"  Has multiple Alis: {has_multiple_alis}")
    print(f"  get_records called: {get_records_called}, delete_called: {delete_called}")
    print(f"  Requires approval: {requires_approval}, Rows unchanged: {rows_unchanged}")
    print(f"  Final status: {status_field}")
    
    if has_multiple_alis and not delete_called and not requires_approval and rows_unchanged:
        log("Ambiguity Handling", PASS)
    else:
        log("Ambiguity Handling", FAIL, "Ambiguity not handled correctly")
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("Ambiguity Handling", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 10. NOT FOUND
# ──────────────────────────────────────────────────────────────────────────────
sep("10. NOT FOUND - Delete XYZ Employee")
try:
    config = {"configurable": {"thread_id": "verify_not_found"}}
    res = agent_executor.invoke({"messages": [HumanMessage(content="Delete XYZ Employee from HR.")], "conversation_id": "verify_not_found"}, config)
    state = agent_executor.get_state(config)
    
    # Verify lookup occurred and returned 0 matches
    tool_msgs = [m for m in res["messages"] if isinstance(m, ToolMessage)]
    get_records_called = any("get_records" in m.content for m in tool_msgs)
    delete_called = any("delete_record" in m.content for m in tool_msgs)
    
    requires_approval = state.values.get("requires_approval", False)
    
    xyz_check = client.table("employees").select("*").ilike("name", "%XYZ%").execute()
    db_unchanged = len(xyz_check.data) == 0
    
    print(f"  get_records called: {get_records_called}, delete_called: {delete_called}")
    print(f"  Requires approval: {requires_approval}, DB unchanged: {db_unchanged}")
    
    if not delete_called and not requires_approval and db_unchanged:
        log("Not Found", PASS)
    else:
        log("Not Found", FAIL)
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("Not Found", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 11. HITL ADD DETAILS  
# ──────────────────────────────────────────────────────────────────────────────
sep("11. HITL ADD DETAILS - Delete Test Ali, clarify department")
try:
    # Setup two Test Ali records
    client.table("employees").insert([
        {"name": "Test Ali", "department": "HR", "email": "ali1@test.com", "phone": "1", "position": "P1"},
        {"name": "Test Ali", "department": "IT", "email": "ali2@test.com", "phone": "2", "position": "P2"}
    ]).execute()

    config = {"configurable": {"thread_id": "verify_details"}}
    res1 = agent_executor.invoke({"messages": [HumanMessage(content="Delete Test Ali.")], "conversation_id": "verify_details"}, config)
    state1 = agent_executor.get_state(config)
    
    requires_approval_1 = state1.values.get("requires_approval", False)
    print(f"  Requires approval before clarification: {requires_approval_1}")
    
    if requires_approval_1:
        log("HITL Add Details", FAIL, "Graph wrongly decided to delete despite ambiguity")
    else:
        # Step 3: Provide details
        res2 = agent_executor.invoke({"messages": [HumanMessage(content="The IT employee.")], "conversation_id": "verify_details"}, config)
        state2 = agent_executor.get_state(config)
        requires_approval_2 = state2.values.get("requires_approval", False)
        print(f"  Requires approval after clarification: {requires_approval_2}")
        
        # Verify both rows still exist before approval
        ali_check = client.table("employees").select("*").eq("name", "Test Ali").execute()
        both_exist = len(ali_check.data) == 2
        
        if requires_approval_2 and both_exist:
            # Step 6: Decline
            resume_workflow("verify_details", False)
            ali_check_after = client.table("employees").select("*").eq("name", "Test Ali").execute()
            both_exist_after = len(ali_check_after.data) == 2
            
            if both_exist_after:
                log("HITL Add Details", PASS)
            else:
                log("HITL Add Details", FAIL, "Decline failed to protect rows")
        else:
            log("HITL Add Details", FAIL, "Did not request approval after clarification or rows missing")
        
    client.table("employees").delete().eq("name", "Test Ali").execute()
except Exception as e:
    if is_429(e): block_all(); _print_final(); sys.exit(0)
    log("HITL Add Details", FAIL, str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 12. HISTORY VERIFICATION
# ──────────────────────────────────────────────────────────────────────────────
sep("12. HISTORY")
try:
    hist = client.table("operation_history").select("*").order("timestamp", desc=True).limit(20).execute()
    statuses = {r["status"] for r in hist.data}
    print(f"  Statuses present: {statuses}")
    
    # We expect completed, cancelled to be definitely present
    if "completed" in statuses and "cancelled" in statuses:
        log("History", PASS)
    else:
        log("History", FAIL, f"Missing expected statuses. Found: {statuses}")
except Exception as e:
    log("History", FAIL, str(e))

# ──────────────────────────────────────────────────────────────────────────────
# CLEANUP & FINAL REPORT
# ──────────────────────────────────────────────────────────────────────────────
cleanup_test_records()
_print_final()
