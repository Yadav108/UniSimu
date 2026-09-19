import pytest

from unisimu.copy import FATE_ACCENT_HEX, STAGE_CAPTIONS, STAGE_LABELS
from unisimu.physics import stellar


@pytest.mark.parametrize("track", [stellar.LOW_MASS_TRACK, stellar.NEUTRON_STAR_TRACK, stellar.BLACK_HOLE_TRACK])
def test_every_stage_after_formation_has_a_caption(track):
    """The viewport caption shows on entering each stage; a missing entry
    would silently skip the explanation for that stage."""
    for stage in track[1:]:  # the protostar is where the sim starts, not entered
        assert STAGE_CAPTIONS.get(stage), f"no caption for {stage}"


def test_every_stage_has_a_label():
    assert set(STAGE_LABELS) == set(stellar.STAGES)


def test_every_terminal_stage_has_a_fate_accent():
    assert set(FATE_ACCENT_HEX) == set(stellar.TERMINAL_STAGES)


def test_captions_are_short_enough_for_the_overlay():
    """The overlay is capped at ~34em wide and shown for 8s; keep captions to a
    couple of sentences."""
    for stage, text in STAGE_CAPTIONS.items():
        assert len(text) <= 260, f"{stage} caption is {len(text)} chars"
