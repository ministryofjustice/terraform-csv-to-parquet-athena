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

# Accepts optional trailing 'Z' in the timestamp (e.g., 20250902103213Z.csv)
TIMESTAMP_RE = re.compile(
    r"""^
    (?P<name>.+?)           # everything up to the underscore before timestamp
    _(?P<ts>\d{14})         # YYYYMMDDHHMMSS (14 digits)
    (?:Z)?                  # optional 'Z'
    \.csv$
    """,
    re.VERBOSE | re.IGNORECASE,
)


def sanitize_table_name(name: str) -> str:
    n = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
    if not re.match(r"^[a-z]", n):
        n = f"t_{n}"
    return n[:255]


def parse_key(key: str) -> tuple[str, str]:
    fn = key.split("/")[-1]
    m = TIMESTAMP_RE.match(fn)
    if not m:
        raise ValueError(
            f"csv_upload_key '{key}' must look like Name_YYYYMMDDHHMMSS.csv (optional trailing 'Z')"
        )
    return m.group("name"), m.group("ts")


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
      "encoding": "utf-8"                          # optional
    }
    """
    try:
        csv_bucket = event["csv_upload_bucket"]
        csv_key = event["csv_upload_key"]
        out_bucket = event["output_bucket"]
        forced_encoding = event.get("encoding") or os.getenv("CSV_ENCODING")
        load_mode = LOAD_MODE.lower()

        base_name, ts_from_key = parse_key(csv_key)

        # Parse the 14-digit timestamp from filename to a pandas/Arrow-friendly datetime
        extraction_ts_dt = pd.to_datetime(ts_from_key, format="%Y%m%d%H%M%S", utc=False)

        table_name = sanitize_table_name(base_name)
        glue_db = GLUE_DATABASE

        input_path = f"s3://{csv_bucket}/{csv_key}"
        base_prefix = f"{PARQUET_PREFIX.strip('/')}/" if PARQUET_PREFIX else ""
        table_prefix = f"{base_prefix}{table_name}/"
        dataset_root = f"s3://{out_bucket}/{table_prefix}"

        # Ensure DB exists
        ensure_database(glue_db)

        # ---- NEW: load_mode handling ----
        if load_mode == "overwrite":
            # 1) Delete all data under the table's prefix
            _delete_prefix(out_bucket, table_prefix)
            # 2) Drop the Glue table so old partitions/schema are removed
            wr.catalog.delete_table_if_exists(database=glue_db, table=table_name)
        elif load_mode != "incremental":
            raise ValueError("load_mode must be 'incremental' or 'overwrite'")

        # Robust CSV read + cleanup
        df = read_csv_safely(input_path, explicit_encoding=forced_encoding)
        df = _clean_nbsp_and_strip(df)
        df = _deduplicate_columns(df)
        df = _stabilize_dtypes(df)

        # Add partition column
        df["extraction_timestamp"] = extraction_ts_dt

        # Write Parquet + update Glue catalog
        wr.s3.to_parquet(
            df=df,
            path=dataset_root,
            dataset=True,
            partition_cols=["extraction_timestamp"],
            database=glue_db,
            table=table_name,
            schema_evolution=True,
            # e.g., max_rows_by_file=500_000,
        )

        # Archive file after succesffully writeen to glue table
        date_path = extraction_ts_dt.strftime("%Y/%m/%d")
        filename = csv_key.split("/")[-1]
        base_prefix = "raw_history/"
        dest_key = f"{base_prefix}{table_name}/{date_path}/{filename}"
        s3.copy_object(
            Bucket=csv_bucket,
            Key=dest_key,
            CopySource={"Bucket": csv_bucket, "Key": csv_key},
            MetadataDirective="COPY",
        )

        # Delete original
        s3.delete_object(Bucket=csv_bucket, Key=csv_key)

    except Exception as e:
        logger.error(f"Error converting CSV to Parquet: {str(e)}")
        raise
