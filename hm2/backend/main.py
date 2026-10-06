import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from backend.agent import agent_executor, resume_workflow
from backend.models import (
    HealthResponse, ChatRequest, ChatResponse,
    HitlApproveRequest, HitlDeclineRequest, HitlDetailsRequest,
    HistoryResponse, Action, HistoryItem
)
from backend.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="HM2 Backend API")


def get_action_from_result(result):
    if result.get("pending_action"):
        action_data = result["pending_action"]
        return Action(
            operation=action_data["name"].replace("_record", ""),
            entity="employee",
            filters=action_data.get("args", {}).get("filters", {}),
            data=action_data.get("args", {}).get("data", {})
        )
    return None

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "https://hm2.kaifsadiq.eu.cc",
        "https://cloudcomputing-five-mu.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    logger.info("Health check endpoint called")
    return HealthResponse(status="ok", message="Backend is running")

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    logger.info(f"Chat request received: {request.message}")
    config = {"configurable": {"thread_id": request.conversation_id}}
    
    try:
        # Run the graph
        result = agent_executor.invoke(
            {"messages": [HumanMessage(content=request.message)], "conversation_id": request.conversation_id},
            config
        )
        
        last_msg = result["messages"][-1]
        action = get_action_from_result(result)
            
        return ChatResponse(
            message=last_msg.content if hasattr(last_msg, "content") and last_msg.content else "Processing your request...",
            status=result.get("status", "completed"),
            action=action,
            requires_approval=result.get("requires_approval", False)
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hitl/approve", response_model=ChatResponse)
def hitl_approve(request: HitlApproveRequest):
    logger.info("HITL approved")
    try:
        result = resume_workflow(request.conversation_id, action_approved=True)
        last_msg = result["messages"][-1]
        return ChatResponse(
            message=last_msg.content,
            status=result.get("status", "completed"),
            action=get_action_from_result(result),
            requires_approval=result.get("requires_approval", False)
        )
    except Exception as e:
        logger.error(f"Error resuming workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/hitl/decline", response_model=ChatResponse)
def hitl_decline(request: HitlDeclineRequest):
    logger.info("HITL declined")
    try:
        result = resume_workflow(request.conversation_id, action_approved=False)
        last_msg = result["messages"][-1]
        return ChatResponse(
            message=last_msg.content,
            status=result.get("status", "completed"),
            action=get_action_from_result(result),
            requires_approval=result.get("requires_approval", False)
        )
    except Exception as e:
        logger.error(f"Error resuming workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/hitl/details", response_model=ChatResponse)
def hitl_details(request: HitlDetailsRequest):
    logger.info("HITL details provided")
    try:
        result = resume_workflow(request.conversation_id, action_approved=False, additional_details=request.details)
        last_msg = result["messages"][-1]
        return ChatResponse(
            message=last_msg.content,
            status=result.get("status", "completed"),
            action=get_action_from_result(result),
            requires_approval=result.get("requires_approval", False)
        )
    except Exception as e:
        logger.error(f"Error resuming workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))

from backend.supabase_client import get_supabase_client

@app.get("/api/history", response_model=HistoryResponse)
def get_history():
    logger.info("History requested")
    try:
        client = get_supabase_client()
        response = client.table("operation_history").select("*").order("timestamp", desc=True).limit(50).execute()
        history_items = []
        for row in response.data:
            history_items.append(HistoryItem(
                id=str(row["id"]),
                timestamp=row["timestamp"],
                operation=row["operation"],
                entity=row["entity"],
                target=row["target"],
                status=row["status"],
                result=row["result"]
            ))
        return HistoryResponse(history=history_items)
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch history")
