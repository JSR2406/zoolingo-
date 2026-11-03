#!/bin/bash
# ZooLingo Dataset Download Script

set -e

echo "🐾 ZooLingo Dataset Downloader"
echo "================================"

mkdir -p data/training/{dogs,cats,birds}
mkdir -p data/test/{dogs,cats}

echo "✅ Created data directories"

# CatMeows dataset (Zenodo)
echo "📥 Downloading CatMeows (cat emotion dataset)..."
if [ ! -d "data/training/cats/catmeows" ]; then
    echo "   Downloading from Zenodo (https://zenodo.org/records/4008297)..."
    echo "   NOTE: Download manually from https://zenodo.org/records/4008297"
    echo "   Extract to: data/training/cats/catmeows/"
else
    echo "   CatMeows already exists"
fi

# Barkopedia dog emotion dataset (Hugging Face)
echo "📥 Downloading Barkopedia (dog emotion dataset)..."
if [ ! -d "data/training/dogs/barkopedia" ]; then
    echo "   Downloading from Hugging Face (codeet/BarkopediaDogEmotionClassification_Data)..."
    echo "   NOTE: Install huggingface_hub and run:"
    echo "   python -c \"from huggingface_hub import snapshot_download; snapshot_download(repo_id='codeet/BarkopediaDogEmotionClassification_Data', local_dir='data/training/dogs/barkopedia')\""
else
    echo "   Barkopedia already exists"
fi

echo ""
echo "📊 Dataset Summary"
echo "=================="
dog_files=$(find data/training/dogs -type f \( -name "*.wav" -o -name "*.mp3" \) 2>/dev/null | wc -l)
cat_files=$(find data/training/cats -type f \( -name "*.wav" -o -name "*.mp3" \) 2>/dev/null | wc -l)
echo "Dog audio files: $dog_files"
echo "Cat audio files: $cat_files"
echo ""
echo "✅ Dataset download script complete (manual download required for Zenodo/HF datasets)"