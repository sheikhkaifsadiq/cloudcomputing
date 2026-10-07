import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage
from backend.agent import agent_executor

def test_gemini_single():
    print("Running a single Gemini test...")
    try:
        config = {"configurable": {"thread_id": "test_gemini"}}
        msg = "Show all employees in HR."
        print(f"User: {msg}")
        
        res = agent_executor.invoke({"messages": [HumanMessage(content=msg)], "conversation_id": "test_gemini"}, config)
        
        tool_called = any(getattr(m, "tool_calls", None) for m in res["messages"])
        final_msg = res["messages"][-1].content
        
        print(f"Tool called: {tool_called}")
        print(f"AI: {final_msg}")
        
        if tool_called:
            print("SINGLE GEMINI TEST PASSED")
        else:
            print("SINGLE GEMINI TEST FAILED: No tool called")
            
    except Exception as e:
        print(f"SINGLE GEMINI TEST FAILED: {e}")

if __name__ == "__main__":
    test_gemini_single()
