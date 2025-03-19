# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import utils
from .hooks import _ensure_face_models_directory

# Set up dedicated logging for the face recognition module
import logging

# Create a dedicated logger with a specific name
face_logger = logging.getLogger('odoo.addons.hr_attendance_face_recognition')

# Configure the logger to include timestamps and levels
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s [Face Recognition] %(message)s')
handler.setFormatter(formatter)
face_logger.addHandler(handler)

# Set default level to INFO, can be overridden in config
face_logger.setLevel(logging.INFO)
