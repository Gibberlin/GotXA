import sys
from collections import defaultdict
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app import api_v1, api_v1_actions, api_v1_consolidated, api_v1_extended


def _collect_route_map():
    app = Flask(__name__)
    for blueprint in [
        api_v1.api,
        api_v1_actions.api,
        api_v1_extended.api,
        api_v1_consolidated.api,
    ]:
        app.register_blueprint(blueprint)

    routes = defaultdict(set)
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith('/static'):
            continue
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            routes[(rule.rule, method)].add(rule.endpoint)
    return routes


def test_duplicate_api_routes_are_not_registered():
    routes = _collect_route_map()
    duplicates = [
        (rule, method)
        for (rule, method), endpoints in routes.items()
        if len(endpoints) > 1
    ]
    assert not duplicates, f"Duplicate endpoints found: {duplicates}"


def test_batch_operation_routes_exist():
    routes = _collect_route_map()
    required = {
        ('/api/alerts/batch-operations', 'POST'),
        ('/api/incidents/<incident_id>/batch-update', 'POST'),
        ('/api/access/jit-sessions/batch-action', 'POST'),
        ('/api/db/batch-operations', 'POST'),
    }
    for route in required:
        assert route in routes, f"Missing route {route}"
