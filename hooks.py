# -*- coding: utf-8 -*-
import os
import logging
from odoo import api, SUPERUSER_ID
from odoo.tools import config

_logger = logging.getLogger(__name__)

def _ensure_face_models_directory(cr, registry):
    """Create the face models directory if it doesn't exist"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Get module path
    module_path = os.path.dirname(os.path.abspath(__file__))
    models_path = os.path.join(module_path, 'static', 'models')
    
    # Create models directory if it doesn't exist
    if not os.path.exists(models_path):
        try:
            os.makedirs(models_path)
            _logger.info(f"Created face models directory at {models_path}")
            
            # Create a placeholder README file
            readme_path = os.path.join(models_path, 'README.md')
            with open(readme_path, 'w') as f:
                f.write("""# Face Recognition Models

This directory should contain the models required for face recognition.
Please download the required models using the script provided in this directory.

Run the following command from this directory:
```
./download_models.sh
```

If the script is not executable, you may need to run:
```
chmod +x download_models.sh
```
""")
                
            # Create the download script
            script_path = os.path.join(models_path, 'download_models.sh')
            with open(script_path, 'w') as f:
                f.write("""#!/bin/bash

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
""")
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            
            _logger.info(f"Created download script at {script_path}")
            
        except Exception as e:
            _logger.error(f"Failed to create face models directory: {e}")
    
    # Inform admin about missing dependencies
    try:
        import numpy
    except ImportError:
        _logger.warning("NumPy is required for face recognition. Install it using: pip install numpy")
    
    try:
        import psutil
    except ImportError:
        _logger.warning("psutil is required for system health checks. Install it using: pip install psutil")
