import json

from evals.session11_generation.run_ragas_s11 import to_jsonable


class FakeArray:
    def tolist(self):
        return [0.91, 0.82]


class FakeScalar:
    def item(self):
        return 0.77


def test_ragas_result_serializer_handles_numpy_like_values():
    payload = {
        "records": [
            {
                "faithfulness": FakeScalar(),
                "answer_relevancy": FakeArray(),
                "context_precision": float("nan"),
                "context_recall": float("inf"),
            }
        ]
    }

    converted = to_jsonable(payload)

    assert converted == {
        "records": [
            {
                "faithfulness": 0.77,
                "answer_relevancy": [0.91, 0.82],
                "context_precision": None,
                "context_recall": None,
            }
        ]
    }

    json.dumps(converted, indent=2, sort_keys=True)
