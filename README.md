# ssr-knowledge

`ssr-knowledge` is an independently runnable, local-only set of knowledge preparation workflows. It does not wait for or call the chat runtime, assume a shared database, or import code from another repository. It reads and writes JSON files under the selected state directory.

## Three independent workflows

1. **Prebuild:** normalize a local source bundle into a candidate. Candidates require review before they can be published. The prebuild review policy is still a product decision; this repo uses manual review as a conservative local default.
2. **Gap research and supplementation:** import an exported gap and its separately prepared, sourced records into a durable research packet. The packet preserves each `gap_id`, `run_id`, and `message_id`. Only a later `supplement` command turns that packet into a candidate, and the candidate cannot be published until a human approves it.
3. **Fixed tool preparation:** inspect a local, fixture-only list of planned tool adapters. No tool is executed, configured with credentials, or connected to a service.

Research packets, candidates, and published versions are stored separately. Publishing creates an immutable versioned JSON bundle with a SHA-256 digest over canonicalized records; every read rechecks the digest and rejects tampered content. `query` requires an explicit version and reads only published bundles. There is no shared database or implicit `latest` pointer. The exact version exchange format between future systems is still undecided.

## Run locally

This repo uses Python 3.11+ and the standard library only. `uv.lock` records the empty dependency set.

```powershell
uv --cache-dir .uv-cache --offline lock
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge prebuild --source fixtures/prebuild-source.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge tools
uv --cache-dir .uv-cache --offline run python -m unittest discover -s tests -v
```

The CLI prints a candidate ID. Review and publish it explicitly:

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge review --candidate-id CANDIDATE_ID --decision approve --reviewer human --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge publish --candidate-id CANDIDATE_ID --version v0.1.0 --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge query --version v0.1.0 --kind game_item --text "星砂"
```

Save the offline research packet first, then create a candidate from its persisted ID. These commands do not perform web research; the supplied evidence is local input and must be reviewed before publication:

```powershell
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge research --gaps fixtures/gap-export.json --records fixtures/gap-records.json --state-dir .local-state
uv --cache-dir .uv-cache --offline run python -m ssr_knowledge supplement --research-id RESEARCH_ID --state-dir .local-state
```

## Local contracts and boundaries

`contracts/` contains this repo's own JSON Schemas, including `research-packet.schema.json`. The standard-library validator checks local fixtures and user-supplied documents against those schemas. Query responses contain only `status`, `materials`, and `sources`; operational diagnostics stay in the local audit log.

No web research, platform connection, model call, deployment, or remote persistence is implemented. Research inputs in fixtures are fictional. A person must inspect candidate content and explicitly approve it before publication; the exact review UI and whether prebuild candidates also require human review remain undecided.
