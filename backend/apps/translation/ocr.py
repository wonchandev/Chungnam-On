"""사진 OCR 결과(Google Vision TEXT_DETECTION 응답)를 문단 단위 영역으로 정리한다.

영역 좌표는 업로드한 원본 이미지의 픽셀 기준이다. 프론트는 image_width/image_height 로 비율을 맞춰 오버레이한다.
"""

MAX_REGIONS = 100

# Vision 의 detectedBreak 종류 → 이어 붙일 문자
_BREAKS = {"SPACE": " ", "SURE_SPACE": " ", "EOL_SURE_SPACE": "\n", "LINE_BREAK": "\n", "HYPHEN": "-\n"}


def _vertices(bounding_box: dict | None) -> list[dict]:
    # Vision 은 값이 0 인 좌표를 생략한다.
    return [{"x": v.get("x", 0), "y": v.get("y", 0)} for v in (bounding_box or {}).get("vertices", [])]


def _box(vertices: list[dict]) -> dict:
    if not vertices:
        return {"x": 0, "y": 0, "width": 0, "height": 0}
    xs, ys = [v["x"] for v in vertices], [v["y"] for v in vertices]
    return {"x": min(xs), "y": min(ys), "width": max(xs) - min(xs), "height": max(ys) - min(ys)}


def _paragraph_text(paragraph: dict) -> str:
    out = []
    for word in paragraph.get("words", []):
        for symbol in word.get("symbols", []):
            out.append(symbol.get("text", ""))
            brk = ((symbol.get("property") or {}).get("detectedBreak") or {}).get("type")
            out.append(_BREAKS.get(brk, ""))
    return "".join(out).strip()


def _language(node: dict) -> str | None:
    languages = (node.get("property") or {}).get("detectedLanguages") or []
    if not languages:
        return None
    return languages[0].get("languageCode", "").split("-", 1)[0].lower() or None


def parse_annotation(response: dict) -> dict:
    """Vision 응답 1건 → {"text", "image_width", "image_height", "regions": [{text, vertices, box, language}]}"""
    full = response.get("fullTextAnnotation") or {}
    pages = full.get("pages") or []
    regions = []
    for page in pages:
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                text = _paragraph_text(paragraph)
                if not text:
                    continue
                vertices = _vertices(paragraph.get("boundingBox"))
                regions.append({
                    "text": text,
                    "vertices": vertices,
                    "box": _box(vertices),
                    "language": _language(paragraph) or _language(block),
                })
    first = pages[0] if pages else {}
    return {
        "text": (full.get("text") or "").strip(),
        "image_width": first.get("width"),
        "image_height": first.get("height"),
        "regions": regions[:MAX_REGIONS],
    }
