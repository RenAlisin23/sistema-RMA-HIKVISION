import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA Hikvision | Dark Mode", layout="wide", page_icon="🛡️")

# 2. CONEXIÓN A BASE DE DATOS
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("⚠️ Error de conexión.")
        return None

supabase = init_connection()

# 3. DISEÑO "FULL DARK & INDUSTRIAL" (Cero Blanco)
st.markdown("""
    <style>
    /* Fondo General: Negro Azulado Profundo */
    .stApp { 
        background-color: #0d1117; 
        color: #c9d1d9;
    }
    
    /* Títulos: Gris Platino */
    h1, h2, h3, p { 
        color: #e6edf3 !important; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Barra lateral: Negro Puro */
    [data-testid="stSidebar"] { 
        background-color: #010409; 
        border-right: 2px solid #eb1c24; 
    }
    
    /* Campos de texto en Sidebar: Gris Oscuro */
    [data-testid="stSidebar"] .stTextInput input, 
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
    [data-testid="stSidebar"] .stTextArea textarea {
        background-color: #0d1117 !important;
        color: #58a6ff !important;
        border: 1px solid #30363d !important;
    }

    /* Tarjetas de métricas: Gris Metálico (Cero Blanco) */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    
    /* Textos de Métricas */
    [data-testid="stMetricLabel"] { color: #8b949e !important; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; }

    /* Buscador Principal: Gris Carbono */
    .stTextInput input {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border: 1px solid #30363d !important;
        border-radius: 10px !important;
    }

    /* Botón: Rojo Sangre con Sombra */
    .stButton>button {
        background: #8b0000;
        color: #f0f6fc !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        font-weight: bold !important;
        box-shadow: 0 0 10px rgba(235, 28, 36, 0.2);
    }
    
    .stButton>button:hover {
        background: #eb1c24;
        box-shadow: 0 0 20px rgba(235, 28, 36, 0.4);
    }

    /* Tabla: Fondo Oscuro y Texto Claro */
    .stDataFrame {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
    }
    
    /* Estilo de líneas divisorias */
    hr { border: 0.1px solid #30363d !important; }

    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL: REGISTRO ---
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=180)
    st.markdown("## ➕ Registro de Equipo")
    
    with st.form("form_registro", clear_on_submit=True):
        rma = st.text_input("RMA Number")
        empresa = st.text_input("Empresa")
        n_rq = st.text_input("Nº RQ")
        ticket = st.text_input("Nº Ticket")
        modelo = st.text_input("Modelo")
        sn = st.text_input("Serial Number")
        info = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        coments = st.text_area("Comentarios del Técnico", height=100)
        
        btn = st.form_submit_button("GUARDAR EN NUBE")
        
        if btn:
            if rma and empresa:
                nuevo = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(nuevo).execute()
                st.success("✅ Datos sincronizados")
                st.rerun()

# --- PANEL PRINCIPAL ---
st.title("HIK-RMA Control Center")

# 4. CARGA DE DATOS
try:
    try:
        res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    except:
        res = supabase.table("inventario_rma").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

# Métricas (Tarjetas Gris Carbono)
if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL REGISTROS", len(df))
    m2.metric("PENDIENTES HQ", len(df[df['informacion'] == 'En proceso']))
    m3.metric("LISTOS / OK", len(df[df['informacion'] == 'FINALIZADO']))

st.markdown("---")

# 5. BUSCADOR Y TABLA
st.markdown("🔍 **FILTRO DINÁMICO DE EVENTOS**")
busqueda = st.text_input("", placeholder="Escribe para filtrar RMA, Empresa o S/N...")

if not df.empty:
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    # Colores para la tabla 
    def highlight_status(val):
        if val == 'FINALIZADO':
            return 'background-color: #062612; color: #34ee71; font-weight: bold;'
        return 'background-color: #2b2106; color: #eec234;'

    columnas_ver = ["rma_number", "empresa", "modelo", "serial_number", "informacion", "comentarios", "fecha_registro"]
    
    st.dataframe(
        df_mostrar[columnas_ver].style.applymap(highlight_status, subset=['informacion']),
        use_container_width=True,
        hide_index=True,
        column_config={
            "rma_number": "RMA",
            "informacion": "Estado",
            "comentarios": st.column_config.TextColumn("Notas Técnicas", width="large"),
            "fecha_registro": st.column_config.DatetimeColumn("Fecha Entrada", format="DD/MM/YY HH:mm")
        }
    )
else:
    st.info("No hay registros en la base de datos.")
