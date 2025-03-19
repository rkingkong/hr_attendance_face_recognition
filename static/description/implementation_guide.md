# Face Recognition Attendance Module - Implementation Guide

This guide provides detailed instructions for implementing the Face Recognition Attendance module in Odoo Community Edition.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Face Recognition Models](#face-recognition-models)
5. [Employee Registration](#employee-registration)
6. [Setting Up the Kiosk](#setting-up-the-kiosk)
7. [Troubleshooting](#troubleshooting)
8. [Security Considerations](#security-considerations)

## Prerequisites

- Odoo Community Edition 16.0
- Python 3.7+
- A device with a camera (for both registration and kiosk mode)
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Network connection between kiosk devices and Odoo server

## Installation

### Method 1: Using the Module Zip File

1. Download the module zip file
2. Go to Odoo Apps menu
3. Click "Upload a Module" button
4. Select the downloaded zip file
5. Click "Install" once the module appears in the list

### Method 2: Using Git

1. Navigate to your Odoo addons directory
2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/hr_attendance_face_recognition.git
   ```
3. Restart Odoo service
4. Go to Apps menu in Odoo
5. Click "Update Apps List"
6. Search for "Face Recognition Attendance"
7. Click "Install"

## Configuration

After installation, you need to configure the module:

1. Go to **Settings > Attendance > Face Recognition Settings**
2. Configure the following options:
   - **Face Recognition Confidence Threshold**: Set the minimum confidence level (0-100) required for a face match (default: 70)
   - **Store Attendance Images**: Enable to store images captured during check-in/out (may have privacy implications)
   - **Kiosk Mode**: Enable to run the interface in fullscreen mode

## Face Recognition Models

The face recognition functionality requires pre-trained models:

1. Navigate to the module's static directory:
   ```bash
   cd /path/to/odoo/addons/hr_attendance_face_recognition/static/models
   ```

2. Run the provided script to download the models:
   ```bash
   chmod +x download_models.sh
   ./download_models.sh
   ```

3. Verify that the following files have been downloaded:
   - face_landmark_68_model-shard1
   - face_landmark_68_model-weights_manifest.json
   - face_recognition_model-shard1
   - face_recognition_model-shard2
   - face_recognition_model-weights_manifest.json
   - tiny_face_detector_model-shard1
   - tiny_face_detector_model-weights_manifest.json

## Employee Registration

Before employees can use facial recognition, they need to register their faces:

1. Go to **Employees > Employees**
2. Select an employee
3. Navigate to the **HR Settings** tab
4. In the Face Recognition section, click **Register Face**
5. Follow the on-screen instructions:
   - Ensure good lighting
   - Position the face within the guide frame
   - Click "Capture Face"
   - Review the captured image
   - Click "Save" if satisfied, or "Retry" to capture again

Tips for optimal face registration:
- Ensure consistent lighting without shadows across the face
- Use a neutral expression
- Capture multiple angles for better recognition (you can register multiple times)
- Remove glasses or other accessories that may obstruct facial features

## Setting Up the Kiosk

1. Set up a dedicated device (tablet, laptop, or desktop with camera) for the kiosk
2. Log in to Odoo with a user that has attendance rights
3. Navigate to **Attendances > Face Recognition Kiosk**
4. Optional: Enable full-screen mode for a better kiosk experience
5. The kiosk is now ready to be used for check-in/check-out

For permanent kiosk setup:
- Consider using a dedicated browser profile in kiosk mode
- Set up automatic login and navigation to the kiosk page
- Install a browser extension to prevent sleep/screensaver

## Troubleshooting

### Common Issues and Solutions

#### Camera Access Issues

- **Issue**: "Could not access camera" error
- **Solution**: 
  - Ensure camera permissions are granted to the browser
  - Try using a different browser
  - Check if another application is using the camera

#### Face Not Detected

- **Issue**: "No face detected" error when attempting to register or check in
- **Solution**:
  - Improve lighting conditions
  - Position face directly in front of the camera
  - Ensure no obstructions (hair, accessories) covering the face

#### Low Recognition Confidence

- **Issue**: Employee not recognized or mistakenly identified as someone else
- **Solution**:
  - Adjust the confidence threshold in settings
  - Re-register the employee's face with better quality captures
  - Register multiple face templates for the same employee

#### Models Not Loading

- **Issue**: "Error loading face detection models" message
- **Solution**:
  - Verify models are correctly downloaded
  - Check network connectivity
  - Clear browser cache and reload

## Security Considerations

### Privacy and Data Protection

- **Facial Data**: The module stores facial recognition data as encrypted templates, not actual images
- **GDPR Compliance**: Ensure proper consent is obtained from employees
- **Data Retention**: Consider implementing a policy to remove facial data when no longer needed

### Physical Security

- **Kiosk Placement**: Position kiosks in areas where they cannot be easily spoofed (e.g., with photos)
- **Supervision**: Consider having initial supervision during deployment to prevent misuse

### Technical Security

- **Network Security**: Ensure the connection between kiosk devices and the Odoo server is secure
- **Access Control**: Limit administrative rights for facial recognition settings
- **Regular Updates**: Keep the module and underlying libraries updated

## Support and Further Development

For support, bug reports, or feature requests, please contact:
- Email: rkong@torelo.net
- Issue Tracker: https://github.com/yourusername/hr_attendance_face_recognition/issues
