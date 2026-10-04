"""Link target requirements."""

from dataclasses import FrozenInstanceError

import pytest

from armarium.targets import LINK_TARGETS, RECORD_LINK_TARGETS, Target


class TestTarget:
    def test_defaults(self) -> None:
        assert Target("Content") == Target("Content", frozenset(), None, False)
        with pytest.raises(FrozenInstanceError):
            setattr(Target("Content"), "campaign", "campaign_1")


class TestLinkTargets:
    def test_tables_hold_targets_by_field(self) -> None:
        tables = [LINK_TARGETS, *RECORD_LINK_TARGETS.values()]
        assert all(
            isinstance(field, str) and isinstance(target, Target)
            for table in tables
            for field, target in table.items()
        )

    def test_universal_fields_are_bound_on_no_single_type(self) -> None:
        assert not any(
            set(LINK_TARGETS) & set(table) for table in RECORD_LINK_TARGETS.values()
        )
