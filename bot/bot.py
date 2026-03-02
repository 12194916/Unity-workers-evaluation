import os
import time
import logging
import threading
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

import database as db

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN must be set in .env")

ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "0"))

bot = telebot.TeleBot(BOT_TOKEN)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MONTHS_EN = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTHS_UZ = [
    "", "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr",
]

# ---- Short ID mapping (Telegram callback_data max 64 bytes) ----
_id_map = {}


def shorten(uuid_str):
    key = uuid_str.replace("-", "")[:8]
    _id_map[key] = uuid_str
    return key


def expand(key):
    return _id_map.get(key, key)


# ---- Message builders ----

def build_poll_keyboard(poll_id, workers):
    markup = InlineKeyboardMarkup(row_width=1)
    sp = shorten(poll_id)
    for w in workers:
        sw = shorten(w["id"])
        markup.add(
            InlineKeyboardButton(
                text=w["name"],
                callback_data=f"v:{sp}:{sw}",
            )
        )
    return markup


def build_poll_text(category_name, month, year, vote_counts, total_votes):
    """Clear bilingual poll question."""
    month_en = MONTHS_EN[month] if 1 <= month <= 12 else str(month)
    month_uz = MONTHS_UZ[month] if 1 <= month <= 12 else str(month)

    lines = [
        f"🏆 *Who is the best {category_name} for {month_en} {year}?*",
        f"🏆 *{month_uz} {year} oyi uchun eng yaxshi {category_name} kim?*",
        "",
        "👇 Tap a name to vote / Ovoz berish uchun ismni bosing:",
        "",
    ]

    if total_votes == 0:
        lines.append("_No votes yet / Hali ovoz berilmagan_")
    else:
        sorted_workers = sorted(vote_counts.values(), key=lambda x: x["count"], reverse=True)
        for i, w in enumerate(sorted_workers):
            bar_length = int((w["count"] / total_votes) * 10) if total_votes > 0 else 0
            bar = "▓" * bar_length + "░" * (10 - bar_length)
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
            lines.append(f"{medal} {w['name']}: {bar} *{w['count']}*")

        lines.append(f"\n📊 Total votes / Jami ovozlar: *{total_votes}*")

    return "\n".join(lines)


def build_closed_text(category_name, month, year, vote_counts, total_votes):
    """Final results after poll closes — no buttons."""
    month_en = MONTHS_EN[month] if 1 <= month <= 12 else str(month)
    month_uz = MONTHS_UZ[month] if 1 <= month <= 12 else str(month)

    lines = [
        f"🔒 *{category_name} — {month_en} {year}*",
        f"Voting closed / Ovoz berish yopildi",
        "",
    ]

    if total_votes == 0:
        lines.append("No votes were cast / Ovoz berilmadi")
    else:
        sorted_workers = sorted(vote_counts.values(), key=lambda x: x["count"], reverse=True)

        # Announce winner
        winner = sorted_workers[0]
        lines.append(f"🏆 *Winner / G'olib: {winner['name']}* ({winner['count']} votes)")
        lines.append("")
        lines.append("Final results / Yakuniy natijalar:")
        lines.append("")

        for i, w in enumerate(sorted_workers):
            bar_length = int((w["count"] / total_votes) * 10) if total_votes > 0 else 0
            bar = "▓" * bar_length + "░" * (10 - bar_length)
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
            lines.append(f"{medal} {w['name']}: {bar} *{w['count']}*")

        lines.append(f"\n📊 Total / Jami: *{total_votes}*")

    return "\n".join(lines)


# ---- /start handler ----

@bot.message_handler(commands=["start"])
def handle_start(message):
    """Register user and show active polls."""
    user = message.from_user

    db.register_user(user.id, message.chat.id, user.username or "", user.first_name or "")
    logger.info(f"User registered: {user.first_name} ({user.id})")

    polls = db.get_active_polls()

    if not polls:
        bot.send_message(
            message.chat.id,
            "👋 *Welcome to Unity Employee Evaluation!*\n"
            "👋 *Unity xodimlarni baholash tizimiga xush kelibsiz!*\n\n"
            "There are no active polls right now.\n"
            "Hozircha faol ovoz berish yo'q.\n\n"
            "You will receive polls automatically when they are created!\n"
            "Yangi ovoz berish yaratilganda sizga avtomatik yuboriladi!",
            parse_mode="Markdown",
        )
        return

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to Unity Employee Evaluation!*\n"
        "👋 *Unity xodimlarni baholash tizimiga xush kelibsiz!*\n\n"
        "Here are the active polls — tap a name to vote:\n"
        "Quyida faol ovoz berishlar — ovoz berish uchun ismni bosing:",
        parse_mode="Markdown",
    )

    for poll in polls:
        send_poll_to_user(poll, message.chat.id)


def send_poll_to_user(poll, chat_id):
    """Send a single poll to a user and track the message."""
    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
    workers = db.get_workers_for_category(poll["category_id"])

    if not workers:
        return

    vote_counts = db.get_vote_counts(poll["id"])
    total_votes = sum(v["count"] for v in vote_counts.values())
    text = build_poll_text(category_name, poll["month"], poll["year"], vote_counts, total_votes)
    keyboard = build_poll_keyboard(poll["id"], workers)

    try:
        sent = bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="Markdown")
        db.save_poll_message(poll["id"], chat_id, sent.message_id)
    except Exception as e:
        logger.warning(f"Could not send poll to {chat_id}: {e}")


# ---- Vote handler ----

@bot.callback_query_handler(func=lambda call: call.data.startswith("v:"))
def handle_vote(call):
    parts = call.data.split(":")
    if len(parts) != 3:
        bot.answer_callback_query(call.id, "Invalid vote.")
        return

    poll_id = expand(parts[1])
    worker_id = expand(parts[2])

    if not db.is_poll_active(poll_id):
        bot.answer_callback_query(
            call.id,
            "⛔ Voting is closed!\n⛔ Ovoz berish yopilgan!",
            show_alert=True,
        )
        return

    user = call.from_user
    db.upsert_vote(poll_id, worker_id, user.id, user.username or "", user.first_name or "")

    # Refresh the message with updated counts
    poll = db.get_poll_by_id(poll_id)
    if not poll:
        bot.answer_callback_query(call.id, "Poll not found.")
        return

    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
    workers = db.get_workers_for_category(poll["category_id"])
    vote_counts = db.get_vote_counts(poll_id)
    total_votes = sum(v["count"] for v in vote_counts.values())

    text = build_poll_text(category_name, poll["month"], poll["year"], vote_counts, total_votes)
    keyboard = build_poll_keyboard(poll_id, workers)

    try:
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.debug(f"Could not edit message: {e}")

    # Find voted worker name
    voted_worker_name = "Unknown"
    for w in workers:
        if w["id"] == worker_id:
            voted_worker_name = w["name"]
            break

    bot.answer_callback_query(call.id, f"✅ You voted for {voted_worker_name}!\n✅ Siz {voted_worker_name} ga ovoz berdingiz!")

    # Notify admin
    if ADMIN_TELEGRAM_ID and user.id != ADMIN_TELEGRAM_ID:
        try:
            bot.send_message(
                ADMIN_TELEGRAM_ID,
                f"🗳 *New Vote / Yangi ovoz*\n\n"
                f"📋 Poll: *{category_name}*\n"
                f"👤 Voter: {user.first_name or 'Unknown'}"
                f"{f' (@{user.username})' if user.username else ''}\n"
                f"✅ Voted for: *{voted_worker_name}*",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")


# ---- Background: broadcast new polls & auto-close after 24h ----

def background_loop():
    """Runs every 30 seconds to broadcast new polls and close expired ones."""
    while True:
        try:
            # 1. Broadcast new polls to all users
            new_polls = db.get_unbroadcast_polls()
            if new_polls:
                users = db.get_all_users()
                for poll in new_polls:
                    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
                    logger.info(f"Broadcasting poll: {category_name} to {len(users)} users")

                    for user in users:
                        send_poll_to_user(poll, user["chat_id"])
                        time.sleep(0.05)  # Rate limit

                    db.mark_poll_broadcast(poll["id"])

            # 2. Close expired polls (24h after creation)
            expired_polls = db.get_polls_to_expire()
            for poll in expired_polls:
                category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
                logger.info(f"Auto-closing poll: {category_name} (24h expired)")

                # Build final results
                vote_counts = db.get_vote_counts(poll["id"])
                total_votes = sum(v["count"] for v in vote_counts.values())
                closed_text = build_closed_text(
                    category_name, poll["month"], poll["year"], vote_counts, total_votes
                )

                # Remove buttons from all sent messages
                messages = db.get_poll_messages(poll["id"])
                for msg in messages:
                    try:
                        bot.edit_message_text(
                            closed_text,
                            chat_id=msg["chat_id"],
                            message_id=msg["message_id"],
                            parse_mode="Markdown",
                        )
                    except Exception as e:
                        logger.debug(f"Could not edit message {msg['message_id']}: {e}")

                # Close poll in DB — this updates the web dashboard too
                db.close_poll(poll["id"])

                # Notify admin
                if ADMIN_TELEGRAM_ID:
                    try:
                        bot.send_message(
                            ADMIN_TELEGRAM_ID,
                            f"🔒 *Poll auto-closed (24h)*\n\n"
                            f"📋 {category_name}\n"
                            f"📊 Total votes: *{total_votes}*",
                            parse_mode="Markdown",
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Background loop error: {e}")

        time.sleep(30)  # Check every 30 seconds


# ---- Main ----

if __name__ == "__main__":
    logger.info("Bot starting... Press Ctrl+C to stop.")
    logger.info(f"Admin ID: {ADMIN_TELEGRAM_ID}")

    bg = threading.Thread(target=background_loop, daemon=True)
    bg.start()
    logger.info("Background checker started (broadcasts new polls, auto-closes after 24h)")

    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Bot crashed: {e}. Restarting in 5s...")
            time.sleep(5)
