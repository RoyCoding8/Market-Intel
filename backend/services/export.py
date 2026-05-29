"""Report export service — JSON, CSV, Markdown, PDF formats."""

from __future__ import annotations

import csv
import html
import io
import os
from datetime import datetime, timezone

from contracts.api import ExportFormat, ExportRequest, ExportResponse, IntelligenceReport


def export_report(report: IntelligenceReport, request: ExportRequest, job_id: str) -> ExportResponse:
    """Dispatch to the appropriate format exporter."""
    exporters = {
        ExportFormat.JSON: _export_json, ExportFormat.CSV: _export_csv,
        ExportFormat.MARKDOWN: _export_markdown, ExportFormat.PDF: _export_pdf,
    }
    return exporters[request.format](report, request, job_id)


def _export_json(report: IntelligenceReport, request: ExportRequest, job_id: str) -> ExportResponse:
    if request.include_raw_data:
        content = report.model_dump_json(indent=2)
    else:
        data = report.model_dump()
        if not request.include_citations:
            for f in data.get("findings", []):
                f.pop("citations", None)
        content = IntelligenceReport(**data).model_dump_json(indent=2)
    return ExportResponse(job_id=job_id, format=ExportFormat.JSON, content=content)


def _export_csv(report: IntelligenceReport, request: ExportRequest, job_id: str) -> ExportResponse:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "title", "category", "confidence", "impact", "recommendation", "sources"])
    for f in report.findings:
        sources = "; ".join(c.url for c in f.citations) if request.include_citations else ""
        writer.writerow([f.id, f.title, f.category, f.confidence.value, f.impact or "", f.recommendation or "", sources])
    return ExportResponse(job_id=job_id, format=ExportFormat.CSV, content=buf.getvalue())


def _export_markdown(report: IntelligenceReport, request: ExportRequest, job_id: str) -> ExportResponse:
    lines: list[str] = [
        f"# {report.title}", "",
        f"*Generated: {report.created_at.isoformat()}*", "",
        "## Executive Summary", "", report.executive_summary, "",
    ]
    if report.trend_analysis:
        lines += ["## Trend Analysis", "", report.trend_analysis, ""]
    lines += ["## Findings", "", "| ID | Title | Category | Confidence | Impact |",
              "|------|---------|----------|------------|--------|"]
    for f in report.findings:
        lines.append(f"| {f.id} | {f.title} | {f.category} | {f.confidence.value} | {f.impact or '-'} |")
    lines.append("")
    if request.include_citations:
        for f in report.findings:
            if f.citations:
                lines += [f"### {f.title}", "", f"*{f.summary}*", ""]
                if f.recommendation:
                    lines += [f"**Recommendation:** {f.recommendation}", ""]
                for c in f.citations:
                    quote = (c.quote or "")[:120]
                    lines.append(f"- [{c.title or c.url}]({c.url}) — \"{quote}...\"")
                lines.append("")
    if report.comparison_tables:
        lines += ["## Comparisons", ""]
        for table in report.comparison_tables:
            lines += [f"### {table.title}", ""]
            header = "| Dimension | " + " | ".join(table.competitor_ids) + " |"
            sep = "|---" * (len(table.competitor_ids) + 1) + "|"
            lines += [header, sep]
            for row in table.rows:
                vals = [row.values.get(cid, "-") for cid in table.competitor_ids]
                lines.append(f"| {row.dimension} | " + " | ".join(vals) + " |")
            lines.append("")
    if report.recommendations:
        lines += ["## Recommendations", ""]
        for i, r in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {r}")
        lines.append("")
    lines += ["---", f"*Sources: {report.total_sources} | Verifications: {report.verification_passes}*"]
    return ExportResponse(job_id=job_id, format=ExportFormat.MARKDOWN, content="\n".join(lines))


def _export_pdf(report: IntelligenceReport, request: ExportRequest, job_id: str) -> ExportResponse:
    """Generate a PDF using reportlab, falling back to HTML if unavailable."""
    # Sanitize job_id to prevent path traversal
    safe_id = "".join(c for c in job_id if c.isalnum() or c in "-_")[:64]
    if not safe_id:
        safe_id = "unknown"
    data_dir = os.path.join(".", "data", "exports")
    os.makedirs(data_dir, exist_ok=True)
    filename = f"report_{safe_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(data_dir, filename)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        story = [
            Paragraph(report.title, styles["Title"]),
            Spacer(1, 0.2 * inch),
            Paragraph(f"Generated: {report.created_at.strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
            Spacer(1, 0.3 * inch),
            Paragraph("Executive Summary", styles["Heading1"]),
            Paragraph(report.executive_summary, styles["Normal"]),
            Spacer(1, 0.2 * inch),
        ]

        if report.trend_analysis:
            story += [Paragraph("Trend Analysis", styles["Heading1"]),
                      Paragraph(report.trend_analysis, styles["Normal"]),
                      Spacer(1, 0.2 * inch)]

        story += [Paragraph("Findings", styles["Heading1"]), Spacer(1, 0.1 * inch)]

        if report.findings:
            data = [["ID", "Title", "Category", "Confidence", "Impact"]]
            for f in report.findings:
                data.append([f.id, f.title, f.category, f.confidence.value, f.impact or "-"])
            t = Table(data, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]))
            story += [t, Spacer(1, 0.2 * inch)]

        if report.recommendations:
            story.append(Paragraph("Recommendations", styles["Heading1"]))
            for i, r in enumerate(report.recommendations, 1):
                story.append(Paragraph(f"{i}. {r}", styles["Normal"]))
            story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph(
            f"Sources: {report.total_sources} | Verifications: {report.verification_passes}", styles["Normal"],
        ))
        doc.build(story)
    except ImportError:
        # reportlab not installed — return HTML content directly instead of
        # writing a misleading .pdf file that's actually HTML
        html_content = _build_html(report)
        return ExportResponse(
            job_id=job_id, format=ExportFormat.PDF,
            content=html_content, download_url=None,
        )

    return ExportResponse(job_id=job_id, format=ExportFormat.PDF, download_url=f"/data/exports/{filename}")


def _build_html(report: IntelligenceReport) -> str:
    """Fallback HTML report for when reportlab is not installed."""
    esc = html.escape
    lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        f"<title>{esc(report.title)}</title>",
        "<style>body{font-family:sans-serif;margin:40px;max-width:900px}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #ddd;padding:8px;text-align:left}",
        "th{background:#2563eb;color:white}</style></head><body>",
        f"<h1>{esc(report.title)}</h1>",
        f"<p><em>Generated: {esc(report.created_at.isoformat())}</em></p>",
        "<h2>Executive Summary</h2>",
        f"<p>{esc(report.executive_summary)}</p>",
    ]
    if report.trend_analysis:
        lines += ["<h2>Trend Analysis</h2>", f"<p>{esc(report.trend_analysis)}</p>"]
    if report.findings:
        lines.append("<h2>Findings</h2><table><tr><th>ID</th><th>Title</th><th>Category</th><th>Confidence</th><th>Impact</th></tr>")
        for f in report.findings:
            lines.append(f"<tr><td>{esc(f.id)}</td><td>{esc(f.title)}</td><td>{esc(f.category)}</td><td>{esc(f.confidence.value)}</td><td>{esc(f.impact or '-')}</td></tr>")
        lines.append("</table>")
    if report.recommendations:
        lines += ["<h2>Recommendations</h2><ol>"]
        for r in report.recommendations:
            lines.append(f"<li>{esc(r)}</li>")
        lines.append("</ol>")
    lines += [f"<hr><p>Sources: {report.total_sources} | Verifications: {report.verification_passes}</p>",
              "</body></html>"]
    return "\n".join(lines)
