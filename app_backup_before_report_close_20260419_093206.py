import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.db import Base, SessionLocal, engine
from database.models import Articulo, Categoria, Combo, Local, ReporteVentaTurno, User
from services.auth import authenticate_user, create_user, delete_user, reset_user_password, update_user

st.set_page_config(page_title="ControlHavanna", layout="wide")

Base.metadata.create_all(bind=engine)

CATEGORY_COLORS = {
    "CAFETERA": "#FFF200",
    "CAFETERIA": "#FFF200",
    "BATIDOS Y YOGURES": "#A9D0F5",
    "PRODUCTO": "#90EE90",
    "HORNO": "#FFA07A",
    "PANIFICACION Y TORTAS": "#FF0000",
    "PANIFICACIÓN Y TORTAS": "#FF0000",
    "ALMUERZO": "#4A4A4A",
    "PRODUCTOS MIXTOS": "#283593",
    "AGUAS Y GASEOSAS": "#FF00FF",
    "ACOMPAÑAMIENTO": "#D4AC0D",
    "OTROS": "#FFFFFF",
}


def get_text_color(bg: str) -> str:
    bg = bg.lstrip("#")
    r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return "#FFFFFF" if lum < 160 else "#111111"


def render_header() -> None:
    st.markdown(
        """
        <style>
        .banner {
            background: #FFD700;
            color: #C00000;
            text-align: center;
            font-size: 26px;
            font-weight: bold;
            height: 80px;
            line-height: 80px;
            margin-top: -1rem;
            margin-bottom: 1.25rem;
        }

        .card {
            width: 100%;
            height: 192px;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            font-weight: bold;
        }

        .ventas-note {
            background: #f7f7f7;
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 14px;
        }

        /* ESTILO BASE: TODOS LOS BOTONES NORMALES EN BLANCO */
        div[data-testid="stButton"] > button {
            background: #FFFFFF !important;
            color: #31333F !important;
            font-weight: 400 !important;
            border: 1px solid rgba(49, 51, 63, 0.2) !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }

        /* SOLO PRIMER BOTON: VOLVER ATRAS */
        div[data-testid="stButton"]:nth-of-type(1) > button {
            background: #198754 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            width: 180px !important;
            height: 50px !important;
            border: 1px solid #146C43 !important;
        }

        /* SOLO SEGUNDO BOTON: CERRAR REPORTE */
        div[data-testid="stButton"]:nth-of-type(2) > button {
            background: #FF4D4D !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            width: 180px !important;
            height: 50px !important;
            border: 1px solid #D93636 !important;
        }

        .confirm {
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border: 2px solid #ccc;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .counter-card-style + div[data-testid="stButton"] > button {
            height: 192px !important;
            min-height: 192px !important;
            width: 120px !important;
            min-width: 120px !important;
            max-width: 120px !important;
            border-radius: 8px !important;
            padding: 10px !important;
            white-space: pre-line !important;
            text-align: center !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }

        .counter-card-style + div[data-testid="stButton"] {
            display: flex !important;
            justify-content: center !important;
        }

        .counter-card-style + div[data-testid="stButton"] > button p {
            white-space: pre-line !important;
            font-size: 15px !important;
            line-height: 1.35 !important;
        }

        .counter-card-style + div[data-testid="stButton"] > button strong {
            font-size: 20px !important;
            font-weight: 800 !important;
        }
        </style>

        <div class="banner">
            SISTEMA DE CONTROL DE FACTURACION HAVANNA
        </div>
        """,
        unsafe_allow_html=True,
    )


def init() -> None:
    if "auth" not in st.session_state:
        st.session_state.auth = False
        st.session_state.username = None
        st.session_state.counts = {}
        st.session_state.hist = []
        st.session_state.confirm = False
        st.session_state.require_hora_cierre = False
        st.session_state.page = "Inicio"
        st.session_state.home_menu = "Inicio"
        st.session_state.config_menu = "Seleccionar"
        st.session_state.home_action = None
        st.session_state.action_success = None


def login() -> None:
    st.title("Ingreso al sistema")

    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")

    if st.button("Ingresar"):
        db = SessionLocal()
        try:
            user = authenticate_user(db, u, p)
        finally:
            db.close()

        if user:
            st.session_state.auth = True
            st.session_state.username = user.username
            st.rerun()
        else:
            st.error("Credenciales incorrectas")


FALLBACK_COLORS = [
    "#FFF200",
    "#A9D0F5",
    "#90EE90",
    "#FFA07A",
    "#FF0000",
    "#4A4A4A",
    "#283593",
    "#FF00FF",
    "#D4AC0D",
    "#FFFFFF",
    "#B8E986",
    "#F8BBD0",
]


def counter_key(item_type: str, codigo: int) -> str:
    return f"{item_type}:{codigo}"


def get_item_color(item_type: str, codigo: int, descripcion: str) -> str:
    if item_type == "cat":
        color = CATEGORY_COLORS.get(descripcion.upper())
        if color:
            return color
    return FALLBACK_COLORS[(int(codigo) - 1) % len(FALLBACK_COLORS)]


def get_group_color(item_type: str, item, index: int) -> str:
    if item_type == "cat":
        color = CATEGORY_COLORS.get(item.descripcion.upper())
        if color:
            return color
    return FALLBACK_COLORS[index % len(FALLBACK_COLORS)]


def get_combo_category_changes(combo: Combo) -> list[tuple[str, int]]:
    changes = []
    for number in (1, 2, 3, 4):
        categoria = getattr(combo, f"categ{number}")
        cantidad = getattr(combo, f"qcateg{number}")
        if categoria is not None and cantidad > 0:
            changes.append((counter_key("cat", int(categoria)), int(cantidad)))
    return changes


def apply_counter_click(item_type: str, item, key: str) -> None:
    st.session_state.counts[key] = st.session_state.counts.get(key, 0) + 1

    if item_type == "combo":
        category_changes = get_combo_category_changes(item)
        for category_key, quantity in category_changes:
            st.session_state.counts[category_key] = (
                st.session_state.counts.get(category_key, 0) + quantity
            )
        st.session_state.hist.append(
            {
                "type": "combo",
                "key": key,
                "categories": category_changes,
            }
        )
    else:
        st.session_state.hist.append(
            {
                "type": "cat",
                "key": key,
            }
        )


def undo_last_counter_click() -> None:
    if not st.session_state.hist:
        return

    last_action = st.session_state.hist.pop()

    if isinstance(last_action, int):
        key = counter_key("cat", last_action)
        if st.session_state.counts.get(key, 0) > 0:
            st.session_state.counts[key] -= 1
        return

    if isinstance(last_action, str):
        if st.session_state.counts.get(last_action, 0) > 0:
            st.session_state.counts[last_action] -= 1
        return

    if last_action.get("type") == "combo":
        combo_key = last_action["key"]
        if st.session_state.counts.get(combo_key, 0) > 0:
            st.session_state.counts[combo_key] -= 1

        for category_key, quantity in last_action["categories"]:
            current = st.session_state.counts.get(category_key, 0)
            st.session_state.counts[category_key] = max(0, current - quantity)
        return

    key = last_action.get("key")
    if key and st.session_state.counts.get(key, 0) > 0:
        st.session_state.counts[key] -= 1


def render_counter_group(title: str, item_type: str, items: list, columns_per_row: int = 6) -> None:
    with st.container(border=True):
        st.subheader(title)

        if not items:
            st.info(f"No hay {title.lower()} cargados.")
            return

        for start in range(0, len(items), columns_per_row):
            row_items = items[start : start + columns_per_row]
            cols = st.columns(columns_per_row)

            for offset, (col, item) in enumerate(zip(cols, row_items)):
                item_index = start + offset
                key = counter_key(item_type, item.codigo)
                old_category_key = item.codigo if item_type == "cat" else None
                if old_category_key is not None and old_category_key in st.session_state.counts:
                    st.session_state.counts.setdefault(
                        key,
                        st.session_state.counts[old_category_key],
                    )
                else:
                    st.session_state.counts.setdefault(key, 0)

                bg = get_group_color(item_type, item, item_index)
                txt = get_text_color(bg)
                count = st.session_state.counts[key]
                button_key = f"sumar_{item_type}_{item.codigo}"
                border = (
                    "1px solid #D0D0D0"
                    if bg.upper() == "#FFFFFF" or item.descripcion.upper() == "OTROS"
                    else "none"
                )

                with col:
                    st.markdown(
                        f"""
                        <style>
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}),
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) {{
                            display: none !important;
                        }}

                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] button,
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container button,
                        .st-key-{button_key} button,
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] > button {{
                            background: {bg} !important;
                            color: {txt} !important;
                            border: {border} !important;
                            height: 192px !important;
                            min-height: 192px !important;
                            width: 120px !important;
                            min-width: 120px !important;
                            max-width: 120px !important;
                            border-radius: 8px !important;
                            padding: 10px !important;
                            white-space: pre-line !important;
                            text-align: center !important;
                            font-weight: 700 !important;
                            box-shadow: none !important;
                        }}
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] div[data-testid="stButton"],
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container div[data-testid="stButton"],
                        .st-key-{button_key},
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] {{
                            display: flex !important;
                            justify-content: center !important;
                        }}
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] button p,
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container button p,
                        .st-key-{button_key} button p,
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] > button p {{
                            color: {txt} !important;
                            white-space: pre-line !important;
                            font-size: 15px !important;
                            line-height: 1.35 !important;
                        }}
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] button strong,
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container button strong,
                        .st-key-{button_key} button strong,
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] > button strong {{
                            color: {txt} !important;
                            font-size: 20px !important;
                            font-weight: 800 !important;
                        }}
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] button:hover,
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container button:hover,
                        .st-key-{button_key} button:hover,
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] > button:hover {{
                            filter: brightness(0.96);
                        }}
                        div[data-testid="stElementContainer"]:has(.counter-card-{item_type}-{item.codigo}) + div[data-testid="stElementContainer"] button:active,
                        div.element-container:has(.counter-card-{item_type}-{item.codigo}) + div.element-container button:active,
                        .st-key-{button_key} button:active,
                        .counter-card-{item_type}-{item.codigo} + div[data-testid="stButton"] > button:active {{
                            filter: brightness(0.92);
                        }}
                        </style>
                        <span class="counter-card-style counter-card-{item_type}-{item.codigo}"></span>
                        """,
                        unsafe_allow_html=True,
                    )

                    label = f"{item.descripcion}\n\n**{count}**"
                    if st.button(label, key=button_key):
                        apply_counter_click(item_type, item, key)
                        st.rerun()


def ventas() -> None:
    st.title("Ventas por turno")

    db = SessionLocal()
    try:
        cats = list(db.scalars(select(Categoria).order_by(Categoria.codigo)).all())
        combos_list = list(db.scalars(select(Combo).order_by(Combo.codigo)).all())
        locs = list(db.scalars(select(Local).order_by(Local.descripcion)).all())
    finally:
        db.close()

    st.markdown(
        """
        <style>
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Datos del Turno")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        local = st.selectbox("Locales", [l.descripcion for l in locs])
    with c2:
        turno = st.number_input("Turno", min_value=1, step=1)
    with c3:
        hi = st.time_input("Hora Inicio (video)")
    with c4:
        hc = st.time_input("Hora Cierre (video)", value=None, key="hora_cierre_video")

    if hc is not None:
        st.session_state.require_hora_cierre = False

    enc = st.text_input("Encargado", max_chars=30)

    st.divider()

    st.markdown(
        '<div class="ventas-note">Haga clic con el mouse sobre cada categoria o combo. Cada clic suma 1 item al contador correspondiente.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        div[data-testid="stElementContainer"]:has(.volver-atras-marker),
        div.element-container:has(.volver-atras-marker),
        div[data-testid="stElementContainer"]:has(.cerrar-reporte-marker),
        div.element-container:has(.cerrar-reporte-marker) {
            display: none !important;
        }

        div[data-testid="stElementContainer"]:has(.volver-atras-marker) + div[data-testid="stElementContainer"] button,
        div.element-container:has(.volver-atras-marker) + div.element-container button {
            background: #198754 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            width: 180px !important;
            height: 50px !important;
            border: 1px solid #146C43 !important;
            border-radius: 8px !important;
        }

        div[data-testid="stElementContainer"]:has(.cerrar-reporte-marker) + div[data-testid="stElementContainer"] button,
        div.element-container:has(.cerrar-reporte-marker) + div.element-container button {
            background: #FF4D4D !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            width: 180px !important;
            height: 50px !important;
            border: 1px solid #D93636 !important;
            border-radius: 8px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col_a, col_b, _ = st.columns([1, 1, 6])

    with col_a:
        st.markdown('<span class="volver-atras-marker"></span>', unsafe_allow_html=True)
        volver = st.button("VOLVER ATRAS", key="volver_atras_ventas")

    with col_b:
        st.markdown('<span class="cerrar-reporte-marker"></span>', unsafe_allow_html=True)
        cerrar = st.button("CERRAR REPORTE", key="cerrar_reporte_ventas")

    if volver:
        undo_last_counter_click()
        st.rerun()

    if cerrar:
        if hc is None:
            st.session_state.require_hora_cierre = True
        else:
            st.session_state.confirm = True
            st.rerun()

    if st.session_state.require_hora_cierre and hc is None:
        st.warning("Debe completar Hora Cierre (video) para cerrar el reporte.")

    if st.session_state.confirm:
        _, centro, _ = st.columns([2, 4, 2])
        with centro:
            st.markdown(
                """
                <div class="confirm">
                    Esta por cerrar el reporte.<br>
                    Esta accion no puede ser vuelta atras.<br><br>
                    ¿Está seguro?
                </div>
                """,
                unsafe_allow_html=True,
            )

            s, n = st.columns(2)

            with s:
                if st.button("SI"):
                    st.success("Guardado (simulado)")
                    st.session_state.confirm = False
                    st.rerun()

            with n:
                if st.button("NO"):
                    st.session_state.confirm = False
                    st.rerun()

    st.divider()

    render_counter_group("Categorias", "cat", cats)
    render_counter_group("Combos", "combo", combos_list)


def inicio() -> None:
    st.title("Inicio")
    st.write("Seleccione una opcion del menu.")

    opciones = [
        "Inicio",
        "Ventas por turno",
        "Configuracion",
        "Categorias",
        "Articulos",
        "Locales",
        "Usuarios",
        "Reportes cerrados",
    ]

    seleccion = st.selectbox(
        "Menu Inicio",
        opciones,
        index=opciones.index(st.session_state.home_menu)
        if st.session_state.home_menu in opciones
        else 0,
    )

    st.session_state.home_menu = seleccion

    if seleccion == "Inicio":
        st.info("Seleccione una opcion del menu desplegable.")
        return

    if seleccion == "Ventas por turno":
        if st.button("Ingresar a Ventas por turno"):
            st.session_state.page = "Ventas por turno"
            st.rerun()
        return

    if seleccion == "Reportes cerrados":
        if st.button("Ver reportes cerrados"):
            st.session_state.page = "Reportes cerrados"
            st.rerun()
        return

    if seleccion == "Configuracion":
        opciones_config = ["Seleccionar", "Combos"]
        config = st.selectbox(
            "Configuracion",
            opciones_config,
            index=opciones_config.index(st.session_state.config_menu)
            if st.session_state.config_menu in opciones_config
            else 0,
        )
        st.session_state.config_menu = config

        if config == "Seleccionar":
            st.info("Seleccione una opcion de configuracion.")
            return

        if config == "Combos":
            st.subheader("Combos")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Crear", key="crear_Combos_config"):
                    st.session_state.page = "Combos"
                    st.session_state.home_action = "Crear"
                    st.rerun()
            with c2:
                if st.button("Modificar", key="modificar_Combos_config"):
                    st.session_state.page = "Combos"
                    st.session_state.home_action = "Modificar"
                    st.rerun()
            with c3:
                if st.button("Eliminar", key="eliminar_Combos_config"):
                    st.session_state.page = "Combos"
                    st.session_state.home_action = "Eliminar"
                    st.rerun()
            return

    st.subheader(seleccion)
    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("Crear", key=f"crear_{seleccion}"):
            st.session_state.page = seleccion
            st.session_state.home_action = "Crear"
            st.rerun()

    with c2:
        if st.button("Modificar", key=f"modificar_{seleccion}"):
            st.session_state.page = seleccion
            st.session_state.home_action = "Modificar"
            st.rerun()

    with c3:
        if st.button("Eliminar", key=f"eliminar_{seleccion}"):
            st.session_state.page = seleccion
            st.session_state.home_action = "Eliminar"
            st.rerun()


def render_action_header(nombre: str) -> None:
    accion = st.session_state.get("home_action")
    if accion:
        st.subheader(f"{accion} {nombre}")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Crear", key=f"crear_pagina_{nombre}"):
                st.session_state.home_action = "Crear"
                st.rerun()
        with c2:
            if st.button("Modificar", key=f"modificar_pagina_{nombre}"):
                st.session_state.home_action = "Modificar"
                st.rerun()
        with c3:
            if st.button("Eliminar", key=f"eliminar_pagina_{nombre}"):
                st.session_state.home_action = "Eliminar"
                st.rerun()


def reset_action() -> None:
    st.session_state.home_action = None


def finish_action(message: str) -> None:
    st.session_state.action_success = message
    reset_action()
    st.rerun()


def show_action_success() -> None:
    message = st.session_state.get("action_success")
    if message:
        st.success(message)
        st.session_state.action_success = None


def categorias() -> None:
    st.title("Categorias")
    render_action_header("Categorias")
    show_action_success()

    db = SessionLocal()
    try:
        cats = list(db.scalars(select(Categoria).order_by(Categoria.codigo)).all())

        if st.session_state.get("home_action") == "Crear":
            with st.form("crear_categoria"):
                codigo = st.number_input("Codigo", min_value=1, step=1)
                descripcion = st.text_input("Descripcion", max_chars=150)
                c1, c2 = st.columns(2)
                with c1:
                    guardar = st.form_submit_button("Guardar")
                with c2:
                    salir = st.form_submit_button("Salir")

            if salir:
                reset_action()
                st.rerun()
            if guardar:
                if not descripcion.strip():
                    st.error("Debe ingresar una descripcion.")
                else:
                    try:
                        db.add(Categoria(codigo=int(codigo), descripcion=descripcion.strip()))
                        db.commit()
                        finish_action("Categoria creada correctamente.")
                    except IntegrityError:
                        db.rollback()
                        st.error("No se pudo crear la categoria. Revise que el codigo y la descripcion no existan.")

        elif st.session_state.get("home_action") == "Modificar":
            if not cats:
                st.warning("No hay categorias para modificar.")
            else:
                categoria = st.selectbox(
                    "Categoria a modificar",
                    cats,
                    format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                )
                with st.form("modificar_categoria"):
                    st.number_input("Codigo", value=int(categoria.codigo), disabled=True)
                    descripcion = st.text_input(
                        "Descripcion",
                        value=categoria.descripcion,
                        max_chars=150,
                    )
                    guardar = st.form_submit_button("Guardar")

                if guardar:
                    if not descripcion.strip():
                        st.error("Debe ingresar una descripcion.")
                    else:
                        try:
                            categoria_db = db.get(Categoria, int(categoria.codigo))
                            if categoria_db is None:
                                st.error("Categoria no encontrada.")
                                return
                            categoria_db.descripcion = descripcion.strip()
                            db.commit()
                            finish_action("Categoria modificada correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo modificar la categoria. Revise que la descripcion no exista.")

        elif st.session_state.get("home_action") == "Eliminar":
            if not cats:
                st.warning("No hay categorias para eliminar.")
            else:
                categoria = st.selectbox(
                    "Categoria a eliminar",
                    cats,
                    format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                )
                st.warning(f"Se esta eliminando la categoria: {categoria.codigo} - {categoria.descripcion}")
                c1, c2 = st.columns(2)

                with c1:
                    if st.button("NO"):
                        reset_action()
                        st.rerun()

                with c2:
                    if st.button("SI"):
                        articulos_asociados = db.scalar(
                            select(Articulo.codigo)
                            .where(Articulo.categoria_codigo == categoria.codigo)
                            .limit(1)
                        )
                        if articulos_asociados is not None:
                            st.error("No se puede eliminar la categoria porque tiene articulos asociados.")
                        else:
                            try:
                                categoria_db = db.get(Categoria, int(categoria.codigo))
                                if categoria_db is None:
                                    st.error("Categoria no encontrada.")
                                    return
                                db.delete(categoria_db)
                                db.commit()
                                finish_action("Categoria eliminada correctamente.")
                            except IntegrityError:
                                db.rollback()
                                st.error("No se pudo eliminar la categoria.")
    finally:
        db.close()

    st.dataframe(
        [{"Codigo": c.codigo, "Descripcion": c.descripcion} for c in cats],
        use_container_width=True,
        hide_index=True,
    )


def articulos() -> None:
    st.title("Articulos")
    render_action_header("Articulos")
    show_action_success()

    db = SessionLocal()
    try:
        arts = list(db.scalars(select(Articulo).order_by(Articulo.codigo)).all())
        cats = list(db.scalars(select(Categoria).order_by(Categoria.codigo)).all())
        combos_list = list(db.scalars(select(Combo).order_by(Combo.codigo)).all())

        if st.session_state.get("home_action") == "Crear":
            if not cats:
                st.error("Debe existir al menos una categoria antes de crear articulos.")
            else:
                codigo = st.number_input("Codigo", min_value=1, step=1, key="crear_articulo_codigo")
                nombre = st.text_input("Nombre", max_chars=200, key="crear_articulo_nombre")
                combo_opcion = st.selectbox("combo?", ["no", "si"], index=0, key="crear_articulo_es_combo")
                categoria = None
                combo = None
                if combo_opcion == "no":
                    categoria = st.selectbox(
                        "Categoria",
                        cats,
                        format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                        key="crear_articulo_categoria",
                    )
                else:
                    if combos_list:
                        combo = st.selectbox(
                            "combos",
                            combos_list,
                            format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                            key="crear_articulo_combo",
                        )
                    else:
                        st.error("No hay combos cargados para seleccionar.")

                c1, c2 = st.columns(2)
                with c1:
                    guardar = st.button("Guardar", key="guardar_crear_articulo")
                with c2:
                    salir = st.button("Salir", key="salir_crear_articulo")

                if salir:
                    reset_action()
                    st.rerun()
                if guardar:
                    if not nombre.strip():
                        st.error("Debe ingresar un nombre.")
                    elif combo_opcion == "no" and categoria is None:
                        st.error("Debe seleccionar una categoria.")
                    elif combo_opcion == "si" and combo is None:
                        st.error("Debe seleccionar un combo.")
                    else:
                        try:
                            db.add(
                                Articulo(
                                    codigo=int(codigo),
                                    nombre=nombre.strip(),
                                    categoria_codigo=(
                                        int(categoria.codigo) if combo_opcion == "no" else None
                                    ),
                                    es_combo=combo_opcion == "si",
                                    combo_codigo=int(combo.codigo) if combo_opcion == "si" else None,
                                )
                            )
                            db.commit()
                            finish_action("Articulo creado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo crear el articulo. Revise que el codigo no exista.")

        elif st.session_state.get("home_action") == "Modificar":
            if not arts:
                st.warning("No hay articulos para modificar.")
            elif not cats:
                st.error("Debe existir al menos una categoria.")
            else:
                articulo = st.selectbox(
                    "Articulo a modificar",
                    arts,
                    format_func=lambda a: f"{a.codigo} - {a.nombre}",
                )
                categoria_actual = next(
                    (i for i, c in enumerate(cats) if c.codigo == articulo.categoria_codigo),
                    0,
                )
                st.number_input(
                    "Codigo",
                    value=int(articulo.codigo),
                    disabled=True,
                    key=f"modificar_articulo_codigo_{articulo.codigo}",
                )
                nombre = st.text_input(
                    "Nombre",
                    value=articulo.nombre,
                    max_chars=200,
                    key=f"modificar_articulo_nombre_{articulo.codigo}",
                )
                combo_opcion = st.selectbox(
                    "combo?",
                    ["no", "si"],
                    index=1 if articulo.es_combo else 0,
                    key=f"modificar_articulo_es_combo_{articulo.codigo}",
                )
                categoria = None
                combo = None
                if combo_opcion == "no":
                    categoria = st.selectbox(
                        "Categoria",
                        cats,
                        index=categoria_actual,
                        format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                        key=f"modificar_articulo_categoria_{articulo.codigo}",
                    )
                else:
                    if combos_list:
                        combo_actual = next(
                            (i for i, c in enumerate(combos_list) if c.codigo == articulo.combo_codigo),
                            0,
                        )
                        combo = st.selectbox(
                            "combos",
                            combos_list,
                            index=combo_actual,
                            format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                            key=f"modificar_articulo_combo_{articulo.codigo}",
                        )
                    else:
                        st.error("No hay combos cargados para seleccionar.")

                guardar = st.button("Guardar", key=f"guardar_modificar_articulo_{articulo.codigo}")
                if guardar:
                    if not nombre.strip():
                        st.error("Debe ingresar un nombre.")
                    elif combo_opcion == "no" and categoria is None:
                        st.error("Debe seleccionar una categoria.")
                    elif combo_opcion == "si" and combo is None:
                        st.error("Debe seleccionar un combo.")
                    else:
                        try:
                            articulo_db = db.get(Articulo, int(articulo.codigo))
                            if articulo_db is None:
                                st.error("Articulo no encontrado.")
                                return
                            articulo_db.nombre = nombre.strip()
                            articulo_db.categoria_codigo = (
                                int(categoria.codigo) if combo_opcion == "no" else None
                            )
                            articulo_db.es_combo = combo_opcion == "si"
                            articulo_db.combo_codigo = (
                                int(combo.codigo) if combo_opcion == "si" else None
                            )
                            db.commit()
                            finish_action("Articulo modificado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo modificar el articulo.")

        elif st.session_state.get("home_action") == "Eliminar":
            if not arts:
                st.warning("No hay articulos para eliminar.")
            else:
                articulo = st.selectbox(
                    "Articulo a eliminar",
                    arts,
                    format_func=lambda a: f"{a.codigo} - {a.nombre}",
                )
                st.warning(f"Se esta eliminando el articulo: {articulo.codigo} - {articulo.nombre}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("NO"):
                        reset_action()
                        st.rerun()
                with c2:
                    if st.button("SI"):
                        try:
                            articulo_db = db.get(Articulo, int(articulo.codigo))
                            if articulo_db is None:
                                st.error("Articulo no encontrado.")
                                return
                            db.delete(articulo_db)
                            db.commit()
                            finish_action("Articulo eliminado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo eliminar el articulo.")
    finally:
        db.close()

    st.dataframe(
        [
            {
                "Codigo": a.codigo,
                "Nombre": a.nombre,
                "Categoria": a.categoria_codigo,
                "combo?": "si" if a.es_combo else "no",
                "combos": a.combo_codigo if a.es_combo else "",
            }
            for a in arts
        ],
        use_container_width=True,
        hide_index=True,
    )


def locales() -> None:
    st.title("Locales")
    render_action_header("Locales")
    show_action_success()

    db = SessionLocal()
    try:
        locs = list(db.scalars(select(Local).order_by(Local.codigo)).all())

        if st.session_state.get("home_action") == "Crear":
            with st.form("crear_local"):
                codigo = st.number_input("Codigo", min_value=1, step=1)
                descripcion = st.text_input("Descripcion", max_chars=150)
                c1, c2 = st.columns(2)
                with c1:
                    guardar = st.form_submit_button("Guardar")
                with c2:
                    salir = st.form_submit_button("Salir")

            if salir:
                reset_action()
                st.rerun()
            if guardar:
                if not descripcion.strip():
                    st.error("Debe ingresar una descripcion.")
                else:
                    try:
                        db.add(Local(codigo=int(codigo), descripcion=descripcion.strip()))
                        db.commit()
                        finish_action("Local creado correctamente.")
                    except IntegrityError:
                        db.rollback()
                        st.error("No se pudo crear el local. Revise que el codigo y la descripcion no existan.")

        elif st.session_state.get("home_action") == "Modificar":
            if not locs:
                st.warning("No hay locales para modificar.")
            else:
                local = st.selectbox(
                    "Local a modificar",
                    locs,
                    format_func=lambda l: f"{l.codigo} - {l.descripcion}",
                )
                with st.form("modificar_local"):
                    st.number_input("Codigo", value=int(local.codigo), disabled=True)
                    descripcion = st.text_input(
                        "Descripcion",
                        value=local.descripcion,
                        max_chars=150,
                    )
                    guardar = st.form_submit_button("Guardar")

                if guardar:
                    if not descripcion.strip():
                        st.error("Debe ingresar una descripcion.")
                    else:
                        try:
                            local_db = db.get(Local, int(local.codigo))
                            if local_db is None:
                                st.error("Local no encontrado.")
                                return
                            local_db.descripcion = descripcion.strip()
                            db.commit()
                            finish_action("Local modificado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo modificar el local. Revise que la descripcion no exista.")

        elif st.session_state.get("home_action") == "Eliminar":
            if not locs:
                st.warning("No hay locales para eliminar.")
            else:
                local = st.selectbox(
                    "Local a eliminar",
                    locs,
                    format_func=lambda l: f"{l.codigo} - {l.descripcion}",
                )
                st.warning(f"Se esta eliminando el local: {local.codigo} - {local.descripcion}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("NO"):
                        reset_action()
                        st.rerun()
                with c2:
                    if st.button("SI"):
                        try:
                            local_db = db.get(Local, int(local.codigo))
                            if local_db is None:
                                st.error("Local no encontrado.")
                                return
                            db.delete(local_db)
                            db.commit()
                            finish_action("Local eliminado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo eliminar el local.")
    finally:
        db.close()

    st.dataframe(
        [{"Codigo": l.codigo, "Descripcion": l.descripcion} for l in locs],
        use_container_width=True,
        hide_index=True,
    )


def usuarios() -> None:
    st.title("Usuarios")
    render_action_header("Usuarios")
    show_action_success()

    db = SessionLocal()
    try:
        users = list(db.scalars(select(User).order_by(User.username)).all())

        if st.session_state.get("home_action") == "Crear":
            with st.form("crear_usuario"):
                username = st.text_input("Usuario", max_chars=50)
                full_name = st.text_input("Nombre completo", max_chars=120)
                temporary_password = st.text_input("Contrasena temporal", type="password")
                role = st.selectbox("Rol", ["user", "admin"])
                is_active = st.checkbox("Activo", value=True)
                c1, c2 = st.columns(2)
                with c1:
                    guardar = st.form_submit_button("Guardar")
                with c2:
                    salir = st.form_submit_button("Salir")

            if salir:
                reset_action()
                st.rerun()
            if guardar:
                if not username.strip() or not temporary_password:
                    st.error("Debe ingresar usuario y contrasena temporal.")
                else:
                    try:
                        create_user(
                            db,
                            username.strip(),
                            full_name.strip(),
                            temporary_password,
                            role,
                            is_active,
                        )
                        finish_action("Usuario creado correctamente.")
                    except ValueError as exc:
                        st.error(str(exc))
                    except IntegrityError:
                        db.rollback()
                        st.error("No se pudo crear el usuario.")

        elif st.session_state.get("home_action") == "Modificar":
            if not users:
                st.warning("No hay usuarios para modificar.")
            else:
                user = st.selectbox(
                    "Usuario a modificar",
                    users,
                    format_func=lambda u: f"{u.username} - {u.full_name}",
                )
                role_options = ["user", "admin"]
                role_index = role_options.index(user.role) if user.role in role_options else 0
                with st.form("modificar_usuario"):
                    st.text_input("Usuario", value=user.username, disabled=True)
                    full_name = st.text_input("Nombre completo", value=user.full_name, max_chars=120)
                    role = st.selectbox("Rol", role_options, index=role_index)
                    is_active = st.checkbox("Activo", value=user.is_active)
                    new_password = st.text_input(
                        "Nueva contrasena temporal (opcional)",
                        type="password",
                    )
                    guardar = st.form_submit_button("Guardar")

                if guardar:
                    try:
                        update_user(db, user.username, full_name, role, is_active)
                        if new_password:
                            reset_user_password(db, user.username, new_password)
                        finish_action("Usuario modificado correctamente.")
                    except ValueError as exc:
                        st.error(str(exc))
                    except IntegrityError:
                        db.rollback()
                        st.error("No se pudo modificar el usuario.")

        elif st.session_state.get("home_action") == "Eliminar":
            if not users:
                st.warning("No hay usuarios para eliminar.")
            else:
                user = st.selectbox(
                    "Usuario a eliminar",
                    users,
                    format_func=lambda u: f"{u.username} - {u.full_name}",
                )
                st.warning(f"Se esta eliminando el usuario: {user.username}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("NO"):
                        reset_action()
                        st.rerun()
                with c2:
                    if st.button("SI"):
                        if user.username == st.session_state.username:
                            st.error("No puede eliminar el usuario con la sesion activa.")
                        else:
                            try:
                                delete_user(db, user.username)
                                finish_action("Usuario eliminado correctamente.")
                            except ValueError as exc:
                                st.error(str(exc))
                            except IntegrityError:
                                db.rollback()
                                st.error("No se pudo eliminar el usuario.")
    finally:
        db.close()

    st.dataframe(
        [
            {
                "Usuario": u.username,
                "Nombre": u.full_name,
                "Rol": u.role,
                "Activo": "SI" if u.is_active else "NO",
            }
            for u in users
        ],
        use_container_width=True,
        hide_index=True,
    )


def combo_form_fields(cats: list[Categoria], combo: Combo | None = None) -> dict:
    descripcion = st.text_input(
        "Descripcion",
        value=combo.descripcion if combo else "",
        max_chars=25,
    )

    optional_cats = [None, *cats]

    def format_optional_categoria(categoria: Categoria | None) -> str:
        if categoria is None:
            return "sin categoria"
        return f"{categoria.codigo} - {categoria.descripcion}"

    def optional_categoria_index(codigo: int | None) -> int:
        if codigo is None:
            return 0
        return next((i for i, c in enumerate(optional_cats) if c and c.codigo == codigo), 0)

    def categoria_index(codigo: int | None) -> int:
        if codigo is None:
            return 0
        return next((i for i, c in enumerate(cats) if c.codigo == codigo), 0)

    c1, c2 = st.columns(2)
    with c1:
        categ1 = st.selectbox(
            "categ1",
            optional_cats,
            index=optional_categoria_index(combo.categ1 if combo else None),
            format_func=format_optional_categoria,
        )
    with c2:
        qcateg1 = st.number_input(
            "qcateg1",
            min_value=0,
            step=1,
            value=int(combo.qcateg1) if combo and combo.categ1 is not None else 0,
        )

    c3, c4 = st.columns(2)
    with c3:
        categ2 = st.selectbox(
            "categ2",
            optional_cats,
            index=optional_categoria_index(combo.categ2 if combo else None),
            format_func=format_optional_categoria,
        )
    with c4:
        qcateg2 = st.number_input(
            "qcateg2",
            min_value=0,
            step=1,
            value=int(combo.qcateg2) if combo and combo.categ2 is not None else 0,
        )

    c5, c6 = st.columns(2)
    with c5:
        categ3 = st.selectbox(
            "categ3",
            optional_cats,
            index=optional_categoria_index(combo.categ3 if combo else None),
            format_func=format_optional_categoria,
        )
    with c6:
        qcateg3 = st.number_input(
            "qcateg3",
            min_value=0,
            step=1,
            value=int(combo.qcateg3) if combo and combo.categ3 is not None else 0,
        )

    c7, c8 = st.columns(2)
    with c7:
        categ4 = st.selectbox(
            "categ4",
            optional_cats,
            index=optional_categoria_index(combo.categ4 if combo else None),
            format_func=format_optional_categoria,
        )
    with c8:
        qcateg4 = st.number_input(
            "qcateg4",
            min_value=0,
            step=1,
            value=int(combo.qcateg4) if combo and combo.categ4 is not None else 0,
        )

    return {
        "descripcion": descripcion.strip(),
        "categ1": int(categ1.codigo) if categ1 else None,
        "qcateg1": int(qcateg1) if categ1 else 0,
        "categ2": int(categ2.codigo) if categ2 else None,
        "qcateg2": int(qcateg2) if categ2 else 0,
        "categ3": int(categ3.codigo) if categ3 else None,
        "qcateg3": int(qcateg3) if categ3 else 0,
        "categ4": int(categ4.codigo) if categ4 else None,
        "qcateg4": int(qcateg4) if categ4 else 0,
    }


def validate_combo_values(values: dict) -> str | None:
    for number in (1, 2, 3, 4):
        categoria = values[f"categ{number}"]
        cantidad = values[f"qcateg{number}"]
        if categoria is None and cantidad != 0:
            return f"qcateg{number} debe quedar en 0 cuando categ{number} esta sin categoria."
        if categoria is not None and cantidad <= 0:
            return f"qcateg{number} debe ser mayor a 0 cuando categ{number} tiene categoria."

    return None


def combos() -> None:
    st.title("Combos")
    render_action_header("Combos")
    show_action_success()

    db = SessionLocal()
    try:
        combos_list = list(db.scalars(select(Combo).order_by(Combo.codigo)).all())
        cats = list(db.scalars(select(Categoria).order_by(Categoria.codigo)).all())

        if st.session_state.get("home_action") == "Crear":
            if not cats:
                st.error("Debe existir al menos una categoria antes de crear combos.")
            else:
                with st.form("crear_combo"):
                    codigo = st.number_input("Codigo", min_value=1, step=1)
                    values = combo_form_fields(cats)
                    c1, c2 = st.columns(2)
                    with c1:
                        guardar = st.form_submit_button("Guardar")
                    with c2:
                        salir = st.form_submit_button("Salir")

                if salir:
                    reset_action()
                    st.rerun()
                if guardar:
                    if not values["descripcion"]:
                        st.error("Debe ingresar una descripcion.")
                    elif validate_combo_values(values):
                        st.error(validate_combo_values(values))
                    else:
                        try:
                            db.add(Combo(codigo=int(codigo), **values))
                            db.commit()
                            finish_action("Combo creado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo crear el combo. Revise que el codigo y la descripcion no existan.")

        elif st.session_state.get("home_action") == "Modificar":
            if not combos_list:
                st.warning("No hay combos para modificar.")
            elif not cats:
                st.error("Debe existir al menos una categoria.")
            else:
                combo = st.selectbox(
                    "Combo a modificar",
                    combos_list,
                    format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                )
                with st.form("modificar_combo"):
                    st.number_input("Codigo", value=int(combo.codigo), disabled=True)
                    values = combo_form_fields(cats, combo)
                    guardar = st.form_submit_button("Guardar")

                if guardar:
                    if not values["descripcion"]:
                        st.error("Debe ingresar una descripcion.")
                    elif validate_combo_values(values):
                        st.error(validate_combo_values(values))
                    else:
                        try:
                            combo_db = db.get(Combo, int(combo.codigo))
                            if combo_db is None:
                                st.error("Combo no encontrado.")
                                return
                            for field, value in values.items():
                                setattr(combo_db, field, value)
                            db.commit()
                            finish_action("Combo modificado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo modificar el combo. Revise que la descripcion no exista.")

        elif st.session_state.get("home_action") == "Eliminar":
            if not combos_list:
                st.warning("No hay combos para eliminar.")
            else:
                combo = st.selectbox(
                    "Combo a eliminar",
                    combos_list,
                    format_func=lambda c: f"{c.codigo} - {c.descripcion}",
                )
                st.warning(f"Se esta eliminando el combo: {combo.codigo} - {combo.descripcion}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("NO"):
                        reset_action()
                        st.rerun()
                with c2:
                    if st.button("SI"):
                        try:
                            combo_db = db.get(Combo, int(combo.codigo))
                            if combo_db is None:
                                st.error("Combo no encontrado.")
                                return
                            db.delete(combo_db)
                            db.commit()
                            finish_action("Combo eliminado correctamente.")
                        except IntegrityError:
                            db.rollback()
                            st.error("No se pudo eliminar el combo.")
    finally:
        db.close()

    st.dataframe(
        [
            {
                "Codigo": c.codigo,
                "Descripcion": c.descripcion,
                "categ1": c.categ1,
                "qcateg1": c.qcateg1,
                "categ2": c.categ2,
                "qcateg2": c.qcateg2,
                "categ3": c.categ3,
                "qcateg3": c.qcateg3,
                "categ4": c.categ4,
                "qcateg4": c.qcateg4,
            }
            for c in combos_list
        ],
        use_container_width=True,
        hide_index=True,
    )


def reportes_cerrados() -> None:
    st.title("Reportes cerrados")

    db = SessionLocal()
    try:
        reportes = list(
            db.scalars(
                select(ReporteVentaTurno).order_by(ReporteVentaTurno.fecha_creacion.desc())
            ).all()
        )
    finally:
        db.close()

    st.dataframe(
        [
            {
                "ID": r.id,
                "Fecha": r.fecha_creacion,
                "Local": r.local_descripcion,
                "Turno": r.turno,
                "Encargado": r.encargado,
                "Usuario cierre": r.usuario_cierre,
                "Total items": r.total_items,
                "Estado": r.estado,
            }
            for r in reportes
        ],
        use_container_width=True,
        hide_index=True,
    )


def menu_lateral() -> str:
    st.sidebar.title("Menu")
    st.sidebar.write(f"Usuario: {st.session_state.username}")

    opciones = [
        "Inicio",
        "Ventas por turno",
        "Configuracion",
        "Categorias",
        "Articulos",
        "Locales",
        "Usuarios",
        "Combos",
        "Reportes cerrados",
    ]
    pagina = st.sidebar.selectbox(
        "Opciones",
        opciones,
        index=opciones.index(st.session_state.page)
        if st.session_state.page in opciones
        else 0,
    )

    st.session_state.page = pagina
    return pagina


def main() -> None:
    init()
    render_header()

    if not st.session_state.auth:
        login()
        return

    pagina = menu_lateral()

    if pagina == "Ventas por turno":
        ventas()
    elif pagina == "Categorias":
        categorias()
    elif pagina == "Articulos":
        articulos()
    elif pagina == "Locales":
        locales()
    elif pagina == "Usuarios":
        usuarios()
    elif pagina == "Combos":
        combos()
    elif pagina == "Reportes cerrados":
        reportes_cerrados()
    else:
        inicio()


if __name__ == "__main__":
    main()
