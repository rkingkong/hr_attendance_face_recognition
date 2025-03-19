# -*- coding: utf-8 -*-
{
    'name': 'Face Recognition Attendance',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Attendance',
    'summary': 'Face Recognition for Attendance Tracking',
    'description': """
Face Recognition Attendance System
==================================
Use facial recognition to clock employees in and out.
This module extends the HR Attendance module to add face recognition capabilities.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_attendance', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/kiosk_face_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_attendance_face_recognition/static/src/js/kiosk_face_mode.js',
            'hr_attendance_face_recognition/static/src/css/kiosk_face_mode.css',
            'hr_attendance_face_recognition/static/src/js/face_registration.js',
            'hr_attendance_face_recognition/static/src/css/face_registration.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
