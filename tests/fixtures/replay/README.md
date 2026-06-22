# Public API Replay Fixtures

`entity_task_object_api.jsonl` is an internal replay-log fixture for the existing
public REST API. It does not define a new server endpoint.

The fixture proves replay/log coverage for:

- entity publish,
- task create,
- task status update,
- task cancel,
- object upload,
- object delete.

Run it against a running Zorn server with:

```bash
zorn replay api tests/fixtures/replay/entity_task_object_api.jsonl \
  --target http://127.0.0.1:8080 \
  --report /tmp/zorn-api-replay-report.json
```
