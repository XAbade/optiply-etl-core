import json
import os

from optiply_etl.tools import snapshot_records, delete_from_snapshot, get_snapshot

optiply_base_url = os.environ.get('optiply_base_url', 'https://api.optiply.com/v1')
print("optiply_base_url: ", optiply_base_url)


# POST RECORDS TO OPTIPLY
def post_optiply(api_creds, auth, payload, entity):
    url = f"{optiply_base_url}/{entity}?accountId={api_creds['account_id']}&couplingId={api_creds['couplingId']}"

    # Preparing payload for the entity
    payload = json.dumps({
        "data": {
            "type": entity,
            "attributes": payload
        }
    })

    response = auth._request("POST", url=url, data=payload)
    return response


# PATCH RECORDS TO OPTIPLY
def patch_optiply(api_creds, auth, payload, optiply_id, entity):
    url = f"{optiply_base_url}/{entity}/{optiply_id}?accountId={api_creds['account_id']}&couplingId={api_creds['couplingId']}"

    # Preparing payload for the entity
    payload = json.dumps({
        "data": {
            "type": entity,
            "attributes": payload
        }
    })

    response = auth._request("PATCH", url=url, data=payload)
    return response


# DELETE RECORDS TO OPTIPLY
def delete_optiply(api_creds, auth, optiply_id, entity):
    url = f"{optiply_base_url}/{entity}/{optiply_id}?accountId={api_creds['account_id']}&couplingId={api_creds['couplingId']}"

    response = auth._request("DELETE", url=url)
    return response


# GET RECORDS TO OPTIPLY
def get_optiply(api_creds, auth, url):
    response = auth._request("GET", url=url)
    return response


###--------- REQUESTS TO OPTIPLY (template loops shared by every entity) ---------###

def run_deletes(api_creds, auth, delete_records, entity, snapshot_name, snapshot_dir, pk="remoteId"):
    delete_records = delete_records.copy()
    delete_records["optiply_id"] = delete_records["optiply_id"].astype(float).astype(int)
    total_records = len(delete_records)
    delete_records = delete_records.reset_index(drop=True)

    try:
        for i, row in delete_records.iterrows():
            print(f"Record: {i+1} of Total: {total_records}")
            optiply_id = int(row['optiply_id'])
            response = delete_optiply(api_creds, auth, optiply_id, entity=entity)

            if response.status_code == 404:
                print(f"Record {optiply_id} is already deleted in Optiply, skipping this record.")
                continue

            # Raise exception manually for any other unsuccessful status
            if not response.ok:
                raise Exception(f"Failed to delete record {optiply_id} - Status code: {response.status_code}")

        # If loop completes successfully, proceed to delete from snapshot
        delete_from_snapshot(delete_records, snapshot_name, snapshot_dir, pk=pk)

        # buyOrders: also remove the deleted orders' lines from the buy_order_lines snapshot
        if entity == "buyOrders":
            buy_order_lines_snap = get_snapshot("buy_order_lines", snapshot_dir)
            if buy_order_lines_snap is not None:
                buy_order_lines_snap["Remote_buyOrderId"] = buy_order_lines_snap["Remote_buyOrderId"].astype(str)
                delete_records["remoteId"] = delete_records["remoteId"].astype(str)
                # Get matching records to delete
                filtered_lines = buy_order_lines_snap[
                    buy_order_lines_snap["Remote_buyOrderId"].isin(delete_records["remoteId"])
                ]
                delete_from_snapshot(filtered_lines, "buy_order_lines", snapshot_dir, pk="remoteId")
                del buy_order_lines_snap

    except Exception as e:
        raise Exception(f"ETL FAILED WHILE DELETING RECORDS\n{e}")


def run_posts(api_creds, auth, new_records, entity, snapshot_name, snapshot_dir, get_payload_fn, pk="remoteId"):
    new_records_ = new_records.copy()
    new_records_["remoteId"] = new_records_["remoteId"].astype(str)
    new_records_ = new_records_.reset_index(drop=True)
    new_records_["optiply_id"] = None
    new_records_["optiply_uuid"] = None
    total_records = len(new_records_)

    try:
        for i, row in new_records_.iterrows():
            print(f"Record: {i+1} of Total: {total_records}")
            payload = get_payload_fn(row, entity)
            response = post_optiply(api_creds, auth, payload, entity=entity)

            if entity == "suppliers" and response.status_code == 400 and "not a valid address" in response.text.lower():
                print(f"Record for supplier.remoteId:{row['remoteId']} has an invalid address, removing emails from payload and posting again.")
                # remove emails from payload
                payload.pop("emails")
                response = post_optiply(api_creds, auth, payload, entity=entity)

                new_records_.loc[i, "optiply_id"] = str(response.json()["data"]["id"])
                new_records_.loc[i, "optiply_uuid"] = str(response.json()["data"]["attributes"]["uuid"])

            elif entity == "supplierProducts" and response.status_code == 409:
                supplier_id = int(row['supplierId'])
                product_id = int(row['productId'])
                print(f"Record for supplierId:{supplier_id} and productId:{product_id} already exists in Optiply, getting the optiply_id for this record.")
                url = f"{optiply_base_url}/supplierProducts?filter[supplierId]={row['supplierId']}&filter[productId]={row['productId']}"
                response = get_optiply(api_creds, auth, url)

                new_records_.loc[i, "optiply_id"] = str(response.json()["data"][0]["id"])
                new_records_.loc[i, "optiply_uuid"] = str(response.json()["data"][0]["attributes"]["uuid"])

            else:
                # Keeping the data for the new records
                new_records_.loc[i, "optiply_id"] = str(response.json()["data"]["id"])
                new_records_.loc[i, "optiply_uuid"] = str(response.json()["data"]["attributes"]["uuid"])

    except:
        raise Exception(f"ETL FAILED WHILE POSTING RECORDS -- SNAPSHOTTING POSTED RECORDS")

    finally:
        # Filter out records without 'optiply_uuid' (Non-posted records)
        new_records_ = new_records_[~new_records_["optiply_uuid"].isna()]
        new_records_["optiply_id"] = new_records_["optiply_id"].astype(float).astype(int)
        # sellOrders: only remoteId/optiply_id/optiply_uuid are kept in the snapshot
        if entity == "sellOrders":
            new_records_ = new_records_[["remoteId", "optiply_id", "optiply_uuid"]]
        snapshot_records(new_records_, snapshot_name, snapshot_dir, pk=pk)


def run_patches(api_creds, auth, update_records, entity, snapshot_name, snapshot_dir, get_payload_fn):
    # supplierProducts snapshot on concat_ids and accept 201 (repost of a 404'd record)
    snapshot_pk = "concat_ids" if entity == "supplierProducts" else "remoteId"
    success_codes = [200, 201] if entity == "supplierProducts" else [200]

    update_records = update_records.copy()
    update_records["remoteId"] = update_records["remoteId"].astype(str)
    update_records["optiply_id"] = update_records["optiply_id"].astype(float).astype(int)
    if entity == "buyOrderLines":
        update_records["buyOrderId"] = update_records["buyOrderId"].astype(float).astype(int)
        update_records["productId"] = update_records["productId"].astype(float).astype(int)
    update_records["response_code"] = None
    total_records = len(update_records)
    update_records = update_records.reset_index(drop=True)

    if "optiply_uuid" in update_records.columns:
        update_records["optiply_uuid"] = None

    try:
        for i, row in update_records.iterrows():
            print(f"Record: {i+1} of Total: {total_records}")
            optiply_id = int(row['optiply_id'])
            payload = get_payload_fn(row, entity)
            response = patch_optiply(api_creds, auth, payload, optiply_id, entity=entity)

            if entity == "suppliers" and response.status_code == 400 and "not a valid address" in response.text.lower():
                print(f"Record for supplier.remoteId:{row['remoteId']} has an invalid address, removing emails from payload and patching again.")
                # remove emails from payload
                payload.pop("emails")
                response = patch_optiply(api_creds, auth, payload, optiply_id, entity=entity)

            elif entity == "supplierProducts" and response.status_code == 404:
                print(f"Record {optiply_id} is already deleted in Optiply, posting it again since it still exists in remote system.")
                # set optiply_id to None so we can POST the record and get a new optiply_id
                update_records.loc[i, "optiply_id"] = None
                payload = get_payload_fn(row, entity)
                response = post_optiply(api_creds, auth, payload, entity=entity)
                update_records.loc[i, "optiply_id"] = str(response.json()["data"]["id"])

            # Keeping response_code for the update_records so we can filter them before snapshotting
            update_records.loc[i, "response_code"] = response.status_code
            update_records.loc[i, "optiply_uuid"] = str(response.json()["data"]["attributes"]["uuid"])

    except:
        raise Exception(f"ETL FAILED WHILE PATCHING RECORDS -- SNAPSHOTTING SUCCESSFULY PATCHED RECORDS")

    finally:
        # keep only records where response code is a success code
        update_records = update_records[update_records["response_code"].isin(success_codes)]
        update_records = update_records.drop(columns=["response_code"])
        update_records["optiply_id"] = update_records["optiply_id"].astype(float).astype(int)
        snapshot_records(update_records, snapshot_name, snapshot_dir, pk=snapshot_pk)
