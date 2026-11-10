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
