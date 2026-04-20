# Preparacion para GitHub y Streamlit Cloud

## Archivos principales

- `app.py`: aplicacion Streamlit.
- `requirements.txt`: dependencias Python que instala Streamlit Cloud.
- `runtime.txt`: version de Python recomendada.
- `.gitignore`: evita subir bases locales, backups, excels, entorno virtual y secretos.
- `.streamlit/secrets.toml.example`: ejemplo de secretos para configurar en Streamlit Cloud.

## Importante sobre la base de datos

La aplicacion ya no usa una ruta fija como `C:\Users\Fvigo\Documents\ControlHavanna`.
Por defecto usa `database/schema.db` dentro del proyecto.

Para varios usuarios en la web, lo recomendable es usar una base externa persistente,
por ejemplo PostgreSQL. En ese caso IT debe configurar en Streamlit Cloud el secreto:

```toml
DATABASE_URL = "postgresql://usuario:password@host:5432/base"
```

Si no se configura `DATABASE_URL`, Streamlit Cloud puede crear una base SQLite local,
pero no es lo ideal para datos permanentes ni trabajo multiusuario.

## Usuario administrador inicial

Si la base esta vacia, la aplicacion puede crear un primer usuario administrador usando
estos secretos:

```toml
CONTROLHAVANNA_ADMIN_USER = "admin"
CONTROLHAVANNA_ADMIN_PASSWORD = "cambiar-esta-clave"
CONTROLHAVANNA_ADMIN_NAME = "Administrador del sistema"
```

Ese usuario queda obligado a cambiar la contrasena en el primer ingreso.

## Pasos sugeridos

1. Crear repositorio en GitHub.
2. Subir el codigo sin `database/schema.db`, sin `database/backups/`, sin `.venv/` y sin archivos Excel.
3. Crear la app en Streamlit Cloud apuntando al repositorio y a `app.py`.
4. Cargar los secretos en Streamlit Cloud.
5. Definir una base de datos persistente antes de usarlo con varios usuarios reales.

