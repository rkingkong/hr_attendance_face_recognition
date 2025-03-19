odoo.define('hr_attendance_face_recognition.kiosk_face_mode', function (require) {
"use strict";

var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

// Load face-api.js from CDN
const script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
document.head.appendChild(script);

var FaceKioskMode = AbstractAction.extend({
    template: 'HrAttendanceFaceKiosk',
    
    events: {
        "click .o_face_kiosk_toggle": function() { this.toggleFullScreen(); },
        "click .o_face_register_btn": function() { this.registerFace(); },
        "click .o_face_detect_btn": function() { this.startDetection(); },
    },
    
    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.faceModelsLoaded = false;
        this.detectRunning = false;
        this.showVideo = true;
        this.stream = null;
        this.employee = null;
    },
    
    willStart: function () {
        return this._super.apply(this, arguments);
    },
    
    start: function () {
        var self = this;
        this.faceStreamPromise = this._startFaceStream();
        
        // Load face-api.js models when script is loaded
        script.onload = function() {
            self._loadFaceDetectionModels();
        };
        
        return this._super.apply(this, arguments).then(function () {
            self.initializeVideoElement();
        });
    },
    
    destroy: function () {
        this._stopFaceStream();
        this._super.apply(this, arguments);
    },
    
    initializeVideoElement: function() {
        this.video = document.getElementById('face_kiosk_video');
        
        // Add video event listeners
        if (this.video) {
            this.canvas = document.createElement('canvas');
            this.canvas.style.position = 'absolute';
            this.canvas.style.top = '0';
            this.canvas.style.left = '0';
            this.video.parentNode.insertBefore(this.canvas, this.video.nextSibling);
            
            window.addEventListener('resize', () => this._resizeCanvas());
            this.video.addEventListener('play', () => this._resizeCanvas());
        }
    },
    
    _resizeCanvas: function() {
        if (this.video && this.canvas) {
            const { width, height } = this.video.getBoundingClientRect();
            this.canvas.width = width;
            this.canvas.height = height;
        }
    },
    
    _loadFaceDetectionModels: async function() {
        try {
            this._showProcessingMessage(_t('Loading face detection models...'));
            
            // Load models from CDN
            await faceapi.nets.tinyFaceDetector.loadFromUri('/hr_attendance_face_recognition/static/models');
            await faceapi.nets.faceLandmark68Net.loadFromUri('/hr_attendance_face_recognition/static/models');
            await faceapi.nets.faceRecognitionNet.loadFromUri('/hr_attendance_face_recognition/static/models');
            
            this.faceModelsLoaded = true;
            this._hideProcessingMessage();
            this._showSuccessMessage(_t('Face detection ready!'));
        } catch (error) {
            console.error('Error loading face detection models', error);
            this._showErrorMessage(_t('Failed to load face detection models'));
        }
    },
    
    _startFaceStream: async function() {
        if (this.stream) {
            return Promise.resolve();
        }
        
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "user"
                }
            });
            
            return Promise.resolve();
        } catch (error) {
            console.error('Error accessing camera', error);
            this._showErrorMessage(_t("Could not access camera. Please ensure you've given permission."));
            return Promise.reject(error);
        }
    },
    
    _stopFaceStream: function() {
        if (this.stream) {
            const tracks = this.stream.getTracks();
            tracks.forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
    },
    
    startDetection: async function() {
        if (!this.faceModelsLoaded) {
            this._showErrorMessage(_t('Face detection models are still loading. Please wait.'));
            return;
        }
        
        if (this.detectRunning) {
            return;
        }
        
        this.detectRunning = true;
        this._showProcessingMessage(_t('Looking for your face...'));
        
        if (!this.video.srcObject && this.stream) {
            this.video.srcObject = this.stream;
            await this.video.play();
        }
        
        // Wait a bit to make sure video is playing
        setTimeout(() => this._detectFace(), 500);
    },
    
    _detectFace: async function() {
        if (!this.detectRunning || !this.video.srcObject) {
            return;
        }
        
        try {
            // Detect faces in video stream
            const detections = await faceapi.detectAllFaces(
                this.video, 
                new faceapi.TinyFaceDetectorOptions()
            ).withFaceLandmarks().withFaceDescriptors();
            
            // Draw detections on canvas
            const dims = faceapi.matchDimensions(this.canvas, this.video, true);
            const resizedDetections = faceapi.resizeResults(detections, dims);
            
            const context = this.canvas.getContext('2d');
            context.clearRect(0, 0, this.canvas.width, this.canvas.height);
            faceapi.draw.drawDetections(this.canvas, resizedDetections);
            faceapi.draw.drawFaceLandmarks(this.canvas, resizedDetections);
            
            if (detections.length === 0) {
                this._showWarningMessage(_t('No face detected. Please center your face in the camera.'));
                // Try again
                setTimeout(() => this._detectFace(), 500);
                return;
            } else if (detections.length > 1) {
                this._showWarningMessage(_t('Multiple faces detected. Please ensure only one face is visible.'));
                // Try again
                setTimeout(() => this._detectFace(), 500);
                return;
            }
            
            // Get the face descriptor
            const descriptor = detections[0].descriptor;
            
            // Take a snapshot for verification
            const snapshot = this._takeSnapshot();
            
            // Verify with server
            this._verifyFace(descriptor, snapshot);
            
        } catch (error) {
            console.error('Error during face detection:', error);
            this._showErrorMessage(_t('Error during face detection. Please try again.'));
            this.detectRunning = false;
        }
    },
    
    _takeSnapshot: function() {
        if (!this.video || !this.video.videoWidth) {
            return null;
        }
        
        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoWidth;
        canvas.height = this.video.videoHeight;
        
        const context = canvas.getContext('2d');
        context.drawImage(this.video, 0, 0, canvas.width, canvas.height);
        
        return canvas.toDataURL('image/jpeg', 0.8);
    },
    
    _verifyFace: function(descriptor, snapshot) {
        this._showProcessingMessage(_t('Verifying identity...'));
        
        // Prepare data for API call
        const data = {
            encoding: btoa(JSON.stringify(Array.from(descriptor))),
            image: snapshot
        };
        
        // Call server to verify face
        this._rpc({
            route: '/face_recognition/verify',
            params: {
                face_data: data
            },
        }).then(result => {
            this.detectRunning = false;
            
            if (result.success) {
                // Successfully recognized
                this._showAttendanceSuccess(result);
            } else {
                // No match found
                this._showAttendanceError(result);
            }
        }).catch(error => {
            console.error('Error verifying face:', error);
            this._showErrorMessage(_t('Error connecting to server. Please try again.'));
            this.detectRunning = false;
        });
    },
    
    registerFace: function() {
        // This function should only be available for administrators in the employee form
        // It will be handled in a separate wizard
    },
    
    _showAttendanceSuccess: function(result) {
        var self = this;
        const action = result.action;
        const name = result.name;
        
        this._hideProcessingMessage();
        
        // Update UI with check-in/out message
        this.$('.o_face_kiosk_clock_status').html(
            action === 'check_in' ? 
            _t('Welcome') : 
            _t('Goodbye')
        );
        
        this.$('.o_face_kiosk_employee_name').text(name);
        this.$('.o_face_kiosk_message').removeClass('alert-danger');
        this.$('.o_face_kiosk_message').addClass('alert-success');
        this.$('.o_face_kiosk_message').text(
            action === 'check_in' ? 
            _t('You have been successfully checked in!') : 
            _t('You have been successfully checked out!')
        );
        
        // Show the success message for 2 seconds then reset
        setTimeout(function() {
            self.$('.o_face_kiosk_clock_status').text(_t('Scan Your Face'));
            self.$('.o_face_kiosk_employee_name').text('');
            self.$('.o_face_kiosk_message').removeClass('alert-success alert-danger');
            self.$('.o_face_kiosk_message').text('');
        }, 5000);
    },
    
    _showAttendanceError: function(result) {
        this._hideProcessingMessage();
        
        const confidence = result.confidence ? result.confidence.toFixed(2) + '%' : 'N/A';
        const message = result.message || _t('Unknown error');
        
        this.$('.o_face_kiosk_clock_status').text(_t('Recognition Failed'));
        this.$('.o_face_kiosk_message').removeClass('alert-success');
        this.$('.o_face_kiosk_message').addClass('alert-danger');
        this.$('.o_face_kiosk_message').html(
            message + '<br/>' + _t('Confidence: ') + confidence
        );
    },
    
    _showProcessingMessage: function(message) {
        this.$('.o_face_kiosk_status_message').text(message);
        this.$('.o_face_processing_container').removeClass('d-none');
    },
    
    _hideProcessingMessage: function() {
        this.$('.o_face_processing_container').addClass('d-none');
    },
    
    _showSuccessMessage: function(message) {
        this.$('.o_face_kiosk_message').removeClass('alert-danger');
        this.$('.o_face_kiosk_message').addClass('alert-success');
        this.$('.o_face_kiosk_message').text(message);
    },
    
    _showErrorMessage: function(message) {
        this.$('.o_face_kiosk_message').removeClass('alert-success');
        this.$('.o_face_kiosk_message').addClass('alert-danger');
        this.$('.o_face_kiosk_message').text(message);
    },
    
    _showWarningMessage: function(message) {
        this.$('.o_face_kiosk_message').removeClass('alert-success alert-danger');
        this.$('.o_face_kiosk_message').addClass('alert-warning');
        this.$('.o_face_kiosk_message').text(message);
    },
    
    toggleFullScreen: function() {
        var elem = document.documentElement;
        
        if (!document.fullscreenElement && !document.mozFullScreenElement &&
            !document.webkitFullscreenElement && !document.msFullscreenElement) {
            if (elem.requestFullscreen) {
                elem.requestFullscreen();
            } else if (elem.msRequestFullscreen) {
                elem.msRequestFullscreen();
            } else if (elem.mozRequestFullScreen) {
                elem.mozRequestFullScreen();
            } else if (elem.webkitRequestFullscreen) {
                elem.webkitRequestFullscreen(Element.ALLOW_KEYBOARD_INPUT);
            }
            this.$('.o_face_kiosk_toggle').text(_t('Exit Full Screen'));
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            }
            this.$('.o_face_kiosk_toggle').text(_t('Full Screen'));
        }
    }
});

core.action_registry.add('hr_attendance_face_kiosk_mode', FaceKioskMode);

return FaceKioskMode;

});
