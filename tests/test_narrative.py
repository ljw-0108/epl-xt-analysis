import numpy as np
import pandas as pd

from epl_xt.narrative import compare_story, direction_story, pass_story, xt_story, zone_phrase


def test_pass_story_uses_summary_numbers_only():
    s = {"matches": 1, "attempted": 329, "successful": 239, "completion_rate": 239 / 329, "progressive": 28}
    text = pass_story("Arsenal", s)
    for part in ("1경기", "329번", "239번", "73%", "28번"):
        assert part in text
    assert pass_story("A", {"matches": 0, "attempted": 0, "successful": 0,
                            "completion_rate": None, "progressive": 0}).startswith("선택한 범위에")


def test_direction_story_names_most_common_and_hardest():
    dist = pd.DataFrame({"direction": ["forward", "lateral", "backward"], "attempted": [141, 153, 35],
                         "share_of_attempted": [141 / 329, 153 / 329, 35 / 329],
                         "completion_rate": [83 / 141, 124 / 153, 32 / 35]})
    text = direction_story(dist)
    assert "47%는 옆으로" in text and "앞(상대 골문 쪽)으로 보낸 패스의 성공률이 59%" in text


def test_zone_phrase_thirds_and_lanes():
    assert zone_phrase(0, 0) == "우리 진영의 측면"
    assert zone_phrase(4, 6) == "중앙의 중앙 통로"
    assert zone_phrase(7, 11) == "상대 진영의 측면"


def test_xt_story_and_missing_row():
    row = pd.Series({"pass_xt_total": 0.761, "positive_xt": 0.942, "negative_xt": -0.181})
    m = np.zeros((8, 12))
    m[0, 11] = 0.22
    text = xt_story("Arsenal", row, m)
    assert "0.76점" in text and "+0.94점" in text and "-0.18점" in text and "상대 진영의 측면(0.22점)" in text
    assert "계산할 수 없습니다" in xt_story("Arsenal", None, m)
    assert "출발 구역" not in xt_story("A", row, -np.ones((8, 12)))  # no positive zone -> no claim


def test_compare_story_lead_and_tie():
    found = pd.DataFrame({"attempted": [27, 26], "progressive": [2, 2], "pass_xt": [0.0161, 0.0231]},
                         index=["Declan Rice", "William Saliba"])
    text = compare_story(found, "Declan Rice", "William Saliba")
    assert "Declan Rice 쪽이 1번 더 많습니다" in text
    assert "전진 패스는 두 선수가 같습니다(2번)" in text
    assert "William Saliba 쪽이 0.007점 더 많습니다" in text
