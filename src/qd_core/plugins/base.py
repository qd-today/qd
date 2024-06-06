from functools import partial, wraps
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter
from plux import plugin  # type: ignore
from pydantic_settings import BaseSettings

from qd_core.utils.decorator import pydantic_convert

router = APIRouter()


def add_api_routes(
    api_paths: List[str],
    fn: Callable,
    api_methods: List[List[str]],
    api_kwargs: Dict = {},
    api_router: Optional[APIRouter] = None,
    api_router_kwargs: Dict = {},
):
    if not api_router:
        _api_router = router
    else:
        _api_router = api_router
    for api_path, api_method in zip(api_paths, api_methods):
        _api_router.add_api_route(api_path, fn, methods=api_method, **api_kwargs)
    if api_router:
        router.include_router(_api_router, **api_router_kwargs)


def api_plugin(
    namespace: str,
    name: str,
    api_paths: List[str],
    api_methods: List[List[str]],
    api_kwargs: Optional[Dict[str, Any]] = None,
    api_router: Optional[APIRouter] = None,
    api_router_kwargs: Optional[Dict[str, Any]] = None,
    settings: Optional[BaseSettings] = None,
):
    if api_kwargs is None:
        api_kwargs = {}
    if api_router_kwargs is None:
        api_router_kwargs = {}
    if settings is None:
        settings = BaseSettings()  # TODO: add settings

    def wrapper(fn):
        pydantic_converted_fn = pydantic_convert(fn)

        @wraps(pydantic_converted_fn)
        @plugin(
            namespace=namespace,
            name=name,
            load=partial(
                add_api_routes,
                api_paths,
                pydantic_converted_fn,
                api_methods=api_methods,
                api_kwargs=api_kwargs,
                api_router=api_router,
                api_router_kwargs=api_router_kwargs,
            ),
        )
        def plugin_wrapper(*args, **kwargs):
            return pydantic_converted_fn(*args, **kwargs)

        return plugin_wrapper

    return wrapper
