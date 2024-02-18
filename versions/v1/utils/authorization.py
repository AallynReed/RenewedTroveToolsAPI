from ..models.database.user import User


async def authorize(request):
    token = request.headers.get("Authorization")
    return await User.find_one({"internal_token": token})
