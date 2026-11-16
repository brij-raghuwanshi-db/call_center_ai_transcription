from __future__ import annotations

from datetime import datetime
from enum import Enum

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

from .core import logger

DEFAULT_WAREHOUSE_ID = "c22b90f5361e6720"


def persist_row(
    ws: WorkspaceClient | None,
    config,
    table: str,
    key_column: str,
    values: dict[str, object],
) -> bool:
    if ws is None:
        return False
    warehouse_id = getattr(config, "warehouse_id", None) or DEFAULT_WAREHOUSE_ID
    catalog = getattr(config, "uc_catalog", "classic_stable_84t3jv_catalog")
    schema = getattr(config, "uc_schema", "toyota_callcenter")
    full_name = f"{catalog}.{schema}.{table}"
    assignments = ", ".join(
        f"t.{_ident(column)} = s.{_ident(column)}" for column in values if column != key_column
    )
    insert_columns = ", ".join(_ident(column) for column in values)
    insert_values = ", ".join(f"s.{_ident(column)}" for column in values)
    select_sql = ", ".join(
        f"{_sql_literal(value)} AS {_ident(column)}" for column, value in values.items()
    )
    statement = (
        f"MERGE INTO {full_name} AS t USING (SELECT {select_sql}) AS s "
        f"ON t.{_ident(key_column)} = s.{_ident(key_column)} "
        f"WHEN MATCHED THEN UPDATE SET {assignments} "
        f"WHEN NOT MATCHED THEN INSERT ({insert_columns}) VALUES ({insert_values})"
    )
    try:
        response = ws.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=statement,
            wait_timeout="0s",
        )
        state = getattr(getattr(response, "status", None), "state", None)
        accepted = {
            StatementState.SUCCEEDED,
            StatementState.PENDING,
            StatementState.RUNNING,
            "SUCCEEDED",
            "PENDING",
            "RUNNING",
            None,
        }
        if state not in accepted:
            logger.warning("UC persist %s state=%s", full_name, state)
            return False
        return True
    except Exception as error:
        logger.warning("UC persist failed for %s: %s", full_name, error)
        return False


def _ident(name: str) -> str:
    return f"`{name}`"


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Enum):
        return _sql_literal(value.value)
    if isinstance(value, datetime):
        return f"TIMESTAMP '{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{text}'"
