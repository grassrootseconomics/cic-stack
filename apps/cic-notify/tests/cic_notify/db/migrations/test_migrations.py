import pytest


def test_single_head_revision(alembic_runner):
    heads = alembic_runner.heads
    head_count = len(heads)
    assert head_count == 1


def test_upgrade(alembic_runner):
    try:
        alembic_runner.migrate_up_to("head")
    except RuntimeError:
        pytest.fail('Failed to upgrade to the head revision.')


def test_up_down_consistency(alembic_runner):
    try:
        for revision in alembic_runner.history.revisions:
            alembic_runner.migrate_up_to(revision)
    except RuntimeError:
        pytest.fail('Failed to upgrade through each revision individually.')

    try:
        for revision in reversed(alembic_runner.history.revisions):
            alembic_runner.migrate_down_to(revision)
    except RuntimeError:
        pytest.fail('Failed to downgrade through each revision individually.')
