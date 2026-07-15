import os
import pandas as pd
import json
from datetime import datetime

###--------- SNAPSHOT FUNCTIONS ---------###
def get_snapshot(stream, snapshot_dir, converters={}):
    if os.path.isfile(f"{snapshot_dir}/{stream}.snapshot.csv"):
        snapshot = pd.read_csv(f"{snapshot_dir}/{stream}.snapshot.csv", converters=converters, dtype="object")
    else:
        snapshot = None

    return snapshot


def delete_from_snapshot(delete_items, stream, snapshot_dir, pk="id"):
    if os.path.isfile(f"{snapshot_dir}/{stream}.snapshot.csv"):
        snapshot = pd.read_csv(f"{snapshot_dir}/{stream}.snapshot.csv", dtype="object")
        snapshot[pk] = snapshot[pk].astype(str)
    else:
        return None
    delete_items[pk] = delete_items[pk].astype(str)
    delete_items = pd.concat([snapshot, delete_items])
    delete_items = delete_items.drop_duplicates(pk, keep=False)
    delete_items.to_csv(f"{snapshot_dir}/{stream}.snapshot.csv", index=False)

    return delete_items


def snapshot_records(stream_data, stream, snapshot_dir, pk="id", return_full=False):
    if stream_data is None:
        return None

    return_data = None

    if os.path.isfile(f"{snapshot_dir}/{stream}.snapshot.csv"):
        snapshot = pd.read_csv(f"{snapshot_dir}/{stream}.snapshot.csv", dtype="object")
        snapshot[pk] = snapshot[pk].astype(str)
    else:
        snapshot = None

    if snapshot is not None:
        # If snapshot is present, drop any duplicats from the return data
        stream_data[pk] = stream_data[pk].astype(str)
        stream_data = pd.concat([snapshot, stream_data])
        return_data = stream_data.drop_duplicates(pk, keep=False)
        # Save the updated snapshot
        stream_data = stream_data.drop_duplicates(pk, keep="last")
        stream_data.to_csv(f"{snapshot_dir}/{stream}.snapshot.csv", index=False)
        if return_full:
            return stream_data
    else:
        # Otherwise, snapshot and use stream_data as the return
        stream_data.to_csv(f"{snapshot_dir}/{stream}.snapshot.csv", index=False)
        return_data = stream_data

    return return_data


# Utils functions
def clean_payload(item):
    item = clean_dict_items(item)
    output = {}
    for k, v in item.items():
        if isinstance(v, datetime):
            dt_str = v.strftime("%Y-%m-%dT%H:%M:%SZ")
            if len(dt_str) > 20:
                output[k] = f"{dt_str[:-2]}:{dt_str[-2:]}"
            else:
                output[k] = dt_str
        elif isinstance(v, dict):
            output[k] = clean_payload(v)
        else:
            output[k] = v
    return output

def clean_dict_items(dict, value=None):
    return {k: v for k, v in dict.items() if v is not None}


# Extract remoteID from an Optiply API response
def extract_remoteId(obj):
    remoteId = obj.get("remoteIdMap")
    key = list(remoteId.keys())[0]
    remote_id = remoteId[key]
    return remote_id

# Handle invalid date formats or invalid dates out of range çike year 3000
def handle_invalid_dates(date_str, date_format='%Y-%m-%dT%H:%M:%S'):
    try:
        dt = pd.to_datetime(date_str, format=date_format)
        return dt
    except ValueError:
        return pd.NaT

# Concatenate columns - Used to compare product changes
def concat_columns(df, columns, sep='|'):
    # Select the specified columns and convert them to strings
    selected = df[columns].astype(str)
    
    # Concatenate the selected columns for each row
    concatenated = selected.apply(lambda x: sep.join(x), axis=1)
    return concatenated

# check Price values - round to 2 decimal
def round_to_2(value):
    if pd.isna(value) or not value or not str(value).replace(".", "").replace("-", "").isnumeric():
        return 0
    elif float(value) > 9999999.99: # maximum our API accepts for a Price or Stock
        return 0
    else:
        return round(float(value), 2)

# check Stock values - round to integer
def round_to_0(value):
    if pd.isna(value) or not value or not str(value).replace(".", "").replace("-", "").isnumeric():
        return 0
    elif float(value) > 9999999.99: # maximum our API accepts for a Price or Stock
        return 0
    else:
        value = round(float(value), 2)
        return int(value)
    
# set NaN values to None on final payloads
def nan_to_none(value):
    return None if pd.isna(value) else value

# Function to validate EAN codes
def validate_attribute(value):
    if not pd.isna(value) and not pd.isnull(value) and len(str(value)) > 0:
        return str(value)
    else:
        return None

def convert_to_bool(val):
    if isinstance(val, bool):
        return val
    elif isinstance(val, str):
        if val.lower() == 'true':
            return True
        elif val.lower() == 'false':
            return False
    return val

# round numeric values to 0 decimal places except NaN, None, pd.NA
def round_numeric_to_0(value):
    if pd.isna(value):
        return value  # leave as is (NaN, None, pd.NA)
    if not value or not str(value).replace(".", "").replace("-", "").isnumeric():
        return 0
    elif float(value) > 9999999.99:
        return 0
    else:
        value = round(float(value), 2)
        return int(value)

# round numeric values to 2 decimal places except NaN, None, pd.NA
def round_numeric_to_2(value):
    if pd.isna(value):
        return value  # leave as is (NaN, None, pd.NA)
    if not value or not str(value).replace(".", "").replace("-", "").isnumeric():
        return 0
    elif float(value) > 9999999.99:
        return 0
    else:
        return round(float(value), 2)

# check if the request was successful
def is_success_request(code):
    return code is not None and 200 <= code < 300

###--------- CUSTOM MAPPINGS ---------###
'''
config.json example:
{
    "custom_mappings": {
        "products": {
            "ProductCode": "ProductCode"
        },
        "supplier_products/changed_item_suppliers_with_defaults": {
            "lotSize": "MinPurchaseQty"
        },
        "suppliers": {
            "SupplierCode": "SupplierCode"
        }
    }
}
'''
# Get custom mappings from config.json
def get_custom_mappings():
    CONFIG_PATH = "./config.json"
    if not os.path.exists(CONFIG_PATH):
        raise Exception("No 'config.json' provided.")

    # 1. Load the original data
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    # 2. Recursive function to physically delete keys with null values
    def scrub_none_values(obj):
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                if obj[key] is None:
                    del obj[key]
                else:
                    scrub_none_values(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                scrub_none_values(item)

    scrub_none_values(config)

    # 3. Overwrite config.json with the cleaned data
    with open(CONFIG_PATH, "w") as f:
        # indent=4 keeps the file human-readable
        json.dump(config, f, indent=4)

    # 4. Extract mappings for return
    custom_mapping_data = config.get("custom_mappings", {})
    
    prod_key = next((k for k in custom_mapping_data if k.startswith("products")), None)
    sup_key = next((k for k in custom_mapping_data if k.startswith("suppliers")), None)
    supp_key = next((k for k in custom_mapping_data if k.startswith("supplier_products")), None)

    # Assign mappings; return None if they are empty {}
    custom_product_mapping = custom_mapping_data.get(prod_key) if prod_key else None
    if not custom_product_mapping:
        custom_product_mapping = None

    custom_supplier_mapping = custom_mapping_data.get(sup_key) if sup_key else None
    if not custom_supplier_mapping:
        custom_supplier_mapping = None

    custom_supplier_product_mapping = custom_mapping_data.get(supp_key) if supp_key else None
    if not custom_supplier_product_mapping:
        custom_supplier_product_mapping = None

    return custom_product_mapping, custom_supplier_mapping, custom_supplier_product_mapping

# Apply custom mapping to input data
def apply_final_mapping(input_data, base_mapping, custom_mapping=None):
    """
    Merges mappings and transforms input data into a structured DataFrame.
    Returns None if no data is available or result is empty.
    """
    # 1. Merge standard and custom mappings
    # If custom_mapping exists, it overrides base_mapping keys
    if custom_mapping:
        final_mapping = {
            key: custom_mapping.get(key, value) 
            for key, value in base_mapping.items()
        }
    else:
        final_mapping = base_mapping

    # 2. Process the sync data
    if input_data is not None and not input_data.empty:
        # Create new DataFrame using the final mapping
        # This maps: target_column = input_data[source_column]
        result_df = pd.DataFrame()
        for final_col, source_col in final_mapping.items():
            if source_col in input_data.columns:
                result_df[final_col] = input_data[source_col]
        
        # Return None if the resulting DataFrame is empty
        return result_df if not result_df.empty else None
    
    return None


###--------- SET CORRECT SNAPSHOT DIR TO GET DATA FROM ---------###
# --- SubTenant Setup ---
ROOT_DIR = os.environ.get("ROOT_DIR", ".")
SNAPSHOT_DIR = f"{ROOT_DIR}/snapshots/"
PARENT_SNAPSHOT_DIR = f"{ROOT_DIR}/parent-snapshots/"

# Only these two can ever come from parent
PARENT_ELIGIBLE = {"products", "suppliers"}

# config.json is read lazily so the package can be imported outside a flow
# directory (local dev, tests). The ETL notebook still fails fast on a
# missing config.json at startup.
_not_sync_entities = None

def _get_not_sync_entities():
    global _not_sync_entities
    if _not_sync_entities is None:
        config_path = f"./config.json"
        if os.path.exists(config_path):
            with open(config_path) as f:
                config = json.load(f)
        else:
            config = {}
        raw = config.get("not_sync_entities", "")
        _not_sync_entities = [e.strip() for e in raw.split(",") if e.strip()]
    return _not_sync_entities

def resolve_snapshot_dir(snapshot_name):
    """
    For products and suppliers: use PARENT_SNAPSHOT_DIR if this is a subtenant
    (parent-snapshots exists) AND the entity is not being synced locally.
    Everything else always uses local SNAPSHOT_DIR.
    """
    if (
        snapshot_name in PARENT_ELIGIBLE
        and os.path.exists(PARENT_SNAPSHOT_DIR)
        and snapshot_name in _get_not_sync_entities()
    ):
        return PARENT_SNAPSHOT_DIR
    return SNAPSHOT_DIR