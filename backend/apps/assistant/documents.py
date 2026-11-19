"""서류 작성 도움: 템플릿 기반 한국어 초안. 법적 효력이 있는 서식이 아니라 문장 초안이다."""
from dataclasses import dataclass, field


@dataclass
class DocTemplate:
    key: str
    title: str
    fields: dict  # name -> 설명
    body: str
    optional: set = field(default_factory=set)


TEMPLATES = {t.key: t for t in [
    DocTemplate(
        "visa_extension_reason", "체류기간 연장 사유서",
        {"name": "성명", "nationality": "국적", "birth_date": "생년월일", "visa_type": "체류자격(비자)", "stay_until": "체류기간 만료일",
         "workplace": "근무처", "reason": "연장 사유"},
        "체류기간 연장 사유서\n\n성명: {name}\n국적: {nationality}\n생년월일: {birth_date}\n체류자격: {visa_type}\n체류기간 만료일: {stay_until}\n근무처: {workplace}\n\n"
        "위 본인은 현재 {workplace}에서 근무하고 있으며, 다음과 같은 사유로 체류기간 연장을 신청하고자 합니다.\n\n{reason}\n\n"
        "성실히 근무하며 대한민국 법령을 준수하겠습니다. 검토하여 주시기 바랍니다.\n\n{today}\n신청인 {name} (서명)",
    ),
    DocTemplate(
        "employment_certificate_request", "재직(근로) 증명서 발급 요청서",
        {"name": "성명", "workplace": "근무처", "period": "근무 기간", "purpose": "제출처/용도"},
        "재직(근로) 증명서 발급 요청서\n\n안녕하십니까. {workplace} 담당자님께.\n\n저는 {period} 동안 귀사에서 근무한 {name}입니다. "
        "{purpose}에 제출하기 위해 재직(근로) 증명서가 필요하여 발급을 요청드립니다.\n\n바쁘시겠지만 확인 부탁드립니다. 감사합니다.\n\n{today}\n{name} 드림",
    ),
    DocTemplate(
        "absence_notice", "결근/휴가 사유서",
        {"name": "성명", "workplace": "근무처", "absence_date": "결근(휴가) 날짜", "reason": "사유"},
        "결근(휴가) 사유서\n\n{workplace} 담당자님께.\n\n저 {name}은(는) {absence_date}에 아래 사유로 근무가 어려워 미리 알려드립니다.\n\n사유: {reason}\n\n"
        "불편을 드려 죄송합니다. 가능한 빨리 복귀하겠습니다.\n\n{today}\n{name} 드림",
    ),
]}


def render(key: str, values: dict, today: str) -> dict:
    t = TEMPLATES[key]
    missing = [n for n in t.fields if not str(values.get(n, "")).strip()]
    data = {n: (str(values.get(n)).strip() if n not in missing else f"[입력 필요: {t.fields[n]}]") for n in t.fields}
    return {"type": key, "title": t.title, "body_ko": t.body.format(today=today, **data), "missing_fields": missing}
