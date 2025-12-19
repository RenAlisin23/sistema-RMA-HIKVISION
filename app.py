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
# 3. DISEÑO 
st.markdown("""
    <style>
    /* Fondo principal: Gris humo ultra suave */
    .stApp { background-color: #f8faff; }
    
    /* Títulos: Degradado elegante */
    h1 { 
        color: #0e1117 !important; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        letter-spacing: -1px;
    }
    
    /* Barra lateral: Azul Medianoche Hikvision */
    [data-testid="stSidebar"] { 
        background-color: #0a0e1a; 
        border-right: 4px solid #eb1c24; 
    }
    
    /* Inputs de la barra lateral: Oscuros con borde rojo al enfocar */
    [data-testid="stSidebar"] .stTextInput input, 
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"],
    [data-testid="stSidebar"] .stTextArea textarea {
        background-color: #161b22 !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px;
    }

    /* Tarjetas de métricas: Estilo Glassmorphism ligero */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0px 10px 25px rgba(0,0,0,0.05);
        border: 1px solid #edf2f7;
    }
    
    /* Etiquetas de métricas: Color acero */
    [data-testid="stMetricLabel"] { 
        color: #64748b !important; 
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.85rem;
    }
    
    /* Valores de métricas: Negro intenso */
    [data-testid="stMetricValue"] { 
        color: #0f172a !important; 
        font-weight: 800 !important;
    }

    /* Buscador: Bordes redondeados y sombra suave */
    .stTextInput input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 12px !important;
    }

    /* Botón: Efecto Neón Rojo */
    .stButton>button {
        background: linear-gradient(135deg, #eb1c24 0%, #b0141a 100%);
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.6rem 1rem !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 15px rgba(235, 28, 36, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(235, 28, 36, 0.5);
        color: #ffffff !important;
    }

    /* Tabla: Limpieza total */
    .stDataFrame {
        border-radius: 15px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
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
st.markdown("Buscador de eventos")
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
