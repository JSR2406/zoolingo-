#!/bin/bash

echo "🐾 ZooLingo Setup Script 🐾"

# Check for .env
if [ ! -f backend/.env ]; then
    echo "⚠️  backend/.env not found! Creating from example..."
    echo "MURF_API_KEY=your_key_here" > backend/.env
    echo "DEEPGRAM_API_KEY=your_key_here" >> backend/.env
    echo "Please update backend/.env with your real API keys."
fi

echo "🚀 Building and starting containers..."
docker-compose up --build -d

echo "✅ ZooLingo is running!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8000"
