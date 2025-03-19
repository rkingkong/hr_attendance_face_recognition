# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import base64
import json
import logging

_logger = logging.getLogger(__name__)

class HrEmployeeFaceWizard(models.TransientModel):
    _name = 'hr.employee.face.wizard'
    _description = 'Face Registration Wizard'
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    
    face_data = fields.Binary(
        string='Face Data',
        help="Binary representation of facial features",
        attachment=False
    )
    
    current_templates = fields.Integer(
        string='Current Templates',
        compute='_compute_current_templates'
    )
    
    @api.depends('employee_id')
    def _compute_current_templates(self):
        for wizard in self:
            if wizard.employee_id and wizard.employee_id.face_encoding:
                try:
                    data = json.loads(base64.b64decode(wizard.employee_id.face_encoding).decode('utf-8'))
                    wizard.current_templates = len(data)
                except Exception as e:
                    _logger.error("Error computing current face templates: %s", e)
                    wizard.current_templates = 0
            else:
                wizard.current_templates = 0
    
    def action_save(self):
        """Save face data to employee record"""
        self.ensure_one()
        
        if not self.face_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("No face data captured. Please try again."),
                    'sticky': False,
                    'type': 'danger',
                }
            }
            
        try:
            self.employee_id.write({
                'face_encoding': self.face_data
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Success"),
                    'message': _("Face recognition data saved successfully."),
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            _logger.error("Error saving face data: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Error"),
                    'message': _("Failed to save face data: %s") % str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }
