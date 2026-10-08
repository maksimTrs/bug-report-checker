"""Teacher labeling: run Claude over bug reports and compare label sets."""

CHECKS = (
    "summary_what",
    "summary_where",
    "summary_when",
    "steps",
    "expected",
    "actual",
    "build_version",
)
