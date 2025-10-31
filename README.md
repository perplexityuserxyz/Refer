# Telegram Referral Bot

A feature-rich Telegram bot with a credits-based referral system, leaderboard, and comprehensive admin controls.

## Features

### User Features
- 🎁 Earn 5 credits per successful referral
- 🏆 View leaderboard to see top referrers
- 👤 Track personal stats and progress
- 💰 Redeem rewards at 300 credits
- 🔗 Unique referral links for each user

### Admin Features
- 📢 Broadcast messages to all users
- 📊 View comprehensive statistics
- ✅ Add/remove mandatory join channels
- ✏️ Customize welcome message
- 👑 Owner-only commands

## Setup Instructions

1. **Create a Telegram Bot**
   - Open Telegram and search for @BotFather
   - Send `/newbot` and follow the instructions
   - Copy the bot token you receive

2. **Set Bot Token**
   - Go to Replit Secrets (Tools > Secrets)
   - Add a new secret:
     - Key: `BOT_TOKEN`
     - Value: Your bot token from BotFather

3. **Run the Bot**
   - Click the Run button
   - The bot will start automatically

## Commands

### User Commands
- `/start` - Start the bot and get your referral link
- `/profile` - View your profile and stats
- `/leaderboard` - See top 10 referrers
- `/redeem` - Redeem credits for rewards (300 credits required)
- `/help` - Show all available commands

### Admin Commands (Owner Only)
- `/broadcast <message>` - Send a message to all users
- `/stats` - View bot statistics
- `/addchannel <channel_id> <name>` - Add a mandatory join channel
- `/removechannel <channel_id>` - Remove a channel
- `/channels` - List all mandatory channels
- `/setstart <message>` - Set custom welcome message

## How It Works

1. Users start the bot and receive a unique referral link
2. When someone joins using their link, they earn 5 credits
3. Users can track their progress and see their rank
4. At 300 credits, users can redeem for rewards
5. Admins can manage channels, broadcast messages, and view stats

## Owner ID
The bot owner ID is configured as: 7924074157

## Database
The bot uses SQLite to store:
- User information and credits
- Referral relationships
- Redemption history
- Channel requirements
- Bot settings
