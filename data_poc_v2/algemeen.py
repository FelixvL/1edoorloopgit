"""Core business logic for the refactored StudyTube proof of concept."""

from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import requests
from flask import Response, abort, jsonify, request

from . import categorie_selector

logger = logging.getLogger(__name__)


EDUFRAME_BASE = "https://api.eduframe.nl/api/v1"
EDUFRAME_TOKEN = "qq"  # test token supplied in the original proof of concept
PER_PAGE = 100

DATA_DIR = Path("data_poc_v2")
PLANNED_DIR = DATA_DIR / "planned_courses_poc_v2"
COURSES_FILE = DATA_DIR / "courses_poc_v2.json"
COURSE_VARIANTS_FILE = DATA_DIR / "course_variants.json"
LEGACY_COURSES_FILES: Sequence[Path] = (Path("courses_poc_v1.json"),)
LEGACY_PLANNED_DIRS: Sequence[Path] = (Path("planned_courses_poc_v1"),)
LEGACY_VARIANT_FILES: Sequence[Path] = (
    Path("course_variants.json"),
    Path("data_poc_v1/course_variants.json"),
)

PROGRESS_PATH = Path("voortgang_eduframe_update.txt")
BASE_JSON_DIR = Path(".").resolve()

DATA_DIR.mkdir(exist_ok=True)
PLANNED_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class EduframeClient:
    """Light-weight client for talking to the Eduframe API."""

    token: str
    base_url: str = EDUFRAME_BASE
    timeout: float = 30.0

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def get(self, endpoint: str, params: Optional[dict] = None) -> requests.Response:
        """Perform a GET request and return the raw :class:`Response`."""
        url = self._build_url(endpoint)
        logger.debug("Requesting %s with %s", url, params)
        response = requests.get(url, headers=self._headers, params=params, timeout=self.timeout)
        return response


@dataclass
class CacheManager:
    """Helper that encapsulates JSON persistence for the POC."""

    data_dir: Path = DATA_DIR
    planned_dir: Path = PLANNED_DIR
    courses_file: Path = COURSES_FILE
    course_variants_file: Path = COURSE_VARIANTS_FILE
    legacy_courses_files: Sequence[Path] = field(default_factory=lambda: LEGACY_COURSES_FILES)
    legacy_planned_dirs: Sequence[Path] = field(default_factory=lambda: LEGACY_PLANNED_DIRS)
    legacy_variant_files: Sequence[Path] = field(default_factory=lambda: LEGACY_VARIANT_FILES)
    _variant_lookup_cache: Optional[Dict[int, str]] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.planned_dir.mkdir(parents=True, exist_ok=True)

    def load_json(self, path: Path) -> Any:
        """Read and parse a JSON file, raising informative errors on failure."""
        text = path.read_text(encoding="utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Bestand {path} bevat geen geldig JSON: {exc}") from exc

    def save_json(self, path: Path, data: Any) -> None:
        """Write JSON data with UTF-8 encoding and pretty formatting."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_courses(self) -> List[dict]:
        """Return cached course data, preferring the v2 location."""
        for path in (self.courses_file, *self.legacy_courses_files):
            if path.exists():
                data = self.load_json(path)
                if isinstance(data, dict):
                    data = [data]
                return list(data) if isinstance(data, list) else []
        return []

    def save_courses(self, courses: List[dict]) -> None:
        """Persist courses to the v2 cache file."""
        self.save_json(self.courses_file, courses)

    def load_planned_courses(self, course_id: int) -> List[dict]:
        """Return cached planned course data for a course, searching legacy folders if needed."""
        targets = [self.planned_dir / f"pc_{course_id}.json"]
        targets.extend(directory / f"pc_{course_id}.json" for directory in self.legacy_planned_dirs)
        for path in targets:
            if path.exists():
                data = self.load_json(path)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
        return []

    def save_planned_courses(self, course_id: int, items: List[dict]) -> Path:
        """Persist planned course data for a given course and return the file path."""
        path = self.planned_dir / f"pc_{course_id}.json"
        self.save_json(path, items)
        return path

    def _resolve_variant_path(self) -> Optional[Path]:
        for path in (self.course_variants_file, *self.legacy_variant_files):
            if path.exists():
                return path
        return None

    def get_variant_lookup(self) -> Dict[int, str]:
        """Lazy-load and cache the mapping of course variant IDs to names."""
        if self._variant_lookup_cache is not None:
            return self._variant_lookup_cache

        path = self._resolve_variant_path()
        if path is None:
            logger.warning("Geen course_variants.json gevonden.")
            self._variant_lookup_cache = {}
            return self._variant_lookup_cache

        data = self.load_json(path)
        if isinstance(data, dict):
            data = [data]

        mapping: Dict[int, str] = {}
        for item in data:
            try:
                mapping[int(item["id"])] = str(item["name"])
            except (KeyError, TypeError, ValueError):  # pragma: no cover - defensief
                continue
        self._variant_lookup_cache = mapping
        return mapping


default_client = EduframeClient(token=EDUFRAME_TOKEN)
default_cache_manager = CacheManager()


def is_studytube_course(course: dict) -> bool:
    """Return ``True`` when the Eduframe course targets the StudyTube channel."""
    custom = (course or {}).get("custom") or {}
    kanaal = custom.get("kanaal")
    if kanaal is None:
        return False
    if isinstance(kanaal, str):
        values = [kanaal]
    elif isinstance(kanaal, list):
        values = kanaal
    else:
        return False
    return any((str(v).strip().lower() == "studytube") for v in values if v is not None)


def _extract_items(data: Any) -> List[dict]:
    """Normalise API responses that sometimes wrap data in ``data`` or ``items`` keys."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(
            data.get("data")
            or data.get("planned_courses")
            or data.get("items")
            or data.get("_embedded", {}).get("courses", [])
        )
    return []


def fetch_studytube_courses(
    *, client: Optional[EduframeClient] = None, per_page: int = PER_PAGE
) -> List[dict]:
    """Retrieve all StudyTube courses from Eduframe."""
    client = client or default_client
    all_courses: List[dict] = []
    page = 1

    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "include": "course_tab_contents.course_tab",
        }
        response = client.get("courses", params=params)
        if response.status_code != 200:
            logger.error("Fout bij ophalen pagina %s: %s", page, response.status_code)
            break
        data = response.json()
        items = _extract_items(data)
        if not items:
            break
        filtered = [c for c in items if is_studytube_course(c)]
        all_courses.extend(filtered)
        page += 1

    logger.info("%s StudyTube-cursussen opgehaald", len(all_courses))
    return all_courses


def fetch_and_save_planned_courses(
    course_id: int,
    *,
    client: Optional[EduframeClient] = None,
    cache_manager: Optional[CacheManager] = None,
    per_page: int = 100,
    max_pages: int = 10_000,
    sleep_seconds: float = 0.1,
) -> List[dict]:
    """Fetch planned courses for an Eduframe course and cache the JSON result."""
    client = client or default_client
    cache_manager = cache_manager or default_cache_manager

    endpoint = f"courses/{course_id}/planned_courses"
    all_items: List[dict] = []
    page = 1

    while page <= max_pages:
        params = {"per_page": per_page, "page": page}
        try:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Fout bij ophalen planned courses voor %s (pagina %s): %s", course_id, page, exc)
            time.sleep(1)
            try:
                response = client.get(endpoint, params=params)
                response.raise_for_status()
            except requests.RequestException as exc2:
                logger.error(
                    "Nogmaals fout bij planned courses voor %s (pagina %s): %s",
                    course_id,
                    page,
                    exc2,
                )
                break

        items = _extract_items(response.json())
        if not items:
            break

        all_items.extend(items)
        if len(items) < per_page:
            break

        page += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)

    path = cache_manager.save_planned_courses(course_id, all_items)
    logger.info("%s geplande sessies opgeslagen naar %s", len(all_items), path)
    return all_items


def studytube_courses_van_eduframe_naar_bestand(
    *, client: Optional[EduframeClient] = None, cache_manager: Optional[CacheManager] = None
):
    """Flask handler that synchronises StudyTube courses to the cache file."""
    client = client or default_client
    cache_manager = cache_manager or default_cache_manager
    courses = fetch_studytube_courses(client=client)
    cache_manager.save_courses(courses)
    return jsonify(courses)


def text_or_empty(value: Any) -> str:
    return "" if value is None else str(value)


def first_or_empty(value: Any) -> str:
    if isinstance(value, list) and value:
        return text_or_empty(value[0])
    return text_or_empty(value)


def iso_date_or_empty(value: Any) -> str:
    if not value:
        return ""
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
        return str(value)
    except Exception:  # pragma: no cover - defensive
        match = re.search(r"\d{4}-\d{2}-\d{2}", str(value))
        return match.group(0) if match else ""


def extract_duration_value(raw: str) -> str:
    """Return the numeric duration component (``"2"`` for ``"2 dagen"``)."""
    if not raw:
        return ""
    match = re.search(r"\d+", str(raw))
    return match.group(0) if match else ""


def extract_duration_unit(raw: str) -> str:
    """Convert Dutch duration units to the StudyTube variant."""
    if not raw:
        return ""
    text = str(raw).strip().lower()
    if re.search(r"\b(uur|u|hr|hrs|hour|hours)\b", text):
        return "hours"
    if re.search(r"\b(dag|dagen|day|days)\b", text):
        return "days"
    return ""


def to_lang_code(nl_word: str) -> str:
    value = (nl_word or "").strip().lower()
    if value.startswith("eng"):
        return "en"
    if value.startswith("duits"):
        return "de"
    if value.startswith("frans"):
        return "fr"
    return "nl"


def _cdata(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{text}]]>"


def training_type_from_course(course: dict) -> str:
    custom = (course or {}).get("custom") or {}
    return "elearning" if custom.get("elearning_id") else "classroom_training"


def agenda_from_course(course: dict) -> str:
    for tab in (course.get("course_tab_contents") or []):
        tab_name = (tab.get("course_tab") or {}).get("name", "")
        if str(tab_name).strip().lower() == "onderwerpen":
            return tab.get("content") or ""
    return ""


def live_session_closed(planned_course: dict) -> bool:
    status = (planned_course.get("status") or "").lower()
    if status in {"canceled", "completed"}:
        return True
    if planned_course.get("is_published") is False:
        return True
    return False


def description_from_course(course: dict) -> str:
    meta = (course.get("meta_description") or "").strip()
    if meta:
        return meta

    tabs = course.get("course_tab_contents") or []
    preferred = None
    for tab in tabs:
        tab_meta = (tab.get("course_tab") or {})
        name = (tab_meta.get("name") or "").strip().lower()
        if name == "algemene omschrijving" or tab_meta.get("position") == 1:
            preferred = tab
            break
    if not preferred and tabs:
        preferred = tabs[0]
    return (preferred or {}).get("content") or ""


def map_variant_name_to_training_type(name: str) -> str:
    text = (name or "").strip().lower()
    if re.search(r"\bexam|examen\b", text):
        return "exam"
    if "webinar" in text:
        return "webinar"
    if "coaching" in text:
        return "coaching"
    if "workshop" in text:
        return "workshop"
    if "virtual classroom" in text or "virtueel" in text or "online klassikaal" in text:
        return "virtual_classroom"
    if "klassikaal" in text or "classroom" in text:
        return "classroom_training"
    if "e-learning" in text or "elearning" in text or "e learning" in text or "zelfstudie" in text or "home study" in text:
        return "elearning"
    if "begeleid" in text or "blended" in text:
        return "blended_learning"
    if "maatwerk" in text or "incompany" in text:
        return "other"
    return "other"


def determine_training_type_for_course(
    planned: Iterable[dict],
    variant_lookup: Dict[int, str],
) -> str:
    mapped: List[str] = []
    for pc in planned:
        variant_id = pc.get("course_variant_id")
        if variant_id is None:
            continue
        name = variant_lookup.get(int(variant_id))
        mapped.append(map_variant_name_to_training_type(name) if name else "other")

    if not mapped:
        return "other"

    online: Set[str] = {"elearning", "home_study"}
    live: Set[str] = {"classroom_training", "virtual_classroom", "webinar", "workshop", "coaching"}
    mapped_set = set(mapped)
    if (mapped_set & online) and (mapped_set & live):
        return "blended_learning"

    if mapped_set == {"other"}:
        return "other"

    priority = [
        "exam",
        "webinar",
        "virtual_classroom",
        "classroom_training",
        "workshop",
        "coaching",
        "elearning",
        "home_study",
        "blended_learning",
        "other",
    ]

    counts = {key: mapped.count(key) for key in set(mapped)}
    best = sorted(
        counts.items(),
        key=lambda kv: (
            -kv[1],
            priority.index(kv[0]) if kv[0] in priority else 9999,
        ),
    )[0][0]
    return best


def xml_product_for_course(
    course: dict,
    *,
    cache_manager: Optional[CacheManager] = None,
    variant_lookup: Optional[Dict[int, str]] = None,
) -> str:
    cache_manager = cache_manager or default_cache_manager
    variant_lookup = variant_lookup or cache_manager.get_variant_lookup()

    course_id = course.get("id")
    code = "_" + str(course.get("code") or f"CRS-{course_id}")
    code = re.sub(r"[^A-Za-z0-9_.-]", "_", code)
    name = course.get("name") or ""
    description = description_from_course(course) or "10"
    price = course.get("starting_price") or course.get("cost") or ""
    language = to_lang_code(first_or_empty((course.get("custom") or {}).get("taal")))
    raw_duration = course.get("duration") or (course.get("custom") or {}).get("duration")
    duration_value = extract_duration_value(raw_duration)
    duration_unit = extract_duration_unit(raw_duration)

    subcats = (course.get("custom") or {}).get("studytube-categorieen") or []
    subcat = ", ".join(subcats)
    category = categorie_selector.choose_category_from_subcats(subcats)

    agenda_html = agenda_from_course(course)
    planned = cache_manager.load_planned_courses(int(course_id)) if course_id is not None else []
    has_planned = len(planned) > 0

    variant_mapping = variant_lookup or {}
    today = date.today()
    per_variant: Dict[Optional[int], Dict[str, int]] = defaultdict(lambda: {"toekomst": 0, "verleden": 0, "vandaag": 0})
    for planned_course in planned:
        start_date = planned_course.get("start_date")
        if not start_date:
            continue
        planned_date = date.fromisoformat(start_date)
        variant_id = planned_course.get("course_variant_id")
        if planned_date > today:
            per_variant[variant_id]["toekomst"] += 1
        elif planned_date < today:
            per_variant[variant_id]["verleden"] += 1
        else:
            per_variant[variant_id]["vandaag"] += 1

    if per_variant:
        logger.debug(
            "Course %s (%s) varianten: %s",
            course.get("id"),
            course.get("name"),
            {
                variant_mapping.get(k, f"id {k}"): v
                for k, v in per_variant.items()
            },
        )

    schedule_type = "scheduled" if has_planned else "nodate"

    parts: List[str] = []
    ap = parts.append

    ap("<Product>")
    ap(f"<ID>{_cdata(code)}</ID>")
    ap("<Name>")
    ap(_cdata(name))
    ap("</Name>")
    ap("<Description>")
    ap(_cdata(description))
    ap("</Description>")
    ap("<Agenda>")
    ap(_cdata(agenda_html))
    ap("</Agenda>")
    ap(f"<Language>{language}</Language>")
    ap(f"<TrainingPriceExVAT>{text_or_empty(price)}</TrainingPriceExVAT>")
    ap("<VATPercentage>21</VATPercentage>")
    ap("<Certificate>Certificaat opleider</Certificate>")
    ap(f"<Category>{_cdata(category)}</Category>")
    ap(f"<SubCategory>{_cdata(subcat)}</SubCategory>")
    ap(f"<Duration>{text_or_empty(duration_value)}</Duration>")
    ap(f"<DurationUnit>{duration_unit}</DurationUnit>")
    web = course.get("website_url") or "https://startel.nl/alle-trainingen/"
    session_url = "https://startel.nl/"
    ap(f"<WebAddress>{_cdata(web)}</WebAddress>")
    ap(f"<ScheduleType>{schedule_type}</ScheduleType>")
    training_type = determine_training_type_for_course(planned, variant_mapping)
    ap(f"<TrainingType>{training_type}</TrainingType>")

    if has_planned:
        ap("<LiveSessions>")
        for pc in planned:
            ap("<LiveSession>")
            session_identifier = _cdata(f"pc-{pc.get('id')}")
            ap(f"<ID>{session_identifier}</ID>")
            ap(f"<Url>{_cdata(session_url)}</Url>")
            if pc.get("min_participants") is not None:
                ap(f"<MinimumParticipants>{pc.get('min_participants')}</MinimumParticipants>")
            if pc.get("max_participants") is not None:
                ap(f"<MaximumParticipants>{pc.get('max_participants')}</MaximumParticipants>")
            ap(f"<LiveSessionClosed>{str(live_session_closed(pc)).lower()}</LiveSessionClosed>")
            ap("<LiveSessionDates>")
            ap("<LiveSessionDate>")
            ap(f"<StartDate>{iso_date_or_empty(pc.get('start_date'))}</StartDate>")
            ap("<StartTime>09:00</StartTime>")
            ap("<EndTime>17:00</EndTime>")
            ap("</LiveSessionDate>")
            ap("</LiveSessionDates>")
            ap("</LiveSession>")
        ap("</LiveSessions>")
    else:
        ap("<LiveSessions> </LiveSessions>")

    ap("</Product>")
    return "\n".join(parts)


def build_products_xml(
    courses: Optional[Iterable[dict]] = None,
    *,
    cache_manager: Optional[CacheManager] = None,
) -> str:
    cache_manager = cache_manager or default_cache_manager
    if courses is None:
        courses = cache_manager.load_courses()
    if isinstance(courses, dict):
        courses = [courses]
    courses_list = list(courses)
    courses_filtered = [c for c in courses_list if is_studytube_course(c)]

    variant_lookup = cache_manager.get_variant_lookup()
    xml_parts = ["<Products>"]
    for course in courses_filtered:
        xml_parts.append(
            xml_product_for_course(course, cache_manager=cache_manager, variant_lookup=variant_lookup)
        )
    xml_parts.append("</Products>")
    return "\n".join(xml_parts)


def studytube_products(*, cache_manager: Optional[CacheManager] = None) -> Response:
    cache_manager = cache_manager or default_cache_manager
    if not cache_manager.courses_file.exists() and not any(path.exists() for path in cache_manager.legacy_courses_files):
        abort(404, description=f"courses.json niet gevonden op {cache_manager.courses_file}")

    xml_str = build_products_xml(cache_manager=cache_manager)
    if "<Product>" not in xml_str:
        return Response("<Products></Products>", status=200, mimetype="application/xml")

    response = Response(xml_str, mimetype="application/xml")
    response.headers["Cache-Control"] = "no-store"
    return response


def load_course_ids(courses: Iterable[dict]) -> List[int]:
    seen: Set[int] = set()
    ids: List[int] = []
    for obj in courses:
        course_id = obj.get("id")
        if course_id is None:
            continue
        try:
            course_id = int(course_id)
        except Exception:
            continue
        if course_id not in seen:
            seen.add(course_id)
            ids.append(course_id)
    return ids


def read_progress(progress_path: Path = PROGRESS_PATH) -> int:
    if not progress_path.exists():
        return 0
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
        if "next_index" in data:
            return int(data["next_index"])
        if "last_index" in data:
            return int(data["last_index"])
        return int(data.get("last_index_processed", 0)) + 1
    except Exception:
        return 0


def write_progress(
    progress_path: Path,
    *,
    next_index: int,
    next_course_id: int,
    last_index_processed: int,
    last_course_id: int,
    total: int,
) -> None:
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "total_courses": total,
        "next_index": next_index,
        "next_course_id": next_course_id,
        "last_index_processed": last_index_processed,
        "last_course_id": last_course_id,
        "note": "Volgende run start bij next_index/course_id.",
    }
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_batch_update(
    fetch_callable,
    *,
    client: Optional[EduframeClient] = None,
    cache_manager: Optional[CacheManager] = None,
    courses_path: Optional[Path] = None,
    progress_path: Path = PROGRESS_PATH,
    max_calls: int = 100,
    sleep_per_call: float = 0.0,
    fetch_kwargs: Optional[dict] = None,
) -> str:
    client = client or default_client
    cache_manager = cache_manager or default_cache_manager

    if courses_path:
        cache_manager = CacheManager(
            data_dir=cache_manager.data_dir,
            planned_dir=cache_manager.planned_dir,
            courses_file=courses_path,
            course_variants_file=cache_manager.course_variants_file,
            legacy_courses_files=cache_manager.legacy_courses_files,
            legacy_planned_dirs=cache_manager.legacy_planned_dirs,
            legacy_variant_files=cache_manager.legacy_variant_files,
        )

    courses = cache_manager.load_courses()
    course_ids = load_course_ids(courses)
    total_courses = len(course_ids)
    if total_courses == 0:
        logger.warning("Geen courses in cache gevonden.")
        return "0"

    start_index = read_progress(progress_path)
    if start_index < 0 or start_index >= total_courses:
        start_index = 0

    calls = 0
    idx = start_index
    last_idx_processed = (start_index - 1) % total_courses
    last_course_id = course_ids[last_idx_processed]

    while calls < max_calls:
        course_id = course_ids[idx]
        kwargs = dict(fetch_kwargs or {})
        kwargs.setdefault("client", client)
        kwargs.setdefault("cache_manager", cache_manager)
        try:
            fetch_callable(course_id, **kwargs)
        except Exception as exc:  # pragma: no cover - defensief
            logger.exception("Fout bij course %s: %s", course_id, exc)
        else:
            logger.info("[%s/%s] OK course %s", calls + 1, max_calls, course_id)
        calls += 1
        last_idx_processed = idx
        last_course_id = course_id
        idx = (idx + 1) % total_courses
        if sleep_per_call:
            time.sleep(sleep_per_call)

    next_index = idx
    next_course_id = course_ids[next_index]
    write_progress(
        progress_path,
        next_index=next_index,
        next_course_id=next_course_id,
        last_index_processed=last_idx_processed,
        last_course_id=last_course_id,
        total=total_courses,
    )
    return (
        "Batch klaar: {calls} calls gedaan. Volgende start: index={next_index} (course_id={next_course_id})."
        "<h1>roep deze pas over 5 minuten aan, dus na: {timestamp}</h1>"
    ).format(
        calls=calls,
        next_index=next_index,
        next_course_id=next_course_id,
        timestamp=str(datetime.now() + timedelta(minutes=5)),
    )


def load_json_safe(relpath: str, base_dir: Path = BASE_JSON_DIR) -> Any:
    if not relpath.endswith(".json"):
        raise ValueError("Alleen .json bestanden zijn toegestaan.")
    requested_path = (base_dir / relpath).resolve()
    try:
        requested_path.relative_to(base_dir)
    except ValueError as exc:  # pragma: no cover - defensief
        raise FileNotFoundError(f"Niet toegestaan: {relpath}") from exc
    if not requested_path.is_file():
        raise FileNotFoundError(f"Bestand bestaat niet: {relpath}")
    return json.loads(requested_path.read_text(encoding="utf-8"))


def get_json_file(relpath: str) -> Response:
    pretty = request.args.get("pretty", "").lower() in {"1", "true", "yes"}
    try:
        data = load_json_safe(relpath)
    except FileNotFoundError as exc:
        abort(404, description=str(exc))
    except ValueError as exc:
        abort(400, description=str(exc))
    except json.JSONDecodeError:
        abort(500, description="Ongeldig JSON-bestand.")

    body = (
        json.dumps(data, ensure_ascii=False, indent=2)
        if pretty
        else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )
    return Response(body, mimetype="application/json")
