import httpx

from ducktap.core.pipeline import discover


def test_graphql_discovery_is_first_class(monkeypatch):
    introspection = {
        "data": {
            "__schema": {
                "queryType": {
                    "fields": [
                        {
                            "name": "launches",
                            "description": "List launches",
                            "args": [
                                {
                                    "name": "limit",
                                    "description": "Maximum launches",
                                    "type": {"kind": "SCALAR", "name": "Int"},
                                }
                            ],
                        },
                        {
                            "name": "node",
                            "description": "Fetch a node",
                            "args": [
                                {
                                    "name": "id",
                                    "description": "Node ID",
                                    "type": {
                                        "kind": "NON_NULL",
                                        "name": None,
                                        "ofType": {"kind": "SCALAR", "name": "ID"},
                                    },
                                }
                            ],
                        },
                    ]
                }
            }
        }
    }

    def fake_post(url, json, timeout):
        assert "__schema" in json["query"]
        return httpx.Response(200, json=introspection)

    monkeypatch.setattr("ducktap.discovery.graphql.httpx.post", fake_post)

    spec = discover("https://api.example.test/graphql", hint="graphql", name="space")

    assert spec.name == "space"
    assert spec.source["discoverer"] == "graphql"
    assert [op.operation_id for op in spec.operations] == ["launches", "node"]
    assert spec.operations[0].params[0].type == "integer"
    assert spec.operations[1].params[0].required is True
