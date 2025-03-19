#!/bin/bash

# Create models directory if it doesn't exist
mkdir -p models

# Base URL for face-api.js models
BASE_URL="https://github.com/justadudewhohacks/face-api.js/raw/master/weights"

# List of model files to download
MODEL_FILES=(
  "face_landmark_68_model-shard1"
  "face_landmark_68_model-weights_manifest.json"
  "face_recognition_model-shard1"
  "face_recognition_model-shard2"
  "face_recognition_model-weights_manifest.json"
  "tiny_face_detector_model-shard1"
  "tiny_face_detector_model-weights_manifest.json"
)

# Download each model file
for file in "${MODEL_FILES[@]}"; do
  echo "Downloading $file..."
  curl -L "$BASE_URL/$file" -o "$file"
done

echo "All models downloaded successfully!"
