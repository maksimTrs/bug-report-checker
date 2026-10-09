import pytest

from bug_report_checker.config import Config, ConfigError, load_config, parse_config


def test_missing_file_gives_defaults(tmp_path):
    assert load_config(tmp_path / "bug-checker.yml") == Config()


@pytest.mark.parametrize("text", ["", "# only a comment\n"])
def test_empty_file_gives_defaults(text):
    assert parse_config(text) == Config()


def test_defaults():
    c = Config()
    assert c.bug_labels == ("bug",)
    assert c.status_labels == ("Submitted", "Open", "In Progress")
    assert c.threshold == 0.827  # calibrated on the published model (T3.4)
    assert c.comment_on_success is True
    assert c.build_version_pattern is None  # no team format in public code
    assert c.environments == ()


def test_full_config_from_file(tmp_path):
    path = tmp_path / "bug-checker.yml"
    path.write_text(
        "bug_labels: [defect]\n"
        "status_labels: [New, Triaged]\n"
        "threshold: 0.9\n"
        "comment_on_success: false\n"
        "build_version_pattern: 'v\\d+\\.\\d+'\n"
        "environments: [staging, qa1]\n",
        encoding="utf-8",
    )
    assert load_config(path) == Config(
        bug_labels=("defect",),
        status_labels=("New", "Triaged"),
        threshold=0.9,
        comment_on_success=False,
        build_version_pattern=r"v\d+\.\d+",
        environments=("staging", "qa1"),
    )


def test_partial_config_keeps_other_defaults():
    assert parse_config("threshold: 1") == Config(threshold=1.0)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("- a\n- b", "must be a mapping of keys"),
        ("treshold: 0.9", "unknown key 'treshold'"),
        ("threshold: high", "'threshold' must be a number from 0.5 to 1"),
        ("threshold: 0.3", "'threshold' must be a number from 0.5 to 1"),
        ("threshold: true", "'threshold' must be a number from 0.5 to 1"),
        ("comment_on_success: 'no'", "'comment_on_success' must be true or false"),
        ("bug_labels: bug", "'bug_labels' must be a list of non-empty strings"),
        ("environments: [dev1, '']", "'environments' must be a list of non-empty"),
        ("status_labels: []", "'status_labels' must list at least one status"),
        ("build_version_pattern: '[0-9'", "'build_version_pattern' is not a valid"),
        ("threshold: [", "not valid YAML"),
    ],
)
def test_invalid_config_names_the_problem(text, message):
    with pytest.raises(ConfigError, match=message):
        parse_config(text)
