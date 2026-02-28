import pytest

from experiments.run_robustness import should_apply_domain_rand


@pytest.mark.parametrize("difficulty,expected", [("easy", True), ("medium", True), ("hard", True)])
def test_scope_all(difficulty, expected):
    assert should_apply_domain_rand(True, "all", difficulty) is expected


@pytest.mark.parametrize("difficulty,expected", [("easy", False), ("medium", True), ("hard", True)])
def test_scope_medium_hard(difficulty, expected):
    assert should_apply_domain_rand(True, "medium_hard", difficulty) is expected


@pytest.mark.parametrize("difficulty,expected", [("easy", False), ("medium", False), ("hard", True)])
def test_scope_hard_only(difficulty, expected):
    assert should_apply_domain_rand(True, "hard_only", difficulty) is expected


def test_disabled_always_false():
    assert should_apply_domain_rand(False, "all", "hard") is False


def test_unknown_scope_raises():
    with pytest.raises(ValueError):
        should_apply_domain_rand(True, "bad_scope", "easy")

