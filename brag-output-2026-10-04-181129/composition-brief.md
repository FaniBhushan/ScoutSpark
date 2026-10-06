# Hyperframes Composition Brief: ScoutSpark

## Objective
Create a short launch-style brag video for ScoutSpark, showing its capstone research workflow and honestly labeling the synthetic offline demo.

## Output
- Composition directory: `brag-output-2026-10-04-181129/composition/`
- Rendered video: `brag-output-2026-10-04-181129/brag.mp4`
- Format: landscape — 1920x1080
- Duration: 20 seconds

## Source Material
- Project root: `/Users/fanibhushan/ScoutSpark`
- Primary files read: `README.md`, `src/ui/app.py`, `src/ui/scorecards.py`
- Product name: ScoutSpark
- Tagline / strongest claim: “helps students find and assess capstone project ideas”
- Key UI or visual moment to recreate: Offline demo configuration → reviewed resolved preview → ranked finalists with evidence and gate caveats
- Copy that must appear verbatim:
  - “Review the source plan and scoring weights before starting research.”
  - “Preview and validate configuration”
  - “Top 2 finalists by weighted score”
  - “Fully offline demo: frozen synthetic sources and deterministic model responses. Not real-world evidence.”

## Creative Direction
- Tone preset: polished
- Creative direction: a calm, confident product film for careful capstone planning
- Interpretation: Crisp UI movement, quiet accents, and readable holds; maintain a clear synthetic demo label.
- Angle: A capstone idea should survive more than a brainstorm. Show ScoutSpark taking a structured request through a reviewed plan and into ranked scorecards, while the offline demo label stays visible so nobody mistakes synthetic records for live evidence.
- Hook: “One project idea. Several checks.” leading into the actual configuration UI.
- Outro / punchline: “Good ideas get reviewed.”
- Avoid: Generic SaaS language, abstract filler visuals, unrelated visual redesign, fabricated research claims, or representing synthetic records as real-world evidence.

## Visual Identity
- Background: Streamlit default light theme; no repository theme override found.
- Text: Streamlit default foreground; no repository override found.
- Accent: Streamlit default primary accent; no repository override found.
- Display font: Streamlit default sans-serif.
- Body font: Streamlit default sans-serif.
- Visual references from the project: Streamlit configuration form, resolved preview summary, ranked finalist scorecards, synthetic evidence notice.

## Storyboard
Use `brag-output-2026-10-04-181129/brag-plan.md` as the creative contract.

Scene summary:
1. The question — 2.5s — “One project idea. Several checks.” and ScoutSpark.
2. Set the request — 4s — actual Offline demo controls and full synthetic data caveat.
3. Review before research — 5s — preview button and resolved plan.
4. Score and inspect — 6s — top two synthetic example scorecards with visible label and evidence/gate caveat.
5. Close — 2.5s — source caption and “Good ideas get reviewed.”

## Audio
- Audio role: warm bed with sparse professional accents.
- Audio arc: low upbeat bed, quiet preview click, modest result reveal, soft final fade.
- Music: `assets/music/happy-beats-business-moves-vol-1-by-ende-dot-app.mp3`
- Music treatment: around 0.32 volume, short fade-in and final-second fade-out.
- Music cue guidance: bundled cue metadata at `assets/music/cues/happy-beats-business-moves-vol-1-by-ende-dot-app.music-cues.json`; use optional strong cues near 6.52s, 17.02s, 17.52s; finalist cards follow 12.02s and 12.52s, prioritizing readability.
- Audio-reactive treatment: skipped because the Hyperframes extraction helper requires system FFmpeg, which is unavailable here; no waveform graphics.
- Audio-coupled moments: preview click; grouped finalist reveals.
- SFX selection guidance: restrained and motion-matched.
- SFX analysis guidance: `/Users/fanibhushan/.codex/plugins/cache/brag/brag/0.4.0/skills/brag/assets/sfx/sfx-analysis.md`; prefer low high-frequency-risk sounds.
- Exact SFX choice: `interface/click_003.ogg` at the preview interaction and `impact/impactSoft_medium_001.ogg` at the result reveal, both at restrained volume.
- Audio files: music and SFX are copied under `composition/assets/`.

## Hyperframes Instructions
Use the current Hyperframes composition workflow and domain guidance if available. This is the `/brag` story and storyboard, not the generic Hyperframes promo workflow. Build in `brag-output-2026-10-04-181129/composition/`, validate with `npx hyperframes check`, then render to the requested local path. Keep all claims grounded in the project and its synthetic demo caveat. No voiceover was requested.
