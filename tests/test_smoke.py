"""Smoke test: import everything the notebook imports, then run the three
request loops against a mocked Optiply API and check the snapshots they write."""
import json
import os
import sys
import tempfile

import pandas as pd

# exactly what etl_v2.ipynb imports
from optiply_etl.auth import OptiplyAuthenticator
from optiply_etl.tools import (snapshot_records, get_snapshot, delete_from_snapshot,
                               concat_columns, handle_invalid_dates, round_to_2, round_to_0,
                               validate_attribute, convert_to_bool, round_numeric_to_2,
                               round_numeric_to_0, get_custom_mappings, apply_final_mapping,
                               resolve_snapshot_dir, is_success_request)
from optiply_etl.payloads import (get_product_payload, get_supplier_payload,
                                  get_payload_function)
from optiply_etl.actions import (post_optiply, patch_optiply, delete_optiply, get_optiply,
                                 run_deletes, run_posts, run_patches)

# tools helpers behave
assert round_to_2("12.345") == 12.35
assert round_to_0("7.9") == 7
assert resolve_snapshot_dir("buy_orders").endswith("/snapshots/")  # no config.json -> no crash
assert is_success_request(201) and not is_success_request(404)

# payload dispatcher
row = pd.Series({"remoteId": "42", "name": "ACME", "emails": "a@b.com"})
p = get_payload_function(row, "suppliers")
assert p["name"] == "ACME", p


class FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body or {}
        self.text = text
        self.ok = 200 <= status_code < 300

    def json(self):
        return self._body


class FakeAuth:
    """Mimics OptiplyAuthenticator._request; returns canned responses."""
    def __init__(self):
        self.calls = []
        self.next_id = 100

    def _request(self, method, url, data=None):
        self.calls.append((method, url))
        if method == "DELETE":
            return FakeResponse(204)
        self.next_id += 1
        body = {"data": {"id": self.next_id, "attributes": {"uuid": f"uuid-{self.next_id}"}}}
        return FakeResponse(200, body)


api_creds = {"account_id": 1, "couplingId": 2}

with tempfile.TemporaryDirectory() as snap_dir:
    auth = FakeAuth()

    # POST two new suppliers
    new_records = pd.DataFrame({"remoteId": ["a", "b"], "name": ["S1", "S2"], "emails": ["x@y.z", "q@w.e"]})
    run_posts(api_creds, auth, new_records, "suppliers", "suppliers", snap_dir, get_payload_function)
    snap = get_snapshot("suppliers", snap_dir)
    assert len(snap) == 2 and set(snap["remoteId"]) == {"a", "b"}, snap
    assert snap["optiply_id"].notna().all() and snap["optiply_uuid"].notna().all()

    # PATCH one of them
    update_records = pd.DataFrame({"remoteId": ["a"], "name": ["S1-renamed"], "emails": ["x@y.z"],
                                   "optiply_id": [snap.iloc[0]["optiply_id"]]})
    run_patches(api_creds, auth, update_records, "suppliers", "suppliers", snap_dir, get_payload_function)
    snap = get_snapshot("suppliers", snap_dir)
    assert len(snap) == 2, snap

    # DELETE the other
    delete_records = pd.DataFrame({"remoteId": ["b"], "optiply_id": [snap[snap['remoteId'] == 'b'].iloc[0]['optiply_id']]})
    run_deletes(api_creds, auth, delete_records, "suppliers", "suppliers", snap_dir)
    snap = get_snapshot("suppliers", snap_dir)
    assert len(snap) == 1 and snap.iloc[0]["remoteId"] == "a", snap

    methods = [m for m, _ in auth.calls]
    assert methods == ["POST", "POST", "PATCH", "DELETE"], methods

print("SMOKE TEST OK - imports, payload dispatcher, run_posts/run_patches/run_deletes + snapshots all behave")
