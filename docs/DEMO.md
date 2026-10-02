# SentinelAgent Demo Guide

## 1. Start Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts\migrate_schema.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 18080