# Windows Bridge

Carpeta reservada para el puente local de Windows.

Arquitectura esperada:

```text
WhatsApp -> Baileys Bridge -> FastAPI Hermes -> Windows Bridge -> PC Windows
```

El bridge de Baileys no ejecuta PowerShell ni acciones de escritorio. FastAPI llama a `BRIDGE_URL` con `BRIDGE_TOKEN` cuando recibe comandos como:

- `abrir carpeta VAXA`
- `crear carpeta VAXA`
- `nota VAXA revisar textos de la web`

