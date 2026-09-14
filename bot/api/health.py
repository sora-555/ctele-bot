from fastapi import APIRouter
router=APIRouter()
@router.get('/')
async def root(): return {'service':'CosplayTele bot','status':'ok'}
@router.get('/healthz')
async def health(): return {'status':'ok'}
@router.get('/readyz')
async def ready(): return {'status':'ready'}
