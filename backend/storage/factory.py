import os

from storage.base import ScanStore
from storage.memory import MemoryStore
from storage.supabase_store import SupabaseStore

_store: ScanStore | None = None


def is_store_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def storage_name() -> str:
    return "supabase" if is_store_configured() else "memory"


def get_store() -> ScanStore:
    global _store
    if _store is None:
        if is_store_configured():
            _store = SupabaseStore(
                os.getenv("SUPABASE_URL"),
                os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
            )
        else:
            _store = MemoryStore()
    return _store