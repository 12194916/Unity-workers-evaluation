-- Migration: Switch to native Telegram polls
-- Run this in Supabase SQL Editor

-- Add worker order tracking to polls
ALTER TABLE polls ADD COLUMN IF NOT EXISTS worker_ids_order jsonb;

-- Add telegram_poll_id to poll_messages (maps Telegram poll -> our poll)
ALTER TABLE poll_messages ADD COLUMN IF NOT EXISTS telegram_poll_id text;

-- Index for fast lookup by telegram_poll_id
CREATE INDEX IF NOT EXISTS idx_poll_messages_tg_poll ON poll_messages(telegram_poll_id);
