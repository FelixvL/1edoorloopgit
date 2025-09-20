"""Flask application exposing the StudyTube endpoints."""

from __future__ import annotations

import os

from flask import Flask
from flask_cors import CORS

from data_poc_v2 import algemeen as data_service

app = Flask(__name__)
CORS(app)


@app.route("/studytube_courses_van_eduframe_naar_bestand")
def studytube_courses_van_eduframe_naar_bestand():
    """Synchronise StudyTube courses from Eduframe to disk."""
    return data_service.studytube_courses_van_eduframe_naar_bestand()


@app.get("/studytube/products_in_xml")
def products_in_xml():
    """Serve the StudyTube products XML feed."""
    return data_service.studytube_products()


@app.get("/planned_courses_schrijven")
def planned_courses_schrijven():
    """Fetch a batch of planned courses and cache them."""
    return data_service.run_batch_update(
        data_service.fetch_and_save_planned_courses,
        max_calls=350,
    )


@app.get("/files/<path:relpath>")
def get_json_file(relpath: str):
    """Serve cached JSON files for debugging purposes."""
    return data_service.get_json_file(relpath)


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
