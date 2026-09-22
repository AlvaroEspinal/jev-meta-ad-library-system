"""Pure request/answer contracts. No credentials, network, policy acceptance or actions."""
import json
import math

CONTRACT_VERSION = "jev-decision/2"
MAX_BODY_BYTES = 120_000  # Local byte guard, NOT the provider's token limit.
MAX_RESPONSE_BYTES = 2_000_000
TYPES = {"choice", "score", "noul"}


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def number(value, low=0, high=1):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def text(value):
    return isinstance(value, str) and bool(value.strip())


def description(value):
    # Structured descriptions are serialized as JSON by the provider. Empty containers
    # and scalar booleans/numbers are not meaningful instructions in this client.
    return text(value) or isinstance(value, (dict, list)) and bool(value)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ContractError("non-finite JSON number")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ContractError("invalid JSON") from exc


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ContractError("request must be finite JSON") from exc


def validate_request(payload, model):
    require(isinstance(payload, dict), "request must be an object")
    require(text(model) and len(model) <= 256, "invalid model identifier")
    require("state" in payload and payload["state"] is not None, "state is required")
    require(isinstance(payload["state"], (str, dict, list)), "state must be text, object or array")
    questions = payload.get("questions")
    require(isinstance(questions, dict) and bool(questions), "questions must be a nonempty object")
    for name, question in questions.items():
        require(text(name), "question ID must be nonempty")
        require(isinstance(question, dict), "question must be an object")
        kind = question.get("type")
        require(isinstance(kind, str) and kind in TYPES, "unsupported question type")
        require(description(question.get("instructions")), "nonempty instructions are required")
        criteria = question.get("criteria")
        if kind == "choice":
            require(isinstance(criteria, dict) and 2 <= len(criteria) <= 255,
                    "Choice requires a map of 2-255 options")
            require(all(text(k) and (v is None or description(v)) for k, v in criteria.items()),
                    "invalid Choice criteria")
        elif kind == "score":
            require(isinstance(criteria, list) and 2 <= len(criteria) <= 10,
                    "Score requires an ordered array of 2-10 levels")
            require(all(description(v) for v in criteria), "invalid Score level")
        elif "criteria" in question:
            require(isinstance(criteria, dict) and set(criteria) == {"true", "false"},
                    "Noul criteria must include true and false")
            require(all(description(v) for v in criteria.values()), "invalid Noul criteria")
    body = {"model": model, "state": payload["state"], "questions": questions}
    require(len(canonical(body)) <= MAX_BODY_BYTES, "request exceeds local byte safety cap")
    return body


def distribution(answer, expected):
    probs = answer.get("probabilities")
    require(isinstance(probs, dict) and set(probs) == set(expected), "probability keys mismatch")
    require(all(number(v) for v in probs.values()), "invalid probability value")
    require(abs(sum(probs.values()) - 1) <= 0.02, "probabilities do not sum to one")
    require(number(answer.get("confidence")), "invalid or missing confidence")
    return probs


def validate_response(response, questions, expected_model=None):
    require(isinstance(response, dict), "response must be an object")
    require(response.get("error") is None, "provider returned an error")
    require(text(response.get("model")), "resolved model is missing")
    require(expected_model is None or response["model"] == expected_model, "resolved model mismatch")
    answers = response.get("answers")
    require(isinstance(answers, dict) and set(answers) == set(questions), "answer IDs mismatch")
    # Return only schema-checked fields, not arbitrary provider text.
    clean = {}
    for name, question in questions.items():
        answer = answers[name]
        kind = question["type"]
        require(isinstance(answer, dict) and answer.get("type") == kind, "answer type mismatch")
        if kind == "noul":
            require(number(answer.get("noul")), "invalid Noul probability")
            clean[name] = {"type": kind, "noul": answer["noul"]}
        elif kind == "choice":
            probs = distribution(answer, question["criteria"])
            choice = answer.get("choice")
            require(isinstance(choice, str) and choice in probs, "invalid choice")
            require(probs[choice] >= max(probs.values()) - 1e-6, "choice is not a maximum")
            clean[name] = {"type": kind, "choice": choice, "probabilities": probs,
                           "confidence": answer["confidence"]}
        else:
            levels = question["criteria"]
            expected = {str(i): v for i, v in enumerate(levels)}
            probs = distribution(answer, expected)
            require(answer.get("legend") == expected, "Score legend mismatch")
            require(number(answer.get("score"), 0, len(levels)-1), "invalid Score value")
            mean = sum(int(i) * p for i, p in probs.items())
            require(abs(mean - answer["score"]) <= 0.02 * (len(levels)-1), "Score/distribution mismatch")
            clean[name] = {"type": kind, "score": answer["score"], "legend": expected,
                           "probabilities": probs, "confidence": answer["confidence"]}
    return clean


def safe_usage(value):
    """Unknown stays unknown. Never copy arbitrary provider error/log text."""
    if not isinstance(value, dict):
        return None
    result = {}
    for key in ("input_tokens", "output_tokens", "prompt_tokens", "completion_tokens", "total_tokens"):
        if type(value.get(key)) is int and value[key] >= 0:
            result[key] = value[key]
    for key in ("cost", "total_cost"):
        if number(value.get(key), 0, float("inf")):
            result[key] = value[key]
    return result or None
