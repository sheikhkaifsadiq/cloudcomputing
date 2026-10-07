from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class HealthResponse(BaseModel):
    status: str
    message: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: str

class Action(BaseModel):
    operation: str
    entity: str
    filters: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: str
    status: str
    action: Optional[Action] = None
    requires_approval: bool = False

class HitlApproveRequest(BaseModel):
    conversation_id: str

class HitlDeclineRequest(BaseModel):
    conversation_id: str

class HitlDetailsRequest(BaseModel):
    conversation_id: str
    details: str

class HistoryItem(BaseModel):
    id: str
    timestamp: str
    operation: str
    entity: str
    target: str
    status: str
    result: str

class HistoryResponse(BaseModel):
    history: List[HistoryItem]
