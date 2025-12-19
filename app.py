import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="RMA Hikvision | Pro", layout="wide", page_icon="🛡️")

# 2. CONEXIÓN (Blindada)
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("⚠️ Error de conexión. Revisa los Secrets.")
        return None

supabase = init_connection()

# 3. DISEÑO DE COLORES Y ESTILO (Darker Background + Modern Cards)
st.markdown("""
    <style>
    /* Fondo general */
    .stApp { background-color: #f0f2f6; }
    
    /* Estilo de la barra lateral */
    [data-testid="stSidebar"] { background-color: #1e1e1e; border-right: 2px solid #eb1c24; }
    [data-testid="stSidebar"] .stMarkdown h2, [data-testid="stSidebar"] label { color: white !important; }
    
    /* Tarjetas de métricas */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #eb1c24;
    }

    /* Botón de guardar */
    .stButton>button {
        background-color: #eb1c24;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #ff4d4d; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (SIDEBAR) PARA REGISTRO ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Hikvision_logo.svg/1200px-Hikvision_logo.svg.png", width=150)
    st.header("➕ Nuevo Ingreso")
    st.caption("Completa los datos del equipo que ingresa al taller.")
    
    with st.form("form_sidebar", clear_on_submit=True):
        rma = st.text_input("RMA Number")
        empresa = st.text_input("Empresa")
        n_rq = st.text_input("Nº RQ")
        ticket = st.text_input("Nº Ticket")
        modelo = st.text_input("Modelo")
        sn = st.text_input("Serial Number")
        info = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        coments = st.text_area("Comentarios", height=100)
        
        btn_guardar = st.form_submit_button("GUARDAR EN BASE DE DATOS")
        
        if btn_guardar:
            if rma and empresa:
                nuevo = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(nuevo).execute()
                st.success("✅ ¡Registrado!")
                st.rerun()
            else:
                st.error("Faltan RMA y Empresa")

# --- CUERPO PRINCIPAL ---
st.title("🛡️ Sistema de Control RMA")

# Obtener datos
try:
    try:
        res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    except:
        res = supabase.table("inventario_rma").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

# Métricas en tarjetas blancas
if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Equipos", len(df))
    m2.metric("Pendientes", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df[df['informacion'] == 'FINALIZADO']))

st.write("---")

# Buscador moderno
busqueda = st.text_input("🔍 Buscar por cualquier campo (Empresa, RMA, S/N o Comentario):", placeholder="Escribe aquí para filtrar...")

if not df.empty:
    # Filtro inteligente
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    # Configuración de colores en la tabla
    def apply_style(val):
        color = '#155724' if val == 'FINALIZADO' else '#856404'
        bg = '#d4edda' if val == 'FINALIZADO' else '#fff3cd'
        return f'background-color: {bg}; color: {color}; font-weight: bold; border-radius: 5px;'

    # Mostrar Tabla
    columnas_orden = ["rma_number", "n_ticket", "empresa", "modelo", "serial_number", "enviado", "informacion", "comentarios", "fecha_registro"]
    
    st.dataframe(
        df_mostrar[columnas_orden].style.applymap(apply_style, subset=['informacion']),
        use_container_width=True,
        hide_index=True,
        column_config={
            "rma_number": st.column_config.TextColumn("RMA"),
            "informacion": st.column_config.TextColumn("ESTADO"),
            "comentarios": st.column_config.TextColumn("COMENTARIOS", width="large"),
            "fecha_registro": st.column_config.DatetimeColumn("FECHA", format="DD/MM/YYYY HH:mm")
        }
    )
else:
    st.info("Aún no hay equipos registrados.")
