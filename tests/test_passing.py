import math

import numpy as np
import pandas as pd
import pytest

from epl_xt.passing import (add_pass_geometry, direction_distribution, distance_to_goal_m,
                            filter_passes, passing_summary)


def p(x, y, end_x, end_y, ok=True, team="A", match="SYNTHETIC_TEST_ONLY_1", player="P1"):
    return dict(match_id=match, team=team, player=player, recipient=None,
                x=x, y=y, end_x=end_x, end_y=end_y, is_successful=ok)


def geom(*rows):
    return add_pass_geometry(pd.DataFrame(list(rows)))


def test_filter_by_team_and_match():
    df = pd.DataFrame([p(10, 50, 20, 50), p(10, 50, 20, 50, team="B"),
                       p(10, 50, 20, 50, match="SYNTHETIC_TEST_ONLY_2")])
    assert len(filter_passes(df, team="A")) == 2
    assert len(filter_passes(df, team="A", match_ids=["SYNTHETIC_TEST_ONLY_2"])) == 1
    assert filter_passes(df, team="Z").empty
    assert filter_passes(df, match_ids=[]).empty


def test_direction_classes_use_metric_pitch():
    g = geom(p(50, 50, 60, 50), p(50, 50, 40, 50), p(50, 50, 50, 60), p(50, 50, 50, 50))
    assert g["direction"].tolist() == ["forward", "backward", "lateral", "zero_length"]
    assert g["length_m"].iloc[0] == pytest.approx(10.5)
    assert g["length_m"].iloc[2] == pytest.approx(6.8)
    assert math.isnan(g["angle_deg"].iloc[3])


def test_exact_45_and_135_degrees_are_lateral():
    # 6.8 x-units = 7.14 m, 10.5 y-units = 7.14 m -> exactly 45 degrees in metres.
    g = geom(p(40, 40, 46.8, 50.5), p(40, 40, 33.2, 50.5))
    assert g["angle_deg"].tolist() == [45.0, 135.0]
    assert g["direction"].tolist() == ["lateral", "lateral"]
    # Raw deltas (10, 12) are 50.2 degrees if 0..100 units were treated as square (lateral),
    # but 10.5 m forward x 8.16 m sideways = 37.9 degrees on the metric pitch (forward).
    g2 = geom(p(40, 40, 50, 52))
    assert g2["angle_deg"].iloc[0] == pytest.approx(math.degrees(math.atan2(8.16, 10.5)))
    assert g2["direction"].iloc[0] == "forward"


def test_progressive_threshold_is_inclusive_25_percent():
    # Start 40 m from goal centre on the x axis: x = 100 - 40/1.05.
    start_x = 100 - 40 / 1.05
    exactly = 100 - 30 / 1.05      # 30 m away = exactly 25% closer
    short = 100 - 30.5 / 1.05      # 30.5 m away = 23.75% closer
    g = geom(p(start_x, 50, exactly, 50), p(start_x, 50, short, 50),
             p(start_x, 50, exactly, 50, ok=False))
    assert distance_to_goal_m([start_x], [50])[0] == pytest.approx(40)
    assert g["is_progressive"].tolist() == [True, False, False]


def test_backward_pass_never_progressive_and_goal_centre_start():
    g = geom(p(60, 50, 40, 50), p(100, 50, 100, 50))
    assert not g["is_progressive"].any()


def test_direction_distribution_and_summary():
    g = geom(p(50, 50, 60, 50), p(50, 50, 60, 50, ok=False), p(50, 50, 40, 50))
    dist = direction_distribution(g).set_index("direction")
    assert dist.loc["forward", "attempted"] == 2
    assert dist.loc["forward", "successful"] == 1
    assert dist.loc["forward", "completion_rate"] == 0.5
    assert dist.loc["backward", "share_of_attempted"] == pytest.approx(1 / 3)
    assert dist.loc["lateral", "attempted"] == 0
    assert np.isnan(dist.loc["lateral", "completion_rate"])
    s = passing_summary(g)
    assert s == {"matches": 1, "attempted": 3, "successful": 2,
                 "completion_rate": pytest.approx(2 / 3), "progressive": 0}


def test_empty_selection_summary_has_no_fake_rates():
    g = geom(p(50, 50, 60, 50)).iloc[0:0]
    assert passing_summary(g) == {"matches": 0, "attempted": 0, "successful": 0,
                                  "completion_rate": None, "progressive": 0}
    assert direction_distribution(g)["attempted"].sum() == 0
