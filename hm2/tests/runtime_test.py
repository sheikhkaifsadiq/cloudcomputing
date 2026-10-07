import os
import sys
from dotenv import load_dotenv

load_dotenv()

from backend.agent import agent_executor
from langchain_core.messages import HumanMessage

def run_tests():
    print("=== TEST 1: GEMINI CONNECTION ===")
    try:
        config = {"configurable": {"thread_id": "test_thread_1"}}
        result = agent_executor.invoke({
            "messages": [HumanMessage(content="Respond with exactly: HM2 Gemini connection successful")]
        }, config)
        print("Response:", result["messages"][-1].content)
    except Exception as e:
        print("GEMINI CONNECTION FAILED:", e)

    print("\n=== TEST 2: TOOL CALLING (READ) ===")
    try:
        config = {"configurable": {"thread_id": "test_thread_2"}}
        result = agent_executor.invoke({
            "messages": [HumanMessage(content="Show all employees in HR.")]
        }, config)
        for msg in result["messages"]:
            print(msg.__class__.__name__, ":", getattr(msg, "content", ""), getattr(msg, "tool_calls", ""))
    except Exception as e:
        print("TOOL CALLING FAILED:", e)
        
    print("\n=== TEST 3: HITL (DELETE) ===")
    try:
        config = {"configurable": {"thread_id": "test_thread_3"}}
        result = agent_executor.invoke({
            "messages": [HumanMessage(content="Delete Ali Ahmed from HR.")]
        }, config)
        
        state = agent_executor.get_state(config)
        print("Next tasks:", state.next)
        print("Pending action:", state.values.get("pending_action"))
        print("Requires approval:", state.values.get("requires_approval"))
    except Exception as e:
        print("HITL FAILED:", e)

if __name__ == "__main__":
    run_tests()
