from typing import List
from db.models.user import User


def list_users() -> List[User]:
    return User.query.order_by(User.username.asc()).all()
