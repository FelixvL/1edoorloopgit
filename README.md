# StudyTube XML feed POC (refactored)

Deze proof-of-concept bevat een opgeschoonde structuur waarin de Flask-applicatie in `app.py`
minimaal blijft en alle herbruikbare logica in `data_poc_v2` woont.

## Structuur

- `app.py` – definieert alleen de Flask-routes en delegeren naar `data_poc_v2`.
- `data_poc_v2/algemeen.py` – bevat de API-clients, caching, XML-generatie, logging en helperfuncties.
- `data_poc_v2/categorie_selector.py` – logica voor categorie- en subcategorie-selectie.
- `data_poc_v2/planned_courses_poc_v2/` – map waar de geplande-cursus-cache (`pc_<course_id>.json`) wordt opgeslagen.
- `data_poc_v2/courses_poc_v2.json` – cache voor Eduframe-cursussen.
- `data_poc_v2/course_variants.json` – mapping van variant-id naar naam (gekopieerd uit de oorspronkelijke POC).

De oude bestanden (`courses_poc_v1.json`, `planned_courses_poc_v1`, `course_variants.json`) blijven aanwezig
voor backward compatibility, maar de nieuwe code gebruikt standaard de `data_poc_v2`-varianten en valt alleen
terug op de oude paden wanneer de nieuwe nog niet bestaan.

## Gebruik

1. Installeer dependencies (`pip install flask flask-cors requests`).
2. Start de applicatie met `FLASK_RUN_PORT=5000 python app.py`.
3. Gebruik de bestaande endpoints:
   - `GET /studytube_courses_van_eduframe_naar_bestand` – haalt StudyTube-cursussen op en schrijft ze naar de cache.
   - `GET /studytube/products_in_xml` – levert de StudyTube XML-feed.
   - `GET /planned_courses_schrijven` – haalt geplande cursussen batchgewijs op.
   - `GET /files/<pad>` – geeft JSON-bestanden uit de cache terug.

## Tests

Voer `pytest` uit om de belangrijkste helpers te testen.
