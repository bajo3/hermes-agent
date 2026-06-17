from html import escape

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app import crud
from app.config import get_settings
from app.database import get_db
from app.whatsapp import router as whatsapp_router
from app.routers import clients, finances, meetings, projects, reminders, tasks


settings = get_settings()
app = FastAPI(title="Hermes Secretario", version="0.1.0")

app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(meetings.router)
app.include_router(finances.router)
app.include_router(reminders.router)
app.include_router(whatsapp_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


def money(value) -> str:
    return f"${value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.get("/", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)):
    data = crud.dashboard_stats(db)
    task_items = "".join(
        f"<li><strong>{escape(task.title)}</strong><span>{escape(task.priority)} - {task.due_date or 'sin fecha'}</span></li>"
        for task in data["pending_tasks"]
    ) or "<li><span>Sin tareas pendientes</span></li>"
    meeting_items = "".join(
        f"<li><strong>{escape(meeting.title)}</strong><span>{meeting.datetime.strftime('%d/%m %H:%M')}</span></li>"
        for meeting in data["upcoming_meetings"]
    ) or "<li><span>Sin reuniones proximas</span></li>"
    charge_items = "".join(
        f"<li><strong>{escape(charge.description or 'Cobro pendiente')}</strong><span>{money(charge.amount)} - {charge.due_date or 'sin fecha'}</span></li>"
        for charge in data["pending_charges"]
    ) or "<li><span>Sin cobros pendientes</span></li>"

    return f"""
    <!doctype html>
    <html lang="es">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Hermes Secretario</title>
        <style>
          :root {{
            color-scheme: light;
            --bg: #f5f7fb;
            --ink: #172033;
            --muted: #647084;
            --line: #dfe5ee;
            --panel: #ffffff;
            --accent: #0f766e;
            --warn: #b45309;
          }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: var(--bg);
            color: var(--ink);
          }}
          header {{
            padding: 28px clamp(18px, 4vw, 48px) 18px;
            border-bottom: 1px solid var(--line);
            background: #fff;
          }}
          h1 {{ margin: 0 0 6px; font-size: clamp(28px, 5vw, 44px); letter-spacing: 0; }}
          p {{ margin: 0; color: var(--muted); }}
          main {{ padding: 24px clamp(18px, 4vw, 48px) 48px; }}
          .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 22px;
          }}
          .metric, section {{
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(16, 24, 40, .05);
          }}
          .metric {{ padding: 16px; }}
          .metric span {{ display: block; color: var(--muted); font-size: 13px; }}
          .metric strong {{ display: block; margin-top: 8px; font-size: 24px; }}
          .metric.profit strong {{ color: var(--accent); }}
          .boards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
          }}
          section {{ padding: 16px; }}
          h2 {{ margin: 0 0 12px; font-size: 18px; letter-spacing: 0; }}
          ul {{ list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }}
          li {{
            min-height: 48px;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
          }}
          li strong {{ overflow-wrap: anywhere; }}
          li span {{ color: var(--muted); font-size: 13px; text-align: right; }}
          @media (max-width: 640px) {{
            li {{ align-items: flex-start; flex-direction: column; }}
            li span {{ text-align: left; }}
          }}
        </style>
      </head>
      <body>
        <header>
          <h1>Hermes Secretario</h1>
          <p>Panel operativo para tareas, clientes, reuniones y finanzas.</p>
        </header>
        <main>
          <div class="metrics">
            <div class="metric"><span>Ingresos del mes</span><strong>{money(data["income_month"])}</strong></div>
            <div class="metric"><span>Gastos del mes</span><strong>{money(data["expenses_month"])}</strong></div>
            <div class="metric profit"><span>Ganancia estimada</span><strong>{money(data["estimated_profit"])}</strong></div>
            <div class="metric"><span>Proyectos activos</span><strong>{data["active_projects_count"]}</strong></div>
            <div class="metric"><span>Clientes activos</span><strong>{data["active_clients_count"]}</strong></div>
          </div>
          <div class="boards">
            <section><h2>Tareas pendientes</h2><ul>{task_items}</ul></section>
            <section><h2>Reuniones proximas</h2><ul>{meeting_items}</ul></section>
            <section><h2>Cobros pendientes</h2><ul>{charge_items}</ul></section>
          </div>
        </main>
      </body>
    </html>
    """
