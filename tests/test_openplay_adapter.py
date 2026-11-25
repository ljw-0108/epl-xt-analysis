import pandas as pd
import pytest
from epl_xt.openplay_adapter import convert_openplay_passes


def fixture():
    return pd.DataFrame([
        dict(comp="eng", season="2526", match_id=42, team="A", player="P1", type="Pass", outcome="Successful", x=20, y=40, end_x=70, end_y=42),
        dict(comp="eng", season="2526", match_id=42, team="A", player="P2", type="Pass", outcome="Unsuccessful", x=70, y=50, end_x=88, end_y=55),
        dict(comp="eng", season="2526", match_id=42, team="A", player="P2", type="Tackle", outcome="Successful", x=50, y=50, end_x=None, end_y=None),
    ])


def test_real_data_adapter_passes_and_missing_recipient():
    result, audit = convert_openplay_passes(fixture())
    assert len(result) == 2
    assert result.recipient.isna().all()  # no fabricated receiver
    assert result.is_successful.tolist() == [True, False]
    assert audit["matches_with_passes"] == 1
    assert audit["dropped_pass_rows"] == 0


def test_wrong_season_is_rejected():
    src = fixture()
    src.loc[0, "season"] = "2627"
    with pytest.raises(ValueError, match="2025/26"):
        convert_openplay_passes(src)


def test_unknown_outcome_is_rejected():
    src = fixture()
    src.loc[0, "outcome"] = "Maybe"
    with pytest.raises(ValueError, match="Unknown"):
        convert_openplay_passes(src)


def test_out_of_bounds_pass_is_dropped_and_reported():
    src = fixture()
    src.loc[0, "end_x"] = 105
    result, report = convert_openplay_passes(src)
    assert len(result) == 1
    assert report["dropped_pass_rows"] == 1


FLAGS = ("q_CornerTaken", "q_FreekickTaken", "q_IndirectFreekickTaken", "q_ThrowIn", "q_GoalKick")


def with_flags():
    src = fixture()
    for f in FLAGS:
        src[f] = False
    src.loc[1, "q_CornerTaken"] = True  # the unsuccessful pass is a corner
    return src


def test_open_play_flag_from_provider_qualifiers():
    result, report = convert_openplay_passes(with_flags())
    assert result.is_open_play.tolist() == [True, False]
    assert report["set_piece_restart_pass_rows"] == 1
    assert report["set_piece_flags"] == list(FLAGS)


def test_missing_flags_disable_open_play_instead_of_guessing():
    result, report = convert_openplay_passes(fixture())
    assert result.is_open_play.isna().all()
    assert "unavailable" in report["set_piece_flags"]


def test_incomplete_flags_are_rejected():
    src = with_flags()
    src["q_ThrowIn"] = src["q_ThrowIn"].astype(object)
    src.loc[0, "q_ThrowIn"] = None
    with pytest.raises(ValueError, match="complete booleans"):
        convert_openplay_passes(src)
