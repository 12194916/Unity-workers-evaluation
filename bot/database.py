import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")

supabase = create_client(url, key)


# ---- Bot Users ----

def register_user(telegram_id, chat_id, username, first_name):
    """Save or update a user who pressed /start."""
    supabase.table("bot_users").upsert(
        {
            "telegram_id": telegram_id,
            "chat_id": chat_id,
            "username": username or "",
            "first_name": first_name or "",
        },
        on_conflict="telegram_id",
    ).execute()


def get_all_users():
    """Get all registered bot users."""
    res = supabase.table("bot_users").select("*").execute()
    return res.data or []


# ---- Polls ----

def get_active_polls():
    """Get all active polls with their category names."""
    res = supabase.table("polls").select("*, categories(name)").eq("status", "active").execute()
    return res.data or []


def get_unbroadcast_polls():
    """Get active polls that haven't been sent to users yet."""
    res = (
        supabase.table("polls")
        .select("*, categories(name)")
        .eq("status", "active")
        .is_("broadcast_at", "null")
        .execute()
    )
    return res.data or []


def mark_poll_broadcast(poll_id):
    """Mark a poll as broadcast."""
    supabase.table("polls").update(
        {"broadcast_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", poll_id).execute()


def save_worker_ids_order(poll_id, worker_ids):
    """Save the ordered list of worker IDs for a poll."""
    supabase.table("polls").update(
        {"worker_ids_order": worker_ids}
    ).eq("id", poll_id).execute()


def get_polls_to_expire():
    """Get active polls older than 24 hours (from created_at or broadcast_at)."""
    res = (
        supabase.table("polls")
        .select("*, categories(name)")
        .eq("status", "active")
        .execute()
    )
    polls = res.data or []
    now = datetime.now(timezone.utc)
    expired = []
    for p in polls:
        ref_time_str = p.get("broadcast_at") or p.get("created_at")
        if not ref_time_str:
            continue
        ref_time = datetime.fromisoformat(ref_time_str.replace("Z", "+00:00"))
        diff = (now - ref_time).total_seconds()
        if diff >= 24 * 3600:
            expired.append(p)
    return expired


def close_poll(poll_id):
    """Close a poll."""
    supabase.table("polls").update(
        {"status": "closed", "closed_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", poll_id).execute()


def get_poll_by_id(poll_id):
    """Get a single poll with category info."""
    res = supabase.table("polls").select("*, categories(name)").eq("id", poll_id).execute()
    return res.data[0] if res.data else None


def is_poll_active(poll_id):
    """Check if a poll is still active."""
    res = supabase.table("polls").select("status").eq("id", poll_id).execute()
    if res.data:
        return res.data[0]["status"] == "active"
    return False


# ---- Poll Messages ----

def save_poll_message(poll_id, chat_id, message_id, telegram_poll_id):
    """Track a poll message sent to a user, with telegram poll ID mapping."""
    supabase.table("poll_messages").insert(
        {
            "poll_id": poll_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "telegram_poll_id": telegram_poll_id,
        }
    ).execute()


def get_poll_messages(poll_id):
    """Get all messages sent for a poll."""
    res = supabase.table("poll_messages").select("*").eq("poll_id", poll_id).execute()
    return res.data or []


def poll_already_sent(poll_id, chat_id):
    """Check if a poll was already sent to this chat."""
    res = (
        supabase.table("poll_messages")
        .select("id")
        .eq("poll_id", poll_id)
        .eq("chat_id", chat_id)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def clear_poll_messages(poll_id):
    """Remove old poll message records so poll can be re-sent."""
    supabase.table("poll_messages").delete().eq("poll_id", poll_id).execute()


def get_poll_by_telegram_poll_id(telegram_poll_id):
    """Find our poll by the Telegram native poll ID."""
    res = (
        supabase.table("poll_messages")
        .select("poll_id, polls(*, categories(name))")
        .eq("telegram_poll_id", telegram_poll_id)
        .limit(1)
        .execute()
    )
    if res.data:
        poll_data = res.data[0].get("polls")
        return poll_data
    return None


# ---- Workers ----

def get_workers_for_category(category_id):
    """Get all workers in a category, ordered by name."""
    res = (
        supabase.table("workers")
        .select("*")
        .eq("category_id", category_id)
        .order("name", desc=False)
        .execute()
    )
    return res.data or []


# ---- Votes ----

def get_vote_counts(poll_id):
    """Get vote counts per worker for a poll."""
    res = (
        supabase.table("votes")
        .select("worker_id, workers(name)")
        .eq("poll_id", poll_id)
        .execute()
    )
    votes = res.data or []

    counts = {}
    for v in votes:
        wid = v["worker_id"]
        wname = v["workers"]["name"] if v.get("workers") else "Unknown"
        if wid not in counts:
            counts[wid] = {"name": wname, "count": 0}
        counts[wid]["count"] += 1

    return counts


def upsert_vote(poll_id, worker_id, voter_telegram_id, voter_username, voter_first_name):
    """Insert or update a vote (one vote per user per poll)."""
    existing = (
        supabase.table("votes")
        .select("id")
        .eq("poll_id", poll_id)
        .eq("voter_telegram_id", voter_telegram_id)
        .execute()
    )

    if existing.data:
        supabase.table("votes").update(
            {
                "worker_id": worker_id,
                "voter_username": voter_username,
                "voter_first_name": voter_first_name,
                "voted_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("votes").insert(
            {
                "poll_id": poll_id,
                "worker_id": worker_id,
                "voter_telegram_id": voter_telegram_id,
                "voter_username": voter_username,
                "voter_first_name": voter_first_name,
            }
        ).execute()


def delete_vote(poll_id, voter_telegram_id):
    """Remove a vote (when user retracts in native poll)."""
    supabase.table("votes").delete().eq(
        "poll_id", poll_id
    ).eq(
        "voter_telegram_id", voter_telegram_id
    ).execute()
