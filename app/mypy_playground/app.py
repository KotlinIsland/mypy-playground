import logging
from pathlib import Path
from typing import Any

from tornado.options import define, options
import tornado.web

from mypy_playground import handlers
from mypy_playground.prometheus import PrometheusMixin
from mypy_playground.utils import ListPairOption


logger = logging.getLogger(__name__)
root_dir = Path(__file__).parents[1]
static_dir = root_dir / "static" / "_next"
templates_dir = root_dir / "static"

define(
    "sandbox",
    type=str,
    default="mypy_playground.sandbox.docker.DockerSandbox",
    help="Sandbox implementation to use.",
)
define(
    "sandbox_concurrency",
    type=int,
    default=3,
    help="The number of running sandboxes at the same time",
)
define(
    "default_python_version",
    type=str,
    default="3.11",
    help="Default Python version",
)
define(
    "python_versions",
    type=str,
    default=["3.12", "3.11", "3.10", "3.9", "3.8", "3.7", "3.6", "3.5", "3.4", "2.7"],
    multiple=True,
    help="Python versions",
)
define("ga_tracking_id", type=str, default=None, help="Google Analytics tracking ID")
define(
    "github_token", type=str, default=None, help="GitHub API token for creating gists"
)
define(
    "mypy_versions",
    type=ListPairOption,
    default=[("mypy latest", "latest"), ("basedmypy 2.1.0", "basedmypy-2.1.0")],
    help="List of mypy versions used by a sandbox",
)
define(
    "enable_prometheus", type=bool, default=False, help="Prometheus metrics endpoint"
)
define("port", type=int, default=8080, help="Port number")
define("debug", type=bool, default=False, help="Debug mode")


class Application(PrometheusMixin, tornado.web.Application):
    pass


def make_app(**kwargs: Any) -> tornado.web.Application:
    # TODO: Support 404 page generated by Next.js
    routes: list[tuple[str, type[tornado.web.RequestHandler]]] = [
        (r"/api/context", handlers.ContextHandler),
        (r"/api/gist", handlers.GistHandler),
        (r"/api/typecheck", handlers.TypecheckHandler),
        (r"/", handlers.IndexHandler),
    ]
    if options.enable_prometheus:
        routes.append((r"/private/metrics", handlers.PrometheusMetricsHandler))
    return Application(
        routes,
        static_path=static_dir,
        static_url_prefix="/_next/",
        template_path=templates_dir,
        debug=options.debug,
        **kwargs
    )
