import os
import re
import logging
import boto3
import awswrangler as wr
import pandas as pd
from awswrangler.exceptions import AlreadyExists

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

GLUE_DATABASE = os.getenv("GLUE_DATABASE")
PARQUET_PREFIX = os.getenv("PARQUET_PREFIX", "")

LOAD_MODE = os.getenv(
    "LOAD_MODE", "incremental"
).lower()  # "incremental" or "overwrite"

s3 = boto3.client("s3")


def derive_name_from_key(s3_key: str) -> str:
    """
    Convert an S3 CSV key to a valid Athena/Glue table name.
    Raises ValueError if the name contains invalid characters.
    """

    # Extract the filename
    filename = os.path.basename(s3_key)

    # Remove extension
    name, ext = os.path.splitext(filename)
    if ext.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, got {ext}")

    # Take part before first underscore
    base = name.split("_", 1)[0]

    if not base:
        raise ValueError(f"No valid name found before underscore in '{filename}'")

    # Check that it contains only letters, numbers, underscores
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", base):
        raise ValueError(
            f"Invalid table name '{base}'. Must start with a letter and contain only letters, numbers, and underscores."
        )

    # Lowercase and truncate to 255
    table_name = base.lower()[:255]

    return table_name


def ensure_database(db_name: str):
    try:
        wr.catalog.create_database(name=db_name, exist_ok=True)
    except AlreadyExists:
        pass  # safe to ignore if a concurrent create sneaks through


def _delete_prefix(bucket: str, prefix: str):
    """Delete all objects under s3://bucket/prefix (non-versioned buckets)."""
    paginator = s3.get_paginator("list_objects_v2")
    to_delete = {"Objects": []}
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            to_delete["Objects"].append({"Key": obj["Key"]})
            if len(to_delete["Objects"]) == 1000:
                s3.delete_objects(Bucket=bucket, Delete=to_delete)
                to_delete = {"Objects": []}
    if to_delete["Objects"]:
        s3.delete_objects(Bucket=bucket, Delete=to_delete)


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all column names are unique and Glue-safe.
    If duplicates exist after sanitization, suffix with _1, _2, ...
    """
    seen = {}
    new_cols = []
    for col in df.columns:
        base = re.sub(r"[^a-zA-Z0-9_]", "_", col).lower().strip("_")
        if base in seen:
            seen[base] += 1
            new_cols.append(f"{base}_{seen[base]}")
        else:
            seen[base] = 0
            new_cols.append(base)
    df.columns = new_cols
    return df


def _clean_nbsp_and_strip(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize headers
    df.columns = [c.replace("\u00a0", " ").strip() for c in df.columns]
    # Normalize string/object cells
    obj_cols = df.select_dtypes(include=["object"]).columns
    for c in obj_cols:
        df[c] = df[c].map(
            lambda x: x.replace("\u00a0", " ").strip() if isinstance(x, str) else x
        )
    return df


def read_csv_safely(s3_uri: str, explicit_encoding: str | None = None) -> pd.DataFrame:
    """
    Try common encodings and let pandas infer the delimiter.
    Prefer an explicit encoding if provided via env/event.
    """
    encodings = [explicit_encoding] if explicit_encoding else []
    encodings += ["utf-8", "utf-8-sig", "cp1252", "iso-8859-1"]
    tried = []
    for enc in [e for e in encodings if e]:
        try:
            return wr.s3.read_csv(
                s3_uri,
                encoding=enc,
                sep=None,  # sniff delimiter
                engine="python",
                dtype_backend="pyarrow",
                on_bad_lines="skip",
            )
        except UnicodeDecodeError:
            tried.append(enc)
            continue
    raise UnicodeDecodeError(
        "csv", b"", 0, 1, f"Failed to decode with encodings tried: {', '.join(tried)}"
    )


def _stabilize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Make Athena-friendly types:
    - All-null object columns -> string
    - Low-cardinality boolean-like text -> boolean
    - Parse datetimes when obvious
    - Otherwise object -> string
    """
    obj_cols = df.select_dtypes(include=["object"]).columns
    for c in obj_cols:
        col = df[c]

        if not col.notna().any():
            df[c] = col.astype("string")
            continue

        sample = col.dropna().astype(str).str.strip()
        lower = sample.str.lower()

        truthy = {"true", "t", "yes", "y", "1"}
        falsy = {"false", "f", "no", "n", "0"}
        unique_vals = set(lower.unique())
        if unique_vals.issubset(truthy | falsy) and len(unique_vals) <= 2:
            df[c] = lower.map(
                lambda x: True if x in truthy else (False if x in falsy else pd.NA)
            ).astype("boolean")
            continue

        dt = pd.to_datetime(
            sample, errors="coerce", utc=False, infer_datetime_format=True
        )
        if dt.notna().mean() >= 0.9:
            df[c] = pd.to_datetime(col, errors="coerce")
            continue

        num = pd.to_numeric(sample.str.replace(",", ""), errors="coerce")
        if num.notna().mean() >= 0.9:
            if (num.dropna() % 1 == 0).all():
                df[c] = pd.to_numeric(
                    col.astype(str).str.replace(",", ""), errors="coerce"
                ).astype("Int64")
            else:
                df[c] = pd.to_numeric(
                    col.astype(str).str.replace(",", ""), errors="coerce"
                )
            continue

        df[c] = col.astype("string")

    return df


def move_to_raw_history(
    *,
    bucket: str,
    src_key: str,
    table_name: str,
    dest_bucket: str | None = None,
):
    """
    Move s3://bucket/src_key -> s3://(dest_bucket or bucket)/raw_history/<table>/<filename>
    """
    filename = src_key.split("/")[-1]
    dest_bucket = dest_bucket or bucket
    dest_key = f"raw_history/{table_name}/{filename}"

    # Guard: don't delete if src and dest resolve to the same object
    if bucket == dest_bucket and src_key == dest_key:
        raise ValueError(
            f"Source and destination are identical: s3://{bucket}/{src_key}"
        )

    # Prepare copy args
    copy_source = {"Bucket": bucket, "Key": src_key}

    # 1) Copy
    s3.copy_object(
        Bucket=dest_bucket,
        Key=dest_key,
        CopySource=copy_source,  # or use the quoted string variant
        MetadataDirective="COPY",
    )

    # 2) Verify destination exists before deleting source
    s3.head_object(Bucket=dest_bucket, Key=dest_key)

    # 3) Delete source
    s3.delete_object(Bucket=bucket, Key=src_key)

    return {"archived_to": f"s3://{dest_bucket}/{dest_key}"}


def handler(event, context):
    """
    Event:
    {
      "csv_upload_bucket": "...",
      "csv_upload_key": "Asset_20250902103213Z.csv",
      "extraction_timestamp": "20250902103213Z",
      "output_bucket": "...",
      "name": "concept",
      "load_mode": "incremental" | "overwrite",
    }
    """
    try:
        logger.info(f"Received event: {event}")

        csv_bucket = event["csv_upload_bucket"]
        csv_key = event["csv_upload_key"]
        out_bucket = event["output_bucket"]
        forced_encoding = event.get("encoding") or os.getenv("CSV_ENCODING")
        load_mode = event.get("load_mode", LOAD_MODE).lower()
        extraction_timestamp = event["extraction_timestamp"]

        table_name = derive_name_from_key(csv_key)
        glue_db = GLUE_DATABASE

        input_path = f"s3://{csv_bucket}/{csv_key}"
        base_prefix = f"{PARQUET_PREFIX.strip('/')}/" if PARQUET_PREFIX else ""
        table_prefix = f"{base_prefix}{table_name}/"
        dataset_root = f"s3://{out_bucket}/{table_prefix}"

        logger.info(
            f"Processing file {input_path} "
            f"-> table={table_name}, db={glue_db}, mode={load_mode}, dest={dataset_root}"
        )

        # Ensure Glue database exists
        ensure_database(glue_db)
        logger.debug(f"Ensured Glue database: {glue_db}")

        if load_mode == "overwrite":
            logger.info(f"Overwriting existing dataset at {dataset_root}")
            _delete_prefix(out_bucket, table_prefix)
            wr.catalog.delete_table_if_exists(database=glue_db, table=table_name)
        elif load_mode != "incremental":
            raise ValueError("load_mode must be 'incremental' or 'overwrite'")

        # Read CSV
        logger.info(
            f"Reading CSV from {input_path} with encodings {forced_encoding or 'auto-detect'}"
        )

        df = read_csv_safely(input_path, explicit_encoding=forced_encoding)

        logger.info(
            f"Loaded DataFrame with {len(df)} rows and {len(df.columns)} columns"
        )

        # Clean + normalize
        df = _clean_nbsp_and_strip(df)
        df = _deduplicate_columns(df)
        df = _stabilize_dtypes(df)
        logger.debug(f"Columns after cleanup: {df.columns.tolist()}")

        # Add partition col
        df["extraction_timestamp"] = extraction_timestamp

        # Write parquet
        logger.info(
            f"Writing Parquet to {dataset_root} with partition extraction_timestamp={extraction_timestamp}"
        )
        wr.s3.to_parquet(
            df=df,
            path=dataset_root,
            dataset=True,
            partition_cols=["extraction_timestamp"],
            database=glue_db,
            table=table_name,
            schema_evolution=True,
        )
        logger.info(
            f"Successfully wrote {len(df)} records to Glue table {glue_db}.{table_name}"
        )

    except Exception as e:
        logger.exception(f"Error converting CSV to Parquet: {str(e)}")
        raise
