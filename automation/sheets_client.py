"""
Google Sheets Client for prompt/video management
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_CREDENTIALS_JSON, SPREADSHEET_ID, SHEET_NAME

# Column mapping
COLUMNS = {
    "id": "A",
    "created_at": "B",
    "prompt": "C",
    "category": "D",
    "status": "E",
    "job_id": "F",
    "video_url": "G",
    "duration": "H",
    "resolution": "I",
    "cost": "J",
    "scheduled_at": "K",
    "published_at": "L",
    "later_id": "M",
    "caption": "N",
    "hashtags": "O",
    "error": "P",
}

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_service():
    """Get Google Sheets service"""
    if not GOOGLE_CREDENTIALS_JSON:
        raise ValueError("GOOGLE_CREDENTIALS_JSON not set")

    # Parse JSON from environment variable
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def get_all_rows() -> List[Dict]:
    """Get all rows from the sheet"""
    service = get_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A2:P",  # Skip header row
    ).execute()

    rows = result.get("values", [])
    records = []

    for row in rows:
        # Pad row to full length
        row = row + [""] * (16 - len(row))
        records.append({
            "id": row[0],
            "created_at": row[1],
            "prompt": row[2],
            "category": row[3],
            "status": row[4],
            "job_id": row[5],
            "video_url": row[6],
            "duration": row[7],
            "resolution": row[8],
            "cost": row[9],
            "scheduled_at": row[10],
            "published_at": row[11],
            "later_id": row[12],
            "caption": row[13],
            "hashtags": row[14],
            "error": row[15],
        })

    return records


def get_rows_by_status(status: str) -> List[Dict]:
    """Get rows with specific status"""
    all_rows = get_all_rows()
    return [r for r in all_rows if r["status"] == status]


def add_prompts(prompts: List[Dict]) -> int:
    """
    Add new prompts to sheet

    Args:
        prompts: List of dicts with 'prompt', 'caption', 'category', 'hashtags'

    Returns:
        Number of rows added
    """
    service = get_service()

    # Get current row count to generate IDs
    current_rows = get_all_rows()
    next_id = len(current_rows) + 1

    values = []
    now = datetime.utcnow().isoformat()

    for p in prompts:
        hashtags = p.get("hashtags", [])
        if isinstance(hashtags, list):
            hashtags = ",".join(hashtags)

        values.append([
            str(next_id),           # id
            now,                    # created_at
            p.get("prompt", ""),    # prompt
            p.get("category", ""),  # category
            "pending",              # status
            "",                     # job_id
            "",                     # video_url
            "",                     # duration
            "",                     # resolution
            "",                     # cost
            "",                     # scheduled_at
            "",                     # published_at
            "",                     # later_id
            p.get("caption", ""),   # caption
            hashtags,               # hashtags
            "",                     # error
        ])
        next_id += 1

    service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A:P",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values},
    ).execute()

    return len(values)


def update_row(row_id: str, updates: Dict) -> bool:
    """
    Update specific fields in a row

    Args:
        row_id: The ID value in column A
        updates: Dict of field names to new values
    """
    service = get_service()

    # Find the row number for this ID
    all_rows = get_all_rows()
    row_num = None

    for i, row in enumerate(all_rows):
        if row["id"] == row_id:
            row_num = i + 2  # +2 for header and 0-index
            break

    if row_num is None:
        return False

    # Build batch update
    data = []
    for field, value in updates.items():
        if field in COLUMNS:
            col = COLUMNS[field]
            data.append({
                "range": f"{SHEET_NAME}!{col}{row_num}",
                "values": [[str(value)]],
            })

    if data:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "valueInputOption": "RAW",
                "data": data,
            },
        ).execute()

    return True


def mark_generating(row_id: str, job_id: str):
    """Mark a row as generating with job_id"""
    return update_row(row_id, {"status": "generating", "job_id": job_id})


def mark_generated(row_id: str, video_url: str, duration: float, resolution: str, cost: float):
    """Mark a row as generated with video details"""
    return update_row(row_id, {
        "status": "generated",
        "video_url": video_url,
        "duration": duration,
        "resolution": resolution,
        "cost": cost,
    })


def mark_scheduled(row_id: str, later_id: str, scheduled_at: str):
    """Mark a row as scheduled"""
    return update_row(row_id, {
        "status": "scheduled",
        "later_id": later_id,
        "scheduled_at": scheduled_at,
    })


def mark_published(row_id: str):
    """Mark a row as published"""
    now = datetime.utcnow().isoformat()
    return update_row(row_id, {"status": "published", "published_at": now})


def mark_error(row_id: str, error: str):
    """Mark a row as failed with error message"""
    return update_row(row_id, {"status": "error", "error": error})


def init_sheet():
    """Initialize sheet with headers if empty"""
    service = get_service()

    # Check if headers exist
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A1:P1",
    ).execute()

    if not result.get("values"):
        # Add headers
        headers = [[
            "id", "created_at", "prompt", "category", "status",
            "job_id", "video_url", "duration", "resolution", "cost",
            "scheduled_at", "published_at", "later_id", "caption", "hashtags", "error"
        ]]

        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A1:P1",
            valueInputOption="RAW",
            body={"values": headers},
        ).execute()

        print("Sheet initialized with headers")


if __name__ == "__main__":
    # Test
    print("Testing sheets client...")
    rows = get_rows_by_status("pending")
    print(f"Found {len(rows)} pending rows")
