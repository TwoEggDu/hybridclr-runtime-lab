# Runtime Lab Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a reproducible public baseline for the existing runtime experiments.
**Architecture:** Three isolated Unity projects, pinned external dependencies, shared CLI tooling and sanitized evidence.
**Tech Stack:** Unity 2022.3 custom Editor, HybridCLR v9, Python, .NET 10, CDB, Git.
**Spec:** ../../design.md

## Global Constraints
- Public repository: TwoEggDu/hybridclr-runtime-lab.
- No Unity implementation, dependency trees, binaries, full logs, or local machine paths in published files.
- Existing article repository changes remain untouched.
- Preserve the existing custom Editor baseline; do not claim standard Unity compatibility.

## Review Focus
- Existing or dirty dependency checkout must fail instead of being reset.
- A reused installed runtime with a different lock must fail.
- Hot DLL must be identical across generic cases; supplementary DLL must remain build-specific.
- Expected negative case is exit 2, not a failed experiment harness.
- Failure in preparation/build/verification stops publication.

## Tasks
- [x] Import owned sample sources into isolated projects, pin relative manifests, add ignores and stable meta GUIDs.
- [x] Implement preparation/build/run/trace tools, check failures and cross-project input identity.
- [x] Build all projects from the new checkout and validate runtime behavior and debugger evidence.
- [x] Write README and evidence, perform independent whole-repository review.
- [ ] Create public GitHub repository, commit explicit file list, push exact SHA and read back remote.

## Ledger
- Initial scope approved in conversation; continue without another naming/visibility confirmation.
- Publish one initial commit after end-to-end verification; the article repository is outside this publication.

- Review fixes: enforce actual Editor ProductVersion; bind complete builds, runs and traces by build ID and hashes; compare 919 non-generated installed implementation files. Six evidence-isolation tests pass; a real wrong-Editor preflight was rejected.
- CDB forwards debuggee exit codes: p0/m0 is expected to return 2. Trace acceptance checks both the code and actual negative-case log.

- Final local acceptance: all three rebuilt Players, five standalone runs, five CDB captures and both deep evidence validators passed. Independent review findings closed. Publication is the remaining delivery step.
