import pytest

from app.models.request import Center
from app.services.nlp.llm_client import RouteCriteriaLLMClient
from app.services.nlp.parser_service import RouteCriteriaParserService
from app.services.nlp.preprocessor import QueryPreprocessor
from app.services.nlp.validator import RouteCriteriaValidator


class StubLLMClient:
    def __init__(self, payload):
        self.payload = payload
        self.received = []

    def parse(self, *, preprocessed, center):
        self.received.append((preprocessed, center))
        return self.payload


class StubNLUBasicClient:
    def __init__(self, payload=None, *, should_raise: bool = False):
        self.payload = payload or {}
        self.should_raise = should_raise
        self.received = []

    def parse(self, *, preprocessed):
        self.received.append(preprocessed)
        if self.should_raise:
            raise RuntimeError("basic model down")
        return self.payload


def test_preprocessor_detects_chinese_language():
    preprocessor = QueryPreprocessor()
    result = preprocessor.process(" 我想找一个安静的公园 散步  ")
    assert result.language == "zh"
    assert result.normalized_text == "我想找一个安静的公园 散步"


def test_parser_pipeline_repairs_and_validates_payload():
    stub_payload = {
        "radius_km": 2,
        "duration_min": 15,
        "distance_km": None,
        "include_categories": ["Park", "Unknown"],
        "avoid_categories": ["SHOPPING"],
        "pet_friendly": True,
        "elevation_gain_min_m": -30,
        "route_type": "point_to_point",
        "time_window": "morning",
    }
    parser = RouteCriteriaParserService(
        preprocessor=QueryPreprocessor(),
        llm_client=StubLLMClient(stub_payload),
        validator=RouteCriteriaValidator(),
    )
    center = Center(lat=1.2834, lng=103.8607)
    result = parser.parse(
        "I'm looking for a circular route that's about an hour long.", center
    )

    assert result.center == center
    assert result.radius_km == 2
    assert result.duration_min == 15
    assert result.include_categories == ["park"]
    assert result.avoid_categories == ["shopping"]
    assert result.route_type == "point_to_point"
    assert result.time_window == "morning"
    assert result.elevation_gain_min_m is None


def test_parser_routes_short_queries_to_basic_model():
    basic_payload = {
        "radius_km": 3,
        "duration_min": 20,
        "include_categories": ["park"],
        "avoid_categories": [],
        "pet_friendly": False,
        "route_type": "loop",
    }
    basic_client = StubNLUBasicClient(basic_payload)
    llm_client = StubLLMClient({})
    parser = RouteCriteriaParserService(
        preprocessor=QueryPreprocessor(),
        llm_client=llm_client,
        basic_client=basic_client,
        validator=RouteCriteriaValidator(),
    )

    center = Center(lat=1.0, lng=2.0)
    result = parser.parse("find park", center)

    assert len(basic_client.received) == 1
    assert len(llm_client.received) == 0
    assert result.radius_km == 3
    assert result.duration_min == 20
    assert result.include_categories == ["park"]


def test_parser_falls_back_to_llm_when_basic_model_fails():
    basic_client = StubNLUBasicClient({}, should_raise=True)
    llm_payload = {
        "radius_km": 4,
        "include_categories": ["park"],
        "avoid_categories": [],
        "pet_friendly": False,
        "route_type": "loop",
    }
    llm_client = StubLLMClient(llm_payload)
    parser = RouteCriteriaParserService(
        preprocessor=QueryPreprocessor(),
        llm_client=llm_client,
        basic_client=basic_client,
        validator=RouteCriteriaValidator(),
    )

    center = Center(lat=1.0, lng=2.0)
    result = parser.parse("short request", center)

    assert len(basic_client.received) == 1
    assert len(llm_client.received) == 1
    assert result.radius_km == 4


def test_llm_client_extracts_json_from_structured_output():
    payload = {
        "output": [
            {
                "content": [
                    {
                        "json": {
                            "radius_km": 4,
                            "include_categories": ["park"],
                            "avoid_categories": [],
                            "pet_friendly": False,
                            "route_type": "loop",
                        }
                    }
                ]
            }
        ]
    }

    result = RouteCriteriaLLMClient._extract_json(payload)
    assert result["radius_km"] == 4
    assert result["route_type"] == "loop"


def test_llm_client_extracts_json_from_text_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "{\n  \"radius_km\": 5,\n  \"include_categories\": [\"park\"],\n  \"avoid_categories\": [],\n  \"pet_friendly\": false,\n  \"route_type\": \"loop\"\n}"
                }
            }
        ]
    }

    result = RouteCriteriaLLMClient._extract_json(payload)
    assert result["radius_km"] == 5


def test_llm_client_extracts_json_from_segmented_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": [
                        {
                            "type": "output_text",
                            "text": {
                                "value": "Here is your result:{\"radius_km\":3,\"include_categories\":[\"park\"],\"avoid_categories\":[],\"pet_friendly\":false,\"route_type\":\"loop\"}"
                            },
                        }
                    ]
                }
            }
        ]
    }

    result = RouteCriteriaLLMClient._extract_json(payload)
    assert result["radius_km"] == 3


def test_llm_client_raises_when_json_cannot_be_found():
    with pytest.raises(RuntimeError):
        RouteCriteriaLLMClient._extract_json({"choices": []})


class _TypeErrorResponses:
    def create(self, **kwargs):
        raise TypeError("Responses.create() got an unexpected keyword argument 'response_format'")


class _ChatCompletionsStub:
    def create(self, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": "{\"radius_km\": 5, \"include_categories\": [\"park\"], \"avoid_categories\": [], \"pet_friendly\": false, \"route_type\": \"loop\"}"
                    }
                }
            ]
        }


class _ChatStub:
    def __init__(self):
        self.completions = _ChatCompletionsStub()


class _FallbackClient:
    def __init__(self):
        self.responses = _TypeErrorResponses()
        self.chat = _ChatStub()


def test_llm_client_falls_back_to_chat_completions(tmp_path):
    client = _FallbackClient()
    llm_client = RouteCriteriaLLMClient(client=client)
    preprocessed = QueryPreprocessor().process("test query")
    center = Center(lat=1.0, lng=2.0)

    result = llm_client.parse(preprocessed=preprocessed, center=center)
    assert result["radius_km"] == 5
