from typing import Dict, Any, Optional
from langchain_core.tools import tool
from backend.supabase_client import get_supabase_client
from backend.logger import get_logger

logger = get_logger(__name__)

# Allowed entities — prevents LLM from accessing arbitrary tables
ALLOWED_ENTITIES = {"employees"}

REQUIRED_EMPLOYEE_FIELDS = {"name", "department", "email", "phone", "position"}


def _validate_entity(entity: str) -> Optional[str]:
    """Return an error string if entity is not allowed, else None."""
    if entity not in ALLOWED_ENTITIES:
        return f"Entity '{entity}' is not accessible. Allowed entities: {', '.join(ALLOWED_ENTITIES)}."
    return None


def _format_target(filters: Optional[Dict[str, Any]]) -> str:
    """Convert filters dict to a human-readable target string."""
    if not filters:
        return "all records"
    parts = []
    if "name" in filters:
        parts.append(filters["name"])
    if "department" in filters:
        parts.append(filters["department"])
    if parts:
        return " · ".join(parts)
    return " · ".join(f"{k}: {v}" for k, v in filters.items())


def _get_records_raw(entity: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Internal direct get, used by safety checks."""
    client = get_supabase_client()
    query = client.table(entity).select("*")
    if filters:
        for k, v in filters.items():
            query = query.eq(k, v)
    response = query.execute()
    return {"success": True, "data": response.data, "count": len(response.data)}


# ──────────────────────────────────────────────────────────────────────────────
# LangChain Tools
# ──────────────────────────────────────────────────────────────────────────────

@tool
def create_record(entity: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new database record. Use ONLY for employees. Required fields: name, department, email, phone, position. If any field is missing, do NOT call this tool — instead ask the user for the missing information."""
    err = _validate_entity(entity)
    if err:
        return {"success": False, "error": err, "count": 0, "data": []}

    # Validate required fields
    missing = REQUIRED_EMPLOYEE_FIELDS - set(data.keys())
    if missing:
        return {"success": False, "error": f"Missing required fields: {', '.join(sorted(missing))}. Please ask the user to provide them.", "count": 0, "data": []}

    try:
        client = get_supabase_client()
        logger.info(f"Creating {entity} with data: {data}")
        response = client.table(entity).insert(data).execute()
        return {"success": True, "data": response.data, "count": len(response.data) if response.data else 0}
    except Exception as e:
        logger.error(f"Error creating record: {e}")
        return {"success": False, "error": str(e), "count": 0, "data": []}


@tool
def get_records(entity: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch existing employee records. Optionally filter by name, department, email, phone, or position. Use this to answer questions about data or to verify a record exists before updating/deleting."""
    err = _validate_entity(entity)
    if err:
        return {"success": False, "error": err, "count": 0, "data": []}

    try:
        result = _get_records_raw(entity, filters)
        logger.info(f"Getting {entity} with filters: {filters} -> {result['count']} results")
        return result
    except Exception as e:
        logger.error(f"Error fetching records: {e}")
        return {"success": False, "error": str(e), "count": 0, "data": []}


@tool
def update_record(entity: str, filters: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing employee record. Provide filters to identify the employee (e.g. name + department). IMPORTANT: you must verify exactly 1 match exists before calling this tool. If 0 or 2+ matches, do not update."""
    err = _validate_entity(entity)
    if err:
        return {"success": False, "error": err, "count": 0, "data": []}

    try:
        # Safety: verify exactly one match before updating
        check = _get_records_raw(entity, filters)
        count = check["count"]
        if count == 0:
            return {"success": False, "error": f"No {entity} found matching {_format_target(filters)}. Cannot update.", "count": 0, "data": []}
        if count > 1:
            return {"success": False, "error": f"Ambiguous: {count} {entity} match {_format_target(filters)}. Please provide more specific filters.", "count": 0, "data": []}

        client = get_supabase_client()
        logger.info(f"Updating {entity} with filters: {filters}, data: {data}")
        query = client.table(entity).update(data)
        for k, v in filters.items():
            query = query.eq(k, v)
        response = query.execute()
        return {"success": True, "data": response.data, "count": len(response.data) if response.data else 0}
    except Exception as e:
        logger.error(f"Error updating record: {e}")
        return {"success": False, "error": str(e), "count": 0, "data": []}


@tool
def delete_record(entity: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """Delete an employee record. Provide filters to uniquely identify the record. IMPORTANT: verify exactly 1 match exists. If 0 matches → not found. If 2+ matches → ambiguous. This tool must NEVER be called without exact single-record identification."""
    err = _validate_entity(entity)
    if err:
        return {"success": False, "error": err, "count": 0, "data": []}

    try:
        # Safety: verify exactly one match before deleting
        check = _get_records_raw(entity, filters)
        count = check["count"]
        if count == 0:
            return {"success": False, "error": f"No {entity} found matching {_format_target(filters)}. Nothing to delete.", "count": 0, "data": []}
        if count > 1:
            return {"success": False, "error": f"Ambiguous: {count} {entity} match {_format_target(filters)}. Please specify more details (e.g. department).", "count": 0, "data": []}

        client = get_supabase_client()
        logger.info(f"Deleting {entity} with filters: {filters}")
        query = client.table(entity).delete()
        for k, v in filters.items():
            query = query.eq(k, v)
        response = query.execute()
        return {"success": True, "data": response.data, "count": len(response.data) if response.data else 0}
    except Exception as e:
        logger.error(f"Error deleting record: {e}")
        return {"success": False, "error": str(e), "count": 0, "data": []}


tools = [create_record, get_records, update_record, delete_record]
