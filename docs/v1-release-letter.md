# ScoutSpark V1 — Early Feedback Release

**Subject: Introducing ScoutSpark V1 for early feedback**

Hello,

I’m opening ScoutSpark V1 for early feedback.

**What ScoutSpark does**

- Helps students explore capstone project ideas against a chosen domain, constraints, and configurable rubric.
- Scout proposes ideas; Library independently gathers evidence; Critic assesses candidates; and the proposal writer drafts when evidence and required checks support a proposal.
- Results include ranked scorecards, evidence and citations, and reasons for failed checks.
- Users can preview configuration, adjust research and scoring settings, and choose synthetic offline examples or available live research sources.

**Current evaluation**

- V1 is an early MVP; reliability is still being measured.
- In a controlled baseline of three cases with synthetic source evidence, the real-model workflow returned:
  - Sequential mode: 1 of 9 requested detailed proposals.
  - Parallel mode: 2 of 9 requested detailed proposals.
  - Neither mode met the requested proposal count in any case.
- The offline demo returned all requested proposals using simulated responses. This does not demonstrate real-world research quality.
- These small evaluations are a starting point, not a broad quality or reliability estimate. Human ratings are not yet available.

**What to keep in mind**
- The system may return fewer detailed proposals than requested when evidence, citations, feasibility checks, hard gates, or run limits prevent a proposal from passing.
- A high-ranked scorecard is not necessarily an approved proposal.
- Review cited sources and displayed caveats before relying on results. Live research coverage and model output can vary.

**Feedback I’m looking for**
- Are the ideas relevant to your project area?
- Are the evidence and citations useful for judging them?
- Are missing or rejected results explained clearly?
- Where does setup or review feel confusing?
- Which results were unexpectedly useful or unhelpful?

Thank you for trying ScoutSpark V1 and helping shape what comes next.

Best,

**The ScoutSpark team**

---

*Evaluation figures above are from the controlled baseline summarized in [`evals/demo_submission_2026-09-27.md`](../evals/demo_submission_2026-09-27.md). They used three cases and synthetic evidence; they should not be read as a broad quality or reliability estimate.*
