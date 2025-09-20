from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_poc_v2 import algemeen


def create_cache_manager(tmp_path: Path) -> algemeen.CacheManager:
    data_dir = tmp_path / "data"
    planned_dir = data_dir / "planned"
    return algemeen.CacheManager(
        data_dir=data_dir,
        planned_dir=planned_dir,
        courses_file=data_dir / "courses_poc_v2.json",
        course_variants_file=data_dir / "course_variants.json",
        legacy_courses_files=(),
        legacy_planned_dirs=(),
        legacy_variant_files=(),
    )


def test_xml_product_for_course_generates_expected_structure(tmp_path: Path) -> None:
    cache_manager = create_cache_manager(tmp_path)
    cache_manager.save_json(
        cache_manager.course_variants_file,
        [
            {"id": 1, "name": "Klassikaal"},
        ],
    )
    cache_manager.save_planned_courses(
        123,
        [
            {
                "id": 987,
                "course_variant_id": 1,
                "start_date": "2025-01-01",
                "status": "planned",
                "is_published": True,
                "min_participants": 5,
                "max_participants": 15,
            }
        ],
    )
    course = {
        "id": 123,
        "code": "ABC",
        "name": "Demo Course",
        "meta_description": "Omschrijving",
        "starting_price": 199.0,
        "duration": "2 dagen",
        "custom": {
            "kanaal": ["studytube"],
            "taal": "Nederlands",
            "studytube-categorieen": ["Internet & Media", "Webdesign"],
        },
        "course_tab_contents": [
            {"course_tab": {"name": "Onderwerpen"}, "content": "Agenda"},
        ],
        "website_url": "https://example.org/course",
    }

    xml = algemeen.xml_product_for_course(course, cache_manager=cache_manager)

    assert "<Product>" in xml
    assert "<![CDATA[Demo Course]]>" in xml
    assert "<Category><![CDATA[Internet & Media]]></Category>" in xml
    assert "<TrainingType>classroom_training</TrainingType>" in xml
    assert "<LiveSessions>" in xml
    assert "<StartDate>2025-01-01</StartDate>" in xml


def test_build_products_xml_filters_non_studytube(tmp_path: Path) -> None:
    cache_manager = create_cache_manager(tmp_path)
    cache_manager.save_json(
        cache_manager.course_variants_file,
        [
            {"id": 1, "name": "Klassikaal"},
        ],
    )
    cache_manager.save_courses(
        [
            {
                "id": 123,
                "code": "ABC",
                "name": "Demo Course",
                "custom": {"kanaal": ["studytube"]},
            },
            {
                "id": 999,
                "code": "XYZ",
                "name": "Ignore",
                "custom": {"kanaal": ["website"]},
            },
        ]
    )
    cache_manager.save_planned_courses(
        123,
        [
            {
                "id": 987,
                "course_variant_id": 1,
                "start_date": "2025-01-01",
                "status": "planned",
            }
        ],
    )

    xml = algemeen.build_products_xml(cache_manager=cache_manager)

    assert xml.startswith("<Products>")
    assert xml.endswith("</Products>")
    assert xml.count("<Product>") == 1


def test_progress_helpers_roundtrip(tmp_path: Path) -> None:
    progress_file = tmp_path / "progress.json"
    algemeen.write_progress(
        progress_file,
        next_index=5,
        next_course_id=42,
        last_index_processed=4,
        last_course_id=21,
        total=10,
    )

    assert progress_file.exists()
    assert algemeen.read_progress(progress_file) == 5

    missing = tmp_path / "missing.json"
    assert algemeen.read_progress(missing) == 0
