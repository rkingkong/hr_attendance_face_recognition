odoo.define('hr_attendance_face_recognition.face_registration', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var _t = core._t;

// Load face-api.js from CDN
const script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.2/dist/face-api.js';
script.crossOrigin = 'anonymous';
document.head.appendChild(script);

var FaceRegistrationFormController = FormController.extend({
    events: _.extend({}, FormController.prototype.events, {
        'click .o_capture_face': '_onCaptureFace',
        'click .o_retry_capture': '_onRetryCapture',
    }),
    
    init: function () {
        this._super.apply(this, arguments);
        this.faceModelsLoaded = false;
        this.stream = null;
        this.video = null;
        this.capturing = false;
    },
    
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Initialize face detection when script is loaded
            script.onload = function() {
                self._loadFaceDetectionModels();
            };
            
            // Initialize webcam when view is fully rendered
            self.renderer.on('renderComplete', self, function() {
                self._initializeWebcam();
            });
        });
    },
    
    destroy: function () {
        this._stopWebcam();
        this._super.apply(this, arguments);
    },
    
    _loadFaceDetectionModels: async function() {
        try {
            // Show loading status
            const statusElement = this.$('.o_face_status');
            statusElement.removeClass('invisible alert-danger').addClass('alert alert-info');
            statusElement.text(_t('Loading face detection models...'));
            
            // Log the model URLs for debugging
            const modelUrl = '/hr_attendance_face_recognition/static/models';
            console.log('Loading face registration models from:', modelUrl);
            
            // Load required models with logging
            console.log('Loading tinyFaceDetector model...');
            await faceapi.nets.tinyFaceDetector.loadFromUri(modelUrl);
            console.log('Loading faceLandmark68Net model...');
            await faceapi.nets.faceLandmark68Net.loadFromUri(modelUrl);
            console.log('Loading faceRecognitionNet model...');
            await faceapi.nets.faceRecognitionNet.loadFromUri(modelUrl);
            
            this.faceModelsLoaded = true;
            console.log('All face registration models loaded successfully!');
            statusElement.removeClass('alert-info').addClass('alert-success');
            statusElement.text(_t('Face detection ready. Position your face in the frame and click "Capture".'));
            
        } catch (error) {
            console.error('Error loading face detection models', error);
            const statusElement = this.$('.o_face_status');
            statusElement.removeClass('invisible alert-info').addClass('alert-danger');
            statusElement.text(_t('Error loading face detection models: ') + error.message);
        }
    },
    
    _initializeWebcam: async function() {
        this.video = this.el.querySelector('#face_registration_video');
        
        if (!this.video) {
            console.error('Video element not found in the DOM');
            return;
        }
        
        try {
            // Check if mediaDevices is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error("Browser doesn't support camera access. Please use Chrome, Firefox, or Edge.");
            }
            
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: "user"
                }
            });
            
            this.video.srcObject = this.stream;
            this.video.play();
            
            const statusElement = this.$('.o_face_status');
            statusElement.removeClass('invisible');
            
        } catch (error) {
            console.error('Error accessing webcam:', error);
            const statusElement = this.$('.o_face_status');
            statusElement.removeClass('invisible alert-info').addClass('alert-danger');
            statusElement.text(_t('Could not access camera. Please ensure you\'ve given permission.'));
        }
    },
    
    _stopWebcam: function() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    },
    
    _onCaptureFace: async function() {
        if (this.capturing) {
            return;
        }
        
        if (!this.faceModelsLoaded) {
            this._displayError(_t('Face detection not ready yet. Please wait a moment.'));
            return;
        }
        
        if (!this.video || !this.video.srcObject) {
            this._displayError(_t('Camera not initialized. Please refresh and try again.'));
            return;
        }
        
        this.capturing = true;
        
        // Update UI
        const statusElement = this.$('.o_face_status');
        statusElement.removeClass('invisible alert-danger alert-success').addClass('alert-info');
        statusElement.text(_t('Processing...'));
        
        try {
            // Detect face in video
            const detections = await faceapi.detectAllFaces(
                this.video, 
                new faceapi.TinyFaceDetectorOptions({ scoreThreshold: 0.5 })
            ).withFaceLandmarks().withFaceDescriptors();
            
            if (detections.length === 0) {
                this._displayError(_t('No face detected. Please ensure your face is clearly visible.'));
                this.capturing = false;
                return;
            }
            
            if (detections.length > 1) {
                this._displayError(_t('Multiple faces detected. Please ensure only your face is in the frame.'));
                this.capturing = false;
                return;
            }
            
            // Get descriptor and convert to Base64 for storage
            const descriptor = detections[0].descriptor;
            const descriptorArray = Array.from(descriptor);
            const descriptorJson = JSON.stringify(descriptorArray);
            const encodedData = btoa(descriptorJson);
            
            // Show capture success
            statusElement.removeClass('alert-info').addClass('alert-success');
            statusElement.text(_t('Face captured successfully!'));
            
            // Store face data in form field
            this.$('input[name="face_data"]').val(encodedData);
            
            // Update UI for successful capture
            this.$('.o_retry_capture').removeClass('invisible');
            this.$('.o_capture_face').text(_t('Capture Again'));
            
            // Create an overlay showing the captured face
            this._createCaptureOverlay(detections[0]);
            
        } catch (error) {
            console.error('Error capturing face:', error);
            this._displayError(_t('Error processing face: ') + error.message);
        } finally {
            this.capturing = false;
        }
    },
    
    _onRetryCapture: function() {
        // Clear previous capture
        this.$('input[name="face_data"]').val('');
        
        // Reset UI
        const statusElement = this.$('.o_face_status');
        statusElement.removeClass('alert-danger alert-success').addClass('alert-info');
        statusElement.text(_t('Position your face in the frame and click "Capture".'));
        
        this.$('.o_retry_capture').addClass('invisible');
        this.$('.o_capture_face').text(_t('Capture Face'));
        
        // Remove overlay if exists
        const overlay = this.el.querySelector('.o_face_capture_overlay');
        if (overlay) {
            overlay.remove();
        }
    },
    
    _createCaptureOverlay: function(detection) {
        // Remove previous overlay if exists
        const previousOverlay = this.el.querySelector('.o_face_capture_overlay');
        if (previousOverlay) {
            previousOverlay.remove();
        }
        
        const videoContainer = this.el.querySelector('.o_face_video_wrapper');
        if (!videoContainer) return;
        
        // Create canvas overlay
        const overlay = document.createElement('canvas');
        overlay.className = 'o_face_capture_overlay';
        overlay.width = this.video.videoWidth;
        overlay.height = this.video.videoHeight;
        overlay.style.position = 'absolute';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        
        videoContainer.appendChild(overlay);
        
        // Draw face detection on overlay
        const ctx = overlay.getContext('2d');
        
        // Draw video frame as background
        ctx.drawImage(this.video, 0, 0, overlay.width, overlay.height);
        
        // Highlight face with box and landmarks
        const box = detection.detection.box;
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 3;
        ctx.strokeRect(box.x, box.y, box.width, box.height);
        
        // Draw face landmarks
        const landmarks = detection.landmarks.positions;
        ctx.fillStyle = '#00FF00';
        for (let i = 0; i < landmarks.length; i++) {
            const { x, y } = landmarks[i];
            ctx.beginPath();
            ctx.arc(x, y, 2, 0, 2 * Math.PI);
            ctx.fill();
        }
    },
    
    _displayError: function(message) {
        const statusElement = this.$('.o_face_status');
        statusElement.removeClass('invisible alert-info alert-success').addClass('alert-danger');
        statusElement.text(message);
    },
    
    _registerButtonHandler: function(button_data, event) {
        // Fix for the "Missing type for doActionButton request" error
        if (!button_data.type) {
            button_data.type = 'object';
        }
        return this._super.apply(this, arguments);
    }
});

var FaceRegistrationFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: FaceRegistrationFormController
    })
});

FormView.include({
    init: function(viewInfo, params) {
        this._super.apply(this, arguments);
        if (params.modelName === 'hr.employee.face.wizard') {
            this.controllerClass = FaceRegistrationFormController;
        }
    }
});

return {
    FaceRegistrationFormController: FaceRegistrationFormController,
    FaceRegistrationFormView: FaceRegistrationFormView
};

});
