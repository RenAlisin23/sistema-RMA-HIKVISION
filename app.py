import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA Hikvision | Pro Dashboard", layout="wide", page_icon="🛡️")

# 2. CONEXIÓN A BASE DE DATOS
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("⚠️ Error de conexión. Revisa los Secrets en Streamlit Cloud.")
        return None

supabase = init_connection()

# 3. DISEÑO DE COLORES Y ALTO CONTRASTE (CSS)
st.markdown("""
    <style>
    /* Fondo principal gris claro para que resalten las tarjetas blancas */
    .stApp { background-color: #f4f7f6; }
    
    /* Títulos en negro profundo */
    h1, h2, h3 { color: #1e1e1e !important; font-weight: 800 !important; }
    
    /* Barra lateral - Estilo oscuro sólido */
    [data-testid="stSidebar"] { 
        background-color: #111111; 
        border-right: 3px solid #eb1c24; 
    }
    
    /* Textos de la barra lateral en blanco */
    [data-testid="stSidebar"] .stMarkdown h2, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p { 
        color: #ffffff !important; 
    }

    /* Tarjetas de métricas blancas con sombra */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 8px 16px rgba(0,0,0,0.08);
        border-top: 5px solid #eb1c24;
    }
    
    /* Números de métricas en negro */
    [data-testid="stMetricValue"] { color: #1e1e1e !important; }
    [data-testid="stMetricLabel"] { color: #555555 !important; }

    /* Estilo de la Tabla */
    .stDataFrame { background-color: white; border-radius: 10px; }

    /* Botón Guardar Rojo Hikvision */
    .stButton>button {
        background-color: #eb1c24;
        color: white;
        border-radius: 10px;
        font-weight: bold;
        height: 3em;
        width: 100%;
        border: none;
    }
    .stButton>button:hover { background-color: #ff4d4d; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL: REGISTRO DE EQUIPOS ---
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=180)
    st.markdown("## ➕ Nuevo Ingreso")
    
    with st.form("form_registro", clear_on_submit=True):
        rma = st.text_input("RMA Number")
        empresa = st.text_input("Empresa")
        n_rq = st.text_input("Nº RQ")
        ticket = st.text_input("Nº Ticket")
        modelo = st.text_input("Modelo")
        sn = st.text_input("Serial Number")
        info = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        coments = st.text_area("Comentarios del Técnico", height=120)
        
        btn = st.form_submit_button("GUARDAR EQUIPO")
        
        if btn:
            if rma and empresa:
                nuevo = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(nuevo).execute()
                st.success("✅ ¡Registrado correctamente!")
                st.rerun()
            else:
                st.error("RMA y Empresa son obligatorios")

# --- PANEL PRINCIPAL ---
st.title("Sistema de Control RMA Hikvision")

# 4. CARGA DE DATOS
try:
    # Intento con orden, si falla trae todo
    try:
        res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    except:
        res = supabase.table("inventario_rma").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

# Muestra métricas si hay datos
if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("A espera por HQ", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df[df['informacion'] == 'FINALIZADO']))

st.markdown("---")

# 5. BUSCADOR Y TABLA
st.markdown("### 🔍 Buscador Inteligente")
busqueda = st.text_input("", placeholder="Busca por RMA, Empresa, Serial o comentario...")

if not df.empty:
    # Filtro global en todas las columnas
    if busqueda:
        mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
        df_mostrar = df[mask]
    else:
        df_mostrar = df

    # Estilo de colores para la columna Estado
    def highlight_status(val):
        color = '#155724' if val == 'FINALIZADO' else '#856404'
        bg = '#d4edda' if val == 'FINALIZADO' else '#fff3cd'
        return f'background-color: {bg}; color: {color}; font-weight: bold;'

    # Configuración de columnas
    columnas_ver = ["rma_number", "empresa", "modelo", "serial_number", "informacion", "comentarios", "fecha_registro"]
    
    st.dataframe(
        df_mostrar[columnas_ver].style.applymap(highlight_status, subset=['informacion']),
        use_container_width=True,
        hide_index=True,
        column_config={
            "rma_number": "Ticket RMA",
            "informacion": "Estado Actual",
            "comentarios": st.column_config.TextColumn("Comentarios Detallados", width="large"),
            "fecha_registro": st.column_config.DatetimeColumn("Fecha de Entrada", format="DD/MM/YYYY HH:mm")
        }
    )
else:
    st.info("No hay registros en la base de datos.")
