#!/bin/bash
# ZooLingo Dataset Download Script

set -e

echo "🐾 ZooLingo Dataset Downloader"
echo "================================"

mkdir -p data/training/{dogs,cats,birds}
mkdir -p data/test/{dogs,cats}

echo "✅ Created data directories"

# DEMO-lite (Dog Emotion Dataset)
echo "📥 Downloading DEMO-lite (Dog Emotion Dataset)..."
if [ ! -d "data/training/dogs/demo_lite" ]; then
    git clone https://github.com/DEMO-lite/dog-emotion-dataset.git temp_demo
    mv temp_demo/* data/training/dogs/demo_lite/
    rm -rf temp_demo
    echo "✅ DEMO-lite downloaded"
else
    echo "⏭️  DEMO-lite already exists"
fi

echo ""
echo "📊 Dataset Summary"
echo "=================="
dog_files=$(find data/training/dogs -type f -name "*.wav" -o -name "*.mp3" 2>/dev/null | wc -l)
echo "Dog audio files: $dog_files"
echo ""
echo "✅ Dataset download complete!"