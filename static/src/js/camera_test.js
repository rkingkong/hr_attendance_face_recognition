odoo.define('hr_attendance_face_recognition.camera_test', function (require) {
"use strict";

// Basic script to test camera access
$(document).ready(function() {
    $(document).on('click', '.o_capture_face', function(e) {
        console.log("Capture Face button clicked");
        
        // Prevent default to avoid any server action attempt
        e.preventDefault();
        e.stopPropagation();
        
        // Test camera access
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then(function(stream) {
                    console.log("Camera access successful");
                    alert("Camera access successful!");
                    
                    // Display camera feed in video element
                    var video = document.getElementById('face_registration_video');
                    if (video) {
                        video.srcObject = stream;
                        video.play();
                    } else {
                        console.error("Video element not found");
                        alert("Video element not found. Check the HTML structure.");
                    }
                })
                .catch(function(error) {
                    console.error("Camera access failed:", error);
                    alert("Camera access failed: " + error.message);
                });
        } else {
            console.error("getUserMedia not supported");
            alert("Your browser doesn't support camera access");
        }
    });
});

});
