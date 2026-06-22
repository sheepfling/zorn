# Zorn Lattice Certification

This directory turns the research registry into an executable certification corpus.

- `fixtures.yaml` pins external repositories by immutable commit SHA.
- `capabilities.yaml` defines pass conditions before fixture execution.
- `domains.yaml` defines the big Zorn systems as capability contracts.
- `coverage.yaml` is the master truth table across official samples, third-party fixtures, and synthetic scenarios.
- `levels.yaml` defines certification levels from SDK smoke through Air Dominance & Strike surrogate behavior.
- `artifacts.yaml` defines the self-checking run outputs expected from scenario certification.
- `runners/` contains language-specific and fixture-specific runners.
- `reports/` stores JSON certification artifacts.

The corpus is cloned into ignored repo-local `cert/lattice/.fixtures` by default.
Upstream sample code is not vendored into this repository.

## Commands

```bash
zorn-cert list
zorn-cert clone --all
zorn-cert clone anduril-sample-ais-rest
zorn-cert inspect anduril-sample-ais-rest
zorn-cert install anduril-sample-ais-rest
zorn-cert run anduril-sample-ais-rest --target http://localhost:8080
zorn-cert report
zorn-cert domains
zorn-cert coverage
zorn-cert levels
zorn-cert validate-contracts
```

`inspect` reports what Zorn currently knows about a fixture workspace: language,
manifest-pinned or inferred install commands, one or more native run commands,
config files, and environment hints.
`install` runs the resolved dependency setup inside the ignored clone workspace
without modifying upstream source.

The first executable milestone is AIS REST entity ingestion: publish a normalized
AIS-style entity to Zorn, verify canonical readback, and verify the REST stream
surface emits an entity event.

## Architecture Target

Zorn is not only a mock endpoint. The certification target is a simulated
battlespace kernel:

```text
SDK/API facade
  -> command/event log
  -> entity/task/object stores
  -> scenario engine
  -> fusion/rules/effects plugins
  -> streaming fanout
  -> UI/replay/export
```

An unmodified public Lattice sample should think Zorn is Lattice, and synthetic
Battlespace Awareness or Air Dominance & Strike scenarios should produce
believable entities, tasks, streams, media, and outcomes.
