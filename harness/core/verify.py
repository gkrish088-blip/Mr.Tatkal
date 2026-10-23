def lookup(value, path):
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def verify(assertion, observation):
    if not assertion:
        return True
    if "text" in assertion:
        return str(assertion["text"]) in str(observation.get("text", observation))
    if "url" in assertion:
        return str(assertion["url"]) in observation.get("url", "")
    if "key" in assertion:
        try:
            actual = lookup(observation, assertion["key"])
            return actual == assertion["equals"] if "equals" in assertion else bool(actual)
        except (KeyError, TypeError, IndexError, ValueError):
            return False
    raise ValueError("Unsupported assertion")
