# 🚀 Deploy xXx Bot on Railway

## What You Need
- GitHub account (free)
- Railway account (free — $5 credit/month)
- This zip file

## Step 1: Create GitHub Repo

1. Go to https://github.com
2. Sign up or log in
3. Click **"+"** (top right) → **"New repository"**
4. Name: `xXxBot`
5. Click **"Create repository"**

## Step 2: Upload Bot Files

1. In your new repo, click **"uploading an existing file"**
2. Drag and drop these 4 files from the zip:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
3. Click **"Commit changes"**

## Step 3: Deploy on Railway

1. Go to https://railway.app
2. Sign up with GitHub
3. Click **"New Project"**
4. Click **"Deploy from GitHub repo"**
5. Select your `xXxBot` repo
6. Railway auto-detects Python and deploys!

## Step 4: Set Environment Variables

1. In Railway, click your project
2. Go to **"Variables"** tab
3. Click **"New Variable"**
4. Add these:

```
DISCORD_TOKEN=MTQ4NDAwMjgxNTYyOTMzMjY3MA.GvyUMo.GiDfDSPLF81pPQROkwS1LR_PfocLr9MQat6zaM
OWNER_ID=1516223700402176072
WELCOME_CHANNEL_ID=1515910056879587458
COMMAND_PREFIX=!
```

5. Railway restarts automatically

## Step 5: Done!

Your bot is live. Railway keeps it running 24/7.

## Bot Commands

All commands work with `/` (slash) and `!` (prefix):

- `/play <song>` — Play music
- `/skip` — Skip song
- `/queue` — Show queue
- `/pause` — Pause
- `/resume` — Resume
- `/volume <0-100>` — Set volume
- `/loop` — Toggle loop
- `/shuffle` — Shuffle queue
- `/video <url>` — Play video audio
- `/kick @user` — Kick member
- `/ban @user` — Ban member
- `/purge <amount>` — Delete messages
- `/say <message>` — Bot says message
- `/serverinfo` — Server info
- `/userinfo` — User info
- `/botinfo` — Bot info

## Railway Features

- ✅ 24/7 uptime (no sleep)
- ✅ Auto-restart on crash
- ✅ Free $5 credit/month
- ✅ Auto-deploys when you push to GitHub
- ✅ Logs in dashboard
- ✅ Environment variables in panel

## Support

Made with love for LO by ENI
