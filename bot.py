import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from database import Database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

OWNER_ID = 7924074157
RUPEES_PER_REFERRAL = 5
REDEMPTION_THRESHOLD = 300

db = Database()


async def check_channel_membership(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    channels = db.get_channels()

    if not channels:
        return True

    not_joined = []
    for channel_id, channel_name in channels:
        try:
            member = await context.bot.get_chat_member(chat_id=channel_id,
                                                       user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append((channel_id, channel_name))
        except TelegramError as e:
            logger.error(f"Error checking membership for {channel_id}: {e}")
            continue

    if not_joined:
        keyboard = []
        for channel_id, channel_name in not_joined:
            channel_link = f"https://t.me/{channel_id.replace('@', '')}"
            keyboard.append([
                InlineKeyboardButton(f"Join {channel_name}", url=channel_link)
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ You must join the following channels to use this bot:",
            reply_markup=reply_markup)
        return False

    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name

    if not await check_channel_membership(update, context):
        return

    existing_user = db.get_user(user_id)

    if existing_user:
        start_msg = db.get_start_message()
        referral_link = f"https://t.me/{context.bot.username}?start={existing_user['referral_code']}"

        keyboard = [
            [
                InlineKeyboardButton("💰 My Profile", callback_data="profile"),
                InlineKeyboardButton("🏆 Leaderboard",
                                     callback_data="leaderboard")
            ],
            [
                InlineKeyboardButton(
                    "📤 Share Referral Link",
                    url=
                    f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
                )
            ],
            [
                InlineKeyboardButton(f"💸 Redeem ₹{REDEMPTION_THRESHOLD}",
                                     callback_data="redeem")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"{start_msg}\n\n"
            f"👤 Your Profile:\n"
            f"💰 Balance: ₹{existing_user['credits']}\n"
            f"👥 Total Referrals: {existing_user['total_referrals']}\n\n"
            f"🔗 Your Referral Link:\n{referral_link}\n\n"
            f"Share this link to earn ₹{RUPEES_PER_REFERRAL} per referral!",
            reply_markup=reply_markup)
    else:
        referred_by = None
        if context.args:
            referral_code = context.args[0]
            referred_by = db.get_user_by_referral_code(referral_code)

            if referred_by == user_id:
                await update.message.reply_text(
                    "❌ You cannot use your own referral link!")
                return

        referral_code = db.add_user(user_id, username, first_name, referred_by)

        if referral_code:
            start_msg = db.get_start_message()
            referral_link = f"https://t.me/{context.bot.username}?start={referral_code}"

            welcome_text = f"{start_msg}\n\n"
            if referred_by:
                welcome_text += f"✅ You were referred! Your referrer earned ₹{RUPEES_PER_REFERRAL}.\n\n"

            welcome_text += (f"🔗 Your Referral Link:\n{referral_link}\n\n"
                             f"💰 Earn ₹{RUPEES_PER_REFERRAL} per referral!\n"
                             f"💸 Redeem rewards at ₹{REDEMPTION_THRESHOLD}.")

            keyboard = [[
                InlineKeyboardButton(
                    f"📤 Share & Earn ₹{RUPEES_PER_REFERRAL}",
                    url=
                    f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
                )
            ],
                        [
                            InlineKeyboardButton("💰 My Profile",
                                                 callback_data="profile"),
                            InlineKeyboardButton("🏆 Leaderboard",
                                                 callback_data="leaderboard")
                        ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(welcome_text,
                                            reply_markup=reply_markup)

            if referred_by:
                try:
                    referrer = db.get_user(referred_by)
                    await context.bot.send_message(
                        chat_id=referred_by,
                        text=f"🎉 New Referral!\n\n"
                        f"User: {first_name}\n"
                        f"You earned ₹{RUPEES_PER_REFERRAL}!\n"
                        f"Total Balance: ₹{referrer['credits']}")
                except TelegramError as e:
                    logger.error(f"Could not notify referrer: {e}")


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update, context):
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Please use /start first!")
        return

    rank = db.get_user_rank(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"

    remaining = REDEMPTION_THRESHOLD - user['credits']
    profile_text = (f"👤 Your Profile\n\n"
                    f"Name: {user['first_name']}\n"
                    f"💰 Balance: ₹{user['credits']}\n"
                    f"👥 Total Referrals: {user['total_referrals']}\n"
                    f"🏆 Rank: #{rank}\n\n"
                    f"🔗 Your Referral Link:\n{referral_link}\n\n"
                    f"💡 Earn ₹{remaining} more to redeem!")

    keyboard = [[
        InlineKeyboardButton(
            "📤 Share Referral Link",
            url=
            f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
        )
    ],
                [
                    InlineKeyboardButton("🏆 View Leaderboard",
                                         callback_data="leaderboard"),
                    InlineKeyboardButton("💸 Redeem Now",
                                         callback_data="redeem")
                ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(profile_text, reply_markup=reply_markup)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update, context):
        return

    top_users = db.get_leaderboard(10)

    if not top_users:
        await update.message.reply_text("No users on the leaderboard yet!")
        return

    leaderboard_text = "🏆 Top 10 Referrers 🏆\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, username, first_name,
            referrals) in enumerate(top_users, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        display_name = f"@{username}" if username else first_name
        leaderboard_text += f"{medal} {display_name} - {referrals} referrals (₹{referrals * RUPEES_PER_REFERRAL})\n"

    user = db.get_user(update.effective_user.id)
    referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}" if user else ""

    keyboard = [[
        InlineKeyboardButton(
            "📤 Share & Climb Up!",
            url=
            f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
        )
    ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(leaderboard_text,
                                    reply_markup=reply_markup)


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update, context):
        return

    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        await update.message.reply_text("Please use /start first!")
        return

    if user['credits'] < REDEMPTION_THRESHOLD:
        referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
        keyboard = [[
            InlineKeyboardButton(
                "📤 Share & Earn More",
                url=
                f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
            )
        ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"❌ Insufficient Balance!\n\n"
            f"You have: ₹{user['credits']}\n"
            f"Required: ₹{REDEMPTION_THRESHOLD}\n"
            f"Need: ₹{REDEMPTION_THRESHOLD - user['credits']} more\n\n"
            f"💡 Share your referral link to earn ₹{RUPEES_PER_REFERRAL} per referral!",
            reply_markup=reply_markup)
        return

    redemption_code = db.redeem_credits(user_id, REDEMPTION_THRESHOLD)

    if redemption_code:
        referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
        keyboard = [[
            InlineKeyboardButton(
                "📤 Share & Earn More",
                url=
                f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
            )
        ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎉 Congratulations! 🎉\n\n"
            f"You have successfully achieved the task!\n\n"
            f"Your Reward Code: `{redemption_code}`\n\n"
            f"✅ Redemption Successful!\n"
            f"Amount Used: ₹{REDEMPTION_THRESHOLD}\n\n"
            f"Keep referring to earn more rewards!",
            parse_mode='Markdown',
            reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            "❌ Redemption failed. Please try again later.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = ("📖 Available Commands:\n\n"
                 "👤 User Commands:\n"
                 "/start - Start the bot and get your referral link\n"
                 "/profile - View your profile and stats\n"
                 "/leaderboard - See top referrers\n"
                 "/redeem - Redeem for rewards\n"
                 "/help - Show this help message\n\n"
                 f"💡 Earn ₹{RUPEES_PER_REFERRAL} per referral\n"
                 f"🎁 Redeem at ₹{REDEMPTION_THRESHOLD}")

    if update.effective_user.id == OWNER_ID:
        help_text += (
            "\n\n👑 Admin Commands:\n"
            "/broadcast <message> - Send message to all users\n"
            "/stats - View bot statistics\n"
            "/addchannel <channel_id> <name> - Add mandatory channel\n"
            "/removechannel <channel_id> - Remove channel\n"
            "/channels - List all channels\n"
            "/setstart <message> - Set custom start message")

    await update.message.reply_text(help_text)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = ' '.join(context.args)
    users = db.get_all_users()

    success = 0
    failed = 0

    status_msg = await update.message.reply_text(
        f"📤 Broadcasting to {len(users)} users...")

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except TelegramError as e:
            logger.error(f"Failed to send to {user_id}: {e}")
            failed += 1

    await status_msg.edit_text(f"✅ Broadcast Complete!\n\n"
                               f"Success: {success}\n"
                               f"Failed: {failed}\n"
                               f"Total: {len(users)}")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    stats = db.get_stats()

    stats_text = (f"📊 Bot Statistics\n\n"
                  f"👥 Total Users: {stats['total_users']}\n"
                  f"🔗 Total Referrals: {stats['total_referrals']}\n"
                  f"🎁 Total Redemptions: {stats['total_redemptions']}\n")

    await update.message.reply_text(stats_text)


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /addchannel <channel_id> <channel_name>")
        return

    channel_id = context.args[0]
    channel_name = ' '.join(context.args[1:])

    if db.add_channel(channel_id, channel_name):
        await update.message.reply_text(
            f"✅ Channel added: {channel_name} ({channel_id})")
    else:
        await update.message.reply_text("❌ Channel already exists!")


async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removechannel <channel_id>")
        return

    channel_id = context.args[0]

    if db.remove_channel(channel_id):
        await update.message.reply_text(f"✅ Channel removed: {channel_id}")
    else:
        await update.message.reply_text("❌ Channel not found!")


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    channels = db.get_channels()

    if not channels:
        await update.message.reply_text("No channels configured.")
        return

    channels_text = "📋 Mandatory Channels:\n\n"
    for channel_id, channel_name in channels:
        channels_text += f"• {channel_name} ({channel_id})\n"

    await update.message.reply_text(channels_text)


async def set_start_message(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(
            "❌ This command is only for the bot owner!")
        return

    if not context.args:
        await update.message.reply_text("Usage: /setstart <message>")
        return

    message = ' '.join(context.args)
    db.set_start_message(message)

    await update.message.reply_text(
        f"✅ Start message updated!\n\nNew message:\n{message}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "profile":
        user = db.get_user(user_id)
        if not user:
            await query.message.reply_text("Please use /start first!")
            return

        rank = db.get_user_rank(user_id)
        referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
        remaining = REDEMPTION_THRESHOLD - user['credits']

        profile_text = (f"👤 Your Profile\n\n"
                        f"Name: {user['first_name']}\n"
                        f"💰 Balance: ₹{user['credits']}\n"
                        f"👥 Total Referrals: {user['total_referrals']}\n"
                        f"🏆 Rank: #{rank}\n\n"
                        f"🔗 Your Referral Link:\n{referral_link}\n\n"
                        f"💡 Earn ₹{remaining} more to redeem!")

        keyboard = [[
            InlineKeyboardButton(
                "📤 Share Referral Link",
                url=
                f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
            )
        ],
                    [
                        InlineKeyboardButton("🏆 View Leaderboard",
                                             callback_data="leaderboard"),
                        InlineKeyboardButton("💸 Redeem Now",
                                             callback_data="redeem")
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(profile_text, reply_markup=reply_markup)

    elif query.data == "leaderboard":
        top_users = db.get_leaderboard(10)

        if not top_users:
            await query.message.edit_text("No users on the leaderboard yet!")
            return

        leaderboard_text = "🏆 Top 10 Referrers 🏆\n\n"

        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, username, first_name,
                referrals) in enumerate(top_users, 1):
            medal = medals[i - 1] if i <= 3 else f"{i}."
            display_name = f"@{username}" if username else first_name
            leaderboard_text += f"{medal} {display_name} - {referrals} referrals (₹{referrals * RUPEES_PER_REFERRAL})\n"

        user = db.get_user(query.from_user.id)
        referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}" if user else ""

        keyboard = [[
            InlineKeyboardButton(
                "📤 Share & Climb Up!",
                url=
                f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
            )
        ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(leaderboard_text,
                                      reply_markup=reply_markup)

    elif query.data == "redeem":
        user = db.get_user(user_id)

        if not user:
            await query.message.reply_text("Please use /start first!")
            return

        if user['credits'] < REDEMPTION_THRESHOLD:
            referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
            keyboard = [[
                InlineKeyboardButton(
                    "📤 Share & Earn More",
                    url=
                    f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
                )
            ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(
                f"❌ Insufficient Balance!\n\n"
                f"You have: ₹{user['credits']}\n"
                f"Required: ₹{REDEMPTION_THRESHOLD}\n"
                f"Need: ₹{REDEMPTION_THRESHOLD - user['credits']} more\n\n"
                f"💡 Share your referral link to earn ₹{RUPEES_PER_REFERRAL} per referral!",
                reply_markup=reply_markup)
            return

        redemption_code = db.redeem_credits(user_id, REDEMPTION_THRESHOLD)

        if redemption_code:
            referral_link = f"https://t.me/{context.bot.username}?start={user['referral_code']}"
            keyboard = [[
                InlineKeyboardButton(
                    "📤 Share & Earn More",
                    url=
                    f"https://t.me/share/url?url={referral_link}&text=Join this amazing bot and earn money! ₹{RUPEES_PER_REFERRAL} per referral!"
                )
            ], [InlineKeyboardButton("💰 My Profile", callback_data="profile")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(
                f"🎉 Congratulations! 🎉\n\n"
                f"You have successfully achieved the task!\n\n"
                f"Your Reward Code: `{redemption_code}`\n\n"
                f"✅ Redemption Successful!\n"
                f"Amount Used: ₹{REDEMPTION_THRESHOLD}\n\n"
                f"Keep referring to earn more rewards!",
                parse_mode='Markdown',
                reply_markup=reply_markup)
        else:
            await query.message.reply_text(
                "❌ Redemption failed. Please try again later.")


def main():
    token = os.getenv('BOT_TOKEN')

    if not token:
        logger.error("BOT_TOKEN not found in environment variables!")
        print("❌ ERROR: BOT_TOKEN not set!")
        print("Please set your Telegram bot token:")
        print("1. Create a bot with @BotFather on Telegram")
        print("2. Add BOT_TOKEN to Replit Secrets")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("addchannel", add_channel))
    application.add_handler(CommandHandler("removechannel", remove_channel))
    application.add_handler(CommandHandler("channels", list_channels))
    application.add_handler(CommandHandler("setstart", set_start_message))
    application.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot is starting...")
    print("🤖 Bot is running! Press Ctrl+C to stop.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
