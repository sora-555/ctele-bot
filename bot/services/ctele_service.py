from ctele import CTeleClient
class CTeleService:
 def __init__(self,settings): self.settings=settings; self.client=CTeleClient(base_url=settings.source_base_url,user_agent=settings.source_user_agent,timeout=settings.request_timeout,max_retries=settings.max_retries)
 async def close(self): await self.client.close()
 async def search(self,q,page=1): return await self.client.search(q,page)
 async def post(self,url): return await self.client.get_post(url)
 async def latest(self,page=1): return await self.client.get_latest(page)
 async def categories(self): return await self.client.get_categories()
