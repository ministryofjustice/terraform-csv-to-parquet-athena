import logging
import os
import re
from pathlib import PurePosixPath
from typing import Optional

import boto3
import awswrangler as wr
import pandas as pd
from awswrangler.exceptions import AlreadyExists

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Global S3 client
s3 = boto3.client("s3")


def env_bool(name: str, default: bool = False) -> bool:
    """Interpret an environment variable as a boolean."""

    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y"}


def derive_table_name(s3_key: str, name_strategy: str) -> str:
    """Derive Athena table name from S3 key based on configured strategy."""

    strategies = {
        "use_full_filename": derive_name_from_full_filename,
        "split_at_last_underscore": derive_name_from_key,
    }

    if name_strategy not in strategies:
        raise ValueError(f"Unknown name_strategy: {name_strategy}")

    return strategies[name_strategy](s3_key)


def validate_base(base: str, original: str) -> str:
    """Ensure base name is Athena-safe and return normalized version."""

    if not re.match(r"^[a-zA-Z][\w]*$", base):
        raise ValueError(
            f"Invalid table name '{base}' from '{original}'. "
            "Must start with a letter and contain only alphanumerics/_"
        )

    return base.lower()[:255]


def derive_name_from_full_filename(s3_key: str) -> str:
    """Derive table name directly from full filename (without extension)."""

    filename = PurePosixPath(s3_key).name
    base, ext = os.path.splitext(filename)
    if ext.lower() != ".csv":

        raise ValueError(f"Expected a .csv file, got '{ext}'")
    if not base:
        raise ValueError(f"No valid base name in '{filename}'")

    return validate_base(base, filename)


def derive_name_from_key(s3_key: str) -> str:
    """Derive table name by removing last underscore and suffix from filename."""

    filename = PurePosixPath(s3_key).name
    base, ext = os.path.splitext(filename)

    if ext.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, got '{ext}'")

    if "_" not in base:
        raise ValueError(f"No underscore found in '{filename}' to split on")

    before_last = base.rsplit("_", 1)[0]

    if not before_last:
        raise ValueError(f"No text before last underscore in '{filename}'")

    return validate_base(before_last, filename)


def ensure_database(db_name: str) -> None:
    """Ensure Glue database exists."""

    if not db_name:
        raise ValueError("GLUE_DATABASE environment variable is required")
    try:
        wr.catalog.create_database(name=db_name, exist_ok=True)
    except AlreadyExists:
        pass


def delete_prefix(s3_client, bucket: str, prefix: str) -> None:
    """Delete all objects under the given S3 prefix using the given client."""

    paginator = s3_client.get_paginator("list_objects_v2")
    batch = []
    total_deleted = 0

    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            batch.append({"Key": obj["Key"]})
            if len(batch) == 1000:
                s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
                total_deleted += len(batch)
                batch.clear()

    if batch:
        s3_client.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        total_deleted += len(batch)

    logger.info(f"Deleted {total_deleted} objects from s3://{bucket}/{prefix}")


def deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure unique and sanitized column names; never empty."""

    seen = {}
    new_cols = []

    for col in df.columns:
        base = re.sub(r"\W+", "_", col).lower().strip("_")
        if not base:
            base = "col"
        count = seen.get(base, 0)
        new_col = base if count == 0 else f"{base}_{count}"
        new_cols.append(new_col)
        seen[base] = count + 1

    df.columns = new_cols
    return df


def clean_nbsp_and_strip(df: pd.DataFrame) -> pd.DataFrame:
    """Replace non-breaking spaces and strip whitespace from strings in DataFrame."""

    df = df.copy()
    df.columns = [c.replace("\u00a0", " ").strip() for c in df.columns]

    obj_cols = df.select_dtypes(include=["object"]).columns
    df[obj_cols] = df[obj_cols].apply(
        lambda col: col.map(
            lambda x: x.replace("\u00a0", " ").strip() if isinstance(x, str) else x
        )
    )
    return df


def read_csv_safely(
    s3_uri: str, explicit_encoding: Optional[str] = None
) -> pd.DataFrame:
    """Read CSV from S3 trying multiple encodings if necessary."""

    encodings = [explicit_encoding] if explicit_encoding else []
    encodings += ["utf-8", "utf-8-sig", "cp1252", "iso-8859-1"]
    tried = []

    for enc in filter(None, encodings):
        try:
            return wr.s3.read_csv(
                s3_uri,
                encoding=enc,
                sep=None,
                engine="python",
                dtype_backend="pyarrow",
                on_bad_lines="skip",
            )
        except UnicodeDecodeError:
            tried.append(enc)

    raise ValueError(f"Failed to decode CSV using encodings: {', '.join(tried)}")


def stabilize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Attempt to convert object columns to more specific types."""

    df = df.copy()  # Avoid SettingWithCopyWarning
    obj_cols = df.select_dtypes(include=["object"]).columns

    truthy = {"true", "t", "yes", "y", "1"}
    falsy = {"false", "f", "no", "n", "0"}

    for c in obj_cols:
        col = df[c]

        if not col.notna().any():
            df[c] = col.astype("string")
            continue

        sample = col.dropna().astype(str).str.strip()
        lower = sample.str.lower()
        unique = set(lower.unique())

        # Boolean detection
        if unique.issubset(truthy | falsy) and len(unique) <= 2:
            df[c] = lower.map(
                lambda x: x in truthy if x in truthy | falsy else pd.NA
            ).astype("boolean")
            continue

        # Datetime detection
        dt = pd.to_datetime(sample, errors="coerce", infer_datetime_format=True)
        if dt.notna().mean() >= 0.9:
            df[c] = pd.to_datetime(col, errors="coerce")
            continue

        # Numeric detection
        num = pd.to_numeric(sample.str.replace(",", ""), errors="coerce")
        if num.notna().mean() >= 0.9:
            cleaned = pd.to_numeric(
                col.astype(str).str.replace(",", ""), errors="coerce"
            )
            df[c] = (
                cleaned.astype("Int64")
                if cleaned.dropna().mod(1).eq(0).all()
                else cleaned
            )
            continue

        df[c] = col.astype("string")

    return df


def handler(event, context):
    """AWS Lambda handler to convert CSV in S3 to Parquet and register in Glue Catalog."""

    logger.info(f"Event received: {event}")

    try:
        csv_bucket = event["csv_upload_bucket"]
        csv_key = event["csv_upload_key"]
        output_bucket = event["output_bucket"]
        extraction_ts = event["extraction_timestamp"]

        # Optional arguments
        encoding = event.get("encoding") or os.getenv("CSV_ENCODING")
        allow_conversion = env_bool("ALLOW_TYPE_CONVERSION", False)
        load_mode = os.getenv("LOAD_MODE", "overwrite").lower()
        glue_database = os.getenv("GLUE_DATABASE")

        if not glue_database:
            raise ValueError("GLUE_DATABASE environment variable is required")

        table_naming = os.getenv("TABLE_NAMING", "use_full_filename").lower()
        prefix = os.getenv("PARQUET_PREFIX", "").strip("/")

        table_name = derive_table_name(csv_key, table_naming)
        table_prefix = f"{prefix}/{table_name}/" if prefix else f"{table_name}/"
        dataset_root = f"s3://{output_bucket}/{table_prefix}"

        logger.info(
            f"CSV: s3://{csv_bucket}/{csv_key} -> {dataset_root} "
            f"(table={table_name}, db={glue_database}, mode={load_mode})"
        )

        ensure_database(glue_database)

        if load_mode == "overwrite":
            logger.info("Overwrite mode: clearing existing dataset")
            delete_prefix(s3, output_bucket, table_prefix)
            wr.catalog.delete_table_if_exists(glue_database, table_name)

        elif load_mode != "incremental":
            raise ValueError("load_mode must be 'incremental' or 'overwrite'")

        df = read_csv_safely(f"s3://{csv_bucket}/{csv_key}", explicit_encoding=encoding)
        logger.info(f"Loaded DataFrame: {df.shape[0]} rows / {df.shape[1]} columns")

        # Clean, deduplicate columns, convert types
        df = clean_nbsp_and_strip(df)
        df = deduplicate_columns(df)

        if allow_conversion:
            df = stabilize_dtypes(df)

        # Add partition column
        df["extraction_timestamp"] = extraction_ts

        wr.s3.to_parquet(
            df=df,
            path=dataset_root,
            dataset=True,
            partition_cols=["extraction_timestamp"],
            database=glue_database,
            table=table_name,
            schema_evolution=True,
        )

        logger.info(f"Write complete: {glue_database}.{table_name}")

    except Exception:
        logger.exception("Error converting CSV to Parquet")
        raise
