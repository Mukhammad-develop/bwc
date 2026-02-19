# Brightway Consulting Website

Modern Flask-based website with a beautiful landing page and comprehensive admin panel.

## Features

### Public Website
- 🏠 **Landing Page**: Hero section, services showcase, how it works, testimonials
- 🎓 **Services Page**: Detailed information about all four services
- 📞 **Contact Page**: Multiple contact methods, FAQ section
- 🌐 **Multilingual Support**: English, Uzbek, Russian (matches the bot)
- 📱 **Responsive Design**: Beautiful on desktop, tablet, and mobile

### Admin Panel
- 📊 **Dashboard**: Statistics overview, recent cases
- 📋 **Cases Management**: View, filter, and update all cases
- 👥 **Users Management**: View all registered users
- 🔍 **Case Details**: Full conversation history, documents, user info
- 🔐 **Secure Authentication**: Login system with session management
- 📄 **Real-time Data**: Connected to the bot's SQLite database

## Setup

1. **Install dependencies:**
   ```bash
   cd web
   pip install -r requirements.txt
   ```

2. **Configure environment variables in `../
.env`:**
   ```bash
   FLASK_SECRET_KEY=your-secret-key-here
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your-password-here
   ```

3. **Run the development server:**
   ```bash
   python app.py
   ```

4. **Access the website:**
   - Landing page: http://127.0.0.1:5000/
   - Admin login: http://127.0.0.1:5000/admin/login
   - Default credentials: `admin` / `admin123` (change in production!)

## File Structure

```
web/
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css     # All styles
│   └── js/
│       └── main.js       # Client-side JS
├── templates/
│   ├── base.html         # Base template with navbar/footer
│   ├── index.html        # Landing page
│   ├── services.html     # Services page
│   ├── contact.html      # Contact page
│   └── admin/
│       ├── login.html    # Admin login
│       ├── dashboard.html # Admin dashboard
│       ├── cases.html     # Cases list
│       ├── case_detail.html # Individual case view
│       └── users.html     # Users list
└── README.md
```

## Database

The web app shares the same SQLite database as the Telegram bot (`../tg_bot/bot.db`). This means:
- All bot conversations are visible in the admin panel
- Case updates in the admin panel are reflected in the bot
- No data duplication or sync issues

## Security Notes

⚠️ **Production Checklist:**
1. Change `FLASK_SECRET_KEY` to a random string (use `python -c "import secrets; print(secrets.token_hex(32))"`)
2. Change `ADMIN_PASSWORD` to a strong password
3. Set `app.debug = False` in `app.py`
4. Use a proper web server (gunicorn/uWSGI) instead of Flask's dev server
5. Add HTTPS/SSL certificate
6. Consider using environment-based config (dev/staging/production)
7. Add rate limiting for login attempts
8. Enable CSRF protection for forms

## Deployment

For production deployment, consider:
- **Gunicorn**: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`
- **Nginx**: Reverse proxy for static files and SSL
- **Systemd**: Service file for auto-restart
- **Docker**: Container deployment (see root `Dockerfile` if available)

## Customization

### Update Telegram Bot Link
Search for `https://t.me/YourBotUsername` in templates and replace with your actual bot username.

### Change Colors/Styling
Edit `/static/css/style.css` variables at the top:
```css
:root {
    --primary: #2563eb;
    --secondary: #64748b;
    /* ... more colors ... */
}
```

### Add More Pages
1. Create template in `templates/`
2. Add route in `app.py`
3. Add navigation link in `base.html`

## API Endpoints (for future integration)

The admin panel could be extended with API endpoints for:
- Mobile app integration
- Third-party integrations
- Webhooks
- Reporting/analytics

## Support

For issues or questions, check the main project README or contact the development team.
