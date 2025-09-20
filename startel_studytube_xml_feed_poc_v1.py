
from flask import jsonify, Response, abort, request
from pathlib import Path
import json
import requests
import time
import os, re, json
from datetime import datetime, timedelta, date
from collections import Counter, defaultdict

from typing import Dict, Iterable, List, Optional, Set

import categorie_selector_studytube_poc_v1 as cv1 


PROGRESS_PATH = Path("voortgang_eduframe_update.txt")

BASE_JSON_DIR = Path("./").resolve()
EDUFRAME_BASE = "https://api.eduframe.nl/api/v1"
EDUFRAME_TOKEN = "qq"  # <-- jouw token
PER_PAGE = 100
COURSES_FILE = Path("./courses_poc_v1.json")
PLANNED_DIR = Path("./planned_courses_poc_v1")
PLANNED_DIR.mkdir(exist_ok=True)

headers = {
    "Authorization": f"Bearer {EDUFRAME_TOKEN}",
    "Accept": "application/json"
}

def load_variant_lookup(course_variants_path: str) -> Dict[int, str]:
    """
    Leest course_variants.json (array met {id, name, ...}) en geeft {id: name} terug.
    """
    data = json.loads(Path(course_variants_path).read_text(encoding="utf-8"))
    return {int(item["id"]): str(item["name"]) for item in data if "id" in item and "name" in item}

variant_lookup = load_variant_lookup("./data_poc_v1/course_variants.json")

def is_studytube_course(course: dict) -> bool:
    custom = (course or {}).get("custom") or {}
    kanaal = custom.get("kanaal")
    # kanaal kan None, een string of een lijst zijn
    if kanaal is None:
        return False
    if isinstance(kanaal, str):
        values = [kanaal]
    elif isinstance(kanaal, list):
        values = kanaal
    else:
        return False
    return any((str(v).strip().lower() == "studytube") for v in values if v is not None)

def fetch_studytube_courses():
    all_courses = []
    page = 1

    while True:
        print(f"Fetching page {page}...")
        url = f"{EDUFRAME_BASE}/courses"
        params = {"per_page": PER_PAGE, "page": page, "include": "course_tab_contents.course_tab"}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"Fout bij ophalen pagina {page}: {response.status_code}")
            break

        data = response.json()

        # Normaliseer de items-collectie
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("data")
                or data.get("courses")
                or data.get("items")
                or data.get("_embedded", {}).get("courses")
                or []
            )
        else:
            print("Onverwacht formaat:", type(data))
            break

        if not items:
            print("Geen items meer.")
            break

        # Alleen courses met kanaal 'studytube' toevoegen
        filtered = [c for c in items if is_studytube_course(c)]
        all_courses.extend(filtered)

        page += 1

    return all_courses

def _extract_items(data):
    # Eduframe geeft soms een lijst terug, soms een dict met 'data' of 'items'
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return (
            data.get("data")
            or data.get("planned_courses")
            or data.get("items")
            or []
        )
    return []

def fetch_and_save_planned_courses(course_id, per_page=100, max_pages=10_000, sleep_seconds=0.1):
    url = f"https://api.eduframe.nl/api/v1/courses/{course_id}/planned_courses"
    headers = {
        "Authorization": f"Bearer {EDUFRAME_TOKEN}",
        "Accept": "application/json"
    }

    all_items = []
    page = 1

    while page <= max_pages:
        params = {"per_page": per_page, "page": page}
        try:
            print("planned_courses X request")
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Fout bij page {page} voor course {course_id}: {e}")
            # simpele retry op 500/timeout
            time.sleep(1)
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=30)
                resp.raise_for_status()
            except requests.RequestException as e2:
                print(f"Nogmaals fout bij page {page}: {e2}")
                break

        data = resp.json()
        items = _extract_items(data)

        if not items:
            # geen resultaten -> klaar
            break

        all_items.extend(items)

        # als minder dan per_page binnenkomt, is dit de laatste pagina
        if len(items) < per_page:
            break

        page += 1
        if sleep_seconds:
            time.sleep(sleep_seconds)

    # Wegschrijven als lijst (consistente structuur)
    file_path = PLANNED_DIR / f"pc_{course_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)

    print(f"{len(all_items)} geplande sessies opgeslagen naar {file_path}")
    return all_items


def studytube_courses_van_eduframe_naar_bestand():
    courses = fetch_studytube_courses()
    print(f"\nTotaal aantal courses opgehaald: {len(courses)}")

    with open(COURSES_FILE, "w", encoding="utf-8") as f:
        json.dump(courses, f, indent=2, ensure_ascii=False)

    return jsonify(courses)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def text_or_empty(x):
    if x is None:
        return ""
    if isinstance(x, (int, float)):
        return str(x)
    return str(x)

def first_or_empty(x):
    if isinstance(x, list) and x:
        return text_or_empty(x[0])
    return text_or_empty(x)

def iso_date_or_empty(s):
    if not s:
        return ""
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        m = re.search(r"\d{4}-\d{2}-\d{2}", str(s))
        return m.group(0) if m else ""

# def extract_duration_days(s):
#     if not s:
#         return ""
#     m = re.search(r"\d+", str(s))
#     return m.group(0) if m else ""

import re

def extract_duration_value(s: str) -> str:
    """Geef het numerieke deel terug als string (bijv. '1 dag' -> '1')."""
    if not s:
        return ""
    m = re.search(r"\d+", str(s))
    return m.group(0) if m else ""

def extract_duration_unit(s: str) -> str:
    """
    Bepaal de unit in het Engels met juiste enkelvoud/meervoud:
      - 'uur', 'u', 'hr', 'hrs', 'hour(s)' -> 'hour' of 'hours'
      - 'dag', 'dagen', 'day(s)'          -> 'day'  of 'days'
    """
    if not s:
        return ""

    txt = str(s).strip().lower()

    if re.search(r"\b(uur|u|hr|hrs|hour|hours)\b", txt):
        return "hours"

    if re.search(r"\b(dag|dagen|day|days)\b", txt):
        return "days"

    return ""

def to_lang_code(nl_word):
    s = (nl_word or "").strip().lower()
    if s.startswith("eng"):  # Engels
        return "en"
    if s.startswith("duits"):
        return "de"
    if s.startswith("frans"):
        return "fr"
    return "nl"

def _cdata(val: str) -> str:
    s = "" if val is None else str(val)
    s = s.replace("]]>", "]]]]><![CDATA[>")
    return "<![CDATA[" + s + "]]>"

def is_studytube_course(course: dict) -> bool:
    custom = (course or {}).get("custom") or {}
    kanaal = custom.get("kanaal")
    vals = kanaal if isinstance(kanaal, list) else ([kanaal] if isinstance(kanaal, str) else [])
    return any((str(v).strip().lower() == "studytube") for v in vals if v is not None)

def training_type_from_course(course: dict) -> str:
    custom = (course or {}).get("custom") or {}
    return "elearning" if custom.get("elearning_id") else "classroom_training"

def agenda_from_course(course: dict) -> str:
    for tab in (course.get("course_tab_contents") or []):
        tab_name = (tab.get("course_tab") or {}).get("name", "")
        if str(tab_name).strip().lower() == "onderwerpen":
            return tab.get("content") or ""
    return ""

def load_planned_for_course(cid: int):
    path = PLANNED_DIR / f"pc_{cid}.json"
    if not path.exists():
        return []
    data = read_json(path) or []
    return data if isinstance(data, list) else [data]

def live_session_closed(pc: dict) -> bool:
    status = (pc.get("status") or "").lower()
    if status in {"canceled", "completed"}:
        return True
    if pc.get("is_published") is False:
        return True
    return False

def description_from_course(course: dict) -> str:
    # 1) als meta_description gevuld is: die gebruiken
    meta = (course.get("meta_description") or "").strip()
    if meta:
        return meta

    # 2) anders: pak tab "Algemene omschrijving" of position==1; fallback: eerste tab
    tabs = course.get("course_tab_contents") or []
    preferred = None
    for t in tabs:
        ct = (t.get("course_tab") or {})
        name = (ct.get("name") or "").strip().lower()
        if name == "algemene omschrijving" or ct.get("position") == 1:
            preferred = t
            break
    if not preferred and tabs:
        preferred = tabs[0]

    return (preferred or {}).get("content") or ""
# ---- 1) variant-id -> variantnaam inladen ----


# ---- 2) variantnaam -> StudyTube TrainingType mappen ----
def map_variant_name_to_training_type(name: str) -> str:
    """
    Zet een Eduframe course-variant *naam* om naar StudyTube TrainingType.
    Mogelijke StudyTube waarden:
      classroom_training, elearning, blended_learning, home_study,
      virtual_classroom, webinar, workshop, coaching, exam, other
    """
    n = (name or "").strip().lower()

    # veelvoorkomende NL/EN varianten afvangen
    # NB: pas dit gerust aan jullie vocabulaire aan.
    if re.search(r"\bexam|examen\b", n):
        return "exam"
    if "webinar" in n:
        return "webinar"
    if "coaching" in n:
        return "coaching"
    if "workshop" in n:
        return "workshop"
    if "virtual classroom" in n or "virtueel" in n or "online klassikaal" in n:
        return "virtual_classroom"
    if "klassikaal" in n or "classroom" in n:
        return "classroom_training"
    if "e-learning" in n or "elearning" in n or "e learning" in n or "zelfstudie" in n or "home study" in n:
        # Als het echt zelfstandig zonder bijeenkomsten is zou "home_study" ook kunnen;
        # standaard kiezen we 'elearning'.
        return "elearning"
    if "begeleid" in n or "blended" in n:
        # vaak mix van online + live
        return "blended_learning"
    if "maatwerk" in n or "incompany" in n:
        # kan alle kanten op → 'other' tenzij je het strakker wilt mappen.
        return "other"

    return "other"

# ---- 3) Aggregatie over planned courses → 1 TrainingType op course-niveau ----
def determine_training_type_for_course(
    planned: Iterable[dict],
    variant_lookup: Dict[int, str]
) -> str:
    """
    Berekent één StudyTube TrainingType voor een *course* op basis van de geplande edities (planned courses).
    Strategie:
    - Verzamel alle types uit de geplande edities (via course_variant_id → naam → type).
    - Als er zowel online (elearning) als live (classroom/virtual/webinar/workshop/coaching) voorkomt → blended_learning.
    - Anders gebruik prioriteiten (exam > webinar > virtual_classroom > classroom_training > workshop > coaching > elearning > other).
    - Als er niets te bepalen valt → 'other'.
    """
    mapped_types: List[str] = []
    for pc in planned:
        variant_id = pc.get("course_variant_id")
        if variant_id is None:
            continue
        name = variant_lookup.get(int(variant_id))
        t = map_variant_name_to_training_type(name) if name else "other"
        mapped_types.append(t)

    if not mapped_types:
        return "other"

    # Blended als mix online + live
    online: Set[str] = {"elearning", "home_study"}
    live: Set[str] = {"classroom_training", "virtual_classroom", "webinar", "workshop", "coaching"}
    s = set(mapped_types)
    if (s & online) and (s & live):
        return "blended_learning"

    # Als alles 'other' is, dan 'other'
    if s == {"other"}:
        return "other"

    # Prioriteiten als er meerdere live/zelfde-achtige types zijn
    priority = [
        "exam",
        "webinar",
        "virtual_classroom",
        "classroom_training",
        "workshop",
        "coaching",
        "elearning",
        "home_study",
        "blended_learning",  # zou al hierboven afgehandeld moeten zijn
        "other",
    ]
    # Neem het meest voorkomende type, gebroken door bovenstaande prioriteit
    counts = Counter(mapped_types)
    # sorteer op (a) aflopende frequentie, (b) priority index
    best = sorted(counts.items(), key=lambda kv: (-kv[1], priority.index(kv[0]) if kv[0] in priority else 9999))[0][0]
    return best

def xml_product_for_course(course: dict) -> str:
    cid = course.get("id")
#    code = course.get("code") or f"CRS-{cid}"
    code = "_"+str(course.get("code") or f"CRS-{cid}")
    code = re.sub(r"[^A-Za-z0-9_.-]", "_", code)
    name = course.get("name") or ""
#    description = course.get("meta_description") or ""
    description = description_from_course(course) or "10"
    price = course.get("starting_price") or course.get("cost") or ""
    language = to_lang_code(first_or_empty((course.get("custom") or {}).get("taal")))
#    duration_days = extract_duration_days(course.get("duration") or (course.get("custom") or {}).get("duration"))
    raw_duration = course.get("duration") or (course.get("custom") or {}).get("duration")

    duration_value = extract_duration_value(raw_duration)
    duration_unit  = extract_duration_unit(raw_duration)

    subcats = (course.get("custom") or {}).get("studytube-categorieen") or []
#    subcat = subcats[0] if subcats else ""
    subcat = ", ".join(subcats)
    category = cv1.choose_category_from_subcats(subcats)

    agenda_html = agenda_from_course(course)
    training_type = training_type_from_course(course)
    planned = load_planned_for_course(cid)
    has_planned = len(planned) > 0
    with open(os.path.join(BASE_JSON_DIR, "data_poc_v1/course_variants.json"), "r", encoding="utf-8") as f:
        _variants = json.load(f)
    variant_name_by_id = {v["id"]: v["name"] for v in _variants}
    if True:
        print()
        print(">>>>>>>>>>>>>>>>>>>", course.get("id"), course.get("name"))
        # toekomst = sum(date.fromisoformat(x['start_date']) > date.today() for x in planned)
        # verleden  = sum(date.fromisoformat(x['start_date']) < date.today() for x in planned)
        # # Optioneel: vandaag apart tellen
        # # vandaag   = sum(date.fromisoformat(x['start_date']) == date.today() for x in planned)

        # print(f"{toekomst} toekomst")
        # print(f"{verleden} verleden")


        vandaag = date.today()
        per_variant = defaultdict(lambda: {"toekomst": 0, "verleden": 0, "vandaag": 0})

        for it in planned:
            sd = it.get("start_date")
            if not sd:
                continue
            d = date.fromisoformat(sd)

            vid = it.get("course_variant_id")  # kan None zijn
            if d > vandaag:
                per_variant[vid]["toekomst"] += 1
            elif d < vandaag:
                per_variant[vid]["verleden"] += 1
            else:
                per_variant[vid]["vandaag"] += 1


        # sorteer: None komt achteraan; verder op variant-naam en dan id
        for vid in sorted(
            per_variant,
            key=lambda k: (
                k is None,
                variant_name_by_id.get(k, ""),  # sorteer op naam waar beschikbaar
                k or 0
            ),
        ):
            t = per_variant[vid]
            if vid is None:
                label = "onbekend"
            else:
                # toon naam; als id niet in json staat, val terug op het nummer
                label = variant_name_by_id.get(vid, f"id {vid}")

            # alleen de naam printen
            print(
                f"{label}: {t['toekomst']} toekomst, {t['verleden']} verleden"
                + (f", {t['vandaag']} vandaag" if t['vandaag'] else "")
            )

            # Wil je ook id erbij? gebruik dit ipv bovenstaande print:
            # print(
            #     f"{label} ({vid}): {t['toekomst']} toekomst, {t['verleden']} verleden"
            #     + (f", {t['vandaag']} vandaag" if t['vandaag'] else "")
            # )
    schedule_type = "scheduled" if has_planned else "nodate"

    parts = []
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

#    ap(f"<Duration>{text_or_empty(duration_days)}</Duration>")
#    ap("<DurationUnit>days</DurationUnit>")
    ap(f"<Duration>{text_or_empty(duration_value)}</Duration>")
    ap(f"<DurationUnit>{duration_unit}</DurationUnit>")    
    web = course.get("website_url") or "https://startel.nl/alle-trainingen/"
    sessionurl = "https://startel.nl/"
    ap(f"<WebAddress>{_cdata(web)}</WebAddress>")

    ap(f"<ScheduleType>{schedule_type}</ScheduleType>")
    training_type = determine_training_type_for_course(planned, variant_lookup)
    ap(f"<TrainingType>{training_type}</TrainingType>")
    # ap(f"<TrainingType>{training_type}</TrainingType>")

    if has_planned:
        ap("<LiveSessions>")
        for pc in planned:
            ap("<LiveSession>")
            #ap(f"<ID>{_cdata("pc-" + str(pc.get("id")))}</ID>")
            val = _cdata(f"pc-{pc.get('id')}")
            ap(f"<ID>{val}</ID>")
            ap(f"<Url>{_cdata(sessionurl)}</Url>")
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

def build_products_xml() -> str:
    courses = read_json(COURSES_FILE) or []
    if isinstance(courses, dict):
        courses = [courses]

    # Filter: alleen kanaal == studytube
    courses_filtered = [c for c in courses if is_studytube_course(c)]

    xml_parts = ["<Products>"]
    for c in courses_filtered:
        xml_parts.append(xml_product_for_course(c))
    xml_parts.append("</Products>")
    return "\n".join(xml_parts)

def studytube_products():
    if not COURSES_FILE.exists():
        abort(404, description=f"courses.json niet gevonden op {COURSES_FILE}")
    xml_str = build_products_xml()
    if "<Product>" not in xml_str:
        # Geen items -> 204 of lege lijst
        return Response("<Products></Products>", status=200, mimetype="application/xml")
    # Content-Type + no-cache (optioneel)
    resp = Response(xml_str, mimetype="application/xml")
    resp.headers["Cache-Control"] = "no-store"
    return resp


def load_course_ids(courses_path: Path) -> list[int]:
    data = json.loads(courses_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = [data]
    # volgorde behouden, duplicaten verwijderen
    seen, ids = set(), []
    for obj in data:
        cid = obj.get("id")
        if cid is None:
            continue
        try:
            cid = int(cid)
        except Exception:
            continue
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)
    return ids

def read_progress(progress_path: Path) -> int:
    if not progress_path.exists():
        return 0
    try:
        j = json.loads(progress_path.read_text(encoding="utf-8"))
        # backward compat: accepteer next_index of last_index
        if "next_index" in j:
            return int(j["next_index"])
        if "last_index" in j:
            return int(j["last_index"])
        return int(j.get("last_index_processed", 0)) + 1
    except Exception:
        return 0

def write_progress(progress_path: Path, next_index: int, next_course_id: int,
                   last_index_processed: int, last_course_id: int, total: int):
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "total_courses": total,
        "next_index": next_index,
        "next_course_id": next_course_id,
        "last_index_processed": last_index_processed,
        "last_course_id": last_course_id,
        "note": "Volgende run start bij next_index/course_id."
    }
    progress_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def run_batch_update(
    fetch_and_save_planned_courses,
    courses_path: Path = COURSES_FILE,
    progress_path: Path = PROGRESS_PATH,
    max_calls: int = 100,
    sleep_per_call: float = 0.0,  # evt. kleine pauze per call (seconds)
) -> int:
    course_ids = load_course_ids(courses_path)
    n = len(course_ids)
    if n == 0:
        print("Geen courses in courses.json gevonden.")
        return 0

    start_index = read_progress(progress_path)
    if start_index < 0 or start_index >= n:
        start_index = 0

    calls = 0
    idx = start_index
    last_idx_processed = (start_index - 1) % n
    last_course_id = course_ids[last_idx_processed]

    while calls < max_calls:
        course_id = course_ids[idx]
        try:
            fetch_and_save_planned_courses(course_id)
        except Exception as e:
            # Log en ga door; we willen niet 'vast' blijven op een falende course
            print(f"[{calls+1}/{max_calls}] Fout bij course {course_id}: {e}")
        else:
            print(f"[{calls+1}/{max_calls}] OK course {course_id}")
        calls += 1
        last_idx_processed = idx
        last_course_id = course_id
        idx = (idx + 1) % n
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
        total=n,
    )
    return f"Batch klaar: {calls} calls gedaan. Volgende start: index={next_index} (course_id={next_course_id}).<h1>roep deze pas over 5 minuten aan, dus na: {str(datetime.now() + timedelta(minutes=5))}</h1>"
    


def load_json_safe(relpath: str):
    if not relpath.endswith(".json"):
        raise ValueError("Alleen .json bestanden zijn toegestaan.")
    # Voorkom path traversal: alleen binnen BASE_JSON_DIR
    req_path = (BASE_JSON_DIR / relpath).resolve()
    try:
        req_path.relative_to(BASE_JSON_DIR)
    except ValueError:
        # buiten de toegestane map
        raise FileNotFoundError(f"Niet toegestaan: {relpath}")
    if not req_path.is_file():
        raise FileNotFoundError(f"Bestand bestaat niet: {relpath}")
    # Lees en parse het JSON (garandeert geldige output)
    return json.loads(req_path.read_text(encoding="utf-8"))

def get_json_file(relpath: str):
    pretty = request.args.get("pretty", "").lower() in {"1", "true", "yes"}
    try:
        data = load_json_safe(relpath)
    except FileNotFoundError as e:
        abort(404, description=str(e))
    except ValueError as e:
        abort(400, description=str(e))
    except json.JSONDecodeError:
        abort(500, description="Ongeldig JSON-bestand.")

    body = (
        json.dumps(data, ensure_ascii=False, indent=2)
        if pretty
        else json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )
    return Response(body, mimetype="application/json")