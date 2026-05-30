from __future__ import annotations

from datetime import datetime

from app.storage.db import connect


async def add_image(
    id: str,
    filename: str,
    display_path: str,
    tmp_path: str,
    file_size: int,
) -> None:
    ts = datetime.now().isoformat()
    async with connect() as db:
        await db.execute(
            "INSERT INTO images (id, filename, display_path, tmp_path, file_size, created_ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (id, filename, display_path, tmp_path, file_size, ts),
        )
        await db.commit()


async def confirm_image(id: str, display_path: str, file_size: int) -> None:
    """Mark image as confirmed: set display_path, clear tmp_path."""
    async with connect() as db:
        await db.execute(
            "UPDATE images SET display_path=?, tmp_path=NULL, file_size=? WHERE id=?",
            (display_path, file_size, id),
        )
        await db.commit()


async def list_images() -> list[dict]:
    """Return all confirmed (tmp_path IS NULL) images ordered by created_ts ASC."""
    async with connect() as db:
        async with db.execute(
            "SELECT id, filename, display_path, file_size, created_ts "
            "FROM images WHERE tmp_path IS NULL ORDER BY created_ts ASC"
        ) as cur:
            rows = await cur.fetchall()
    return [
        {
            "id": r[0],
            "filename": r[1],
            "display_path": r[2],
            "file_size": r[3],
            "created_ts": r[4],
        }
        for r in rows
    ]


async def get_image(id: str) -> dict | None:
    async with connect() as db:
        async with db.execute(
            "SELECT id, filename, display_path, tmp_path, file_size, created_ts "
            "FROM images WHERE id=?",
            (id,),
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "display_path": row[2],
        "tmp_path": row[3],
        "file_size": row[4],
        "created_ts": row[5],
    }


async def delete_image_record(id: str) -> dict | None:
    """Delete DB record and return it so caller can remove files."""
    row = await get_image(id)
    if row is None:
        return None
    async with connect() as db:
        await db.execute("DELETE FROM images WHERE id=?", (id,))
        await db.commit()
    return row


async def count_confirmed_images() -> int:
    async with connect() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM images WHERE tmp_path IS NULL"
        ) as cur:
            result = await cur.fetchone()
    return result[0] if result else 0


async def get_oldest_confirmed_image() -> dict | None:
    async with connect() as db:
        async with db.execute(
            "SELECT id, filename, display_path, file_size, created_ts "
            "FROM images WHERE tmp_path IS NULL ORDER BY created_ts ASC LIMIT 1"
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "filename": row[1],
        "display_path": row[2],
        "file_size": row[3],
        "created_ts": row[4],
    }


async def get_unconfirmed_images() -> list[dict]:
    """Return orphan upload records where tmp_path IS NOT NULL."""
    async with connect() as db:
        async with db.execute(
            "SELECT id, tmp_path FROM images WHERE tmp_path IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
    return [{"id": r[0], "tmp_path": r[1]} for r in rows]
