"""
test_credibility.py — contract tests for score_url().

    python test_credibility.py

These check the SHAPE of your output, not its quality. They must keep passing
however much you rewrite the internals — the app, the grader, and evaluate.py
all rely on this contract. Use `evaluate.py` to measure quality.

Deliverable 1 asks for "initial testing to validate input/output handling".
This file is that, and adding your own cases here is part of the deliverable.

No pytest required, deliberately — one less thing to install.
"""

from credibility import page_based_signals, score_band, score_url

PASSED = 0
FAILED = 0


def check(condition: bool, description: str) -> None:
    """Assert-with-a-label so one failure doesn't stop the whole run."""
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS  {description}")
    else:
        FAILED += 1
        print(f"  FAIL  {description}")


print("\nContract: return shape")
result = score_url("https://www.nature.com/articles/example", use_llm=False)
check(isinstance(result, dict), "returns a dict")
check(set(result.keys()) == {"score", "explanation"}, "has exactly the keys 'score' and 'explanation'")
check(isinstance(result["score"], float), "score is a float")
check(isinstance(result["explanation"], str), "explanation is a str")
check(len(result["explanation"]) > 0, "explanation is not empty")

print("\nContract: score range")
for url in [
    "https://www.nature.com/x",
    "https://medium.com/@a/b",
    "http://unknown-site.xyz/page",
    "https://en.wikipedia.org/wiki/X",
]:
    score = score_url(url, use_llm=False)["score"]
    check(0.0 <= score <= 1.0, f"{url[:40]:<42} -> {score:.2f} is within [0, 1]")

print("\nContract: malformed input is handled, not raised")
for bad in ["", "   ", "not a url", "ftp://files.example.com/x", "javascript:alert(1)", "//example.com"]:
    try:
        bad_result = score_url(bad, use_llm=False)
        ok = isinstance(bad_result, dict) and 0.0 <= bad_result["score"] <= 1.0
        check(ok, f"{bad!r:<28} -> {bad_result['score']:.2f} (no exception)")
    except Exception as e:
        check(False, f"{bad!r:<28} raised {type(e).__name__}")

print("\nContract: determinism")
a = score_url("https://arxiv.org/abs/1706.03762", use_llm=False)
b = score_url("https://arxiv.org/abs/1706.03762", use_llm=False)
check(a == b, "same URL scored twice gives the same result")

print("\nSanity: ordering the baseline should already get right")
journal = score_url("https://www.nature.com/articles/x", use_llm=False)["score"]
blog = score_url("https://randomblog.blogspot.com/x", use_llm=False)["score"]
check(journal > blog, f"a journal ({journal:.2f}) outranks a personal blog ({blog:.2f})")

gov = score_url("https://www.census.gov/data", use_llm=False)["score"]
throwaway = score_url("http://whatever.xyz/page", use_llm=False)["score"]
check(gov > throwaway, f"a .gov source ({gov:.2f}) outranks a throwaway domain ({throwaway:.2f})")

print("\nContract: score_band")
check(score_band(0.9)[0] == "HIGH", "0.90 -> HIGH")
check(score_band(0.5)[0] == "MEDIUM", "0.50 -> MEDIUM")
check(score_band(0.1)[0] == "LOW", "0.10 -> LOW")

print("\nStudent tests: page-level credibility signals")

# Use small synthetic HTML examples instead of live websites so these tests
# remain deterministic even if a website is unavailable or changes its HTML.
# Each example isolates a feature added to the credibility scoring algorithm.
scholarly_html = """
<html>
<head>
    <meta name="author" content="Jane Researcher">
    <meta name="citation_title" content="Example Research Article">
    <meta name="citation_doi" content="10.1234/example">
    <meta property="article:published_time" content="2026-01-01">
</head>
<body>
    <section id="references">References</section>
</body>
</html>
"""

print("\nStudent tests: preprint detection")

# A page may look scholarly while explicitly identifying itself as a preprint.
# The scorer should recognize that peer review cannot be assumed simply because
# the page contains academic-looking metadata.
preprint_html = """
<html>
<head>
    <meta name="author" content="Example Researcher">
    <meta name="citation_title" content="Example Study">
</head>
<body>
    <p>This manuscript is a preprint and has not yet been peer reviewed.</p>
</body>
</html>
"""

# A peer-reviewed article may cite a preprint in its references. Mentioning a
# preprint as a source should not cause the current document to be classified
# as a preprint.
peer_reviewed_html = """
<html>
<head>
    <meta name="citation_title" content="Peer-Reviewed Article">
</head>
<body>
    <p>References</p>
    <p>Example Research. Preprint at https://arxiv.org/abs/1234.5678</p>
</body>
</html>
"""

peer_reviewed_signals = page_based_signals(peer_reviewed_html)
peer_reviewed_names = [signal.name for signal in peer_reviewed_signals]

check(
    "preprint" not in peer_reviewed_names,
    "a cited preprint does not classify the current article as a preprint",
)

print("\nStudent tests: suspicious URL language")

# Sensational claim language should reduce credibility relative to an otherwise
# similar URL. This tests the behavior of the path penalties without requiring
# one exact score, allowing weights to be adjusted later without breaking it.
ordinary_url = score_url(
    "https://unknown-source.info/research-report",
    use_llm=False,
)["score"]

sensational_url = score_url(
    "https://unknown-source.info/miracle-cure-doctors-hate",
    use_llm=False,
)["score"]

check(
    sensational_url < ordinary_url,
    f"sensational path ({sensational_url:.2f}) scores below ordinary path ({ordinary_url:.2f})",
)

preprint_signals = page_based_signals(preprint_html)
preprint_names = [signal.name for signal in preprint_signals]

check("preprint" in preprint_names, "detects an explicitly identified preprint")

scholarly_signals = page_based_signals(scholarly_html)
scholarly_names = [signal.name for signal in scholarly_signals]

check("page_author" in scholarly_names, "detects author metadata")
check("page_date" in scholarly_names, "detects publication-date metadata")
check("scholarly_metadata" in scholarly_names, "detects scholarly citation metadata")
check("references" in scholarly_names, "detects a references section")

print(f"\n{'=' * 60}")
print(f"  {PASSED} passed, {FAILED} failed")
print(f"{'=' * 60}\n")
raise SystemExit(1 if FAILED else 0)
