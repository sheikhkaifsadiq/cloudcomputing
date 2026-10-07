import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()

from backend.agent import agent_executor, resume_workflow
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from backend.supabase_client import get_supabase_client

def print_separator(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def verify_supabase():
    print_separator("VERIFY SUPABASE CONNECTION & DUMMY DATA")
    client = get_supabase_client()
    try:
        emp = client.table("employees").select("*").execute()
        hist = client.table("operation_history").select("*").execute()
        print(f"PASS: Found {len(emp.data)} employees and {len(hist.data)} history records.")
        for e in emp.data:
            print(f" - {e['name']} ({e['department']})")
    except Exception as e:
        print("FAIL: Supabase connection error:", e)

def verify_read():
    print_separator("VERIFY REAL TOOL CALLING (READ)")
    config = {"configurable": {"thread_id": "test_read"}}
    try:
        result = agent_executor.invoke({"messages": [HumanMessage(content="Show all employees in HR.")]}, config)
        print("Final response:", result["messages"][-1].content)
        # Find tool calls
        for m in result["messages"]:
            if getattr(m, "tool_calls", None):
                print("Tool calls executed:", [tc["name"] for tc in m.tool_calls])
    except Exception as e:
        print("FAIL: Read operation error:", e)

def verify_create():
    print_separator("VERIFY CREATE")
    config = {"configurable": {"thread_id": "test_create"}}
    try:
        result = agent_executor.invoke({"messages": [HumanMessage(content="Create Hamza Test in IT with email hamzatest@example.com, phone 03009999999, position Developer.")]}, config)
        print("Final response:", result["messages"][-1].content)
        
        # Verify directly in supabase
        client = get_supabase_client()
        emp = client.table("employees").select("*").eq("name", "Hamza Test").execute()
        if len(emp.data) > 0:
            print("PASS: Hamza Test found in Supabase")
        else:
            print("FAIL: Hamza Test not found in Supabase")
    except Exception as e:
        print("FAIL: Create error:", e)

def verify_update():
    print_separator("VERIFY UPDATE")
    config = {"configurable": {"thread_id": "test_update"}}
    try:
        result = agent_executor.invoke({"messages": [HumanMessage(content="Move Hamza Test from IT to HR.")]}, config)
        print("Final response:", result["messages"][-1].content)
        
        # Verify directly
        client = get_supabase_client()
        emp = client.table("employees").select("*").eq("name", "Hamza Test").execute()
        if len(emp.data) > 0 and emp.data[0]['department'] == 'HR':
            print("PASS: Hamza Test department is now HR")
        else:
            print("FAIL: Hamza Test department update failed")
    except Exception as e:
        print("FAIL: Update error:", e)

def verify_delete_hitl_approve():
    print_separator("VERIFY DELETE + HITL (APPROVE)")
    config = {"configurable": {"thread_id": "test_delete_approve"}}
    try:
        print("Step 1: Request Delete")
        result = agent_executor.invoke({"messages": [HumanMessage(content="Delete Hamza Test from HR.")]}, config)
        state = agent_executor.get_state(config)
        print("Requires approval:", state.values.get("requires_approval"))
        
        if state.values.get("requires_approval"):
            print("Step 2: Approve Action")
            resume_result = resume_workflow("test_delete_approve", True)
            print("Final response:", resume_result["messages"][-1].content)
            
            # Verify deleted
            client = get_supabase_client()
            emp = client.table("employees").select("*").eq("name", "Hamza Test").execute()
            if len(emp.data) == 0:
                print("PASS: Hamza Test successfully deleted")
            else:
                print("FAIL: Hamza Test still exists")
        else:
            print("FAIL: Did not pause for approval")
    except Exception as e:
        print("FAIL: HITL Approve error:", e)

def verify_delete_hitl_decline():
    print_separator("VERIFY DELETE + HITL (DECLINE)")
    # Insert test record
    client = get_supabase_client()
    client.table("employees").insert({"name": "Test Decline", "department": "IT", "email": "d@d.com", "phone": "123", "position": "Dev"}).execute()
    
    config = {"configurable": {"thread_id": "test_delete_decline"}}
    try:
        print("Step 1: Request Delete")
        result = agent_executor.invoke({"messages": [HumanMessage(content="Delete Test Decline from IT.")]}, config)
        state = agent_executor.get_state(config)
        
        if state.values.get("requires_approval"):
            print("Step 2: Decline Action")
            resume_result = resume_workflow("test_delete_decline", False)
            print("Final response:", resume_result["messages"][-1].content)
            
            # Verify still exists
            emp = client.table("employees").select("*").eq("name", "Test Decline").execute()
            if len(emp.data) > 0:
                print("PASS: Test Decline still exists in database")
            else:
                print("FAIL: Test Decline was wrongly deleted")
        else:
            print("FAIL: Did not pause for approval")
    except Exception as e:
        print("FAIL: HITL Decline error:", e)

def verify_ambiguity():
    print_separator("VERIFY AMBIGUITY")
    client = get_supabase_client()
    client.table("employees").insert({"name": "Ambiguous Ali", "department": "IT", "email": "a1@a.com", "phone": "1", "position": "Dev"}).execute()
    client.table("employees").insert({"name": "Ambiguous Ali", "department": "HR", "email": "a2@a.com", "phone": "2", "position": "Dev"}).execute()
    
    config = {"configurable": {"thread_id": "test_ambiguity"}}
    try:
        result = agent_executor.invoke({"messages": [HumanMessage(content="Delete Ambiguous Ali.")]}, config)
        print("Final response:", result["messages"][-1].content)
        state = agent_executor.get_state(config)
        print("Requires approval:", state.values.get("requires_approval"))
        if not state.values.get("requires_approval"):
            print("PASS: Handled ambiguity without destructive tool call")
        else:
            print("FAIL: Blindly called destructive tool")
    except Exception as e:
        print("FAIL: Ambiguity error:", e)

def verify_add_details():
    print_separator("VERIFY ADD DETAILS")
    # Continuing from the previous ambiguity thread where we were asked for clarification
    config = {"configurable": {"thread_id": "test_ambiguity"}}
    try:
        print("Step 1: Provide details")
        # Technically in the ambiguity test it didn't pause for approval, it just asked a question.
        # So we just send a new HumanMessage. Add Details is for when it IS paused but we want to change details.
        
        # Let's test the actual Add Details flow: Ask to delete something, it interrupts, we provide details.
        config_details = {"configurable": {"thread_id": "test_details_flow"}}
        agent_executor.invoke({"messages": [HumanMessage(content="Delete Ambiguous Ali from IT.")]}, config_details)
        state = agent_executor.get_state(config_details)
        
        if state.values.get("requires_approval"):
            print("Paused for approval correctly. Now adding details.")
            resume_result = resume_workflow("test_details_flow", False, additional_details="Actually, don't delete him. Update his email to new@test.com instead.")
            print("Final response after details:", resume_result["messages"][-1].content)
            
            client = get_supabase_client()
            emp = client.table("employees").select("*").eq("name", "Ambiguous Ali").eq("department", "IT").execute()
            if emp.data[0]["email"] == "new@test.com":
                print("PASS: Details caused re-evaluation and update")
            else:
                print("FAIL: Details didn't trigger update correctly")
        else:
            print("FAIL: Did not pause")
    except Exception as e:
        print("FAIL: Add Details error:", e)


if __name__ == "__main__":
    verify_supabase()
    verify_read()
    verify_create()
    verify_update()
    verify_delete_hitl_approve()
    verify_delete_hitl_decline()
    verify_ambiguity()
    verify_add_details()
    
    print_separator("ALL TESTS COMPLETED")
