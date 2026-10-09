# ScoutSpark limited preview — 9 October 2026

This is a **limited preview**, not the V2 release milestone. The current build
lets a user enter one interest area and constraints, compare scored ideas with
source receipts and gate warnings, and receive a detailed proposal when its
existing gates and automatic evidence checks pass. A scored idea or Scout
concept summary is not a verified detailed proposal. A user may now request a
separate exploratory proposal for any displayed idea. It remains unverified
and keeps failed gates visible.

The project owner reports that a couple of additional live runs completed
acceptably and considers that sufficient to invite preview users. Those runs
are not part of the saved evaluation sample below and do not establish a
measured live success rate. The current unit suite passes 267 tests; fixture
validation and `git diff --check` also pass.

The [release check](v2-release-check-2026-10-08.md) used one frozen synthetic
robotics request repeated ten times. Every run completed its automatic checks,
showed five scored ideas, and produced three of three requested proposals. Every
run also missed the requested candidate count: five of twelve ideas were
accepted. The registered candidate-count target therefore failed (0/10 runs).
These results measure the offline harness and do not establish live quality.

Independent Scout, Library, Critic, proposal, and verifier reviews are pending.
No independent reviewer has judged first-run usefulness or factual support for
the saved sample. A one-request Tavily pilot found eight usable web articles but
no verified proposal; see the [release check](v2-release-check-2026-10-08.md).
The existing five hard gates and saved gate outcomes remain in force. A failed
gate continues to withhold a detailed proposal.

The independent and broader reliability evaluations are scheduled after this
preview at the user's direction. The owner reports that a couple of additional
live runs completed acceptably; they are not part of the saved sample or a
measured quality result. The [V2 milestone](../TASKS.md) remains open until the
registered and human-reviewed checks pass.
