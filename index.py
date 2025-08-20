# index.py
from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime

main_bp = Blueprint("main", __name__)


@main_bp.app_context_processor
def inject_now():
    return {"current_year": datetime.now().year}


@main_bp.route("/")
@login_required
def home():
    return render_template("index.html")
