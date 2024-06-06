from typing import List

from starlette.routing import Match, Route


def match_route_path(route_path: str, method: str, routes: List[Route]):
    for route in routes:
        match = route.path_regex.match(route_path)
        if match:
            matched_params = match.groupdict()
            for key, value in matched_params.items():
                matched_params[key] = route.param_convertors[key].convert(value)
            path_params = {}
            path_params.update(matched_params)
            child_scope = {"endpoint": route.endpoint, "path_params": path_params}
            if route.methods and method not in route.methods:
                return Match.PARTIAL, child_scope
            else:
                return Match.FULL, child_scope
    return Match.NONE, {}
