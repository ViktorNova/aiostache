from aiohttp import web
import asyncio
import os
import pystache
import functools


def Response(text):
    return web.Response(body=text.encode('utf-8'))


def Json(obj):
    json = str(obj)
    return Response(json)


def render_template(template_name, root_path, request, data={}):
    renderer = pystache.renderer.Renderer(search_dirs=root_path)
    html = renderer.render(renderer.load_template(template_name), data)
    return Response(html)


class Route(dict):

    def __init__(self, method, path, view_func):
        self.method = method
        self.path = path
        self.view_func = view_func


class Stache(web.Application):
    loop = asyncio.get_event_loop()

    def __init__(self, instance_file, static_folder="static",
                 template_folder="templates"):
        super().__init__()
        self.root_path = os.path.abspath(os.path.dirname(instance_file))
        self.static_folder = os.path.join(self.root_path, static_folder)
        self.template_folder = os.path.join(self.root_path, template_folder)

    @asyncio.coroutine
    def create_server(self, loop, host="0.0.0.0", port="8080"):
        handler = self.make_handler()
        srv = yield from self.loop.create_server(handler, host, port)
        return srv, handler

    def add_middleware(self, middleware):
        self._middlewares += (middleware,)

    def route(self, path, methods=["GET"]):

        def decorated(f):
            for method in methods:
                self.router.add_route(method, path, f)
                if path.endswith("/"):
                    self.router.add_route(method, path[:-1], f)
            return asyncio.coroutine(f)
        return decorated

    def template(self, template_name, *args):

        def wrapper(func):
            @asyncio.coroutine
            @functools.wraps(func)
            def wrapped(*args):
                if asyncio.iscoroutinefunction(func):
                    coro = func
                else:
                    coro = asyncio.coroutine(func)

                request = args[-1]
                context = yield from coro(request)

                return render_template(
                    template_name,
                    self.template_folder,
                    request,
                    context)
            return wrapped
        return wrapper

    def register_beard(self, beard, url_prefix=None):
        beard.register(self, url_prefix=url_prefix)

    def run(self, host="0.0.0.0", port=8080):
        srv, self.handler = self.loop.run_until_complete(
            self.create_server(self.loop, host, port))
        print("Running server on", host, port)
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.run_until_complete(self.handler.finish_connections())

    def shutdown(self):
        self.loop.run_until_complete(self.handler.finish_connections())


class Beard(Stache):

    def __init__(self, instance_file, url_prefix=None):
        super().__init__(instance_file)
        self.url_prefix = url_prefix

        self.routes = []

    def register(self, stache, url_prefix=None):
        self.stache = stache
        if url_prefix is not None:
            self.url_prefix = url_prefix
        self.register_routes(url_prefix)

    def route(self, path, methods=["GET"]):

        def decorated(f):
            for method in methods:
                self.routes.append(Route(method, path, f))
                if path.endswith("/"):
                    self.routes.append(Route(method, path[:-1], f))
            return asyncio.coroutine(f)
        return decorated

    def register_routes(self, url_prefix=None):
        for route in self.routes:
            if url_prefix is None:
                self.stache.router.add_route(
                    route.method, route.path, route.view_func)
            else:
                self.stache.router.add_route(
                    route.method,
                    self.url_prefix + route.path,
                    route.view_func
                )
