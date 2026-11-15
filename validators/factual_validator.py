import json
import re
from typing import Any


class FactualValidationError(Exception):
    """Raised when generated content contains unsupported factual claims."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.details = details or {}
        super().__init__(message)


# --------------------------------------------------
# Number Words
# --------------------------------------------------

ENGLISH_NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
}


ARABIC_NUMBER_WORDS = {
    "صفر": "0",
    "واحد": "1",
    "واحدة": "1",
    "اثنان": "2",
    "اثنين": "2",
    "اثنتان": "2",
    "ثلاثة": "3",
    "أربعة": "4",
    "اربعة": "4",
    "خمسة": "5",
    "ستة": "6",
    "سبعة": "7",
    "سبع": "7",
    "ثمانية": "8",
    "ثمان": "8",
    "تسعة": "9",
    "عشرة": "10",
}


# --------------------------------------------------
# Capability / Claim Rules
# --------------------------------------------------

CAPABILITY_RULES = {

    "digital_application": {

        "generated_patterns": [
            r"\bapply now\b",
            r"\bapply online\b",
            r"\bapply through\b",
            r"\bsubmit (?:your |an )?(?:application|request)\b",
            r"\bstart (?:your |an )?(?:application|request)\b",
            r"\bcomplete (?:your |the )?(?:application|request)\b",
            r"ابدأ بطلبك",
            r"ابدأ طلبك",
            r"قدّم طلبك",
            r"قدم طلبك",
            r"قدّم الطلب",
            r"قدم الطلب",
            r"التقديم الإلكتروني",
            r"التقديم عبر الإنترنت",
        ],

        "evidence_patterns": [
            r"\bapply online\b",
            r"\bsubmit (?:an |your )?(?:application|request)\b",
            r"\bdigital application\b",
            r"التقديم الإلكتروني",
            r"تقديم الطلب إلكترونياً",
            r"تقديم الطلب إلكترونيًا",
        ],

        "message": (
            "Generated content implies digital application or "
            "request submission, but the campaign brief does not "
            "explicitly confirm that capability."
        )
    },


    "online_payment": {

        "generated_patterns": [
            r"\bonline payment\b",
            r"\bpay online\b",
            r"\bdigital payment\b",
            r"الدفع الإلكتروني",
            r"ادفع إلكترونياً",
            r"ادفع إلكترونيًا",
            r"الدفع عبر الإنترنت",
        ],

        "evidence_patterns": [
            r"\bonline payment\b",
            r"\bpay online\b",
            r"\bdigital payment\b",
            r"الدفع الإلكتروني",
            r"الدفع عبر الإنترنت",
        ],

        "message": (
            "Generated content claims online payment, but the "
            "campaign brief does not explicitly confirm payment."
        )
    },


    "request_tracking": {

        "generated_patterns": [
            r"\btrack (?:your )?(?:request|application)\b",
            r"\brequest tracking\b",
            r"\bapplication tracking\b",
            r"تتبّع طلبك",
            r"تتبع طلبك",
            r"متابعة الطلب",
            r"متابعة طلبك",
            r"متابعة الطلبات",
        ],

        "evidence_patterns": [
            r"\btrack (?:your )?(?:request|application)\b",
            r"\brequest tracking\b",
            r"\bapplication tracking\b",
            r"تتبع طلبك",
            r"تتبّع طلبك",
            r"متابعة الطلب",
        ],

        "message": (
            "Generated content claims request tracking, but the "
            "campaign brief does not explicitly confirm tracking."
        )
    },


    "continuous_availability": {

        "generated_patterns": [
            r"\b24\s*/\s*7\b",
            r"\b24\s+hours\s+a\s+day\b",
            r"\b(?:available|accessible)\s+(?:online\s+)?(?:24\s+hours(?:\s+a\s+day)?|anytime|at\s+any\s+time)\b",
            r"\b(?:access|use)\s+(?:the\s+)?(?:services?\s+)?(?:anytime|at\s+any\s+time)\b",
            r"\balways\s+(?:available|accessible)\b",
            r"\b(?:available|accessible)\s+always\b",
            r"\baround the clock\b",
            r"على مدار الساعة",
            r"متاح(?:ة|ات)?\s+دائم(?:اً|ا)",
            r"متاح(?:ة|ات)?\s+في أي وقت",
            r"في أي وقت",
            r"٢٤\s+ساعة\s+يومي(?:اً|ا)",
            r"٢٤\s*/\s*٧",
        ],

        "evidence_patterns": [
            r"\b24\s*/\s*7\b",
            r"\b24\s+hours\s+a\s+day\b",
            r"\b(?:available|accessible)\s+(?:online\s+)?(?:24\s+hours(?:\s+a\s+day)?|anytime|at\s+any\s+time)\b",
            r"\b(?:access|use)\s+(?:the\s+)?(?:services?\s+)?(?:anytime|at\s+any\s+time)\b",
            r"\balways\s+(?:available|accessible)\b",
            r"\b(?:available|accessible)\s+always\b",
            r"\baround the clock\b",
            r"على مدار الساعة",
            r"متاح(?:ة|ات)?\s+دائم(?:اً|ا)",
            r"متاح(?:ة|ات)?\s+في أي وقت",
            r"في أي وقت",
            r"٢٤\s+ساعة\s+يومي(?:اً|ا)",
            r"٢٤\s*/\s*٧",
        ],

        "message": (
            "Generated content claims continuous availability, "
            "but the campaign brief does not explicitly confirm it."
        )
    },


    "unrestricted_access": {

        "generated_patterns": [
            r"\b(?:access|use)\s+(?:the\s+)?(?:services?\s+)?(?:(?:anytime|at\s+any\s+time)\s+)?from\s+anywhere\b",
            r"\b(?:available|accessible)\s+(?:online\s+)?from\s+anywhere\b",
            r"\bwherever\s+you\s+(?:are|may\s+be)\b",
            r"من أي مكان",
            r"أينما كنت",
        ],

        "evidence_patterns": [
            r"\b(?:access|use)\s+(?:the\s+)?(?:services?\s+)?(?:(?:anytime|at\s+any\s+time)\s+)?from\s+anywhere\b",
            r"\b(?:available|accessible)\s+(?:online\s+)?from\s+anywhere\b",
            r"\bwherever\s+you\s+(?:are|may\s+be)\b",
            r"من أي مكان",
            r"أينما كنت",
        ],

        "message": (
            "Generated content claims unrestricted access from anywhere, "
            "but the approved evidence does not explicitly support it."
        )
    },


    "new_service_claim": {

        "generated_patterns": [
            r"\bnew(?:ly\s+launched)?\s+(?:[a-z-]+\s+){0,4}services\b",
            r"خدمات(?:\s+[\u0600-\u06ff]+){0,4}\s+جديدة",
            r"خدمات\s+جديدة",
        ],

        "evidence_patterns": [
            r"\bnew(?:ly\s+launched)?\s+(?:[a-z-]+\s+){0,4}services\b",
            r"خدمات(?:\s+[\u0600-\u06ff]+){0,4}\s+جديدة",
            r"خدمات\s+جديدة",
        ],

        "message": (
            "Generated content describes the services themselves as new, "
            "but the approved evidence only establishes current availability."
        )
    },


    "faster_processing": {

        "generated_patterns": [
            r"\bfaster processing\b",
            r"\breduce waiting\b",
            r"\breduced waiting\b",
            r"\bsave time\b",
            r"\bfaster procedures\b",
            r"\bquicker processing\b",
            r"توفير الوقت",
            r"تقليل وقت الانتظار",
            r"تسريع الإجراءات",
            r"إجراءات أسرع",
        ],

        "evidence_patterns": [
            r"\bfaster processing\b",
            r"\breduce waiting\b",
            r"\breduced waiting\b",
            r"\bsave time\b",
            r"\bquicker processing\b",
            r"توفير الوقت",
            r"تقليل وقت الانتظار",
            r"تسريع الإجراءات",
        ],

        "message": (
            "Generated content claims faster processing or time "
            "savings, but the campaign brief does not confirm it."
        )
    },


    "efficiency_improvement": {

        "generated_patterns": [
            r"\bimprove efficiency\b",
            r"\bimproved efficiency\b",
            r"\bmore efficient\b",
            r"\bincrease efficiency\b",
            r"\benhance efficiency\b",
            r"\befficient procedures\b",
            r"\bstreamlin(?:e|es|ed|ing)\b",
            r"تحقيق كفاءة",
            r"تحسين الكفاءة",
            r"زيادة الكفاءة",
            r"رفع الكفاءة",
            r"إجراءات أكثر كفاءة",
            r"اجراءات أكثر كفاءة",
        ],

        "evidence_patterns": [
            r"\bimprove efficiency\b",
            r"\bimproved efficiency\b",
            r"\bmore efficient\b",
            r"\bincrease efficiency\b",
            r"\benhance efficiency\b",
            r"\bstreamlin(?:e|es|ed|ing)\b",
            r"تحقيق كفاءة",
            r"تحسين الكفاءة",
            r"زيادة الكفاءة",
            r"رفع الكفاءة",
        ],

        "message": (
            "Generated content claims an efficiency improvement, "
            "but the campaign brief does not explicitly support "
            "that benefit."
        )
    },


    "productivity_improvement": {

        "generated_patterns": [
            r"\bimprov(?:e|es|ed|ing) productivity\b",
            r"\bincreas(?:e|es|ed|ing) productivity\b",
            r"\bboost(?:s|ed|ing)? productivity\b",
            r"\bmore productive\b",
        ],

        "evidence_patterns": [
            r"\bimprov(?:e|es|ed|ing) productivity\b",
            r"\bincreas(?:e|es|ed|ing) productivity\b",
            r"\bboost(?:s|ed|ing)? productivity\b",
            r"\bmore productive\b",
        ],

        "message": (
            "Generated content claims a productivity benefit, but "
            "the approved evidence does not explicitly support it."
        )
    },


    "ease_of_process": {

        "generated_patterns": [
            r"\beasier\b",
            r"\beasily\b",
            r"\bsimplify\b",
            r"\bsimplifies\b",
            r"\bsimplified\b",
            r"\bmore convenient\b",
            r"\bwith ease\b",
            r"بسهولة",
            r"أسهل",
            r"اسهل",
            r"تسهيل",
            r"تبسيط",
            r"بشكل أسهل",
            r"بطريقة أسهل",
        ],

        "evidence_patterns": [
            r"\beasier\b",
            r"\beasily\b",
            r"\bsimplify\b",
            r"\bsimplified\b",
            r"\bmore convenient\b",
            r"بسهولة",
            r"أسهل",
            r"اسهل",
            r"تسهيل",
            r"تبسيط",
        ],

        "message": (
            "Generated content claims that the service or process "
            "is easier or simplified, but the campaign brief does "
            "not explicitly support that benefit."
        )
    },
}


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _contains_pattern(
    text: str,
    pattern: str
) -> bool:

    return (
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )
        is not None
    )


def _extract_numbers(
    text: str
) -> set[str]:

    numbers = set()

    arabic_indic_map = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789"
    )

    normalized_text = text.translate(
        arabic_indic_map
    )


    numbers.update(
        re.findall(
            r"\b\d+\b",
            normalized_text
        )
    )


    lowered = normalized_text.casefold()


    for word, value in (
        ENGLISH_NUMBER_WORDS.items()
    ):

        if re.search(
            rf"\b{re.escape(word)}\b",
            lowered
        ):

            numbers.add(
                value
            )


    for word, value in (
        ARABIC_NUMBER_WORDS.items()
    ):

        if word in normalized_text:

            numbers.add(
                value
            )


    return numbers


# --------------------------------------------------
# Structured Campaign Validation
# --------------------------------------------------

PLATFORM_BEHAVIOR_RULES = {
    "link_in_bio": [
        r"\blink in (?:our |the )?bio\b",
        r"\bvisit (?:our |the )?bio\b",
        r"الرابط في (?:النبذة التعريفية|البايو)",
    ],
    "swipe_up": [r"\bswipe up\b"],
    "click_or_tap_link": [
        r"\bclick (?:on )?(?:the |our )?link\b",
        r"\btap (?:on )?(?:the |our )?link\b",
    ],
}


AUDIENCE_PATTERNS = {
    "farmers": r"\bfarmers?\b",
    "producers": r"\bproducers?\b",
    "agricultural_businesses": r"\bagricultural businesses\b",
    "rural_communities": r"\brural communit(?:y|ies)\b",
    "rural_residents": r"\brural residents?\b",
    "citizens": r"\b(?:all\s+)?(?:Lebanese citizens|citizens?(?: of Lebanon)?)\b",
    "residents": r"\bresidents?\b",
    "general_public": r"\b(?:the\s+)?general public\b",
    "businesses_generally": r"(?<!agricultural )\bbusinesses\b",
    "families": r"\bfamil(?:y|ies)\b",
    "students": r"\bstudents?\b",
    "entrepreneurs": r"\bentrepreneurs?\b",
    "small_businesses": r"\bsmall businesses\b|\bSMEs?\b",
    "municipalities": r"\bmunicipalit(?:y|ies)\b",
    "public_employees": r"\bpublic employees?\b",
    "arabic_farmers": r"المزارع(?:ون|ين)?",
    "arabic_producers": r"المنتج(?:ون|ين)?",
    "arabic_rural_communities": r"المجتمعات الريفية",
    "arabic_citizens": r"المواطن(?:ون|ين)?",
}


# These terms normally identify a concrete service, capability, or program
# rather than the safe generic phrase "available services". A matching
# structured field must be traceable to the approved evidence.
SERVICE_DETAIL_PATTERN = re.compile(
    r"\b(?:subsid(?:y|ies)|insurance|registrations?|records?|"
    r"extension services?|market prices?|monitoring|procurement|"
    r"training programs?|permits?|licen[cs]es?|certificates?|grants?|"
    r"appointments?|applications?|payments?|tracking|testing|inspection|"
    r"certification|irrigation|pesticides?|veterinary|fisheries|livestock|"
    r"crop(?:s)?|land records?|soil testing|farm inputs?|technical assistance|"
    r"advisory services?|water management)\b|"
    r"(?:إعانات?|دعم|تأمين|تسجيل|سجلات?|إرشاد زراعي|أسعار السوق|مشتريات|"
    r"برامج تدريب|تدريب|تراخيص?|رخصة|شهادات?|طلبات?|دفع|تتبّع|تتبع|فحص|"
    r"ري|مبيدات?|بيطري|أسماك|مواشي|محاصيل?|أراضي)",
    flags=re.IGNORECASE,
)


ENTITY_ARABIC_TERMS = {
    "ministry": "وزارة",
    "agriculture": "الزراعة",
    "health": "الصحة",
    "education": "التربية",
    "finance": "المالية",
    "interior": "الداخلية",
    "environment": "البيئة",
    "labor": "العمل",
    "tourism": "السياحة",
}


UNKNOWN_SERVICE_VISUAL_PATTERNS = [
    r"\b(?:grid\s+of\s+)?(?:\d+|seven)\s+(?:named\s+)?service\s+cards?\b",
    r"\beach\s+card\b[^.!?]*(?:service\s+name|description|link|url)",
    r"\bindividual\s+service\s+(?:names?|descriptions?|links?|urls?|icons?)\b",
    r"\bservice\s+names?\s+in\s+(?:arabic|english)",
    r"\blink\s+to\s+(?:the|each|a)\s+service\s+page\b",
    r"\bservice\s+urls?\b",
    r"بطاقات\s+(?:ل)?خدمات[^.!?]*(?:أسماء|وصف|روابط)",
    r"رابط\s+(?:لكل|إلى)\s+خدمة",
]


def _quantified_service_subject(
    brief: str,
    approved_strategy: dict[str, Any] | None,
) -> dict[str, str] | None:
    sources = [brief]
    if isinstance(approved_strategy, dict):
        angle = approved_strategy.get("campaign_angle")
        if isinstance(angle, str):
            sources.append(angle)
    source = "\n".join(sources)
    number_words = "|".join(ENGLISH_NUMBER_WORDS)
    match = re.search(
        rf"\b(?P<number>\d+|{number_words})\s+"
        r"(?P<descriptor>[^.!?\n]{1,100}?)\s+services\b",
        source,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    numbers = _extract_numbers(match.group("number"))
    if not numbers:
        return None
    descriptor = re.sub(r"\s+", " ", match.group("descriptor")).strip()
    ministry = re.search(
        r"\bministry\s+of\s+[a-z][a-z\s&-]*",
        descriptor,
        flags=re.IGNORECASE,
    )
    entity = ministry.group(0).strip() if ministry else descriptor
    return {
        "number": sorted(numbers, key=int)[0],
        "entity": entity,
        "label": f"{match.group('number')} {descriptor} services",
    }


def _entity_present(text: str, entity: str) -> bool:
    if entity.casefold() in text.casefold():
        return True
    words = re.findall(r"[a-z]+", entity.casefold())
    translated = [ENTITY_ARABIC_TERMS[word] for word in words if word in ENTITY_ARABIC_TERMS]
    return len(translated) >= 2 and all(term in text for term in translated)


def _approved_service_records(
    approved_knowledge: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(approved_knowledge, dict):
        return []
    catalog = approved_knowledge.get("approved_services", {})
    services = catalog.get("services", []) if isinstance(catalog, dict) else []
    return [service for service in services if isinstance(service, dict)]


def _platform_fact_names(
    approved_knowledge: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(approved_knowledge, dict):
        return []
    organization = approved_knowledge.get("organization", {})
    functions = organization.get("core_functions", []) if isinstance(organization, dict) else []
    names: list[str] = []
    for function in functions:
        if not isinstance(function, dict):
            continue
        for key in ("name_en", "name_ar"):
            value = function.get(key)
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
    return names


def _explicit_platform_context(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in (
        r"\b(?:as\s+)?(?:the\s+)?dawlati\s+platform\b",
        r"\bplatform[- ]wide\b",
        r"\bgeneral\s+(?:dawlati\s+)?platform\s+(?:context|feature|function)",
        r"\bseparate(?:ly)?\s+from\s+the\s+(?:announced\s+)?services\b",
        r"منصة\s+[«\"]?دولتي",
    ))


def _subject_binding_issues(
    path: str,
    text: str,
    subject: dict[str, str] | None,
    platform_names: list[str],
    approved_services: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not subject:
        return []
    issues: list[dict[str, Any]] = []
    count = subject["number"]
    number_forms = [re.escape(count)] + [
        re.escape(word) for word, value in ENGLISH_NUMBER_WORDS.items()
        if value == count
    ]
    number_pattern = "(?:" + "|".join(number_forms) + ")"
    quantified_patterns = (
        rf"\b{number_pattern}\b[^.!?\n]{{0,100}}\bservices\b",
        rf"(?:{re.escape(count)}|٧)\s+خدمات",
    )
    quantified_match = next((
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in quantified_patterns
        if re.search(pattern, text, flags=re.IGNORECASE)
    ), None)
    if quantified_match and not _entity_present(text, subject["entity"]):
        issues.append({
            "type": "subject_preservation_failure",
            "field": path,
            "campaign_subject": subject["label"],
            "required_entity": subject["entity"],
            "generated_substitution": quantified_match.group(0),
            "message": (
                "Subject preservation failure. "
                f"field: {path}; required entity: \"{subject['entity']}\"; "
                f"generated text only says: \"{quantified_match.group(0)}\"."
            ),
        })

    approved_names: set[str] = set()
    for service in approved_services:
        names = service.get("names", {})
        if isinstance(names, dict):
            approved_names.update(
                value.casefold() for value in names.values()
                if isinstance(value, str) and value.strip()
            )

    for platform_name in platform_names:
        match = re.search(re.escape(platform_name), text, flags=re.IGNORECASE)
        if not match or platform_name.casefold() in approved_names:
            continue
        if _explicit_platform_context(text):
            continue
        issues.append({
            "type": "subject_binding_violation",
            "field": path,
            "campaign_subject": subject["label"],
            "generated_substitution": match.group(0),
            "knowledge_scope": "platform_level",
            "message": (
                "Subject binding violation. "
                f"field: {path}; campaign subject: \"{subject['label']}\"; "
                f"generated substitution: \"{match.group(0)}\"."
            ),
        })
    return issues


def _unknown_service_visual_issues(
    path: str,
    text: str,
    subject: dict[str, str] | None,
    approved_services: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if (
        not subject
        or approved_services
        or path not in {"visual_concept", "visual_generation_prompt"}
    ):
        return []
    issues = []
    for pattern in UNKNOWN_SERVICE_VISUAL_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        prefix = text[max(0, match.start() - 40):match.start()]
        if re.search(
            r"(?:without|do\s+not|don't|avoid|must\s+not|not\s+display)\s+[^.!?]{0,30}$",
            prefix,
            flags=re.IGNORECASE,
        ):
            continue
        issues.append({
            "type": "unknown_service_visual_detail",
            "field": path,
            "campaign_subject": subject["label"],
            "matched_phrase": match.group(0),
            "message": (
                "Visual prompt requires unavailable service-level details. "
                f"field: {path}; matched phrase: \"{match.group(0)}\"; "
                "the approved service catalog does not provide individual "
                "service names, descriptions, links, or identities."
            ),
        })
    return issues


def _campaign_text_fields(content: dict[str, Any]) -> list[tuple[str, str]]:
    """Return every user-visible factual field with its stable JSON path."""
    fields: list[tuple[str, str]] = []
    for name in (
        "caption_ar", "caption_en", "visual_concept",
        "visual_generation_prompt", "cta",
    ):
        value = content.get(name, "")
        if isinstance(value, str) and value.strip():
            fields.append((name, value))

    hashtags = content.get("hashtags", [])
    if isinstance(hashtags, list):
        for index, value in enumerate(hashtags):
            if isinstance(value, str) and value.strip():
                fields.append((f"hashtags[{index}]", value))

    structure = content.get("content_structure", [])
    if isinstance(structure, list):
        for index, item in enumerate(structure):
            if not isinstance(item, dict):
                continue
            for name in ("type", "headline", "body"):
                value = item.get(name, "")
                if isinstance(value, str) and value.strip():
                    fields.append((f"content_structure[{index}].{name}", value))
    return fields


def _positive_knowledge_text(approved_knowledge: dict[str, Any] | None) -> str:
    """Exclude templates and guardrails; they describe rules, not evidence."""
    if not isinstance(approved_knowledge, dict):
        return ""
    positive: dict[str, Any] = {}
    organization = approved_knowledge.get("organization")
    if isinstance(organization, dict):
        positive["organization"] = {
            key: value for key, value in organization.items()
            if key not in {
                "communication_guardrails", "service_claim_rules",
                "communication_principles",
            }
        }
    approved_services = approved_knowledge.get("approved_services")
    if isinstance(approved_services, dict):
        services = approved_services.get("services", [])
        if isinstance(services, list):
            positive["services"] = services
    return json.dumps(positive, ensure_ascii=False)


def _approved_audience_scope(
    brief: str,
    approved_strategy: dict[str, Any] | None,
    fallback_evidence: str,
) -> tuple[str, list[str]]:
    """An explicit campaign target audience is a closed, narrowing scope."""
    strategy = approved_strategy if isinstance(approved_strategy, dict) else {}
    values = strategy.get("target_audience", [])
    if isinstance(values, str):
        values = [values]
    approved = [
        value.strip() for value in values
        if isinstance(value, str) and value.strip()
    ]
    if approved:
        return "\n".join([brief, *approved]), approved
    return fallback_evidence, []


def _normal_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _service_segment_supported(segment: str, evidence: str) -> bool:
    normalized_segment = " ".join(_normal_words(segment))
    normalized_evidence = " ".join(_normal_words(evidence))
    if normalized_segment and normalized_segment in normalized_evidence:
        return True

    # Allow a grounded service name inside surrounding creative direction,
    # e.g. "use an icon for Crop Insurance Registration". The matching
    # n-gram itself must contain a service-detail term and occur in evidence.
    words = _normal_words(segment)
    for size in range(min(7, len(words)), 1, -1):
        for start in range(0, len(words) - size + 1):
            phrase = " ".join(words[start:start + size])
            if SERVICE_DETAIL_PATTERN.search(phrase) and phrase in normalized_evidence:
                return True

    stopwords = {
        "a", "an", "and", "the", "to", "for", "on", "in", "of", "our",
        "your", "through", "with", "now", "online", "available", "service",
        "services", "slide", "scene", "show", "create", "highlight", "learn",
        "discover", "explore", "dawlati",
    }
    distinctive = [word for word in _normal_words(segment) if word not in stopwords]
    return len(distinctive) >= 2 and " ".join(distinctive) in normalized_evidence


def validate_structured_factual_claims(
    brief: str,
    content: dict[str, Any],
    approved_strategy: dict[str, Any] | None = None,
    approved_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate factual claims independently in every campaign output field."""
    if not isinstance(brief, str) or not brief.strip():
        raise FactualValidationError("Campaign brief cannot be empty.")
    if not isinstance(content, dict):
        raise FactualValidationError("Campaign content must be a dictionary.")

    evidence = "\n".join(part for part in (
        brief,
        json.dumps(approved_strategy or {}, ensure_ascii=False),
        _positive_knowledge_text(approved_knowledge),
    ) if part)
    audience_evidence, approved_audience = _approved_audience_scope(
        brief=brief,
        approved_strategy=approved_strategy,
        fallback_evidence=evidence,
    )
    subject = _quantified_service_subject(brief, approved_strategy)
    approved_services = _approved_service_records(approved_knowledge)
    platform_names = _platform_fact_names(approved_knowledge)
    service_level_evidence = "\n".join((
        brief,
        json.dumps(approved_strategy or {}, ensure_ascii=False),
        json.dumps(approved_services, ensure_ascii=False),
    ))
    fields = _campaign_text_fields(content)
    field_results: dict[str, dict[str, Any]] = {}
    all_issues: list[dict[str, Any]] = []

    for path, text in fields:
        issues: list[dict[str, Any]] = []

        for capability, rule in CAPABILITY_RULES.items():
            generated_match = next((
                re.search(pattern, text, flags=re.IGNORECASE)
                for pattern in rule["generated_patterns"]
                if re.search(pattern, text, flags=re.IGNORECASE)
            ), None)
            if generated_match is None:
                continue
            claim_evidence = (
                evidence if _explicit_platform_context(text)
                else service_level_evidence
            )
            if not any(_contains_pattern(claim_evidence, pattern) for pattern in rule["evidence_patterns"]):
                if capability in {"continuous_availability", "unrestricted_access"}:
                    message = (
                        "Unsupported continuous/unrestricted access claim. "
                        f"field: {path}; matched phrase: "
                        f'"{generated_match.group(0)}".'
                    )
                else:
                    message = rule["message"]
                issues.append({
                    "type": "unsupported_claim",
                    "capability": capability,
                    "field": path,
                    "matched_phrase": generated_match.group(0),
                    "message": message,
                })

        for behavior, patterns in PLATFORM_BEHAVIOR_RULES.items():
            if any(_contains_pattern(text, pattern) for pattern in patterns) and not any(
                _contains_pattern(evidence, pattern) for pattern in patterns
            ):
                issues.append({
                    "type": "unsupported_platform_behavior",
                    "behavior": behavior,
                    "field": path,
                    "message": (
                        f"{path} contains unsupported platform behavior: "
                        f"{behavior.replace('_', ' ')}."
                    ),
                })

        for audience, pattern in AUDIENCE_PATTERNS.items():
            audience_match = re.search(pattern, text, flags=re.IGNORECASE)
            if audience_match and not _contains_pattern(audience_evidence, pattern):
                approved_label = (
                    ", ".join(approved_audience)
                    if approved_audience
                    else "brief and directly relevant approved knowledge"
                )
                issues.append({
                    "type": "unsupported_audience",
                    "audience": audience,
                    "field": path,
                    "generated_audience": audience_match.group(0),
                    "approved_audience": approved_audience,
                    "message": (
                        "Unsupported audience expansion. "
                        f"field: {path}; generated audience: "
                        f'"{audience_match.group(0)}"; approved audience: '
                        f"{approved_label}."
                    ),
                })

        issues.extend(_subject_binding_issues(
            path=path,
            text=text,
            subject=subject,
            platform_names=platform_names,
            approved_services=approved_services,
        ))
        issues.extend(_unknown_service_visual_issues(
            path=path,
            text=text,
            subject=subject,
            approved_services=approved_services,
        ))

        segments = re.split(r"[\r\n;|•]+|(?<=[.!?])\s+|\s*,\s*", text)
        for segment in segments:
            if SERVICE_DETAIL_PATTERN.search(segment) and not _service_segment_supported(segment, evidence):
                issues.append({
                    "type": "unsupported_service_detail",
                    "field": path,
                    "value": segment.strip(),
                    "message": (
                        f"{path} contains a specific service title or service detail "
                        "that is not grounded in approved evidence."
                    ),
                })

        if re.search(r"\[(?:link|url|website)\]", text, flags=re.IGNORECASE):
            issues.append({
                "type": "placeholder_link",
                "field": path,
                "message": f"{path} contains a placeholder link.",
            })

        field_results[path] = {
            "valid": not issues,
            "status": "PASS" if not issues else "BLOCK",
            "issues": issues,
        }
        all_issues.extend(issues)

    combined_text = "\n".join(text for _, text in fields)
    brief_numbers = _extract_numbers(brief)
    generated_numbers = _extract_numbers(combined_text)
    missing_numbers = brief_numbers - generated_numbers
    if missing_numbers:
        all_issues.append({
            "type": "missing_explicit_number",
            "numbers": sorted(missing_numbers, key=int),
            "field": "campaign",
            "message": "One or more explicit numbers from the campaign brief were not preserved.",
        })

    return {
        "valid": not all_issues,
        "status": "PASS" if not all_issues else "BLOCK",
        "issues": all_issues,
        "field_results": field_results,
        "brief_numbers": sorted(brief_numbers, key=int),
        "generated_numbers": sorted(generated_numbers, key=int),
    }


def enforce_structured_factual_claims(
    brief: str,
    content: dict[str, Any],
    approved_strategy: dict[str, Any] | None = None,
    approved_knowledge: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = validate_structured_factual_claims(
        brief=brief,
        content=content,
        approved_strategy=approved_strategy,
        approved_knowledge=approved_knowledge,
    )
    if not result["valid"]:
        messages = list(dict.fromkeys(issue["message"] for issue in result["issues"]))
        raise FactualValidationError(
            "Factual validation failed: " + "; ".join(messages),
            details={
                "validation_stage": "factual_validation",
                "issues": result["issues"],
            },
        )
    return result


# --------------------------------------------------
# Main Validation
# --------------------------------------------------

def validate_factual_claims(
    brief: str,
    generated_text: str
) -> dict[str, Any]:

    if not isinstance(
        brief,
        str
    ):

        raise FactualValidationError(
            "Campaign brief must be a string."
        )


    if not isinstance(
        generated_text,
        str
    ):

        raise FactualValidationError(
            "Generated content must be a string."
        )


    if not brief.strip():

        raise FactualValidationError(
            "Campaign brief cannot be empty."
        )


    issues = []


    # --------------------------------------------------
    # Unsupported Claims
    # --------------------------------------------------

    for capability, rule in (
        CAPABILITY_RULES.items()
    ):

        generated_claim = any(
            _contains_pattern(
                generated_text,
                pattern
            )

            for pattern
            in rule[
                "generated_patterns"
            ]
        )


        if not generated_claim:
            continue


        brief_supports_claim = any(
            _contains_pattern(
                brief,
                pattern
            )

            for pattern
            in rule[
                "evidence_patterns"
            ]
        )


        if not brief_supports_claim:

            issues.append(
                {
                    "type": "unsupported_claim",
                    "capability": capability,
                    "message": rule[
                        "message"
                    ]
                }
            )


    # --------------------------------------------------
    # Placeholder Links
    # --------------------------------------------------

    placeholder_patterns = [
        r"\[link\]",
        r"\[url\]",
        r"\[website\]",
        r"\[الرابط\]",
    ]


    for pattern in placeholder_patterns:

        if _contains_pattern(
            generated_text,
            pattern
        ):

            issues.append(
                {
                    "type": "placeholder_link",
                    "message": (
                        "Generated content contains "
                        "a placeholder link."
                    )
                }
            )

            break


    # --------------------------------------------------
    # Explicit Number Preservation
    # --------------------------------------------------

    brief_numbers = _extract_numbers(
        brief
    )

    generated_numbers = _extract_numbers(
        generated_text
    )


    missing_numbers = (
        brief_numbers
        - generated_numbers
    )


    if missing_numbers:

        issues.append(
            {
                "type": "missing_explicit_number",

                "numbers": sorted(
                    missing_numbers,
                    key=int
                ),

                "message": (
                    "One or more explicit numbers from "
                    "the campaign brief were not preserved."
                )
            }
        )


    # --------------------------------------------------
    # Result
    # --------------------------------------------------

    return {
        "valid": (
            len(
                issues
            ) == 0
        ),

        "status": (
            "PASS"
            if len(issues) == 0
            else "BLOCK"
        ),

        "issues": issues,

        "brief_numbers": sorted(
            brief_numbers,
            key=int
        ),

        "generated_numbers": sorted(
            generated_numbers,
            key=int
        )
    }


# --------------------------------------------------
# Enforcement
# --------------------------------------------------

def enforce_factual_claims(
    brief: str,
    generated_text: str
) -> dict[str, Any]:

    result = validate_factual_claims(
        brief=brief,
        generated_text=generated_text
    )


    if not result[
        "valid"
    ]:

        messages = [
            issue[
                "message"
            ]

            for issue
            in result[
                "issues"
            ]
        ]


        raise FactualValidationError(
            "Factual validation failed: "
            + "; ".join(
                messages
            )
        )


    return result


# --------------------------------------------------
# Manual Tests
# --------------------------------------------------

if __name__ == "__main__":

    brief = (
        "Seven Ministry of Agriculture services "
        "are now available online through Dawlati."
    )


    samples = [

        (
            "SAFE",
            (
                "7 Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        ),

        (
            "UNSUPPORTED APPLICATION",
            (
                "7 services are available online. "
                "Start your application through Dawlati."
            )
        ),

        (
            "UNSUPPORTED ARABIC APPLICATION",
            (
                "أصبحت 7 خدمات متاحة إلكترونياً عبر دولتي. "
                "ابدأ بطلبك عبر دولتي."
            )
        ),

        (
            "UNSUPPORTED 24/7",
            (
                "7 services are available "
                "through Dawlati 24/7."
            )
        ),

        (
            "UNSUPPORTED EFFICIENCY",
            (
                "أصبحت 7 خدمات متاحة عبر دولتي "
                "لتحقيق كفاءة في الإجراءات الحكومية."
            )
        ),

        (
            "UNSUPPORTED EASE",
            (
                "أصبحت 7 خدمات متاحة إلكترونياً عبر منصة دولتي "
                "للاستفادة من الخدمات الحكومية بسهولة."
            )
        ),

        (
            "MISSING NUMBER",
            (
                "Ministry of Agriculture services "
                "are now available online through Dawlati."
            )
        ),
    ]


    for label, text in samples:

        result = validate_factual_claims(
            brief=brief,
            generated_text=text
        )


        print(
            "\nTEST:",
            label
        )

        print(
            "STATUS:",
            result[
                "status"
            ]
        )

        print(
            "BRIEF NUMBERS:",
            result[
                "brief_numbers"
            ]
        )

        print(
            "GENERATED NUMBERS:",
            result[
                "generated_numbers"
            ]
        )


        for issue in result[
            "issues"
        ]:

            print(
                "ISSUE:",
                issue[
                    "message"
                ]
            )
            
