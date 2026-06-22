# Zorn work lanes

Each lane owns a coherent slice of the ecosystem while respecting the public-compatible API boundary.

## LANE-CORE — Compatibility Kernel

**Mission:** Keep public-compatible REST/gRPC behavior stable while all higher-level Zorn modules expand around it.

**Milestones:** Z0, Z1, Z2

**Modules:**
- c2_compat_sandbox.core
- c2_compat_sandbox.routes
- c2_compat_sandbox.grpc_api

**Primary outputs:**
- descriptor audit
- contract tests
- REST/gRPC compatibility report

**References:** SRC-LATTICE-CONCEPTS, SRC-LATTICE-MIGRATION

## LANE-SANDBOX — Sandbox Environment Manager

**Mission:** Provide resettable, seedable, replayable local environments that resemble developer sandboxes.

**Milestones:** Z3

**Modules:**
- c2_compat_sandbox.environments
- c2_compat_sandbox.fixtures
- c2_compat_sandbox.clock

**Primary outputs:**
- environment registry
- seed/reset/export APIs
- deterministic clock

**References:** SRC-LATTICE-CONCEPTS, SRC-LATTICE-DEV-CONSOLE

## LANE-DEVELOPER-CONSOLE — Developer Console

**Mission:** Expose a debugging console for entities, tasks, objects, streams, schemas, and compatibility status.

**Milestones:** Z4

**Modules:**
- zorn-ui/developer-console
- c2_compat_sandbox.local_inspection

**Primary outputs:**
- Entity Explorer
- Task Explorer
- Object Explorer
- stream inspector

**References:** SRC-LATTICE-DEV-CONSOLE, SRC-LATTICE-ENTITIES, SRC-LATTICE-TASKS

## LANE-C2 — Operator C2

**Mission:** Build a map-first COP and tasking surface for rich showcase scenarios without copying proprietary UI design.

**Milestones:** Z5

**Modules:**
- zorn-ui/c2
- zorn-ui/map
- zorn-ui/task-board

**Primary outputs:**
- live COP
- entity details
- task board
- media panel
- alerts

**References:** SRC-LATTICE-C2, SRC-LATTICE-ENTITIES, SRC-LATTICE-TASKS

## LANE-ADAPTERS — Sensors, Tracks, and Protocol Adapters

**Mission:** Translate simulation and open feed protocols into public-compatible entities, tasks, objects, and events.

**Milestones:** Z6

**Modules:**
- zorn-adapter-ais
- zorn-adapter-dis
- zorn-adapter-hla
- zorn-adapter-cot

**Primary outputs:**
- AIS adapter
- DIS Entity State adapter
- adapter health monitor
- mapping registry

**References:** SRC-LATTICE-CONCEPTS, SRC-LATTICE-ENTITIES

## LANE-OBJECTS-MEDIA — Objects, Media, Reports, and Evidence

**Mission:** Turn the Objects API into visible workflows: thumbnails, reports, manifests, scenario evidence, and exports.

**Milestones:** Z7

**Modules:**
- c2_compat_sandbox.objects
- zorn-ui/object-browser
- zorn-evidence

**Primary outputs:**
- object browser
- thumbnail workflow
- evidence bundle exporter

**References:** SRC-LATTICE-CONCEPTS, SRC-LATTICE-DEV-CONSOLE

## LANE-AUTONOMY — Mission Autonomy and Taskable Agents

**Mission:** Exercise TaskCatalog routing, multi-agent tasking, human-supervised mission graphs, and mock autonomy.

**Milestones:** Z8

**Modules:**
- zorn-agent-runtime
- zorn-mission-graph
- zorn-agents

**Primary outputs:**
- agent registry
- mission graph runner
- mock agents
- human approval gates

**References:** SRC-LATTICE-AUTONOMY, SRC-LATTICE-TASKS

## LANE-MESH — Mesh and Edge Simulation

**Mission:** Simulate local-first event distribution, object availability, partitions, reconnection, and constrained links.

**Milestones:** Z9

**Modules:**
- zorn-mesh-sim
- zorn-node
- zorn-replication

**Primary outputs:**
- node registry
- link profiles
- partition simulator
- replication trace

**References:** SRC-LATTICE-MESH, SRC-LATTICE-CONCEPTS

## LANE-PARTNER — Partner-Style Integration System

**Mission:** Provide a local partner sandbox experience for packages, manifests, conformance tests, and compatibility scorecards.

**Milestones:** Z10

**Modules:**
- zorn-partner-registry
- zorn-plugin-runner
- zorn-conformance

**Primary outputs:**
- plugin manifest schema
- integration catalog
- scorecards
- reference datasets

**References:** SRC-LATTICE-PARTNER, SRC-LATTICE-SDK

## LANE-DOMAINS — Domain Scenario Packs

**Mission:** Package rich but safe demonstrations across maritime, DIS, C-UAS surveillance, space tracking, undersea, and readiness workflows.

**Milestones:** Z11

**Modules:**
- zorn-domain-maritime
- zorn-domain-dis
- zorn-domain-cuas
- zorn-domain-space
- zorn-domain-undersea

**Primary outputs:**
- scenario packs
- fixtures
- runbooks
- synthetic data generators

**References:** SRC-LATTICE-C2, SRC-LATTICE-AUTONOMY, SRC-LATTICE-MESH

## LANE-SHOWCASE — Showcase and Evaluation Mode

**Mission:** Make the whole environment demonstrable, repeatable, measurable, and presentable.

**Milestones:** Z12

**Modules:**
- zorn-showcase-runner
- zorn-eval
- zorn-recording

**Primary outputs:**
- one-command demos
- evaluation reports
- recordings
- compatibility matrix

**References:** SRC-LATTICE-SDK, SRC-LATTICE-PARTNER
