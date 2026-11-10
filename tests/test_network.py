import pandas as pd
from epl_xt.network import build_pass_network


def test_successful_pass_edges_and_nodes():
    df = pd.DataFrame([
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P1", recipient="P2", x=20, y=30, end_x=30, end_y=40, is_successful=True),
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P1", recipient="P2", x=40, y=50, end_x=60, end_y=40, is_successful=True),
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P1", recipient="P2", x=20, y=30, end_x=30, end_y=40, is_successful=False),
        dict(match_id="SYNTHETIC_TEST_ONLY", team="A", player="P2", recipient="P1", x=60, y=20, end_x=20, end_y=30, is_successful=True),
    ])
    nodes, edges = build_pass_network(df, min_passes=2)
    assert len(edges) == 1
    assert edges.iloc[0]["pass_count"] == 2
    assert edges.iloc[0]["player"] == "P1"
    assert nodes.set_index("player").loc["P1", "x"] == 30
