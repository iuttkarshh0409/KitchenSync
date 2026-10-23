import backend.batching as batching
import backend.database as database
import backend.main as main
from backend.database import connect


def test_batch_replaces_queued_tasks_and_completes_each_source_order(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "batching.sqlite")
    database.init_db()

    order_ids = []
    for _ in range(2):
        result = main.create_order(main.OrderInput(items=[
            {"menu_item_id": "veg-momo", "quantity": 2},
            {"menu_item_id": "hakka-noodles", "quantity": 1},
        ]))
        order_ids.append(result["order_id"])

    created = batching.optimize_batches(window_minutes=3)
    assert len(created) == 2
    assert all(len(batch["orders"]) == 2 for batch in created)

    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0] == 2
        assert db.execute("SELECT COUNT(*) FROM tasks WHERE status='batched'").fetchone()[0] == 4

    main.start(created[0]["batch_id"])
    main.complete(created[0]["batch_id"])
    with connect() as db:
        rows = db.execute("SELECT id,status FROM orders WHERE id IN (?,?)", order_ids).fetchall()
        assert {row["status"] for row in rows} == {"queued"}

    main.start(created[1]["batch_id"])
    main.complete(created[1]["batch_id"])

    with connect() as db:
        rows = db.execute("SELECT id,status FROM orders WHERE id IN (?,?)", order_ids).fetchall()
        assert {row["status"] for row in rows} == {"completed"}
