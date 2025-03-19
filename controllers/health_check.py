# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
import time
import platform
import psutil
from datetime import datetime, timedelta
from odoo import http, fields, _
from odoo.http import request, Response
from odoo.tools import config
from odoo.addons.hr_attendance_face_recognition import face_logger

class FaceRecognitionHealthCheck(http.Controller):
    
    @http.route('/face_recognition/health', type='json', auth='user')
    def health_check(self):
        """Return health status of the face recognition service"""
        # Check if user has admin rights
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return {
                'status': 'error',
                'message': _("Insufficient permissions to check system health")
            }
            
        face_logger.info(f"Health check initiated by {request.env.user.name}")
        
        start_time = time.time()
        status = {
            'status': 'ok',
            'timestamp': fields.Datetime.now(),
            'checks': {
                'models_check': self._check_face_models(),
                'database_check': self._check_database(),
                'system_check': self._check_system_resources(),
                'usage_statistics': self._get_usage_statistics(),
                'recognition_performance': self._check_recognition_performance()
            }
        }
        
        # Determine overall status based on individual checks
        if any(check.get('status') == 'error' for check in status['checks'].values()):
            status['status'] = 'error'
        elif any(check.get('status') == 'warning' for check in status['checks'].values()):
            status['status'] = 'warning'
            
        # Add response time
        status['response_time'] = time.time() - start_time
        
        return status
        
    def _check_face_models(self):
        """Verify face recognition models exist and are accessible"""
        result = {
            'status': 'ok',
            'message': 'Face recognition models are properly installed'
        }
        
        try:
            # Get module path
            module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            models_path = os.path.join(module_path, 'static', 'models')
            
            # Required model files
            required_models = [
                'face_landmark_68_model-weights_manifest.json',
                'face_recognition_model-weights_manifest.json',
                'tiny_face_detector_model-weights_manifest.json'
            ]
            
            # Check if models directory exists
            if not os.path.exists(models_path):
                result['status'] = 'error'
                result['message'] = f"Models directory not found at {models_path}"
                return result
                
            # Check for required model files
            missing_models = []
            for model in required_models:
                if not os.path.exists(os.path.join(models_path, model)):
                    missing_models.append(model)
            
            if missing_models:
                result['status'] = 'error'
                result['message'] = f"Missing required model files: {', '.join(missing_models)}"
                result['models_path'] = models_path
                result['missing_models'] = missing_models
            else:
                # Count total model files for info
                model_files = os.listdir(models_path)
                result['model_count'] = len(model_files)
                result['models_path'] = models_path
                
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f"Error checking face models: {str(e)}"
            
        return result
        
    def _check_database(self):
        """Check database connectivity and face recognition data"""
        result = {
            'status': 'ok',
            'message': 'Database checks passed'
        }
        
        try:
            # Check if we can query employees
            employee_count = request.env['hr.employee'].sudo().search_count([])
            result['employee_count'] = employee_count
            
            # Check how many employees have face recognition data
            face_count = request.env['hr.employee'].sudo().search_count([
                ('face_encoding', '!=', False),
                ('face_recognition_active', '=', True)
            ])
            result['face_registered_count'] = face_count
            
            # Warning if no employees have face data
            if employee_count > 0 and face_count == 0:
                result['status'] = 'warning'
                result['message'] = 'No employees have registered face data'
                
            # Check for recent attendances using face recognition
            one_week_ago = fields.Datetime.now() - timedelta(days=7)
            face_attendance_count = request.env['hr.attendance'].sudo().search_count([
                '|', 
                ('check_in_method', '=', 'face'), 
                ('check_out_method', '=', 'face'),
                ('create_date', '>=', one_week_ago)
            ])
            result['recent_face_attendance_count'] = face_attendance_count
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f"Database check failed: {str(e)}"
            
        return result
        
    def _check_system_resources(self):
        """Check system resources (memory, disk space, etc.)"""
        result = {
            'status': 'ok',
            'message': 'System resources are adequate',
            'system_info': {
                'platform': platform.platform(),
                'python_version': sys.version,
                'odoo_version': config.get('version', 'Unknown')
            }
        }
        
        try:
            # Check memory usage
            memory = psutil.virtual_memory()
            result['memory'] = {
                'total': memory.total,
                'available': memory.available,
                'percent_used': memory.percent,
                'used': memory.used,
                'free': memory.free
            }
            
            # Warning if memory usage is high
            if memory.percent > 90:
                result['status'] = 'warning'
                result['message'] = f"High memory usage: {memory.percent}%"
                
            # Check disk space
            disk = psutil.disk_usage('/')
            result['disk'] = {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent_used': disk.percent
            }
            
            # Warning if disk usage is high
            if disk.percent > 90:
                result['status'] = 'warning'
                result['message'] = f"Low disk space: {disk.percent}% used"
                
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            result['cpu'] = {
                'percent_used': cpu_percent,
                'cores': psutil.cpu_count()
            }
            
            # Warning if CPU usage is high
            if cpu_percent > 90:
                result['status'] = 'warning'
                result['message'] = f"High CPU usage: {cpu_percent}%"
                
        except Exception as e:
            # Non-critical error, just log it
            result['status'] = 'warning'
            result['message'] = f"Could not check system resources: {str(e)}"
            
        return result
        
    def _get_usage_statistics(self):
        """Get usage statistics for face recognition"""
        result = {
            'status': 'ok',
            'message': 'Usage statistics retrieved successfully'
        }
        
        try:
            # Last 30 days
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
            
            # Total attendances using face recognition
            total_face_attendances = request.env['hr.attendance'].sudo().search_count([
                '|', 
                ('check_in_method', '=', 'face'), 
                ('check_out_method', '=', 'face')
            ])
            result['total_face_attendances'] = total_face_attendances
            
            # Recent attendances (last 30 days)
            recent_face_attendances = request.env['hr.attendance'].sudo().search_count([
                '|', 
                ('check_in_method', '=', 'face'), 
                ('check_out_method', '=', 'face'),
                ('create_date', '>=', thirty_days_ago)
            ])
            result['recent_face_attendances'] = recent_face_attendances
            
            # Get usage by day for the last 7 days
            seven_days_ago = fields.Datetime.now() - timedelta(days=7)
            
            # This query gets the count of attendances per day
            request.env.cr.execute("""
                SELECT DATE(create_date) as date, COUNT(*) as count
                FROM hr_attendance
                WHERE (check_in_method = 'face' OR check_out_method = 'face')
                AND create_date >= %s
                GROUP BY DATE(create_date)
                ORDER BY date
            """, (seven_days_ago,))
            
            daily_counts = request.env.cr.dictfetchall()
            result['daily_usage'] = daily_counts
            
            # Most active employees
            request.env.cr.execute("""
                SELECT employee_id, COUNT(*) as count
                FROM hr_attendance
                WHERE (check_in_method = 'face' OR check_out_method = 'face')
                AND create_date >= %s
                GROUP BY employee_id
                ORDER BY count DESC
                LIMIT 5
            """, (thirty_days_ago,))
            
            top_employees_data = request.env.cr.dictfetchall()
            
            # Get employee names
            top_employees = []
            for item in top_employees_data:
                employee = request.env['hr.employee'].sudo().browse(item['employee_id'])
                top_employees.append({
                    'employee_id': item['employee_id'],
                    'name': employee.name if employee.exists() else 'Unknown',
                    'count': item['count']
                })
            
            result['top_employees'] = top_employees
            
        except Exception as e:
            result['status'] = 'warning'
            result['message'] = f"Error retrieving usage statistics: {str(e)}"
            
        return result
        
    def _check_recognition_performance(self):
        """Check face recognition performance metrics"""
        result = {
            'status': 'ok',
            'message': 'Recognition performance is acceptable'
        }
        
        try:
            # Get average confidence score for recent recognitions
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
            
            request.env.cr.execute("""
                SELECT AVG(confidence_score) as avg_confidence
                FROM hr_attendance
                WHERE (check_in_method = 'face' OR check_out_method = 'face')
                AND confidence_score > 0
                AND create_date >= %s
            """, (thirty_days_ago,))
            
            avg_result = request.env.cr.dictfetchone()
            avg_confidence = avg_result.get('avg_confidence', 0) if avg_result else 0
            
            result['avg_confidence'] = avg_confidence
            
            # Warning if average confidence is low
            if avg_confidence and avg_confidence < 80:
                result['status'] = 'warning'
                result['message'] = f"Low average recognition confidence: {avg_confidence:.2f}%"
                
            # Get confidence score distribution
            request.env.cr.execute("""
                SELECT
                    CASE
                        WHEN confidence_score >= 90 THEN '90-100%'
                        WHEN confidence_score >= 80 THEN '80-90%'
                        WHEN confidence_score >= 70 THEN '70-80%'
                        ELSE 'Below 70%'
                    END as range,
                    COUNT(*) as count
                FROM hr_attendance
                WHERE (check_in_method = 'face' OR check_out_method = 'face')
                AND confidence_score > 0
                AND create_date >= %s
                GROUP BY range
                ORDER BY range
            """, (thirty_days_ago,))
            
            confidence_distribution = request.env.cr.dictfetchall()
            result['confidence_distribution'] = confidence_distribution
            
            # Calculate total entries for percentage
            total_entries = sum(item['count'] for item in confidence_distribution)
            if total_entries > 0:
                for item in result['confidence_distribution']:
                    item['percentage'] = (item['count'] / total_entries) * 100
                    
            # Warning if more than 10% of recognitions are below 70% confidence
            below_70_item = next((item for item in confidence_distribution if item['range'] == 'Below 70%'), None)
            if below_70_item and total_entries > 0:
                below_70_percent = (below_70_item['count'] / total_entries) * 100
                if below_70_percent > 10:
                    result['status'] = 'warning'
                    result['message'] = f"{below_70_percent:.2f}% of recognitions have confidence below 70%"
            
        except Exception as e:
            result['status'] = 'warning'
            result['message'] = f"Error checking recognition performance: {str(e)}"
            
        return result
        
    @http.route('/face_recognition/diagnostics', type='json', auth='user')
    def run_diagnostics(self):
        """Run comprehensive diagnostics on the face recognition system"""
        # Check if user has admin rights
        if not request.env.user.has_group('hr_attendance.group_hr_attendance_manager'):
            return {
                'status': 'error',
                'message': _("Insufficient permissions to run diagnostics")
            }
            
        face_logger.info(f"Diagnostics initiated by {request.env.user.name}")
        
        diagnostics = {
            'timestamp': fields.Datetime.now(),
            'issues': [],
            'recommendations': []
        }
        
        # Check face data integrity
        self._check_face_data_integrity(diagnostics)
        
        # Check configuration settings
        self._check_configuration(diagnostics)
        
        # Check for unusual patterns
        self._check_attendance_patterns(diagnostics)
        
        # Generate recommendations based on findings
        self._generate_recommendations(diagnostics)
        
        return diagnostics
        
    def _check_face_data_integrity(self, diagnostics):
        """Check face data integrity for all employees"""
        try:
            employees = request.env['hr.employee'].sudo().search([
                ('face_recognition_active', '=', True)
            ])
            
            for employee in employees:
                # Check if employee has face data
                if not employee.face_encoding:
                    diagnostics['issues'].append({
                        'type': 'data_integrity',
                        'severity': 'warning',
                        'message': f"Employee {employee.name} has face recognition enabled but no face data"
                    })
                    continue
                
                # Check if face data is valid
                try:
                    face_data = base64.b64decode(employee.face_encoding)
                    templates = json.loads(face_data.decode('utf-8'))
                    
                    if not templates or not isinstance(templates, list):
                        diagnostics['issues'].append({
                            'type': 'data_integrity',
                            'severity': 'error',
                            'message': f"Employee {employee.name} has invalid face data format"
                        })
                    elif len(templates) < 2:
                        diagnostics['issues'].append({
                            'type': 'data_integrity',
                            'severity': 'warning',
                            'message': f"Employee {employee.name} has only {len(templates)} face template(s)"
                        })
                        
                except Exception as e:
                    diagnostics['issues'].append({
                        'type': 'data_integrity',
                        'severity': 'error',
                        'message': f"Employee {employee.name} has corrupted face data: {str(e)}"
                    })
                    
        except Exception as e:
            diagnostics['issues'].append({
                'type': 'system',
                'severity': 'error',
                'message': f"Error checking face data integrity: {str(e)}"
            })
            
    def _check_configuration(self, diagnostics):
        """Check system configuration settings"""
        try:
            # Check confidence threshold
            threshold = float(request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.threshold', '70.0'))
                
            if threshold < 60:
                diagnostics['issues'].append({
                    'type': 'configuration',
                    'severity': 'warning',
                    'message': f"Face recognition threshold is set very low ({threshold}%)"
                })
            elif threshold > 90:
                diagnostics['issues'].append({
                    'type': 'configuration',
                    'severity': 'warning',
                    'message': f"Face recognition threshold is set very high ({threshold}%)"
                })
                
            # Check if storing images is enabled
            store_images = request.env['ir.config_parameter'].sudo().get_param(
                'hr_attendance_face_recognition.store_images', 'False') == 'True'
                
            if store_images:
                # Check disk space if storing images
                disk = psutil.disk_usage('/')
                if disk.percent > 85:
                    diagnostics['issues'].append({
                        'type': 'configuration',
                        'severity': 'warning',
                        'message': f"Storing attendance images is enabled but disk space is low ({disk.percent}% used)"
                    })
                    
        except Exception as e:
            diagnostics['issues'].append({
                'type': 'system',
                'severity': 'error',
                'message': f"Error checking configuration: {str(e)}"
            })
            
    def _check_attendance_patterns(self, diagnostics):
        """Check for unusual attendance patterns"""
        try:
            # Check for employees with low recognition confidence
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
            
            request.env.cr.execute("""
                SELECT employee_id, AVG(confidence_score) as avg_confidence
                FROM hr_attendance
                WHERE (check_in_method = 'face' OR check_out_method = 'face')
                AND confidence_score > 0
                AND create_date >= %s
                GROUP BY employee_id
                HAVING AVG(confidence_score) < 75
                ORDER BY avg_confidence
            """, (thirty_days_ago,))
            
            low_confidence_employees = request.env.cr.dictfetchall()
            
            for entry in low_confidence_employees:
                employee = request.env['hr.employee'].sudo().browse(entry['employee_id'])
                diagnostics['issues'].append({
                    'type': 'recognition_quality',
                    'severity': 'warning',
                    'message': f"Employee {employee.name if employee.exists() else 'Unknown'} has consistently low recognition confidence ({entry['avg_confidence']:.2f}%)"
                })
                
            # Check for time periods with high failure rates
            seven_days_ago = fields.Datetime.now() - timedelta(days=7)
            
            # This requires a custom tracking table for failed recognitions
            # Implementation would depend on how you track failed recognitions
                
        except Exception as e:
            diagnostics['issues'].append({
                'type': 'system',
                'severity': 'error',
                'message': f"Error checking attendance patterns: {str(e)}"
            })
            
    def _generate_recommendations(self, diagnostics):
        """Generate recommendations based on diagnostic issues"""
        issue_types = [issue['type'] for issue in diagnostics['issues']]
        
        # Data integrity recommendations
        if 'data_integrity' in issue_types:
            diagnostics['recommendations'].append(
                "Re-register face templates for employees with missing or corrupted data"
            )
            diagnostics['recommendations'].append(
                "Ensure employees have at least 3-5 face templates registered from different angles"
            )
            
        # Configuration recommendations
        if 'configuration' in issue_types:
            threshold_issues = [i for i in diagnostics['issues'] if i['type'] == 'configuration' and 'threshold' in i['message']]
            if threshold_issues:
                if 'high' in threshold_issues[0]['message']:
                    diagnostics['recommendations'].append(
                        "Consider lowering the recognition threshold to improve success rate"
                    )
                else:
                    diagnostics['recommendations'].append(
                        "Consider raising the recognition threshold to improve security"
                    )
                    
        # Recognition quality recommendations
        if 'recognition_quality' in issue_types:
            diagnostics['recommendations'].append(
                "Improve lighting conditions in the kiosk area"
            )
            diagnostics['recommendations'].append(
                "Re-register face templates for employees with consistently low recognition confidence"
            )
            
        # General recommendations
        diagnostics['recommendations'].append(
            "Regularly clean the camera lens for optimal recognition"
        )
        diagnostics['recommendations'].append(
            "Consider updating face templates every 3-6 months"
        )
