from bot.services.ctele_service import CTeleService
from bot.config import settings
class CTeleMiddleware:
 def __init__(self): self.service=CTeleService(settings)
 async def __call__(self,handler,event,data): data['ctele']=self.service; return await handler(event,data)
