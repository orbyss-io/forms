# Optional multi-provider content-comprehension experiments

This is a local/user-invoked acceptance layer, not a CI model call or proof of search discovery.
Use one public fixture and the same questions for every model/provider/version. Include at least
two independent providers or one hosted plus one local/open-weight implementation, repeated
trials, and HTML/Markdown representations. Preserve source hashes, model settings, prompts, raw
answers, dates and any retrieval configuration alongside the report. Do not transmit private
content. Explicitly authorize any paid model execution; Program Kit's scorer never calls a model.

Example question document:

```json
{"version":"1.0","questions":[{"id":"quota","prompt":"What is the sample service limit and its period?","requiredFacts":["100","per month"],"allowedCitations":["https://example.invalid/guide"]}]}
```

Collected trial format (replace the sample with actual, identified model output):

```json
{"version":"1.0","trials":[{"provider":"local-example","model":"actual-model-id","version":"actual-build-or-date","trial":1,"representation":"html","answers":[{"questionId":"quota","answer":"The sample is limited to 100 requests per month.","citations":["https://example.invalid/guide"]}]}]}
```

Run `python .specify/extensions/program-kit-governance/scripts/ui_evaluation.py --questions
questions.json --trials trials.json --report artifacts/ui-evaluation/new-report.json`.

The scorer validates complete identical question sets, trial identity and provider/model/version
provenance. It reports **literal fact coverage** and exact canonical-citation matches. These are
diagnostic metrics, not factual accuracy: a negated fact or an unsupported statement can still
contain expected words. A human or independently validated semantic judge must evaluate truth,
units/qualifiers, unsupported additions and whether citations actually support each assertion.
Measure discovery separately in real search/retrieval systems. Do not infer ranking, conversion,
cross-provider universality, or a benefit from llms.txt from comprehension scores.
