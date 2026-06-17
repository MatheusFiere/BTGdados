import os
from supabase import create_client, Client
import dotenv
import logging

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    dotenv.load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError("Supabase URL or KEY not set in environment variables")

    return create_client(url, key)


if __name__ == "__main__":
    supabase = get_supabase_client()
    print("Supabase client connected successfully")
