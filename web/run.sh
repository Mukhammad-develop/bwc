#!/bin/bash
# Quick start script for Brightway web app

echo "🌟 Starting Brightway Consulting Website..."

# Check if .env exists
if [ ! -f "../.env" ]; then
    echo "❌ Error: .env file not found in project root"
    echo "Create ../env with required variables:"
    echo "  - BOT_TOKEN"
    echo "  - FLASK_SECRET_KEY"
    echo "  - ADMIN_USERNAME"
    echo "  - ADMIN_PASSWORD"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Run the app
echo "🚀 Starting Flask server on port 8080..."
echo ""
python app.py
