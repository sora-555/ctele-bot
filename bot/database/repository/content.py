from sqlalchemy import select, delete
from bot.database.models import Favorite
async def toggle_favorite(session,user_id,url,title,thumbnail=None):
 r=await session.execute(select(Favorite).where(Favorite.user_id==user_id,Favorite.post_url==url)); old=r.scalar_one_or_none()
 if old: await session.delete(old); saved=False
 else: session.add(Favorite(user_id=user_id,post_url=url,post_title=title,thumbnail=thumbnail)); saved=True
 await session.commit(); return saved
