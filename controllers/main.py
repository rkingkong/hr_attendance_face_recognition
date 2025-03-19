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

# Import dedicated logger and utils
from odoo.addons.hr_attendance_face_recognition import face_logger
from odoo.addons.hr_attendance_face_recognition.utils.logging_utils import (
    log_entry_exit, log_face_recognition_attempt, 
    log_face_registration, log_system_error, log_recognition_metrics
)

class FaceRecognitionController(http.Controller):
    # Class variables for caching
    _face_encodings_cache = {}
    _cache_timestamp = None
    _cache_validity = 600  # 10 minutes in seconds
    
    @log_entry_exit
    def _get_all_face_encodings(self):
        """Cache all employee face encodings for faster recognition"""
        current_time = time.time()
        
        # Return cached data if valid
        if self._cache_timestamp and (current_time - self._cache_timestamp < self._cache_validity):
            face_logger.debug(f"Using cached face encodings for {len(self._face_encodings_cache)} employees")
            return self._face_encodings_cache
            
        # Rebuild cache
        start_time = time.time()
        self._face_encodings_cache = {}
        employees = request.env['hr.employee'].search([
            ('face_encoding', '!=', False),
            ('face_recognition_active', '=', True)
        ])
        
        face_logger.info(f"Rebuilding face encoding cache for {len(employees)} employees")
        
        valid_employees = 0
        for employee in employees:
            try:
                templates = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                self._face_encodings_cache[employee.id] = {
                    'employee': employee,
                    'templates': templates
                }
                valid_employees += 1
            except Exception as e:
                log_system_error("template_decode_error", 
                    f"Error loading face template for employee {employee.name}", {
                        "employee_id": employee.id,
                        "error": str(e)
                    }
                )
        
        self._cache_timestamp = current_time
        cache_build_time = time.time() - start_time
        face_logger.info(
            f"Face encoding cache rebuilt with {valid_employees}/{len(employees)} "
            f"employees in {cache_build_time:.2f} seconds"
        )
        
        return self._face_encodings_cache
    
    @http.route('/face_recognition/kiosk', type='http', auth='user', website=True)
    def face_kiosk_mode(self, **kw):
        """Render the kiosk mode interface"""
        face_logger.info(f"Kiosk mode accessed by user {request.env.user.name} (ID: {request.env.user.id})")
        return request.render('hr_attendance_face_recognition.kiosk_face_mode')
    
    @http.route('/face_recognition/register', type='json', auth='user')
    @log_entry_exit
    def register_face(self, employee_id, face_data):
        """Register a new face for an employee"""
        employee = request.env['hr.employee'].browse(int(employee_id))
        
        face_logger.info(f"Face registration initiated for employee ID {employee_id} by {request.env.user.name}")
        
        if not employee.exists():
            log_face_registration(employee_id, "Not Found", 0, False)
            return {'success': False, 'message': _("Employee not found")}
            
        try:
            templates_count = 0
            
            # face_data should be a base64 encoded JSON string of face encodings
            if employee.face_encoding:
                # If the employee already has face data, load it and append
                current_data = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                new_data = json.loads(base64.b64decode(face_data).decode('utf-8'))
                
                face_logger.debug(f"Adding {len(new_data)} templates to existing {len(current_data)} templates")
                
                # Combine and deduplicate face templates
                combined_data = current_data + new_data
                templates_count = len(combined_data)
                
                # Save the updated data
                encoded_data = base64.b64encode(json.dumps(combined_data).encode('utf-8'))
            else:
                # First time registration
                encoded_data = face_data
                new_data = json.loads(base64.b64decode(face_data).decode('utf-8'))
                templates_count = len(new_data)
                face_logger.debug(f"First-time registration with {templates_count} templates")
                
            employee.write({
                'face_encoding': encoded_data
            })
            
            # Invalidate the cache since we've updated an employee's face data
            self.__class__._cache_timestamp = None
            
            log_face_registration(employee_id, employee.name, templates_count, True)
            
            return {
                'success': True, 
                'message': _("Face template registered successfully"),
                'templates_count': templates_count
            }
            
        except Exception as e:
            log_system_error("face_registration_error", 
                f"Error during face registration for employee {employee.name}", {
                    "employee_id": employee.id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
            )
            
            log_face_registration(employee_id, employee.name, 0, False)
            
            return {
                'success': False, 
                'message': _("Face registration failed: %s") % str(e)
            }
    
    @http.route('/face_recognition/verify', type='json', auth='public')
    @log_entry_exit
    def verify_face(self, face_data):
        """Verify a face against all employees and check in/out if matched"""
        ensure_db()
        
        # Get client info for logging
        user_agent = request.httprequest.user_agent.string
        remote_addr = request.httprequest.remote_addr
        
        face_logger.info(f"Face verification request from {remote_addr} ({user_agent})")
        
        # Security check for public access
        if not request.session.uid:
            log_system_error("authentication_error", "Authentication required for face verification", {
                "remote_addr": remote_addr,
                "user_agent": user_agent
            })
            return {'success': False, 'message': _("Authentication required")}
            
        try:
            start_time = time.time()
            
            # Get the threshold from settings
            threshold = float(request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.threshold', '70.0'))
            
            # Check if we should store captured images
            store_images = request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.store_images', 'False') == 'True'
            
            # face_data should be an object with encoding and optionally an image
            face_encoding = face_data.get('encoding')
            face_image = face_data.get('image') if store_images else False
            
            if not face_encoding:
                log_system_error("invalid_data", "Missing face encoding in request", {
                    "remote_addr": remote_addr
                })
                return {'success': False, 'message': _("Missing face encoding data")}
            
            # Find the employee with the highest match confidence
            best_match = None
            highest_confidence = 0
            
            # Get all employee face encodings from cache
            employee_encodings = self._get_all_face_encodings()
            
            if not employee_encodings:
                log_system_error("empty_cache", "No face templates available for matching", {
                    "cache_timestamp": self._cache_timestamp
                })
                return {'success': False, 'message': _("No registered faces available for matching")}
            
            # Convert input face encoding
            try:
                input_encoding = json.loads(base64.b64decode(face_encoding).decode('utf-8'))
            except Exception as e:
                log_system_error("encoding_decode_error", "Failed to decode input face encoding", {
                    "error": str(e)
                })
                return {'success': False, 'message': _("Invalid face encoding format")}
            
            # Compare against all employees in the cache
            comparison_count = 0
            for employee_id, data in employee_encodings.items():
                employee = data['employee']
                templates = data['templates']
                
                # Compare against all templates for this employee
                for template in templates:
                    comparison_count += 1
                    # Calculate similarity between face templates
                    confidence = calculate_face_similarity(input_encoding, template)
                    
                    if confidence > highest_confidence:
                        highest_confidence = confidence
                        best_match = employee
            
            # Convert to percentage for easier understanding
            confidence_percentage = highest_confidence * 100
            
            face_logger.debug(
                f"Compared against {comparison_count} templates from {len(employee_encodings)} employees. "
                f"Best match: {best_match.name if best_match else 'None'} with {confidence_percentage:.2f}% confidence"
            )
            
            # Record metrics
            processing_time = time.time() - start_time
            log_recognition_metrics(confidence_percentage, processing_time, {
                "user_agent": user_agent,
                "remote_addr": remote_addr
            })
            
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
                
                action = "check_out" if attendance else "check_in"
                
                if attendance:  # Check out
                    attendance.write({
                        'check_out': fields.Datetime.now(),
                        'check_out_method': 'face',
                        **attendance_vals
                    })
                else:  # Check in
                    request.env['hr.attendance'].create({
                        'employee_id': best_match.id,
                        'check_in': fields.Datetime.now(),
                        'check_in_method': 'face',
                        **attendance_vals
                    })
                
                log_face_recognition_attempt(
                    best_match.id, confidence_percentage, True, action
                )
                
                return {
                    'success': True,
                    'action': action,
                    'name': best_match.name,
                    'confidence': confidence_percentage,
                    'employee_id': best_match.id,
                    'processing_time': processing_time
                }
            else:
                # Log failed recognition attempt
                employee_id = best_match.id if best_match else None
                log_face_recognition_attempt(employee_id, confidence_percentage, False)
                
                return {
                    'success': False,
                    'message': _("No matching employee found"),
                    'confidence': confidence_percentage if best_match else 0,
                    'processing_time': processing_time
                }
                
        except Exception as e:
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "remote_addr": remote_addr,
                "user_agent": user_agent
            }
            
            log_system_error("face_verification_error", "Unexpected error during face verification", error_details)
            
            return {
                'success': False,
                'message': _("Face verification failed: %s") % str(e)
            }

    @http.route('/face_recognition/cache/status', type='json', auth='user')
    def cache_status(self):
        """Return status of the face encoding cache"""
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            face_logger.warning(
                f"Unauthorized cache status access attempt by user {request.env.user.name} "
                f"(ID: {request.env.user.id})"
            )
            return {'success': False, 'message': _("Insufficient permissions")}
            
        current_time = time.time()
        cache_age = current_time - (self._cache_timestamp or 0)
        is_valid = self._cache_timestamp and (cache_age < self._cache_validity)
        
        face_logger.info(f"Cache status requested by {request.env.user.name}")
        
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
            face_logger.warning(
                f"Unauthorized cache refresh attempt by user {request.env.user.name} "
                f"(ID: {request.env.user.id})"
            )
            return {'success': False, 'message': _("Insufficient permissions")}
            
        face_logger.info(f"Cache refresh requested by {request.env.user.name}")
        
        # Reset cache timestamp to force rebuild
        self.__class__._cache_timestamp = None
        
        # Rebuild cache
        start_time = time.time()
        employee_encodings = self._get_all_face_encodings()
        refresh_time = time.time() - start_time
        
        face_logger.info(f"Cache refreshed in {refresh_time:.2f} seconds with {len(employee_encodings)} employees")
        
        return {
            'success': True,
            'message': _("Face encoding cache refreshed successfully"),
            'cache_size': len(employee_encodings),
            'refresh_time': refresh_time
        }

    @http.route('/face_recognition/logs', type='json', auth='user')
    def get_logs(self, limit=100):
        """Return recent face recognition logs"""
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            face_logger.warning(
                f"Unauthorized logs access attempt by user {request.env.user.name} "
                f"(ID: {request.env.user.id})"
            )
            return {'success': False, 'message': _("Insufficient permissions")}
            
        face_logger.info(f"Logs requested by {request.env.user.name}")
        
        # Fetch recent attendance logs with face recognition
        attendances = request.env['hr.attendance'].search_read(
            domain=['|', 
                ('check_in_method', '=', 'face'), 
                ('check_out_method', '=', 'face')
            ],
            fields=[
                'employee_id', 'check_in', 'check_out', 
                'check_in_method', 'check_out_method', 'confidence_score'
            ],
            limit=limit,
            order='create_date desc'
        )
        
        # Format logs for display
        logs = []
        for attendance in attendances:
            employee = request.env['hr.employee'].browse(attendance['employee_id'][0])
            
            if attendance['check_in_method'] == 'face':
                logs.append({
                    'timestamp': attendance['check_in'],
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'action': 'check_in',
                    'confidence': attendance['confidence_score']
                })
                
            if attendance['check_out_method'] == 'face' and attendance['check_out']:
                logs.append({
                    'timestamp': attendance['check_out'],
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'action': 'check_out',
                    'confidence': attendance['confidence_score']
                })
        
        # Sort logs by timestamp
        logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'success': True,
            'logs': logs[:limit]
        }


@log_entry_exit
def calculate_face_similarity(encoding1, encoding2):
    """
    Calculate similarity between two face encodings
    Returns a value between 0 and 1, where 1 is a perfect match
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
        log_system_error("similarity_calculation_error", 
            "Error calculating face similarity", {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )
        return 0
