#!/bin/bash
# ZooLingo SARVAM MVP Setup Script

set -e

echo "🐾 ZooLingo SARVAM MVP Setup"
echo "=============================="

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create .env
if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Add your API keys to backend/.env:"
    echo "   SARVAM_API_KEY=your_key (https://dashboard.sarvam.ai)"
    echo "   MURF_API_KEY=your_key (https://murf.ai)"
    echo "   DEEPGRAM_API_KEY=your_key (https://deepgram.com)"
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Backend dependencies installed"
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
echo "✅ Frontend dependencies installed"
cd ..

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next Steps:"
echo "1. Add API keys to backend/.env"
echo "2. python backend/train_model.py"
echo "3. python backend/app.py"
echo "4. npm start --prefix frontend"