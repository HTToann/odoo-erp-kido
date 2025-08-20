from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from configs import db
from db.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.pop("_flashes", None)

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Sai tài khoản hoặc mật khẩu", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Tài khoản đã bị khóa", "warning")
            return render_template("auth/login.html")

        login_user(user, remember=True)
        flash("Đăng nhập thành công", "success")
        next_url = request.args.get("next") or url_for("main.home")
        return redirect(next_url)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
        session.pop("_flashes", None)
        flash("Đã đăng xuất", "info")
    return redirect(url_for("auth.login"))
