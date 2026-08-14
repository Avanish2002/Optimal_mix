"""Concrete mix multi-objective optimisation API.

Run with: flask --app app run --debug
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from optimizer import optimise

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "optimization.db"
MATERIALS = ("cement", "water", "fine", "coarse", "flyAsh", "silica", "slag", "plastic")
INPUT_FIELDS = ("stdDev",) + tuple(
    f"{material}{suffix}" for suffix in ("INR", "CO2", "KG") for material in MATERIALS
)


def initialise_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS optimization_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            )"""
        )


def parse_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required.")
    grade = str(payload.get("grade", ""))
    if grade not in {f"M{number}" for number in range(40, 121, 10)}:
        raise ValueError("grade must be between M40 and M120.")

    parsed = {"grade": grade}
    for field in INPUT_FIELDS:
        try:
            value = float(payload[field])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"{field} must be a number.") from error
        if value < 0:
            raise ValueError(f"{field} cannot be negative.")
        parsed[field] = value
    return parsed


@app.post("/api/optimizations")
def run_optimization():
    try:
        data = parse_payload(request.get_json(silent=True))
        result = optimise(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute(
            "INSERT INTO optimization_runs (created_at, request_json, result_json) VALUES (?, ?, ?)",
            (created_at, json.dumps(data), json.dumps(result)),
        )
        run_id = cursor.lastrowid
    return jsonify({"id": run_id, "createdAt": created_at, **result}), 201


@app.get("/api/optimizations")
def optimization_history():
    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            "SELECT id, created_at, request_json, result_json FROM optimization_runs ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return jsonify([
        {"id": row[0], "createdAt": row[1], "input": json.loads(row[2]), "result": json.loads(row[3])}
        for row in rows
    ])


initialise_database()
