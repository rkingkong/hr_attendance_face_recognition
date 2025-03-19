# Face-API.js Models

This directory should contain the models required by face-api.js for face detection, landmarks, and recognition.

## Required Models

Place the following model files in this directory:

- face_landmark_68_model-shard1
- face_landmark_68_model-weights_manifest.json
- face_recognition_model-shard1
- face_recognition_model-shard2
- face_recognition_model-weights_manifest.json
- tiny_face_detector_model-shard1
- tiny_face_detector_model-weights_manifest.json

## How to Obtain the Models

You can download the models from the official face-api.js repository:

1. Visit: https://github.com/justadudewhohacks/face-api.js/tree/master/weights
2. Download each required model file
3. Place them in this directory

Alternatively, you can use a script to automatically download all required models:

```bash
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
  curl -L "$BASE_URL/$file" -o "models/$file"
done

echo "All models downloaded successfully!"
```

Save this as `download_models.sh` and run it to download all required models.
