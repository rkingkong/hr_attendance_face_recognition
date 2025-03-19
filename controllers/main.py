# -*- coding: utf-8 -*-
import json
import logging
import base64
import numpy as np
import time
import traceback
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request, Response
from odoo.addons.web.controllers.main import ensure_db

_logger = logging.getLogger(__name__)

class FaceRecognitionController(http.Controller):
    # Class variables for caching
    _face_encodings_cache = {}
    _cache_timestamp = None
    _cache_validity = 600  # 10 minutes in seconds
    
    def _get_all_face_encodings(self):
        """Cache all employee face encodings for faster recognition"""
        current_time = time.time()
        
        # Return cached data if valid
        if self._cache_timestamp and (current_time - self._cache_timestamp < self._cache_validity):
            return self._face_encodings_cache
            
        # Rebuild cache
        self._face_encodings_cache = {}
        employees = request.env['hr.employee'].search([
            ('face_encoding', '!=', False),
            ('face_recognition_active', '=', True)
        ])
        
        for employee in employees:
            try:
                templates = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                self._face_encodings_cache[employee.id] = {
                    'employee': employee,
                    'templates': templates
                }
            except Exception as e:
                _logger.error("Error loading face template for employee %s: %s", employee.name, e)
        
        self._cache_timestamp = current_time
        _logger.info("Face encoding cache rebuilt with %s employees", len(self._face_encodings_cache))
        return self._face_encodings_cache
    
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
            
            # Invalidate the cache since we've updated an employee's face data
            self.__class__._cache_timestamp = None
            
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
            
            # Get all employee face encodings from cache
            employee_encodings = self._get_all_face_encodings()
            
            # Convert input face encoding
            input_encoding = json.loads(base64.b64decode(face_encoding).decode('utf-8'))
            
            # Compare against all employees in the cache
            for employee_id, data in employee_encodings.items():
                employee = data['employee']
                templates = data['templates']
                
                # Compare against all templates for this employee
                for template in templates:
                    # Calculate similarity between face templates
                    confidence = calculate_face_similarity(input_encoding, template)
                    
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
            _logger.error("Face verification error: %s\nTraceback: %s", str(e), traceback.format_exc())
            return {
                'success': False,
                'message': _("Face verification failed: %s") % str(e)
            }

    @http.route('/face_recognition/cache/status', type='json', auth='user')
    def cache_status(self):
        """Return status of the face encoding cache"""
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return {'success': False, 'message': _("Insufficient permissions")}
            
        current_time = time.time()
        cache_age = current_time - (self._cache_timestamp or 0)
        is_valid = self._cache_timestamp and (cache_age < self._cache_validity)
        
        return {
            'success': True,
            'cache_exists': self._cache_timestamp is not None,
            'cache_valid': is_valid,
            'cache_age_seconds': cache_age if self._cache_timestamp else 0,
            'cache_size': len(self._face_encodings_cache),
            'validity_period': self._cache_validity
        }
        
    @http.route('/face_recognition/cache/refresh', type='json', auth='user')
    def refresh_cache(self):
        """Force refresh the face encoding cache"""
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return {'success': False, 'message': _("Insufficient permissions")}
            
        # Reset cache timestamp to force rebuild
        self.__class__._cache_timestamp = None
        
        # Rebuild cache
        employee_encodings = self._get_all_face_encodings()
        
        return {
            'success': True,
            'message': _("Face encoding cache refreshed successfully"),
            'cache_size': len(employee_encodings)
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
