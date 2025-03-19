# -*- coding: utf-8 -*-
import json
import logging
import base64
import numpy as np
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request, Response
from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)

class FaceRecognitionController(http.Controller):
    
    @http.route('/face_recognition/kiosk', type='http', auth='user', website=True)
    def face_kiosk_mode(self, **kw):
        """Render the kiosk mode interface"""
        return request.render('hr_attendance_face_recognition.kiosk_face_mode')
    
    @http.route('/face_recognition/register', type='json', auth='user')
    def register_face(self, employee_id, face_data):
        """Register a new face for an employee"""
        employee = request.env['hr.employee'].browse(int(employee_id))
        
        if not employee.exists():
            return {'success': False, 'message': _("Employee not found")}
            
        try:
            # face_data should be a base64 encoded JSON string of face encodings
            if employee.face_encoding:
                # If the employee already has face data, load it and append
                current_data = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                new_data = json.loads(base64.b64decode(face_data).decode('utf-8'))
                
                # Combine and deduplicate face templates
                combined_data = current_data + new_data
                
                # Save the updated data
                encoded_data = base64.b64encode(json.dumps(combined_data).encode('utf-8'))
            else:
                # First time registration
                encoded_data = face_data
                
            employee.write({
                'face_encoding': encoded_data
            })
            
            return {
                'success': True, 
                'message': _("Face template registered successfully")
            }
            
        except Exception as e:
            _logger.error("Face registration error: %s", e)
            return {
                'success': False, 
                'message': _("Face registration failed: %s") % str(e)
            }
    
    @http.route('/face_recognition/verify', type='json', auth='public')
    def verify_face(self, face_data):
        """Verify a face against all employees and check in/out if matched"""
        ensure_db()
        
        # Security check for public access
        if not request.session.uid:
            return {'success': False, 'message': _("Authentication required")}
            
        try:
            # Get the threshold from settings
            threshold = float(request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.threshold', '70.0'))
            
            # Check if we should store captured images
            store_images = request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.store_images', 'False') == 'True'
            
            # face_data should be an object with encoding and optionally an image
            face_encoding = face_data.get('encoding')
            face_image = face_data.get('image') if store_images else False
            
            # Find the employee with the highest match confidence
            best_match = None
            highest_confidence = 0
            
            employees = request.env['hr.employee'].search([
                ('face_encoding', '!=', False),
                ('face_recognition_active', '=', True)
            ])
            
            for employee in employees:
                # Get the employee's face templates
                templates = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                
                # Compare against all templates for this employee
                for template in templates:
                    # This is a simplified comparison - in a real system,
                    # you would use a proper facial recognition algorithm
                    confidence = calculate_face_similarity(
                        json.loads(base64.b64decode(face_encoding).decode('utf-8')),
                        template
                    )
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_match = employee
            
            # Convert to percentage for easier understanding
            confidence_percentage = highest_confidence * 100
            
            # Check if we have a match above the threshold
            if best_match and confidence_percentage >= threshold:
                # Check if employee is already checked in
                attendance = request.env['hr.attendance'].search([
                    ('employee_id', '=', best_match.id),
                    ('check_out', '=', False)
                ], limit=1)
                
                attendance_vals = {
                    'confidence_score': confidence_percentage,
                    'face_image': face_image if store_images else False,
                }
                
                if attendance:  # Check out
                    attendance.write({
                        'check_out': fields.Datetime.now(),
                        'check_out_method': 'face',
                        **attendance_vals
                    })
                    
                    return {
                        'success': True,
                        'action': 'check_out',
                        'name': best_match.name,
                        'confidence': confidence_percentage,
                        'employee_id': best_match.id
                    }
                else:  # Check in
                    request.env['hr.attendance'].create({
                        'employee_id': best_match.id,
                        'check_in': fields.Datetime.now(),
                        'check_in_method': 'face',
                        **attendance_vals
                    })
                    
                    return {
                        'success': True,
                        'action': 'check_in',
                        'name': best_match.name,
                        'confidence': confidence_percentage,
                        'employee_id': best_match.id
                    }
            else:
                return {
                    'success': False,
                    'message': _("No matching employee found"),
                    'confidence': confidence_percentage if best_match else 0
                }
                
        except Exception as e:
            _logger.error("Face verification error: %s", e)
            return {
                'success': False,
                'message': _("Face verification failed: %s") % str(e)
            }


def calculate_face_similarity(encoding1, encoding2):
    """
    Calculate similarity between two face encodings
    Returns a value between 0 and 1, where 1 is a perfect match
    
    Note: In a real implementation, you would use a proper face recognition
    library like face_recognition, DeepFace, or a cloud-based service.
    This is a simplified placeholder function.
    """
    try:
        # Convert to numpy arrays for vector operations
        arr1 = np.array(encoding1)
        arr2 = np.array(encoding2)
        
        # Calculate Euclidean distance
        distance = np.linalg.norm(arr1 - arr2)
        
        # Convert distance to similarity score (0-1)
        # Assuming max distance is 1.0 for normalized encodings
        similarity = max(0, 1 - distance)
        
        return similarity
    except Exception as e:
        _logger.error("Error calculating face similarity: %s", e)
        return 0
