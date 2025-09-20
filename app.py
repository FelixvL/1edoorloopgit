
from flask import Flask
from flask_cors import CORS


# app.py
import os

import startel_studytube_xml_feed_poc_v1 as ssxfpv

# Configureer paden via env vars of defaults


app = Flask(__name__)
CORS(app)


@app.route("/studytube_courses_van_eduframe_naar_bestand")
def studytube_courses_van_eduframe_naar_bestand():
    return ssxfpv.studytube_courses_van_eduframe_naar_bestand()

@app.get("/studytube/products_in_xml")
def products_in_xml():
    return ssxfpv.studytube_products()

@app.get("/planned_courses_schrijven")
def planned_courses_schrijven():
    return ssxfpv.run_batch_update(ssxfpv.fetch_and_save_planned_courses, max_calls=350)

@app.get("/files/<path:relpath>")
def get_json_file(relpath: str):
    return ssxfpv.get_json_file(relpath)

if __name__ == "__main__":
    # Run:  FLASK_RUN_PORT=5000  python app.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
