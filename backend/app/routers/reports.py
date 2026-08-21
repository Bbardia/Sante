"""Reports router: JSON report + Excel export."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import require_roles
from app.services.reporting import build_report
from app.services.excel_export import build_excel

router = APIRouter(prefix="/reports", tags=["reports"])

_allowed = require_roles("admin", "manager", "salesman")

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("")
def get_report(
    type: Optional[str] = Query(None, alias="type"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_allowed),
) -> dict:
    """Return the full report as JSON."""
    return build_report(db, type or "Daily", start, end)


@router.get("/export.xlsx")
def export_xlsx(
    type: Optional[str] = Query(None, alias="type"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_allowed),
):
    """Return an Excel workbook as a downloadable attachment."""
    report = build_report(db, type or "Daily", start, end)
    xlsx_bytes = build_excel(report)
    return Response(
        content=xlsx_bytes,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": "attachment; filename=\"sante-report.xlsx\""},
    )
