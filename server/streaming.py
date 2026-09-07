"""Read top-level JSON string fields safely while a model is still generating."""
import json


def fields_so_far(text):
    decoder = json.JSONDecoder()
    fields = {}
    i = 0
    while i < len(text) and text[i].isspace(): i += 1
    if i == len(text) or text[i] != '{': return fields
    i += 1
    while i < len(text):
        while i < len(text) and (text[i].isspace() or text[i] == ','): i += 1
        try: key, end = decoder.raw_decode(text, i)
        except ValueError: break
        if not isinstance(key, str): break
        i = end
        while i < len(text) and text[i].isspace(): i += 1
        if i == len(text) or text[i] != ':': break
        i += 1
        while i < len(text) and text[i].isspace(): i += 1
        try:
            value, end = decoder.raw_decode(text, i)
            fields[key] = value
            i = end
        except ValueError:
            if i < len(text) and text[i] == '"':
                # Remove only an unfinished escape at the end, never invent text.
                partial = text[i:]
                for trim in range(min(7, len(partial))):
                    candidate = partial[:len(partial)-trim] if trim else partial
                    try:
                        fields[key] = json.loads(candidate+'"')
                        break
                    except ValueError: pass
            break
    return fields
