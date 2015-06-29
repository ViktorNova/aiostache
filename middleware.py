import asyncio
import time


@asyncio.coroutine
def Logger(app, handler):
    @asyncio.coroutine
    def middleware(request):
        t1 = time.time()
        srv = yield from handler(request)
        t2 = time.time() - t1
        print("Method:", request.method, "Path:",
              request.path, "Time:", round(t2, 4), "secs")
        return srv
    return middleware
