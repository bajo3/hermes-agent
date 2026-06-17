from datetime import date, timedelta
from decimal import Decimal

from app import crud, models
from app.database import SessionLocal


CLIENTS = [
    "VAXA Fumigaciones",
    "Romero Impermeabilizaciones",
    "JD Automotores",
    "Autos Tandil",
]


def main() -> None:
    with SessionLocal() as db:
        created_clients = []
        for name in CLIENTS:
            client = crud.find_client_by_name(db, name) or crud.create(
                db,
                models.Client,
                {"name": name, "status": "activo", "notes": "Cliente de ejemplo"},
            )
            created_clients.append(client)

        for client in created_clients:
            project = crud.create(
                db,
                models.Project,
                {
                    "client_id": client.id,
                    "name": f"Web {client.name}",
                    "description": "Proyecto de ejemplo para Hermes",
                    "status": "en_progreso",
                    "priority": "media",
                    "price": Decimal("120000"),
                    "due_date": date.today() + timedelta(days=14),
                },
            )
            crud.create(
                db,
                models.Task,
                {
                    "title": f"Revisar pendientes de {client.name}",
                    "client_id": client.id,
                    "project_id": project.id,
                    "status": "pendiente",
                    "priority": "media",
                    "due_date": date.today() + timedelta(days=2),
                },
            )
            crud.create(
                db,
                models.FinanceEntry,
                {
                    "type": "ingreso",
                    "category": "web",
                    "client_id": client.id,
                    "project_id": project.id,
                    "amount": Decimal("60000"),
                    "description": f"Anticipo {client.name}",
                    "due_date": date.today() + timedelta(days=7),
                    "status": "pendiente",
                },
            )
    print("Seed data created.")


if __name__ == "__main__":
    main()

