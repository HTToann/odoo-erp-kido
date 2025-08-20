from flask import Flask
from configs import db, login
import os
from flask_login import LoginManager

from dotenv import load_dotenv
from db.models.user import User, UserRole
from flask_login import login_required
from blueprint import blue_print
from admin.setup import init_admin

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "dev_secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


db.init_app(app)
login.init_app(app)
login.login_view = "auth.login"


@app.context_processor
def inject_enums():
    return dict(UserRole=UserRole)


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 🔗 đăng ký blueprint (không còn vòng lặp import)


init_admin(app)  # tạo /admin
blue_print(app)  # đăng ký các blueprint khác
# debug: in danh sách route trước khi run
# for r in app.url_map.iter_rules():
#     print("ROUTE:", r)
# print("BLUEPRINTS:", list(app.blueprints.keys()))
# print(app.url_map)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
