import operator
import json
from typing import Annotated, TypedDict, List, Dict, Any, Union, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from backend.llm import get_llm
from backend.crud_tools import tools, _format_target
from backend.logger import get_logger
from backend.supabase_client import get_supabase_client

logger = get_logger(__name__)

DESTRUCTIVE_TOOLS = {"delete_record"}

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    requires_approval: bool
    pending_action: Optional[Dict[str, Any]]
    conversation_id: str
    status: str

SYSTEM_PROMPT = """You are a senior HR database assistant.
You help users manage employee records using tools.
The database entity is 'employees' (fields: name, department, email, phone, position).

Available Tools:
- get_records: Fetch existing records. Use this to find information or verify a record exists/is unique BEFORE updating or deleting.
- create_record: Add a new employee. You MUST have all required fields (name, department, email, phone, position) first.
- update_record: Modify an existing employee. Always use get_records first to confirm a unique match.
- delete_record: Delete an employee. Always use get_records first to confirm a unique match. NEVER call delete_record on the same turn as get_records.

Rules:
1. For DELETE or UPDATE: FIRST call get_records to verify the employee exists and is uniquely identified. Then (on the next turn) call the mutation tool.
2. If multiple records match → ask the user to clarify (e.g. which department).
3. If no records match → tell the user the employee was not found.
4. Do NOT guess missing fields. Ask the user for missing create fields.
5. Never claim a mutation succeeded unless the tool returned success.
6. If the user request is ambiguous, ask for clarification before any mutation.
7. IMPORTANT: Never call delete_record in the same response as get_records. Always get first, then decide.
8. CRITICAL: If a tool just executed successfully (like update_record), your response MUST confirm the success to the user. NEVER ignore a successful tool result, and NEVER ask for clarification about a request you just successfully performed in the database.
"""


def record_history(conversation_id: str, operation: str, entity: str, target: str, status: str, result: str):
    """Write an entry to operation_history. Silently fails to not break the main flow."""
    try:
        client = get_supabase_client()
        client.table("operation_history").insert({
            "conversation_id": conversation_id,
            "operation": operation,
            "entity": entity,
            "target": target,
            "status": status,
            "result": result
        }).execute()
    except Exception as e:
        logger.error(f"Failed to record history: {e}")


def process_message(state: AgentState):
    """Invoke the LLM and determine if any destructive tool is requested."""
    llm = get_llm().bind_tools(tools)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    requires_approval = False
    pending_action = None

    if response.tool_calls:
        # Collect tool call names in this response
        tool_names = [tc["name"] for tc in response.tool_calls]

        # Critical safety rule: if BOTH get_records AND delete_record appear in
        # the same response, we must NOT route to destructive node.
        # Instead, strip the delete_record call and only execute get_records first.
        # This forces LLM to see the read result before deciding to delete.
        has_safe = any(n not in DESTRUCTIVE_TOOLS for n in tool_names)
        has_destructive = any(n in DESTRUCTIVE_TOOLS for n in tool_names)

        if has_destructive and has_safe:
            # Remove destructive calls from this response — force safe-first
            filtered_calls = [tc for tc in response.tool_calls if tc["name"] not in DESTRUCTIVE_TOOLS]
            # Rebuild the AI message without the destructive tool calls
            response = AIMessage(
                content=response.content,
                tool_calls=filtered_calls
            )
            logger.info("Safety gate: removed delete_record from mixed response — read first")
        elif has_destructive and not has_safe:
            # Pure destructive — set approval flag
            for tc in response.tool_calls:
                if tc["name"] in DESTRUCTIVE_TOOLS:
                    requires_approval = True
                    pending_action = tc
                    break

    status = "completed"
    if requires_approval:
        status = "approval_required"
    elif not response.tool_calls:
        # Check if the previous message was a tool message with an error
        last_msg = state["messages"][-1] if state["messages"] else None
        if isinstance(last_msg, ToolMessage):
            try:
                parsed = json.loads(last_msg.content)
                if parsed.get("success") is False:
                    if "decline" in str(parsed.get("error", "")).lower():
                        status = "cancelled"
                    else:
                        status = "failed"
            except:
                if "error" in last_msg.content.lower():
                    status = "failed"


    return {
        "messages": [response],
        "requires_approval": requires_approval,
        "pending_action": pending_action,
        "status": status
    }


def safety_gate(state: AgentState):
    """Route to the correct next node."""
    if state.get("requires_approval"):
        return "execute_destructive_tools"
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "execute_safe_tools"
    return END


def execute_safe_tools(state: AgentState):
    """Execute all non-destructive tool calls and return ToolMessages."""
    last_msg = state["messages"][-1]
    tool_msgs = []
    tool_map = {t.name: t for t in tools}
    conversation_id = state["conversation_id"]

    status = "completed"
    for tc in last_msg.tool_calls:
        if tc["name"] in DESTRUCTIVE_TOOLS:
            continue  # Should not happen due to safety_gate, but guard anyway
        tool_fn = tool_map.get(tc["name"])
        if tool_fn:
            logger.info(f"Executing safe tool: {tc['name']} with args {tc['args']}")
            try:
                result = tool_fn.invoke(tc["args"])
                tool_msgs.append(ToolMessage(content=json.dumps(result), tool_call_id=tc["id"]))
                target = _format_target(tc["args"].get("filters") or tc["args"].get("data"))
                if result.get("success") is True:
                    record_history(conversation_id, tc["name"].replace("_record", ""), "employee", target, "completed", "Success")
                else:
                    status = "failed"
                    record_history(conversation_id, tc["name"].replace("_record", ""), "employee", target, "failed", result.get("error", "Unknown error"))
            except Exception as e:
                status = "failed"
                tool_msgs.append(ToolMessage(content=json.dumps({"error": str(e)}), tool_call_id=tc["id"]))
                record_history(conversation_id, tc["name"].replace("_record", ""), "employee", str(tc["args"]), "failed", str(e))

    return {"messages": tool_msgs, "status": status}


def execute_destructive_tools(state: AgentState):
    """Interrupt execution, wait for user decision, then apply it."""
    pending_action = state.get("pending_action")
    if not pending_action:
        return {"messages": []}

    filters = pending_action["args"].get("filters", {})
    target_str = _format_target(filters)

    # Pause and surface the approval request
    decision_data = interrupt({
        "type": "approval_required",
        "operation": "delete",
        "entity": "employee",
        "target": target_str
    })

    decision = decision_data.get("decision")

    if decision == "details":
        details = decision_data.get("details", "")
        logger.info(f"HITL: user provided additional details: {details}")
        return {
            "messages": [HumanMessage(content=f"Additional details provided: {details}. Please re-evaluate the request from the beginning.")],
            "requires_approval": False,
            "pending_action": None
        }

    tool_map = {t.name: t for t in tools}
    tool_fn = tool_map.get(pending_action["name"])
    conversation_id = state["conversation_id"]

    status = "completed"
    if decision == "approve":
        logger.info(f"HITL: approved → executing {pending_action['name']}")
        try:
            result = tool_fn.invoke(pending_action["args"])
            msg = ToolMessage(content=json.dumps(result), tool_call_id=pending_action["id"])
            if result.get("success") is True:
                record_history(conversation_id, "delete", "employee", target_str, "completed", "Approved and executed")
            else:
                status = "failed"
                record_history(conversation_id, "delete", "employee", target_str, "failed", result.get("error", "Unknown error"))
        except Exception as e:
            status = "failed"
            msg = ToolMessage(content=json.dumps({"error": str(e)}), tool_call_id=pending_action["id"])
            record_history(conversation_id, "delete", "employee", target_str, "failed", str(e))
        return {"messages": [msg], "requires_approval": False, "pending_action": None, "status": status}
    else:
        logger.info("HITL: declined")
        msg = ToolMessage(
            content=json.dumps({"success": False, "error": "User declined the operation. It was cancelled."}),
            tool_call_id=pending_action["id"]
        )
        record_history(conversation_id, "delete", "employee", target_str, "cancelled", "User declined")
        return {"messages": [msg], "requires_approval": False, "pending_action": None, "status": "cancelled"}


# ──────────────────────────────────────────────────────────────────────────────
# Graph construction
# ──────────────────────────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)

workflow.add_node("process_message", process_message)
workflow.add_node("execute_safe_tools", execute_safe_tools)
workflow.add_node("execute_destructive_tools", execute_destructive_tools)

workflow.add_edge(START, "process_message")

workflow.add_conditional_edges(
    "process_message",
    safety_gate,
    {
        "execute_destructive_tools": "execute_destructive_tools",
        "execute_safe_tools": "execute_safe_tools",
        END: END
    }
)

workflow.add_edge("execute_safe_tools", "process_message")
workflow.add_edge("execute_destructive_tools", "process_message")

memory = MemorySaver()
agent_executor = workflow.compile(checkpointer=memory)


def resume_workflow(conversation_id: str, action_approved: bool, additional_details: str = None):
    """Resume a paused LangGraph workflow after HITL decision."""
    config = {"configurable": {"thread_id": conversation_id}}

    if additional_details:
        return agent_executor.invoke(Command(resume={"decision": "details", "details": additional_details}), config)

    if action_approved:
        return agent_executor.invoke(Command(resume={"decision": "approve"}), config)
    else:
        return agent_executor.invoke(Command(resume={"decision": "decline"}), config)
