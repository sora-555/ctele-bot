from fastapi import APIRouter,Request,HTTPException
router=APIRouter()
def setup_webhook(router,dp,secret):
 @router.post('/webhook')
 async def webhook(request:Request):
  if secret and request.headers.get('X-Telegram-Bot-Api-Secret-Token')!=secret: raise HTTPException(403,'invalid webhook secret')
  from aiogram.types import Update
  await dp.feed_update(request.app.state.bot,Update.model_validate(await request.json())); return {'ok':True}
