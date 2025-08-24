import streamlit as st
from collections import Counter
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Diagnóstico de Madurez IA", layout="centered")

# ==============================
# GOOGLE SHEETS
# ==============================
SHEET_URL = "https://docs.google.com/spreadsheets/d/19pxY8QRy2Tsxkn1LsQSRg-efJ7h1KItEWcU0wCn8u6I/edit?gid=0#gid=0"
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource(show_spinner=False)
def get_gs_client():
    creds_dict = dict(st.secrets["gcp_service_account"])  # <- secrets TOML
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    return gspread.authorize(creds)

@st.cache_resource(show_spinner=False)
def get_worksheet():
    sh = get_gs_client().open_by_url(SHEET_URL)
    ws = sh.sheet1
    headers = [
        "timestamp","email","nombre","empresa","tamano_empleados","sector",
        "q1","q2","q3","q4","q5","q6","q7","nivel","etiqueta"
    ]
    try:
        if not ws.get_all_values():
            ws.append_row(headers, value_input_option="USER_ENTERED")
    except Exception:
        pass
    return ws

def guardar_respuesta_en_sheets(row_dict):
    ws = get_worksheet()
    fila = [row_dict.get(k, "") for k in [
        "timestamp","email","nombre","empresa","tamano_empleados","sector",
        "q1","q2","q3","q4","q5","q6","q7","nivel","etiqueta"
    ]]
    ws.append_row(fila, value_input_option="USER_ENTERED")

# ==============================
# LÓGICA
# ==============================
def calcular_nivel(letras):
    letras = [r.split(")")[0] for r in letras if r]
    if len(letras) < 7:
        return None, "Faltan respuestas."

    cnt = Counter(letras)
    a = cnt.get("a",0); b = cnt.get("b",0); c = cnt.get("c",0); d = cnt.get("d",0)
    mayor = max(a,b,c,d)

    if d == mayor:
        return (5, "Transformacional") if d >= c else (4, "Sistemático")
    if c == mayor:
        return (4, "Sistemático") if (c + d) >= 4 and d > 0 else (3, "Operacional")
    if b == mayor:
        return (2, "Activo")
    return (1, "Conciencia")

def texto_recomendacion(nivel):
    return {
        1: "Nivel 1 – Conciencia: inicien pilotos y capacitación básica.",
        2: "Nivel 2 – Activo: formalicen PoC, métricas y roadmap corto.",
        3: "Nivel 3 – Operacional: escalen con gobierno de datos y MLOps.",
        4: "Nivel 4 – Sistemático: integren IA en productos y cadena de valor.",
        5: "Nivel 5 – Transformacional: IA como motor estratégico del negocio."
    }.get(nivel,"")

# ==============================
# UI
# ==============================
st.title("¿En qué nivel de madurez de IA está su empresa?")
st.caption("Evaluación rápida basada en el Modelo de Madurez de IA (Gartner).")

with st.expander("Datos de contacto (obligatorios)"):
    email = st.text_input("Email *")
    nombre = st.text_input("Nombres y Apellidos *")
    empresa = st.text_input("Empresa *")
    tam_emp = st.radio(
        "¿Cuál es el tamaño de la empresa por cantidad de empleados aproximadamente? *",
        ["Menos de 10", "Entre 11 y 50", "Entre 51 y 250", "Más de 250"],
        index=None
    )
    sector = st.selectbox(
        "Sector - Industria *",
        ["Selecciona...", "Comercio", "Manufactura", "Servicios", "Salud", "Educación", "Tecnología", "Otro"],
        index=0
    )

st.subheader("Cuestionario (selección única por pregunta)")
PREGUNTAS = [
    ("¿Han hablado en su empresa sobre usar IA o cómo podría ayudarles?",
     {"a": "Apenas empezamos a hablar del tema.",
      "b": "Vemos cómo aplicarla en algunas partes.",
      "c": "Tenemos un plan claro y metas.",
      "d": "Es parte esencial de cómo operamos."}),
    ("¿Por qué les interesa la IA?",
     {"a": "Curiosidad: entender de qué se trata.",
      "b": "Probar mejoras específicas.",
      "c": "Aumentar eficiencia/experiencia de cliente.",
      "d": "Liderar, crear cosas nuevas y nuevos ingresos."}),
    ("¿Tienen equipo experto en IA?",
     {"a": "No y no pensamos contratar aún.",
      "b": "Buscando/tenemos algunas personas para pilotos.",
      "c": "Equipo que hace que la IA funcione día a día.",
      "d": "Varios equipos expertos y liderazgo claro en IA."}),
    ("¿Cómo están sus datos para IA?",
     {"a": "Problema: no sabemos usarlos bien.",
      "b": "Empezando a ordenarlos y prepararlos.",
      "c": "Plan para calidad, linaje y preparación.",
      "d": "Gestión avanzada y operación a gran escala."}),
    ("¿Usan IA en el día a día?",
     {"a": "No, solo ideas.",
      "b": "Pruebas o proyectos pequeños.",
      "c": "Al menos un proyecto en producción con buenos resultados.",
      "d": "La IA está en casi todo o habilita nuevos productos/servicios."}),
    ("¿Resultados/ganancias de IA?",
     {"a": "Aún no medimos o es muy pronto.",
      "b": "Vemos potencial pero sin resultados claros.",
      "c": "Sí, beneficios visibles (eficiencia, menos errores...).",
      "d": "Gran valor: más ingresos y mejores decisiones."}),
    ("¿IA responsable?",
     {"a": "No lo hemos pensado mucho.",
      "b": "Reglas básicas iniciales.",
      "c": "Políticas y planes claras.",
      "d": "Gobierno de datos/IA responsable es parte de la cultura."}),
]
respuestas = []
for i,(preg,ops) in enumerate(PREGUNTAS, start=1):
    st.write(f"**{i}. {preg}**")
    choice = st.radio(
        label="",
        options=[f"{k}) {v}" for k,v in ops.items()],
        index=None,
        key=f"q{i}"
    )
    respuestas.append(choice)
    st.divider()

if st.button("📊 Calcular y guardar resultado"):
    # Validar datos obligatorios
    if not email or not nombre or not empresa or not tam_emp or (sector == "Selecciona..."):
        st.error("❌ Por favor complete todos los datos de contacto (Email, Nombre, Empresa, Tamaño y Sector).")
    else:
        nivel, etiqueta = calcular_nivel(respuestas)
        if not nivel:
            st.error("Por favor responde todas las preguntas.")
        else:
            st.markdown(
                f"<h2 style='margin-top:8px;color:#2E86C1;'>Resultado: Nivel {nivel} – {etiqueta}</h2>",
                unsafe_allow_html=True
            )
            st.write(f"📌 {texto_recomendacion(nivel)}")

            letras = [r.split(')')[0] for r in respuestas]
            row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "email": email,
                "nombre": nombre,
                "empresa": empresa,
                "tamano_empleados": tam_emp,
                "sector": sector,
                "q1": letras[0], "q2": letras[1], "q3": letras[2],
                "q4": letras[3], "q5": letras[4], "q6": letras[5], "q7": letras[6],
                "nivel": nivel, "etiqueta": etiqueta
            }
            try:
                guardar_respuesta_en_sheets(row)
                st.info("✅ Respuesta guardada en Google Sheets.")
            except Exception as e:
                st.error(f"❌ No se pudo guardar en Google Sheets: {e}. "
                         "Verifique que compartió la hoja con la cuenta de servicio y que la URL es correcta.")

            st.markdown(
                f"<p style='margin-top:12px;font-size:18px;'>"
                f"Gracias, <strong>{nombre}</strong>, por participar en el diagnóstico. "
                f"Nos pondremos en contacto con <strong>{email}</strong> si desea el informe detallado."
                f"</p>",
                unsafe_allow_html=True
            )

st.caption("Basado en el Modelo de Madurez de IA de Gartner.")
