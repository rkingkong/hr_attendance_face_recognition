# -*- coding: utf-8 -*-
import logging
import traceback
import json
import time
from functools import wraps

# Import the dedicated logger
from odoo.addons.hr_attendance_face_recognition import face_logger

def log_entry_exit(func):
    """Decorator to log entry and exit of important functions"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        face_logger.debug(f"ENTER: {func_name}")
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # Log detailed timing if function takes longer than expected
            if elapsed > 1.0:  # More than 1 second
                face_logger.warning(f"SLOW EXECUTION: {func_name} took {elapsed:.2f} seconds")
            else:
                face_logger.debug(f"EXIT: {func_name} - Execution time: {elapsed:.2f} seconds")
                
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            face_logger.error(
                f"ERROR in {func_name} after {elapsed:.2f} seconds: {str(e)}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise
    return wrapper

def log_face_recognition_attempt(employee_id, confidence, success, action=None):
    """Log details about a face recognition attempt"""
    status = "SUCCESS" if success else "FAILED"
    action_str = f" - Action: {action}" if action else ""
    face_logger.info(
        f"Face Recognition {status} - Employee ID: {employee_id} - "
        f"Confidence: {confidence:.2f}%{action_str}"
    )

def log_face_registration(employee_id, employee_name, templates_count, success):
    """Log details about a face registration attempt"""
    status = "SUCCESS" if success else "FAILED"
    face_logger.info(
        f"Face Registration {status} - Employee ID: {employee_id} - "
        f"Name: {employee_name} - Templates: {templates_count}"
    )

def log_system_error(error_type, message, details=None):
    """Log system-level errors with detailed information"""
    error_data = {
        "error_type": error_type,
        "message": message
    }
    
    if details:
        error_data["details"] = details
        
    face_logger.error(f"SYSTEM ERROR: {json.dumps(error_data)}")

def log_recognition_metrics(confidence, processing_time, device_info=None):
    """Log metrics about recognition performance"""
    metrics = {
        "confidence": confidence,
        "processing_time_ms": int(processing_time * 1000)
    }
    
    if device_info:
        metrics["device"] = device_info
        
    face_logger.info(f"METRICS: {json.dumps(metrics)}")
