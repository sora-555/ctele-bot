from bot.config import settings
from bot.services.ctele_service import CTeleService

service = CTeleService(settings)


class CTeleMiddleware:
    """Expose one cached source client to every handler."""

    async def __call__(self, handler, event, data):
        data['ctele'] = service
        return await handler(event, data)
