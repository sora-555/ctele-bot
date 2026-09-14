import asyncio, time, secrets
from dataclasses import dataclass
@dataclass
class Session: user_id:int; data:dict; expires:float
class SessionStore:
 def __init__(self,ttl=1800): self.ttl=ttl; self._data={}; self._locks={}
 def create(self,user_id,data):
  sid=secrets.token_urlsafe(6); self._data[sid]=Session(user_id,data,time.monotonic()+self.ttl); self._locks[sid]=asyncio.Lock(); return sid
 def get(self,sid,user_id):
  s=self._data.get(sid)
  if not s or s.user_id!=user_id or s.expires<time.monotonic(): self._data.pop(sid,None); return None
  s.expires=time.monotonic()+self.ttl; return s.data
 def lock(self,sid): return self._locks.setdefault(sid,asyncio.Lock())
store = SessionStore()
