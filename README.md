# optiply-etl-core

Shared template logic for Optiply hotglue ETL flows. Everything in here is
connector-agnostic: a connector's `etl.ipynb` keeps only its source-specific
("Custom") mapping cells and calls into this package for the rest.

## Modules

| Module | Contents |
|---|---|
| `optiply_etl.auth` | `OptiplyAuthenticator` (token handling, retries) |
| `optiply_etl.tools` | Snapshot helpers, value cleaning/rounding, custom mappings, `resolve_snapshot_dir` |
| `optiply_etl.models` | Pydantic models for every Optiply entity |
| `optiply_etl.payloads` | Per-entity payload builders + `get_payload_function(row, entity)` dispatcher |
| `optiply_etl.actions` | `post/patch/delete/get_optiply` + the shared request loops `run_deletes`, `run_posts`, `run_patches` |

## Per-entity behavior baked into the request loops

- **suppliers**: on `400 … not a valid address`, retry POST/PATCH without `emails`.
- **supplierProducts**: POST `409` → GET existing record's id; PATCH `404` → re-POST; snapshots on `concat_ids`; success codes `200/201`.
- **buyOrders**: after DELETE, matching lines are removed from the `buy_order_lines` snapshot.
- **buyOrderLines**: `buyOrderId`/`productId` cast to int before PATCH.
- **sellOrders**: only `remoteId`/`optiply_id`/`optiply_uuid` are snapshotted after POST.

## Usage in a hotglue flow

`requirements.txt` of the flow — always pin a tag, never a branch:

```
optiply-etl-core @ git+https://github.com/XAbade/optiply-etl-core@v0.1.0
```

(For a private repo, hotglue's env needs a token: `git+https://${GITHUB_TOKEN}@github.com/...`.)

In the notebook:

```python
from optiply_etl.auth import OptiplyAuthenticator
from optiply_etl.tools import snapshot_records, get_snapshot, delete_from_snapshot, ...
from optiply_etl.payloads import get_payload_function
from optiply_etl.actions import run_deletes, run_posts, run_patches

# ... custom mapping + global mapping + snapshot diff per entity ...

if delete_records is not None:
    run_deletes(api_creds, auth, delete_records, entity, snapshot_name, SNAPSHOT_DIR)
if new_records is not None:
    run_posts(api_creds, auth, new_records, entity, snapshot_name, SNAPSHOT_DIR, get_payload_function)
if update_records is not None:
    run_patches(api_creds, auth, update_records, entity, snapshot_name, SNAPSHOT_DIR, get_payload_function)
```

## Releasing

1. Bump `version` in `pyproject.toml` (and `optiply_etl/__init__.py`).
2. Tag: `git tag v0.x.y && git push --tags`.
3. Upgrade flows one at a time by bumping the pin in their `requirements.txt`.
