"""
Main Blueprint - Simplified
Only handles home page route. Other functionality moved to specialized blueprints:
- auth.py: Authentication (login, logout)
- assets.py: Asset operations (checkout, checkin, transfer, lookup)
- admin.py: Administrative functions (user management, loan agreements, VIP access)
"""
from flask import Blueprint, render_template
import logging

main_bp = Blueprint('main_bp', __name__)
logger = logging.getLogger(__name__)


@main_bp.route('/')
def home():
    """Landing page"""
    logger.debug('Landing page accessed')
    return render_template('landing.html')
