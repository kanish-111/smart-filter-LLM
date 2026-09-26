"""Create a deterministic SQLite dataset of synthetic solar work orders."""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "work_orders.sqlite3"
RECORD_COUNT = 2500
INSPECTION_COUNT = 1200
SEED = 731_904

REGIONS = {
    "Leinster": ["Dublin", "Wicklow", "Kildare", "Meath", "Laois"],
    "Munster": ["Cork", "Kerry", "Limerick", "Clare", "Tipperary"],
    "Connacht": ["Galway", "Mayo", "Sligo", "Roscommon", "Leitrim"],
    "Ulster": ["Donegal", "Cavan", "Monaghan"],
}
ASSET_TYPES = ["Inverter", "Solar Panel", "Battery", "Tracker", "Transformer", "Combiner Box", "Monitoring Gateway"]
STATUSES = ["Open", "In Progress", "Blocked", "Resolved", "Closed"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
TECHNICIANS = ["Aisling Byrne", "Cian Murphy", "Niamh Kelly", "Rory Walsh", "Aoife Ryan", "Eoin Doyle", "Orla Quinn", "Finn Gallagher", "Maeve O'Brien", "Luca Martin"]
BRANDS = ["SMA", "Huawei", "SolarEdge", "Fronius", "ABB", "Trina", "Jinko", "BYD", "Schneider", "Sungrow"]
NOTES = [
    "Thermal scan found a hot connection at the terminal.",
    "Replacement part is on order from the supplier.",
    "Remote reset restored normal operation.",
    "Awaiting site access approval before inspection.",
    "Output is below the expected curve after heavy rain.",
    "Firmware update scheduled during the next maintenance window.",
    "Inspection found no active fault; monitoring for recurrence.",
    "String voltage readings are inconsistent with the baseline.",
    "Communications dropped after the network cabinet was moved.",
    "Preventive maintenance visit requested by the site manager.",
    "Loose mounting hardware tightened and rechecked.",
    "Battery temperature sensor needs a replacement.",
]


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS work_orders (
            ticket_no TEXT PRIMARY KEY,
            site_name TEXT NOT NULL,
            region TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            technician TEXT,
            opened_at TEXT NOT NULL,
            days_open INTEGER NOT NULL,
            estimated_cost_eur REAL NOT NULL,
            generation_loss_kw REAL,
            notes TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_work_orders_status ON work_orders(status);
        CREATE INDEX IF NOT EXISTS idx_work_orders_priority ON work_orders(priority);
        CREATE INDEX IF NOT EXISTS idx_work_orders_region ON work_orders(region);
        CREATE INDEX IF NOT EXISTS idx_work_orders_asset_type ON work_orders(asset_type);
        CREATE INDEX IF NOT EXISTS idx_work_orders_cost ON work_orders(estimated_cost_eur);
        CREATE INDEX IF NOT EXISTS idx_work_orders_opened_at ON work_orders(opened_at);
        CREATE TABLE IF NOT EXISTS site_inspections (
            inspection_id TEXT PRIMARY KEY,
            site_name TEXT NOT NULL,
            region TEXT NOT NULL,
            inspector TEXT NOT NULL,
            inspection_type TEXT NOT NULL,
            result TEXT NOT NULL,
            inspected_at TEXT NOT NULL,
            issues_found INTEGER NOT NULL,
            downtime_hours REAL NOT NULL,
            estimated_cost_eur REAL NOT NULL,
            summary TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_inspections_result ON site_inspections(result);
        CREATE INDEX IF NOT EXISTS idx_inspections_region ON site_inspections(region);
        CREATE INDEX IF NOT EXISTS idx_inspections_date ON site_inspections(inspected_at);
        """
    )


def make_row(
    rng: random.Random,
    number: int,
    *,
    region: str | None = None,
    county: str | None = None,
    asset_type: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    cost: float | None = None,
    opened_at: str | None = None,
) -> tuple[Any, ...]:
    region = region or rng.choice(list(REGIONS))
    county = county or rng.choice(REGIONS[region])
    asset_type = asset_type or rng.choice(ASSET_TYPES)
    priority = priority or rng.choices(PRIORITIES, weights=[14, 36, 34, 16], k=1)[0]
    status = status or rng.choices(STATUSES, weights=[24, 27, 10, 20, 19], k=1)[0]
    opened_at = opened_at or (date(2024, 1, 1) + timedelta(days=rng.randint(0, 997))).isoformat()
    cost = round(cost if cost is not None else rng.uniform(180, 48_000), 2)
    days_open = max(0, min(950, (date(2026, 9, 23) - date.fromisoformat(opened_at)).days))
    if status in {"Resolved", "Closed"}:
        days_open = rng.randint(0, min(days_open, 250))
    generation_loss = None if rng.random() < 0.14 else round(rng.uniform(0, 750), 1)
    technician = None if rng.random() < 0.055 else rng.choice(TECHNICIANS)
    brand = rng.choice(BRANDS)
    model = rng.choice(["X1", "M2", "Pro-40", "Edge-12", "3000", "S-880", "Nova-6"])
    asset_name = brand + " " + asset_type.lower() + " " + model
    if asset_type == "Solar Panel":
        asset_name = brand + " Vertex " + rng.choice(["410W", "450W", "480W"])
    site_name = county + " " + rng.choice(["Solar Park", "Renewables Site", "PV Farm", "Energy Hub", "Array"])
    return (
        "WO-2026-" + str(number).zfill(5),
        site_name,
        region,
        asset_type,
        asset_name,
        status,
        priority,
        technician,
        opened_at,
        days_open,
        cost,
        generation_loss,
        rng.choice(NOTES),
    )


def make_inspection_row(rng: random.Random, number: int) -> tuple[Any, ...]:
    """Create one repeatable, fictional site-inspection record."""
    region = rng.choice(list(REGIONS))
    county = rng.choice(REGIONS[region])
    site_name = county + " " + rng.choice(["Solar Park", "Renewables Site", "PV Farm", "Energy Hub", "Array"])
    inspection_type = rng.choice(["Routine", "Safety", "Performance", "Post-repair", "Annual"])
    result = rng.choices(["Pass", "Follow-up", "Failed"], weights=[58, 30, 12], k=1)[0]
    issues_found = 0 if result == "Pass" else rng.randint(1, 8)
    downtime = 0.0 if result == "Pass" else round(rng.uniform(0.5, 48), 1)
    estimated_cost = 0.0 if result == "Pass" else round(rng.uniform(250, 24_000), 2)
    inspected_at = (date(2024, 1, 1) + timedelta(days=rng.randint(0, 997))).isoformat()
    summaries = {
        "Pass": ["No material issues found during the site check.", "Output and safety checks are within expected limits."],
        "Follow-up": ["Monitor the inverter readings and recheck next visit.", "Minor cable wear needs a follow-up inspection.", "Schedule a panel wash and review output."],
        "Failed": ["Isolation test failed; repair is required before restart.", "Thermal scan found a damaged connection.", "Protective relay did not pass the response test."],
    }
    inspector = rng.choice(["Aisling Byrne", "Cian Murphy", "Niamh Kelly", "Rory Walsh", "Aoife Ryan", "Eoin Doyle"])
    return (
        "IN-2026-" + str(number).zfill(5),
        site_name,
        region,
        inspector,
        inspection_type,
        result,
        inspected_at,
        issues_found,
        downtime,
        estimated_cost,
        rng.choice(summaries[result]),
    )


def seed_database(path: Path = DB_PATH, force: bool = False) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        create_schema(connection)
        if force:
            connection.execute("DELETE FROM work_orders")
            connection.execute("DELETE FROM site_inspections")
        work_order_count = int(connection.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0])
        inspection_count = int(connection.execute("SELECT COUNT(*) FROM site_inspections").fetchone()[0])

        # Seed each table independently so older demo databases gain the new sample table.
        if work_order_count == 0:
            rng = random.Random(SEED)
            rows = [
                make_row(rng, 1, region="Munster", county="Cork", asset_type="Inverter", priority="Critical", status="Open", cost=6400, opened_at="2026-09-01"),
                make_row(rng, 2, region="Munster", county="Limerick", asset_type="Inverter", priority="Critical", status="In Progress", cost=11200, opened_at="2026-08-24"),
                make_row(rng, 3, region="Munster", county="Kerry", asset_type="Inverter", priority="Critical", status="Resolved", cost=2600, opened_at="2026-06-16"),
                make_row(rng, 4, region="Leinster", county="Dublin", asset_type="Inverter", priority="Critical", status="Open", cost=7100, opened_at="2026-08-20"),
                make_row(rng, 5, region="Munster", county="Cork", asset_type="Solar Panel", priority="Critical", status="Blocked", cost=7500, opened_at="2026-08-13"),
                make_row(rng, 6, region="Munster", county="Clare", asset_type="Inverter", priority="High", status="Open", cost=8200, opened_at="2026-09-04"),
                make_row(rng, 7, region="Munster", county="Tipperary", asset_type="Inverter", priority="Critical", status="In Progress", cost=5100, opened_at="2026-07-19"),
            ]
            rows.extend(make_row(rng, number) for number in range(8, RECORD_COUNT + 1))
            connection.executemany("INSERT INTO work_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

        if inspection_count == 0:
            rng = random.Random(SEED + 1)
            inspections = [make_inspection_row(rng, number) for number in range(1, INSPECTION_COUNT + 1)]
            # Keep useful matches in every fresh database, independent of random sampling.
            inspections[:3] = [
                ("IN-2026-00001", "Cork Solar Park", "Munster", "Aisling Byrne", "Safety", "Failed", "2026-09-03", 3, 12.5, 8400.0, "Thermal scan found a damaged connection."),
                ("IN-2026-00002", "Dublin PV Farm", "Leinster", "Cian Murphy", "Performance", "Follow-up", "2026-08-22", 2, 4.0, 2100.0, "Monitor the inverter readings and recheck next visit."),
                ("IN-2026-00003", "Galway Energy Hub", "Connacht", "Niamh Kelly", "Routine", "Pass", "2026-08-14", 0, 0.0, 0.0, "No material issues found during the site check."),
            ]
            connection.executemany("INSERT INTO site_inspections VALUES (?,?,?,?,?,?,?,?,?,?,?)", inspections)
        connection.commit()
    return RECORD_COUNT


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the local synthetic solar work-order database")
    parser.add_argument("--force", action="store_true", help="replace existing synthetic rows")
    args = parser.parse_args()
    seed_database(force=args.force)
    print("Ready: synthetic work orders and site inspections in " + str(DB_PATH))


if __name__ == "__main__":
    main()
