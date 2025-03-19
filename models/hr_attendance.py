# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrAttendanceFace(models.Model):
    _inherit = 'hr.attendance'
    
    check_in_method = fields.Selection(
        [('manual', 'Manual'), 
        ('face', 'Face Recognition')],
        default='manual',
        string='Check In Method'
    )
    
    check_out_method = fields.Selection(
        [('manual', 'Manual'), 
        ('face', 'Face Recognition')],
        default='manual',
        string='Check Out Method'
    )
    
    confidence_score = fields.Float(
        string='Recognition Confidence',
        help="Confidence score of the facial recognition (0-100)",
        default=0.0
    )
    
    face_image = fields.Binary(
        string='Captured Image',
        attachment=True,
        help="Image captured during check-in/out (if enabled in settings)",
        copy=False
    )


class FaceRecognitionSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    face_recognition_threshold = fields.Float(
        string='Face Recognition Confidence Threshold',
        config_parameter='hr_attendance_face_recognition.threshold',
        default=70.0,
        help="Minimum confidence level (0-100) required for a face match to be accepted"
    )
    
    store_attendance_images = fields.Boolean(
        string='Store Attendance Images',
        config_parameter='hr_attendance_face_recognition.store_images',
        default=False,
        help="If enabled, the system will store images captured during check-in/out"
    )
    
    face_recognition_kiosk_mode = fields.Boolean(
        string='Kiosk Mode',
        config_parameter='hr_attendance_face_recognition.kiosk_mode',
        default=True,
        help="Run the face recognition interface in fullscreen kiosk mode"
    )
