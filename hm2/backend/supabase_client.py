from supabase import create_client, Client
from backend.config import get_settings

def get_supabase_client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise ValueError("Supabase credentials are not fully configured.")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
