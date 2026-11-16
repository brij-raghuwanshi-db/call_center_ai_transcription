#!/usr/bin/env python3
"""Create Toyota operational tables, seed demo history, and retarget Genie."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

CATALOG = "classic_stable_84t3jv_catalog"
SCHEMA = "toyota_callcenter"
WAREHOUSE_ID = "c22b90f5361e6720"
GENIE_SPACE_ID = "01f1cd73a77c1162b80b4a86b2b72390"
APP_NAME = "toyota-call-center"
APP_SP = "app-3yllo1 toyota-call-center"
LAKEBASE_ENDPOINT = "projects/toyota-call-center/branches/production/endpoints/primary"
FQN = f"{CATALOG}.{SCHEMA}"

TABLE_DDL = {
    "calls": f"""
CREATE TABLE IF NOT EXISTS {FQN}.calls (
  call_id STRING,
  status STRING,
  scenario_id STRING,
  scenario_title STRING,
  family STRING,
  queue STRING,
  vehicle STRING,
  location STRING,
  coverage STRING,
  patient_name STRING,
  latest_transcript STRING,
  latest_intent STRING,
  current_risk_level STRING,
  current_recommendation_id STRING,
  disposition STRING,
  started_at TIMESTAMP,
  ended_at TIMESTAMP
) USING DELTA
COMMENT 'Toyota owner-support calls. Grain: one row per call_id. Use for volume, queues, problem families, risk, and live vs ended status. patient_name is the caller name in this demo.'
""",
    "transcript_segments": f"""
CREATE TABLE IF NOT EXISTS {FQN}.transcript_segments (
  segment_id STRING,
  call_id STRING,
  speaker STRING,
  text STRING,
  is_partial BOOLEAN,
  start_ms INT,
  end_ms INT,
  asr_latency_ms INT,
  confidence DOUBLE,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'ASR transcript turns for Toyota calls. Grain: one row per segment_id. Speaker Patient means the caller. Join to calls on call_id.'
""",
    "next_best_actions": f"""
CREATE TABLE IF NOT EXISTS {FQN}.next_best_actions (
  recommendation_id STRING,
  call_id STRING,
  trigger_segment_id STRING,
  intent STRING,
  topic STRING,
  patient_state STRING,
  risk_level STRING,
  urgency_level STRING,
  recommended_response STRING,
  next_best_action STRING,
  action_rationale STRING,
  confidence DOUBLE,
  should_escalate BOOLEAN,
  escalation_reason STRING,
  llm_latency_ms INT,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'Next-best-action recommendations produced during a call. Grain: one row per recommendation_id. Join to calls on call_id.'
""",
    "recommendation_alerts": f"""
CREATE TABLE IF NOT EXISTS {FQN}.recommendation_alerts (
  alert_row_id STRING,
  recommendation_id STRING,
  call_id STRING,
  alert_index INT,
  code STRING,
  title STRING,
  detail STRING,
  risk_level STRING,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'Safety and process alerts attached to a recommendation.'
""",
    "recommendation_citations": f"""
CREATE TABLE IF NOT EXISTS {FQN}.recommendation_citations (
  citation_row_id STRING,
  recommendation_id STRING,
  call_id STRING,
  citation_index INT,
  document_id STRING,
  title STRING,
  section STRING,
  quote STRING,
  score DOUBLE,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'Knowledge citations attached to a recommendation.'
""",
    "agent_feedback": f"""
CREATE TABLE IF NOT EXISTS {FQN}.agent_feedback (
  feedback_id STRING,
  recommendation_id STRING,
  call_id STRING,
  feedback_type STRING,
  free_text STRING,
  created_by STRING,
  created_at TIMESTAMP
) USING DELTA
COMMENT 'Agent quality labels on recommendations. feedback_type is used, helpful, not_helpful, wrong, or ignored.'
""",
    "call_closures": f"""
CREATE TABLE IF NOT EXISTS {FQN}.call_closures (
  call_id STRING,
  disposition STRING,
  family STRING,
  queue STRING,
  intent STRING,
  risk_level STRING,
  should_escalate BOOLEAN,
  transcript_count INT,
  recommendation_count INT,
  resolution_summary STRING,
  closed_by STRING,
  closed_at TIMESTAMP
) USING DELTA
COMMENT 'Call outcomes for analytics. disposition is resolved, transferred, escalated, or open. Grain: one row per call_id.'
""",
}


def load_token() -> None:
    lines = (ROOT / "token_Details").read_text(encoding="utf-8").splitlines()
    host = lines[0].strip().split("?", 1)[0].rstrip("/")
    token = lines[1].strip()
    os.environ["DATABRICKS_HOST"] = host
    os.environ["DATABRICKS_TOKEN"] = token
    os.environ.pop("DATABRICKS_CONFIG_PROFILE", None)
    os.environ.pop("DATABRICKS_AUTH_TYPE", None)
    os.environ["LAKEBASE_ENDPOINT"] = LAKEBASE_ENDPOINT
    print(f"Using host {host}")


def run_sql(ws, statement: str):
    from databricks.sdk.service.sql import StatementState

    response = ws.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=statement,
        wait_timeout="50s",
        catalog=CATALOG,
        schema=SCHEMA,
    )
    state = getattr(getattr(response, "status", None), "state", None)
    ok = state in {StatementState.SUCCEEDED, "SUCCEEDED", None}
    if not ok:
        error = getattr(getattr(response, "status", None), "error", None)
        raise RuntimeError(f"SQL failed state={state} error={error}: {statement[:240]}")
    return response


def _app_principals(ws) -> list[str]:
    principals = [APP_SP]
    try:
        app = ws.apps.get(APP_NAME)
        raw = app.as_dict() if hasattr(app, "as_dict") else {}
        for key in (
            "service_principal_client_id",
            "service_principal_id",
            "service_principal_name",
            "id",
        ):
            value = raw.get(key)
            if value:
                principals.append(str(value))
        effective = getattr(app, "effective_user_api_scopes", None)
        print("App identity fields:", {k: raw.get(k) for k in raw if "principal" in k.lower() or k in {"id", "name", "url"}})
    except Exception as error:
        print(f"Could not load app identity: {error}")
    seen = []
    for principal in principals:
        if principal not in seen:
            seen.append(principal)
    return seen


def create_uc_tables(ws) -> None:
    for name, ddl in TABLE_DDL.items():
        print(f"Creating UC table {FQN}.{name}")
        run_sql(ws, ddl.strip())
    try:
        grants = run_sql(ws, f"SHOW GRANTS ON TABLE {FQN}.knowledge_chunks")
        print("knowledge_chunks grants:", getattr(getattr(grants, "result", None), "data_array", None))
    except Exception as error:
        print(f"Could not inspect existing grants: {error}")
    for principal in _app_principals(ws):
        quoted = f"`{principal}`"
        for statement in (
            f"GRANT USE CATALOG ON CATALOG {CATALOG} TO {quoted}",
            f"GRANT USE SCHEMA ON SCHEMA {FQN} TO {quoted}",
            *(f"GRANT SELECT, MODIFY ON TABLE {FQN}.{name} TO {quoted}" for name in TABLE_DDL),
        ):
            try:
                run_sql(ws, statement)
                print(f"Granted: {statement}")
            except Exception as error:
                print(f"Grant skipped: {error}")


def create_lakebase_and_seed(ws):
    from callcenter_usecase.backend.core._config import AppConfig
    from callcenter_usecase.backend.core.lakebase import (
        DatabaseConfig,
        create_db_engine,
        initialize_models,
        validate_db,
    )
    from callcenter_usecase.backend.operational_store import seed_demo_history_if_empty

    db_config = DatabaseConfig()
    engine = create_db_engine(db_config, ws)
    validate_db(engine, db_config)
    initialize_models(engine)
    _grant_lakebase_roles(engine)
    seeded = seed_demo_history_if_empty(engine, ws, AppConfig())
    print(f"Lakebase seed wrote {seeded} demo calls")
    from sqlalchemy import text

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema = 'toyota_callcenter' ORDER BY table_name"
            )
        ).fetchall()
        print("Lakebase tables:", rows)
        count = connection.execute(text("SELECT COUNT(*) FROM toyota_callcenter.calls")).scalar()
        print("Lakebase calls count:", count)
    engine.dispose()
    return seeded


def _grant_lakebase_roles(engine) -> None:
    from sqlalchemy import text

    skip_prefixes = ("pg_", "cloudsql", "neon", "rds", "databricks_system")
    with engine.begin() as connection:
        rows = connection.execute(text("SELECT rolname FROM pg_roles WHERE rolcanlogin")).fetchall()
        for (role,) in rows:
            role_name = str(role)
            if role_name.startswith(skip_prefixes):
                continue
            quoted = role_name.replace('"', '""')
            statements = [
                f'GRANT USAGE, CREATE ON SCHEMA toyota_callcenter TO "{quoted}"',
                f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA toyota_callcenter TO "{quoted}"',
                "ALTER DEFAULT PRIVILEGES IN SCHEMA toyota_callcenter "
                f'GRANT ALL ON TABLES TO "{quoted}"',
            ]
            for statement in statements:
                try:
                    connection.execute(text(statement))
                    print(f"Lakebase grant ok: {statement}")
                except Exception as error:
                    print(f"Skipped Lakebase grant: {error}")


def _configs(columns: list[dict]) -> list[dict]:
    return sorted(columns, key=lambda item: item["column_name"])


def genie_serialized_space() -> dict:
    calls = f"{FQN}.calls"
    segs = f"{FQN}.transcript_segments"
    nba = f"{FQN}.next_best_actions"
    feedback = f"{FQN}.agent_feedback"
    closures = f"{FQN}.call_closures"
    payload = {
        "version": 2,
        "config": {
            "sample_questions": sorted(
                [
                    {
                        "id": "a0000000000000000000000000000001",
                        "question": ["What are the overall Toyota call-center metrics?"],
                    },
                    {
                        "id": "a0000000000000000000000000000002",
                        "question": ["What kinds of problems are owners calling about?"],
                    },
                    {
                        "id": "a0000000000000000000000000000003",
                        "question": ["Which problem families have the highest escalation rate?"],
                    },
                    {
                        "id": "a0000000000000000000000000000004",
                        "question": ["How are calls being closed — resolved, transferred, or escalated?"],
                    },
                    {
                        "id": "a0000000000000000000000000000005",
                        "question": ["How often do agents use or like the next-best-action recommendations?"],
                    },
                ],
                key=lambda item: item["id"],
            )
        },
        "data_sources": {
            "tables": sorted(
                [
                    {
                        "identifier": feedback,
                        "column_configs": _configs(
                            [
                                {
                                    "column_name": "feedback_id",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "feedback_type",
                                    "description": [
                                        "Agent label: used, helpful, not_helpful, wrong, or ignored."
                                    ],
                                    "synonyms": ["thumbs", "quality label", "NBA feedback"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                            ]
                        ),
                    },
                    {
                        "identifier": closures,
                        "column_configs": _configs(
                            [
                                {
                                    "column_name": "disposition",
                                    "description": [
                                        "Outcome of the call: resolved, transferred, escalated, or open."
                                    ],
                                    "synonyms": ["outcome", "closure", "how the call ended"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "family",
                                    "description": ["Problem family copied from the call at close."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "should_escalate",
                                    "description": [
                                        "True when the last next-best-action said the call must escalate."
                                    ],
                                    "synonyms": ["escalated", "safety transfer"],
                                },
                            ]
                        ),
                    },
                    {
                        "identifier": calls,
                        "column_configs": _configs(
                            [
                                {
                                    "column_name": "call_id",
                                    "description": ["Primary key for a Toyota owner-support call."],
                                },
                                {
                                    "column_name": "current_recommendation_id",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "current_risk_level",
                                    "description": ["Latest risk on the call: low, medium, high, or critical."],
                                    "synonyms": ["severity", "risk"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "disposition",
                                    "description": [
                                        "Latest outcome when the call has closed; null while the call is live."
                                    ],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "family",
                                    "description": [
                                        "Problem family such as Roadside & warning lights or Warranty & goodwill."
                                    ],
                                    "synonyms": ["problem type", "issue category", "kinds of problems"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "latest_intent",
                                    "description": ["Latest classified owner intent for the call."],
                                    "synonyms": ["intent", "reason for call"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "patient_name",
                                    "description": ["Caller name. This demo keeps the API field name patient_name."],
                                    "synonyms": ["caller", "owner name"],
                                },
                                {
                                    "column_name": "queue",
                                    "description": ["Toyota support queue that handled the call."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "scenario_title",
                                    "description": ["Demo scenario title for this call."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "status",
                                    "description": ["Call lifecycle: ready, active, or ended."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                            ]
                        ),
                    },
                    {
                        "identifier": nba,
                        "column_configs": _configs(
                            [
                                {
                                    "column_name": "intent",
                                    "description": ["Recommended handling intent."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "llm_latency_ms",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "next_best_action",
                                    "description": ["The action the agent should take next."],
                                    "synonyms": ["NBA", "recommendation", "what to do"],
                                },
                                {
                                    "column_name": "risk_level",
                                    "description": ["Risk attached to the recommendation."],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "should_escalate",
                                    "description": ["True when the recommendation requires escalation."],
                                },
                                {
                                    "column_name": "trigger_segment_id",
                                    "exclude": True,
                                },
                            ]
                        ),
                    },
                    {
                        "identifier": segs,
                        "column_configs": _configs(
                            [
                                {
                                    "column_name": "asr_latency_ms",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "end_ms",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "is_partial",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "segment_id",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "speaker",
                                    "description": [
                                        "Who spoke. Patient is the caller; Agent is the Toyota advisor."
                                    ],
                                    "synonyms": ["caller", "advisor"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                },
                                {
                                    "column_name": "start_ms",
                                    "exclude": True,
                                },
                                {
                                    "column_name": "text",
                                    "description": [
                                        "Transcribed utterance. Use to illustrate problem types, not to count calls."
                                    ],
                                    "synonyms": ["transcript", "what the caller said"],
                                },
                            ]
                        ),
                    },
                ],
                key=lambda item: item["identifier"],
            )
        },
        "instructions": {
            "text_instructions": [
                {
                    "id": "c0000000000000000000000000000001",
                    "content": [
                        "This agent answers Toyota owner-support management questions from operational call data.",
                        "Call volume is COUNT(DISTINCT calls.call_id), never COUNT of transcript_segments.",
                        "Problem types come from calls.family, calls.latest_intent, and next_best_actions.intent. Use transcript_segments.text only to illustrate what callers said.",
                        "Outcomes live in call_closures.disposition: resolved, transferred, escalated, or open.",
                        "Escalation rate is the share of call_closures where should_escalate is true or disposition is escalated.",
                        "Recommendation quality lives in agent_feedback.feedback_type: used, helpful, not_helpful, wrong, ignored.",
                        "Speaker Patient means the vehicle owner. The column patient_name is the caller name.",
                        "Join calls to transcript_segments, next_best_actions, and call_closures on call_id. Join next_best_actions to agent_feedback on recommendation_id.",
                    ],
                }
            ],
            "join_specs": sorted(
                [
                    {
                        "id": "d0000000000000000000000000000001",
                        "left": {"identifier": calls, "alias": "calls"},
                        "right": {"identifier": segs, "alias": "transcript_segments"},
                        "sql": [
                            "`calls`.`call_id` = `transcript_segments`.`call_id`",
                            "--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--",
                        ],
                    },
                    {
                        "id": "d0000000000000000000000000000002",
                        "left": {"identifier": calls, "alias": "calls"},
                        "right": {"identifier": nba, "alias": "next_best_actions"},
                        "sql": [
                            "`calls`.`call_id` = `next_best_actions`.`call_id`",
                            "--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--",
                        ],
                    },
                    {
                        "id": "d0000000000000000000000000000003",
                        "left": {"identifier": calls, "alias": "calls"},
                        "right": {"identifier": closures, "alias": "call_closures"},
                        "sql": [
                            "`calls`.`call_id` = `call_closures`.`call_id`",
                            "--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--",
                        ],
                    },
                    {
                        "id": "d0000000000000000000000000000004",
                        "left": {"identifier": nba, "alias": "next_best_actions"},
                        "right": {"identifier": feedback, "alias": "agent_feedback"},
                        "sql": [
                            "`next_best_actions`.`recommendation_id` = `agent_feedback`.`recommendation_id`",
                            "--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_MANY--",
                        ],
                    },
                ],
                key=lambda item: item["id"],
            ),
            "sql_snippets": {
                "measures": sorted(
                    [
                        {
                            "id": "e0000000000000000000000000000001",
                            "alias": "call_volume",
                            "display_name": "Call volume",
                            "sql": ["COUNT(DISTINCT calls.call_id)"],
                            "synonyms": ["number of calls", "call count", "volume"],
                        },
                        {
                            "id": "e0000000000000000000000000000002",
                            "alias": "escalation_rate",
                            "display_name": "Escalation rate",
                            "sql": [
                                "AVG(CASE WHEN call_closures.should_escalate THEN 1 ELSE 0 END)"
                            ],
                            "synonyms": ["percent escalated", "safety transfer rate"],
                        },
                    ],
                    key=lambda item: item["id"],
                ),
                "filters": sorted(
                    [
                        {
                            "id": "e0000000000000000000000000000011",
                            "display_name": "Ended calls",
                            "sql": ["calls.status = 'ended'"],
                            "synonyms": ["completed calls", "closed calls"],
                        }
                    ],
                    key=lambda item: item["id"],
                ),
                "expressions": [],
            },
            "example_question_sqls": sorted(
                [
                    {
                        "id": "b0000000000000000000000000000001",
                        "question": ["What kinds of problems are we facing?"],
                        "sql": [
                            "SELECT calls.family, calls.latest_intent, COUNT(DISTINCT calls.call_id) AS call_count "
                            f"FROM {calls} calls GROUP BY calls.family, calls.latest_intent "
                            "ORDER BY call_count DESC"
                        ],
                    },
                    {
                        "id": "b0000000000000000000000000000002",
                        "question": ["What are overall call-center metrics?"],
                        "sql": [
                            "SELECT COUNT(DISTINCT calls.call_id) AS call_volume, "
                            "SUM(CASE WHEN calls.status = 'ended' THEN 1 ELSE 0 END) AS ended_calls, "
                            "SUM(CASE WHEN call_closures.disposition = 'escalated' THEN 1 ELSE 0 END) AS escalated_calls, "
                            "SUM(CASE WHEN call_closures.disposition = 'transferred' THEN 1 ELSE 0 END) AS transferred_calls, "
                            "SUM(CASE WHEN call_closures.disposition = 'resolved' THEN 1 ELSE 0 END) AS resolved_calls "
                            f"FROM {calls} calls LEFT JOIN {closures} call_closures ON calls.call_id = call_closures.call_id"
                        ],
                    },
                    {
                        "id": "b0000000000000000000000000000003",
                        "question": ["Which families escalate most?"],
                        "sql": [
                            "SELECT call_closures.family, COUNT(*) AS closed_calls, "
                            "SUM(CASE WHEN call_closures.should_escalate THEN 1 ELSE 0 END) AS escalations, "
                            "ROUND(AVG(CASE WHEN call_closures.should_escalate THEN 1 ELSE 0 END), 2) AS escalation_rate "
                            f"FROM {closures} call_closures GROUP BY call_closures.family ORDER BY escalation_rate DESC"
                        ],
                    },
                    {
                        "id": "b0000000000000000000000000000004",
                        "question": ["How is recommendation quality?"],
                        "sql": [
                            "SELECT agent_feedback.feedback_type, COUNT(*) AS labels "
                            f"FROM {feedback} agent_feedback GROUP BY agent_feedback.feedback_type ORDER BY labels DESC"
                        ],
                    },
                    {
                        "id": "b0000000000000000000000000000005",
                        "question": ["What are callers saying about overheating and no-start?"],
                        "sql": [
                            "SELECT calls.family, calls.scenario_title, transcript_segments.speaker, transcript_segments.text "
                            f"FROM {segs} transcript_segments JOIN {calls} calls ON transcript_segments.call_id = calls.call_id "
                            "WHERE transcript_segments.speaker = 'Patient' "
                            "AND (LOWER(calls.family) LIKE '%roadside%' OR LOWER(calls.latest_intent) LIKE '%overheat%' "
                            "OR LOWER(calls.latest_intent) LIKE '%nostart%' OR LOWER(calls.scenario_title) LIKE '%hybrid%') "
                            "ORDER BY transcript_segments.created_at"
                        ],
                    },
                ],
                key=lambda item: item["id"],
            ),
        },
    }
    return payload


def update_genie(ws) -> None:
    space = genie_serialized_space()
    serialized = json.dumps(space, separators=(",", ":"))
    payload = {
        "warehouse_id": WAREHOUSE_ID,
        "title": "Toyota Call Center",
        "description": (
            "Management analytics for Toyota owner-support: call volume, problem families, "
            "escalations, dispositions, transcripts, next-best-actions, and agent feedback."
        ),
        "serialized_space": serialized,
    }
    last_error = None
    for method, path in (
        ("POST", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}"),
        ("PATCH", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}"),
        ("PUT", f"/api/2.0/genie/spaces/{GENIE_SPACE_ID}"),
    ):
        try:
            ws.api_client.do(method, path, body=payload)
            print(f"Updated Genie space {GENIE_SPACE_ID} via {method}")
            return
        except Exception as error:
            last_error = error
            print(f"Genie {method} {path} failed: {error}")
    raise RuntimeError(f"Genie update failed: {last_error}")


def merge_app_resources(ws) -> None:
    app = ws.apps.get(APP_NAME)
    existing = list(getattr(app, "resources", None) or [])
    print("Current app resources:")
    by_name = {}
    for resource in existing:
        raw = resource.as_dict() if hasattr(resource, "as_dict") else dict(resource)
        print(json.dumps(raw, default=str))
        by_name[raw.get("name")] = raw
    wanted = {
        "sql-warehouse": {
            "name": "sql-warehouse",
            "sql_warehouse": {"id": WAREHOUSE_ID, "permission": "CAN_USE"},
        },
        "calls-table": _table_resource("calls-table", f"{FQN}.calls"),
        "transcript-table": _table_resource("transcript-table", f"{FQN}.transcript_segments"),
        "nba-table": _table_resource("nba-table", f"{FQN}.next_best_actions"),
        "feedback-table": _table_resource("feedback-table", f"{FQN}.agent_feedback"),
        "closures-table": _table_resource("closures-table", f"{FQN}.call_closures"),
    }
    by_name.update(wanted)
    resources = list(by_name.values())
    print(f"Updating {APP_NAME} with {len(resources)} resources")
    try:
        ws.apps.update(name=APP_NAME, resources=resources)
        print("App resources updated via SDK update")
        return
    except Exception as error:
        print(f"apps.update failed: {error}")
    ws.api_client.do("PATCH", f"/api/2.0/apps/{APP_NAME}", body={"resources": resources})
    print("App resources updated via PATCH")


def _table_resource(name: str, full_name: str) -> dict:
    return {
        "name": name,
        "uc_securable": {
            "securable_type": "TABLE",
            "securable_full_name": full_name,
            "permission": "MODIFY",
        },
    }


def verify(ws) -> None:
    for name in ("calls", "transcript_segments", "next_best_actions", "agent_feedback", "call_closures"):
        response = run_sql(ws, f"SELECT COUNT(*) AS n FROM {FQN}.{name}")
        data = getattr(response, "result", None)
        rows = getattr(data, "data_array", None) if data else None
        print(f"UC {name} rows={rows}")


def main() -> int:
    load_token()
    from databricks.sdk import WorkspaceClient

    ws = WorkspaceClient()
    me = ws.current_user.me()
    print(f"Authenticated as {me.user_name}")
    create_uc_tables(ws)
    create_lakebase_and_seed(ws)
    verify(ws)
    update_genie(ws)
    try:
        merge_app_resources(ws)
    except Exception as error:
        print(f"App resource merge skipped: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
