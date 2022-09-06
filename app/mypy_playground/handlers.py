import dataclasses
from http import HTTPStatus
import json
import logging
import traceback
from typing import Any, cast

from prometheus_client import exposition
import tornado.escape
from tornado.options import options
import tornado.web

from mypy_playground import gist
from mypy_playground.prometheus import PrometheusMixin
from mypy_playground.sandbox import run_typecheck_in_sandbox
from mypy_playground.sandbox.base import (
    AbstractSandbox,
)
from .tools.mypy import     ARGUMENT_FLAGS
from mypy_playground.sandbox.cloud_functions import CloudFunctionsSandbox
from mypy_playground.sandbox.docker import DockerSandbox


logger = logging.getLogger(__name__)
initial_code = """from typing import Iterator


def fib(n: int) -> Iterator[int]:
    a, b = 0, 1
    while a < n:
        yield a
        a, b = b, a + b


fib(10)
fib("10")
"""


class IndexHandler(tornado.web.RequestHandler):
    async def get(self) -> None:
        self.render("index.html")


class JsonRequestHandler(tornado.web.RequestHandler):
    def prepare(self) -> None:
        if self.request.method in {"HEAD", "GET"}:
            return
        content_type = self.request.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            raise tornado.web.HTTPError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                log_message="Content-type must be application/json",
            )

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        error = {}

        if "exc_info" in kwargs:
            exc_info = kwargs["exc_info"]
            if self.settings.get("serve_traceback"):
                # in debug mode, try to send a traceback
                lines = traceback.format_exception(*exc_info)
                error["traceback"] = "\n".join(lines)

            exc = exc_info[1]
            if isinstance(exc, tornado.web.HTTPError) and exc.log_message:
                error["message"] = exc.log_message

        self.finish(error)

    def parse_json_request_body(self) -> Any:
        try:
            return tornado.escape.json_decode(self.request.body)
        except json.JSONDecodeError:
            raise tornado.web.HTTPError(
                HTTPStatus.BAD_REQUEST, log_message="failed to parse JSON body"
            )


class ContextHandler(JsonRequestHandler):
    async def get(self) -> None:
        tool_selections = options.tool_selections
        tool_versions = options.tool_versions
        default: dict[str, bool | str] = {flag: False for flag in ARGUMENT_FLAGS}
        default["toolSelection"] = "mypy"
        default["toolVersion"] = tool_versions[default["toolSelection"]][0][1]
        default["pythonVersion"] = options.default_python_version
        context = {
            "defaultConfig": default,
            "initialCode": initial_code,
            "pythonVersions": options.python_versions,
            "toolSelections": tool_selections,
            "toolVersions": tool_versions,
            "flags": ARGUMENT_FLAGS,
            "gaTrackingId": options.ga_tracking_id,
        }
        self.write(context)


class TypecheckHandler(JsonRequestHandler):
    async def post(self) -> None:
        json = self.parse_json_request_body()

        source = json.get("source")
        if source is None or not isinstance(source, str):
            raise tornado.web.HTTPError(
                HTTPStatus.BAD_REQUEST, log_message="'source' is required"
            )

        args = {}
        if (
            version := json.get("pythonVersion")
        ) is not None and version in options.python_versions:
            args["python_version"] = version
        for flag in ARGUMENT_FLAGS:
            flag_value = json.get(flag)
            if flag_value is not None and flag_value is True:
                args[flag] = flag_value

        tool = args["tool_selection"] = json.get("toolSelection", "mypy")
        args["tool_version"] = json.get("tool_version", options.tool_versions[args["tool_selection"]][0][0])

        sandbox = self._get_sandbox()
        result = await run_typecheck_in_sandbox(sandbox, source, **args)
        if result is None:
            logger.error("an error occurred during running check")
            raise tornado.web.HTTPError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                log_message=f"an error occurred during running {tool}",
            )

        self.write(dataclasses.asdict(result))

    def _get_sandbox(self) -> AbstractSandbox:
        sandbox_class = options["sandbox"]
        if sandbox_class == "mypy_playground.sandbox.docker.DockerSandbox":
            return DockerSandbox()
        elif (
            sandbox_class
            == "mypy_playground.sandbox.cloud_functions.CloudFunctionsSandbox"
        ):
            return CloudFunctionsSandbox()
        raise Exception("Unsupported sandbox")


class GistHandler(JsonRequestHandler):
    async def post(self) -> None:
        json = self.parse_json_request_body()

        source = json.get("source")
        if source is None or not isinstance(source, str):
            raise tornado.web.HTTPError(
                HTTPStatus.BAD_REQUEST, log_message="'source' is required"
            )

        result = await gist.create_gist(source)

        if result is None:
            logger.error("an error occurred during creating a gist")
            raise tornado.web.HTTPError(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                log_message="an error occurred during creating a gist",
            )

        self.set_status(201)
        self.write(result)


class PrometheusMetricsHandler(tornado.web.RequestHandler):
    """Endpoint to expose Prometheus metrics.

    This handler must be used with PrometheusMixin for getting a registry.
    """

    async def get(self) -> None:
        accept_header = self.request.headers.get("accept")
        if not isinstance(accept_header, str):
            accept_header = ""
        encoder, content_type = exposition.choose_encoder(accept_header)
        application = cast(PrometheusMixin, self.application)
        output = encoder(application.prometheus_registry)
        self.set_header("Content-Type", content_type)
        self.write(output)
