#!/usr/bin/env python3
"""
Back-fill FishType.image_data → Supabase Storage → FishType.image_path

Run once, then drop the legacy columns in a follow-up migration.
"""

import io
import sys
import time
from contextlib import suppress

from sqlalchemy import func

# --- initialise your Flask app & DB -----------------------------------------
from app import create_app, db
from app.models import FishType
from app.services.supa_images import upload_image   # helper we wrote earlier

BATCH_SIZE = 50             # rows per commit
NULL_BLOBS_AFTER_UPLOAD = True   # set False if you want to keep blobs for a while

app = create_app()

def migrate():
    total = db.session.execute(
        db.select(func.count()).select_from(
            FishType
        ).where(
            FishType.image_data.is_not(None),
            FishType.image_path.is_(None)
        )
    ).scalar_one()

    if total == 0:
        print("✅ Nothing to migrate — all rows already use image_path.")
        return

    print(f"🔄 Starting migration for {total} rows…")
    migrated = failed = 0
    start_ts = time.perf_counter()

    # Stream rows to keep memory low
    query = (
        FishType.query
        .filter(FishType.image_data.isnot(None), FishType.image_path.is_(None))
        .yield_per(100)
    )

    batch = 0
    for row in query:
        try:
            path = upload_image(io.BytesIO(row.image_data),
                                row.image_mime_type or "image/jpeg",
                                row.type_code)
            row.image_path = path
            if NULL_BLOBS_AFTER_UPLOAD:
                row.image_data = None
                row.image_mime_type = None
            migrated += 1
        except Exception as exc:
            failed += 1
            print(f"❌  type_id={row.type_id}  upload failed: {exc}", file=sys.stderr)

        batch += 1
        if batch >= BATCH_SIZE:
            db.session.commit()
            print(f"  ✔ committed batch, progress: {migrated + failed}/{total}")
            batch = 0

    # commit any remainder
    db.session.commit()
    duration = time.perf_counter() - start_ts
    print(f"\n🏁 Done in {duration:0.1f}s — migrated {migrated}, failed {failed}")

if __name__ == "__main__":
    with app.app_context():
        migrate()
