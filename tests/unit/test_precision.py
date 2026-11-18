from ranx import Qrels, Run, evaluate

from test_precision import build_reranked_run, document_text, print_rank_changes


def test_document_text_labels_movie_attributes() -> None:
    text = document_text(
        {
            "title": "Интерстеллар",
            "year": 2014,
            "countries": ["США", "Великобритания"],
            "genres": ["фантастика", "драма"],
            "moods": ["эпичный"],
            "rating": 8.6,
            "description": "Экспедиция в космос ради спасения человечества.",
        }
    )

    assert text == (
        "Название: Интерстеллар. Год: 2014. Страны: США, Великобритания. "
        "Жанры: фантастика, драма. Настроение: эпичный. Рейтинг: 8.6. "
        "Сюжет: Экспедиция в космос ради спасения человечества."
    )


def test_document_text_omits_empty_attributes() -> None:
    assert document_text({"title": "Фильм", "year": None, "genres": [], "rating": 0}) == (
        "Название: Фильм. Рейтинг: 0"
    )


def test_print_rank_changes_shows_movie_titles_and_positions(capsys) -> None:
    print_rank_changes(
        "космическое путешествие",
        [
            {"id": "1", "title": "Фильм до", "year": 2000},
            {"id": "2", "title": "Фильм после", "year": 2020},
        ],
        [
            {"id": "2", "title": "Фильм после", "year": 2020},
            {"id": "1", "title": "Фильм до", "year": 2000},
        ],
    )

    output = capsys.readouterr().out
    assert "1 ->  2  Фильм до (2000) [id=1]" in output
    assert "2 ->  1  Фильм после (2020) [id=2]" in output


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
