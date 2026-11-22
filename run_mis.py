"""Generate a fixed fictional dataset, run checks, and export the MIS (Python 3.10+)."""
import csv
import sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "sample"
HEADERS = ["record_id", "sale_date", "dealer", "sku", "sell_in", "sell_out"]
DEALERS = {"D01": "West", "D02": "North", "D03": "South"}
SKUS = ("AC-INV", "COOLER")


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def make_sample():
    (DATA / "sales").mkdir(parents=True, exist_ok=True)
    write_csv(DATA / "dealers.csv", ["dealer", "region"], DEALERS.items())
    write_csv(DATA / "skus.csv", ["sku"], [(sku,) for sku in SKUS])
    targets = []
    for year in (2025, 2026):
        for month in range(1, 8):
            period = f"{year}-{month:02}"
            rows = []
            for i, (dealer, region) in enumerate(DEALERS.items()):
                plan = 8 * (40 + 6 * i + 12 * max(0, 4 - abs(month - 5)))
                if (year, month, region) != (2026, 7, "South"):
                    targets.append((period, region, plan))
                for week, day in enumerate((3, 10, 17, 24)):
                    for j, sku in enumerate(SKUS):
                        record = f"{period}-{dealer}-{day}-{sku}"
                        units = plan // 8 + week * 2 - j * 5
                        units += (year - 2025) * (5 - 3 * i)
                        if (year, month, region) == (2026, 6, "West"):
                            units -= 14
                        gap = 20 if (year, month, region) == (2026, 6, "West") else 4
                        rows.append((record, date(year, month, day), f" {dealer.lower()} ",
                                     sku.lower(), units + gap, units))
            if (year, month) == (2026, 6):
                rows.extend([rows[0], ("INVALID-1", "2026-06-03", "D99", "AC-INV", 20, 15)])
            write_csv(DATA / "sales" / f"{period}.csv", HEADERS, rows)
    write_csv(DATA / "targets.csv", ["month", "region", "target_units"], targets)


def run():
    write_outputs = ROOT / "results"
    write_outputs.mkdir(exist_ok=True)
    clean, rejected, seen = [], [], set()
    raw_count = 0
    for path in sorted((DATA / "sales").glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                raw_count += 1
                record = row["record_id"].strip()
                dealer, sku = (row[key].strip().upper() for key in ("dealer", "sku"))
                if dealer not in DEALERS or sku not in SKUS:
                    rejected.append((path.name, record, "unmapped code"))
                    continue
                if record in seen:
                    rejected.append((path.name, record, "duplicate ID"))
                    continue
                sale_date = date.fromisoformat(row["sale_date"]).isoformat()
                sell_in, sell_out = (int(row[key]) for key in ("sell_in", "sell_out"))
                seen.add(record)
                clean.append((record, sale_date, dealer, sku, DEALERS[dealer], sell_in, sell_out))
    write_csv(write_outputs / "clean_sales.csv",
              ["record_id", "sale_date", "dealer", "sku", "region", "sell_in", "sell_out"], clean)
    write_csv(write_outputs / "exceptions.csv", ["file", "record_id", "reason"], rejected)
    with sqlite3.connect(":memory:") as db:
        db.executescript(
            "CREATE TABLE sales(id TEXT PRIMARY KEY, sale_date TEXT, dealer TEXT, sku TEXT,"
            "region TEXT, sell_in INT, sell_out INT);"
            "CREATE TABLE targets(month TEXT, region TEXT, target_units INT, PRIMARY KEY(month, region));"
        )
        db.executemany("INSERT INTO sales VALUES (?,?,?,?,?,?,?)", clean)
        with (DATA / "targets.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.reader(stream)
            next(reader)
            db.executemany("INSERT INTO targets VALUES (?,?,?)", reader)
        report = db.execute((ROOT / "monthly_mis.sql").read_text(encoding="utf-8"))
        rows = report.fetchall()
        write_csv(write_outputs / "monthly_mis.csv", [item[0] for item in report.description], rows)
    assert raw_count == len(clean) + len(rejected) == 338
    assert len(rejected) == 2 and len(rows) == 42
    assert sum(row[3] for row in rows) == sum(row[6] for row in clean)
    assert next(row for row in rows if row[:2] == ("2026-07", "South"))[5] is None
    print(f"Reconciled {raw_count} source rows: {len(clean)} accepted, {len(rejected)} exceptions.")
    for row in rows:
        if row[0] == "2026-06":
            print(row)


if __name__ == "__main__":
    make_sample()
    run()
