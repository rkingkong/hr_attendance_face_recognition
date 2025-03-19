# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import base64
import logging
import json

_logger = logging.getLogger(__name__)

class HrEmployeeFace(models.Model):
    _inherit = 'hr.employee'
    
    face_encoding = fields.Binary(
        string='Face Encoding Data',
        attachment=True,
        help="Facial encoding data used for recognition",
        copy=False
    )
    
    face_template_count = fields.Integer(
        string='Face Templates', 
        compute='_compute_face_template_count',
        help="Number of facial templates registered for this employee"
    )
    
    face_recognition_active = fields.Boolean(
        string='Face Recognition Active',
        default=True,
        help="Whether this employee can use face recognition for attendance"
    )
    
    @api.depends('face_encoding')
    def _compute_face_template_count(self):
        for employee in self:
            if employee.face_encoding:
                try:
                    # The face encoding is stored as a JSON array of templates
                    templates = json.loads(base64.b64decode(employee.face_encoding).decode('utf-8'))
                    employee.face_template_count = len(templates)
                except Exception as e:
                    _logger.error("Error computing face template count: %s", e)
                    employee.face_template_count = 0
            else:
                employee.face_template_count = 0
    
    def action_register_face(self):
        """Open wizard to register employee face"""
        self.ensure_one()
        return {
            'name': _('Register Face'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.employee.face.wizard',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            },
        }
    
    def action_clear_face_data(self):
        """Clear all facial recognition data for this employee"""
        self.ensure_one()
        self.face_encoding = False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Face data cleared'),
                'message': _('All facial recognition data for %s has been deleted.') % self.name,
                'sticky': False,
                'type': 'success',
            }
        }
