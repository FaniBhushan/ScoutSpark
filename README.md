# ScoutSpark

ScoutSpark helps students explore capstone project ideas that fit their interests,
skills, time, and resources. It searches for supporting sources, compares ideas,
and explains when the evidence is not strong enough for a detailed plan.

> **Limited preview · 9 October 2026**
> Try it and [share feedback](https://github.com/FaniBhushan/SparkScout/issues/new/choose).
> Results can be incomplete or unverified. Check the sources and warnings before
> relying on an idea. The full reliability review is still in progress; see the
> [preview notes](docs/v2-limited-preview-2026-10-08.md).

## See ScoutSpark

**Short video walkthrough:** coming soon. The [recording guide](docs/demo_recording_guide.md)
and [video script](docs/demo_video_script.md) show what the walkthrough will cover.

## How it works

![ScoutSpark architecture](docs/scoutspark_architecture.png)

1. You describe what you want to build and your limits.
2. **Scout** searches for problems and suggests project ideas.
3. **Library** searches for more evidence about the topic.
4. **Critic** compares each idea with the evidence and checks practical limits.
5. ScoutSpark shows the scores, sources, and reasons an idea may not be ready.
   It writes a detailed plan only when its checks pass. You can also ask for an
   exploratory plan, which is clearly marked as unverified.

See the [architecture image as SVG](docs/scoutspark_architecture.svg) or read the
[plain-language guide to results](docs/getting-useful-results.md).

## Run it on your computer

You need Python 3.10 or newer. Each person running ScoutSpark uses their own
model and search API keys. The **Offline demo** works without keys and uses
synthetic examples; it does not search the live web.

Clone the repository, install the packages, and start the app:

```sh
git clone https://github.com/FaniBhushan/SparkScout.git
cd SparkScout
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` instead of
`source .venv/bin/activate`.

When the app opens, choose **Offline demo** to try it without credentials. For
live research, choose **Live sources** and provide your own `OPENAI_API_KEY` and
`TAVILY_API_KEY`. A GitHub token is optional. You can put these values in a
`.env` file in your local copy of the repository, in this format:

```text
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
```

Never commit that file or post keys in feedback. Live model and search services
may charge you. Review the budget controls before starting a run.

## What to expect

ScoutSpark is an early preview. It may show fewer ideas than requested, find
sources that do not support a useful plan, or withhold a detailed proposal. In
the saved preview checks, the offline run missed its requested candidate count
in all ten repeats, and one live pilot returned no verified proposals. These
checks are small and do not establish general quality. Read the
[release check and its limits](docs/v2-release-check-2026-10-08.md).

Please share bugs, confusing results, source problems, and ideas for improvement
through [GitHub Issues](https://github.com/FaniBhushan/SparkScout/issues/new/choose).
Do not include API keys, personal data, or private documents in public issues.

## More details

- [How to get useful results](docs/getting-useful-results.md)
- [How scoring and warnings work](docs/candidate_scoring.md)
- [Source and privacy limits](docs/guardrails.md)
- [Evaluation results](evals/README.md)
- [Pending and future tasks](TASKS.md)
