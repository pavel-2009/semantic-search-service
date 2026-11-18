from ranx import Qrels, Run, evaluate

from test_precision import build_reranked_run


def test_precision_at_5_is_relevant_results_in_top_5() -> None:
    reranked = build_reranked_run(
        {
            "q1": [
                {"id": 1},
                {"id": 2},
                {"id": 3},
                {"id": 4},
                {"id": 5},
                {"id": 6},
            ]
        }
    )
    qrels = Qrels({"q1": {"1": 2, "3": 1, "6": 1}})
    run = Run(reranked)

    result = evaluate(qrels, run, metrics=["precision@5"])

    assert float(result) == 2 / 5
