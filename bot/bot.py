import os
import time
import logging
import threading
from dotenv import load_dotenv
import telebot

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


# ---- /start handler ----

@bot.message_handler(commands=["start"])
def handle_start(message):
    user = message.from_user
    db.register_user(user.id, message.chat.id, user.username or "", user.first_name or "")
    logger.info(f"User registered: {user.first_name} ({user.id})")

    polls = db.get_active_polls()

    if not polls:
        bot.send_message(
            message.chat.id,
            "Unity Employee Evaluation\n\n"
            "Welcome! / Xush kelibsiz!\n\n"
            "No active polls right now.\n"
            "Hozircha faol ovoz berish yo'q.\n\n"
            "You will be notified when a new poll starts.\n"
            "Yangi ovoz berish boshlanganida xabar beramiz.",
        )
        return

    bot.send_message(
        message.chat.id,
        "Unity Employee Evaluation\n\n"
        "Welcome! / Xush kelibsiz!\n\n"
        "Active polls below. You can change your vote anytime.\n"
        "Quyida faol ovozlar. Ovozingizni istalgan vaqt o'zgartirishingiz mumkin.",
    )

    for poll in polls:
        send_poll_to_user(poll, message.chat.id)


# ---- Send native Telegram poll ----

def send_poll_to_user(poll, chat_id):
    """Send a native Telegram poll to a user."""
    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
    workers = db.get_workers_for_category(poll["category_id"])

    if len(workers) < 2:
        logger.warning(f"Skipping poll {category_name}: need at least 2 workers")
        return

    # Skip if already sent to this user for this poll
    if db.poll_already_sent(poll["id"], chat_id):
        return

    month_en = MONTHS_EN[poll["month"]] if 1 <= poll["month"] <= 12 else str(poll["month"])
    month_uz = MONTHS_UZ[poll["month"]] if 1 <= poll["month"] <= 12 else str(poll["month"])

    question = (
        f"Who is the best {category_name} for {month_en} {poll['year']}?\n"
        f"{month_uz} {poll['year']} oyi uchun {category_name} kimga ovoz berasiz?"
    )

    options = [w["name"] for w in workers]
    worker_ids = [w["id"] for w in workers]

    try:
        sent = bot.send_poll(
            chat_id,
            question=question,
            options=options,
            is_anonymous=False,
            allows_multiple_answers=False,
            type="regular",
        )

        # Save worker order on the poll (first time only)
        if not poll.get("worker_ids_order"):
            db.save_worker_ids_order(poll["id"], worker_ids)
            poll["worker_ids_order"] = worker_ids

        # Track message + telegram poll ID mapping
        db.save_poll_message(poll["id"], chat_id, sent.message_id, sent.poll.id)

    except Exception as e:
        logger.warning(f"Could not send poll to {chat_id}: {e}")


# ---- Vote handler (native poll) ----

@bot.poll_answer_handler()
def handle_poll_answer(poll_answer):
    telegram_poll_id = poll_answer.poll_id
    user = poll_answer.user
    option_ids = poll_answer.option_ids

    # Look up our poll via the telegram poll ID
    poll = db.get_poll_by_telegram_poll_id(telegram_poll_id)
    if not poll:
        logger.warning(f"Unknown telegram poll: {telegram_poll_id}")
        return

    poll_id = poll["id"]
    worker_ids_order = poll.get("worker_ids_order") or []

    # User retracted their vote
    if not option_ids:
        db.delete_vote(poll_id, user.id)
        logger.info(f"Vote retracted: {user.first_name} ({user.id})")
        return

    # Map option index to worker ID
    option_index = option_ids[0]
    if option_index >= len(worker_ids_order):
        logger.warning(f"Invalid option index {option_index} for poll {poll_id}")
        return

    worker_id = worker_ids_order[option_index]
    db.upsert_vote(poll_id, worker_id, user.id, user.username or "", user.first_name or "")

    # Find worker name for admin notification
    workers = db.get_workers_for_category(poll["category_id"])
    voted_worker_name = "Unknown"
    for w in workers:
        if w["id"] == worker_id:
            voted_worker_name = w["name"]
            break

    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
    logger.info(f"Vote: {user.first_name} -> {voted_worker_name} ({category_name})")

    # Notify admin
    if ADMIN_TELEGRAM_ID and user.id != ADMIN_TELEGRAM_ID:
        try:
            bot.send_message(
                ADMIN_TELEGRAM_ID,
                f"New Vote\n\n"
                f"Poll: {category_name}\n"
                f"Voter: {user.first_name or 'Unknown'}"
                f"{f' (@{user.username})' if user.username else ''}\n"
                f"Voted for: {voted_worker_name}",
            )
        except Exception as e:
            logger.warning(f"Could not notify admin: {e}")


# ---- Background: broadcast new polls & auto-close after 24h ----

def background_loop():
    while True:
        try:
            # 1. Broadcast new polls to all users
            new_polls = db.get_unbroadcast_polls()
            if new_polls:
                users = db.get_all_users()
                for poll in new_polls:
                    category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
                    logger.info(f"Broadcasting poll: {category_name} to {len(users)} users")

                    # Mark as broadcast FIRST so bot restart won't re-trigger
                    db.mark_poll_broadcast(poll["id"])

                    for user in users:
                        send_poll_to_user(poll, user["chat_id"])
                        time.sleep(0.05)

            # 2. Close expired polls (24h after broadcast)
            expired_polls = db.get_polls_to_expire()
            for poll in expired_polls:
                category_name = poll["categories"]["name"] if poll.get("categories") else "Unknown"
                logger.info(f"Auto-closing poll: {category_name} (24h expired)")

                # Stop native polls on all sent messages
                messages = db.get_poll_messages(poll["id"])
                for msg in messages:
                    try:
                        bot.stop_poll(msg["chat_id"], msg["message_id"])
                    except Exception as e:
                        logger.debug(f"Could not stop poll {msg['message_id']}: {e}")

                db.close_poll(poll["id"])

                # Notify admin
                vote_counts = db.get_vote_counts(poll["id"])
                total_votes = sum(v["count"] for v in vote_counts.values())
                if ADMIN_TELEGRAM_ID:
                    try:
                        bot.send_message(
                            ADMIN_TELEGRAM_ID,
                            f"Poll closed (24h)\n\n"
                            f"{category_name}\n"
                            f"Total votes: {total_votes}",
                        )
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Background loop error: {e}")

        time.sleep(30)


# ---- Main ----

if __name__ == "__main__":
    logger.info("Bot starting...")
    logger.info(f"Admin ID: {ADMIN_TELEGRAM_ID}")

    bg = threading.Thread(target=background_loop, daemon=True)
    bg.start()
    logger.info("Background checker started")

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=["message", "poll_answer"],
            )
        except Exception as e:
            logger.error(f"Bot crashed: {e}. Restarting in 5s...")
            time.sleep(5)
