# Build Notes

## Unity Catalog Target

Use this Unity Catalog namespace for the Call Center Use Case demo:

```text
catalog: users
schema:  brijendra_raghuwanshi
```

The app defaults are wired in `src/callcenter_usecase/backend/core/_config.py`:

```text
CALLCENTER_USECASE_UC_CATALOG=users
CALLCENTER_USECASE_UC_SCHEMA=brijendra_raghuwanshi
CALLCENTER_USECASE_DELTA_SCHEMA_NAME=brijendra_raghuwanshi
```

Use this namespace for:

- Parsed healthcare knowledge-base chunks.
- Vector Search source tables.
- Transcript, recommendation, feedback, audit, and evaluation Delta tables.
- Demo setup notebooks or jobs that create UC objects.

Do not default to `main` or a project-specific schema for this demo unless explicitly requested.

## Databricks Profile

Use the `east-fe` Databricks CLI profile for this demo workspace:

```text
profile: east-fe
host:    https://adb-984752964297111.11.azuredatabricks.net
user:    brijendra.raghuwanshi@databricks.com
```

The profile works when tested in isolation. The local shell may contain `DATABRICKS_HOST`,
`DATABRICKS_TOKEN`, or `DATABRICKS_AUTH_TYPE` environment variables that override the
profile. For reliable bundle commands, unset those variables inline:

```bash
env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks current-user me -p east-fe
```

Validate and deploy with the explicit `east-fe` bundle target:

```bash
python3 scripts/build_databricks_app.py

env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks bundle validate -t east-fe -p east-fe

env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_AUTH_TYPE \
  databricks bundle deploy -t east-fe -p east-fe
```

The bundle build intentionally uses `scripts/build_databricks_app.py` instead of
`apx build` so local deployment is not blocked by PyPI/npm network failures. It
packages the FastAPI backend and serves `ui-preview.html` as the frontend. Switch
the artifact build back to `apx build` after package registry access is restored.
