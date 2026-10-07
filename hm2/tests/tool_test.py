import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crud_tools import create_record, get_records, update_record, delete_record
from backend.supabase_client import get_supabase_client

client = get_supabase_client()

def test_crud_tools():
    print("Testing CRUD Tools locally without LLM...")

    # 1. READ
    print("\n[1] READ existing HR employee")
    res = get_records.invoke({"entity": "employees", "filters": {"name": "Hamza Malik"}})
    print("READ result:", res)
    assert res["success"] is True

    # 2. CREATE (Validation Check)
    print("\n[2] CREATE validation (missing email)")
    res = create_record.invoke({"entity": "employees", "data": {"name": "Tool Test", "department": "IT", "phone": "123", "position": "Tester"}})
    print("CREATE missing fields result:", res)
    assert res["success"] is False
    assert "Missing required fields" in res["error"]

    # 3. CREATE (Success)
    print("\n[3] CREATE successful")
    client.table("employees").delete().eq("name", "Tool Test").execute() # cleanup if exists
    res = create_record.invoke({"entity": "employees", "data": {"name": "Tool Test", "department": "IT", "email": "test@tool.com", "phone": "123", "position": "Tester"}})
    print("CREATE result:", res)
    assert res["success"] is True

    # 4. UPDATE (Not Found)
    print("\n[4] UPDATE not found")
    res = update_record.invoke({"entity": "employees", "filters": {"name": "Nonexistent XYZ"}, "data": {"department": "HR"}})
    print("UPDATE not found result:", res)
    assert res["success"] is False

    # 5. UPDATE (Ambiguous)
    print("\n[5] UPDATE ambiguous")
    # create duplicate
    client.table("employees").insert({"name": "Tool Test", "department": "IT", "email": "dup@tool.com", "phone": "123", "position": "Tester"}).execute()
    res = update_record.invoke({"entity": "employees", "filters": {"name": "Tool Test"}, "data": {"department": "HR"}})
    print("UPDATE ambiguous result:", res)
    assert res["success"] is False

    # 6. DELETE (Ambiguous)
    print("\n[6] DELETE ambiguous")
    res = delete_record.invoke({"entity": "employees", "filters": {"name": "Tool Test"}})
    print("DELETE ambiguous result:", res)
    assert res["success"] is False

    # cleanup dup
    client.table("employees").delete().eq("email", "dup@tool.com").execute()

    # 7. UPDATE (Success)
    print("\n[7] UPDATE success")
    res = update_record.invoke({"entity": "employees", "filters": {"name": "Tool Test"}, "data": {"department": "HR"}})
    print("UPDATE success result:", res)
    assert res["success"] is True

    # 8. DELETE (Success)
    print("\n[8] DELETE success")
    res = delete_record.invoke({"entity": "employees", "filters": {"name": "Tool Test"}})
    print("DELETE success result:", res)
    assert res["success"] is True
    
    # 9. DELETE (Not Found)
    print("\n[9] DELETE not found")
    res = delete_record.invoke({"entity": "employees", "filters": {"name": "Tool Test"}})
    print("DELETE not found result:", res)
    assert res["success"] is False

    print("\nALL TOOL TESTS PASSED")

if __name__ == "__main__":
    test_crud_tools()
