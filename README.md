# hr_attendance_face_recognition
Odoo Module: Custom module to store facial data and manage attendance Web/Mobile Interface: Kiosk application that captures faces and communicates with Odoo Face Recognition Engine: Service to analyze and match facial data

hr_attendance_face_recognition/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── models/
│   ├── __init__.py
│   ├── hr_employee.py
│   └── hr_attendance.py
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   └── kiosk_face_mode.js
│   │   └── css/
│   │       └── kiosk_face_mode.css
│   └── description/
│       └── icon.png
└── views/
    ├── hr_employee_views.xml
    ├── hr_attendance_views.xml
    └── kiosk_face_view.xml
