odoo.define('hr_attendance_face_recognition.face_registration', function (require) {
"use strict";

var core = require('web.core');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var _t = core._t;

// Load face-api.js from CDN
const script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
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
            
            // Load required models
            await faceapi.nets.tinyFaceDetector.loadFromUri('/hr_attendance_face_recognition/static/models');
            await faceapi.nets.faceLandmark68Net.loadFromUri('/hr_attendance_face_recognition/static/models');
            await faceapi.nets.faceRecognitionNet.loadFromUri('/hr_attendance_face_recognition/static/models');
            
            this.faceModelsLoaded = true;
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
            return;
        }
        
        try {
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
            const descriptor = detections[0].
