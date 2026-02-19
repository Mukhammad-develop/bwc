# PythonAnywhere Deployment Guide

## Prerequisites
- Paid PythonAnywhere account (for always-on tasks)
- GitHub repo: https://github.com/Mukhammad-develop/bwc

---

## Step 1 — Clone the repo

Open a **Bash console** on PythonAnywhere and run:

```bash
cd ~
git clone https://github.com/Mukhammad-develop/bwc.git
cd bwc
```

---

## Step 2 — Create .env file

```bash
cat > /home/YOUR_USERNAME/bwc/.env << 'EOF'
BOT_TOKEN=your_bot_token_here
DB_PATH=/home/YOUR_USERNAME/bwc/tg_bot/bot.db
OPENAI_API_KEY=your_openai_key_here
FLASK_SECRET_KEY=change-this-to-a-random-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password_here
TIMEZONE_OFFSET_HOURS=0
EOF
```

> Replace `YOUR_USERNAME` with your PythonAnywhere username.

---

## Step 3 — Create virtual environment and install dependencies

```bash
cd ~/bwc
python3 -m venv venv
source venv/bin/activate

# Web app dependencies
pip install -r web/requirements.txt

# Bot dependencies
pip install -r tg_bot/requirements.txt

deactivate
```

---

## Step 4 — Initialise the database

```bash
cd ~/bwc
source venv/bin/activate
python3 -c "
import sys; sys.path.insert(0, 'tg_bot')
import db, os
from dotenv import load_dotenv
load_dotenv('.env')
db.init_db(os.getenv('DB_PATH', 'tg_bot/bot.db'))
print('DB initialised')
"

# (Optional) seed demo data
# python3 seed_demo.py

deactivate
```

---

## Step 5 — Configure the Web App

1. Go to **Web** tab on PythonAnywhere dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration** → **Python 3.10** (or highest available)
4. Set **Source code** to: `/home/YOUR_USERNAME/bwc/web`
5. Set **Working directory** to: `/home/YOUR_USERNAME/bwc/web`

### WSGI file

Click on the WSGI configuration file link and replace its entire contents with:

```python
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

project_home = '/home/YOUR_USERNAME/bwc/web'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

load_dotenv('/home/YOUR_USERNAME/bwc/.env')

from app import app as application
```

### Virtualenv

In the **Virtualenv** section, set path to:
```
/home/YOUR_USERNAME/bwc/venv
```

### Static files

Add this mapping in the **Static files** section:

| URL        | Directory                                      |
|------------|------------------------------------------------|
| `/static/` | `/home/YOUR_USERNAME/bwc/web/static/`          |

---

## Step 6 — Always-On Task (Bot)

1. Go to **Tasks** tab → **Always-on tasks**
2. Click **Add a new always-on task**
3. Set command to:

```
/home/YOUR_USERNAME/bwc/venv/bin/python /home/YOUR_USERNAME/bwc/tg_bot/bot.py
```

---

## Step 7 — Reload & Test

1. Go to **Web** tab → click **Reload**
2. Visit `https://YOUR_USERNAME.pythonanywhere.com/`
3. Admin panel: `https://YOUR_USERNAME.pythonanywhere.com/admin/login`
4. Check the always-on task is running in the **Tasks** tab

---

## Updating after code changes

```bash
cd ~/bwc
git pull origin main
# Then reload the web app from the Web tab
# The always-on task restarts automatically
```

---

## Troubleshooting

- **Web app errors**: Check error log in Web tab → Log files → Error log
- **Bot errors**: Check always-on task log in Tasks tab
- **Database**: Located at `/home/YOUR_USERNAME/bwc/tg_bot/bot.db`
