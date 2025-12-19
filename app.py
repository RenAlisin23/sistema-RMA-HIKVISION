import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="RMA Tracker | Hikvision", layout="wide", page_icon="📦")

# 2. CONEXIÓN (Mantenemos tu lógica pero con blindaje)
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        st.error("Error de conexión. Revisa los Secrets.")
        return None

supabase = init_connection()

# 3. ESTILO CSS PERSONALIZADO (Aquí está la magia)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #eb1c24; }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #eb1c24; color: white; border: none; }
    .stButton>button:hover { background-color: #c1161d; color: white; }
    .main { background-color: #f8f9fa; }
    div[data-testid="stExpander"] { border: none; box-shadow: 0px 4px 12px rgba(0,0,0,0.05); background: white; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA ---
col_logo, col_tit = st.columns([1, 4])
with col_tit:
    st.title("Panel de Control RMA")
    st.caption("Gestión de inventario y seguimiento de garantías")

# 4. OBTENER DATOS PRIMERO PARA LAS MÉTRICAS
try:
    # Intento obtener datos ordenados, si falla por la columna fecha, los trae normal
    try:
        res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    except:
        res = supabase.table("inventario_rma").select("*").execute()
    
    df_base = pd.DataFrame(res.data) if res.data else pd.DataFrame()
except Exception as e:
    st.error(f"Error al conectar con la tabla: {e}")
    df_base = pd.DataFrame()

# --- MÉTRICAS RÁPIDAS ---
if not df_base.empty:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Equipos", len(df_base))
    m2.metric("En Proceso", len(df_base[df_base['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df_base[df_base['informacion'] == 'FINALIZADO']))
    m4.metric("Empresas", df_base['empresa'].nunique())

st.divider()

# --- SECCIÓN 1: REGISTRO ---
with st.expander("REGISTRAR NUEVO INGRESO", expanded=False):
    with st.form("formulario_registro", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            rma = st.text_input("RMA Number", placeholder="Ej: RMA-1002")
            n_rq = st.text_input("Nº RQ")
            empresa = st.text_input("Empresa")
        with c2:
            ticket = st.text_input("Nº Ticket")
            modelo = st.text_input("Modelo")
            sn = st.text_input("Serial Number (S/N)")
        with c3:
            info = st.selectbox("Estado Inicial", ["En proceso", "FINALIZADO"])
            coments = st.text_area("Comentarios", height=68)
        
        if st.form_submit_button("GUARDAR REGISTRO"):
            if rma and empresa:
                nuevo_dato = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(nuevo_dato).execute()
                st.success("¡Registro guardado!")
                st.rerun()
            else:
                st.error("Faltan campos obligatorios (RMA y Empresa)")

# --- SECCIÓN 2: BUSCADOR ---
st.subheader("Filtros y Búsqueda")
busqueda = st.text_input("", placeholder="Busca por Empresa, RMA o Serial Number...")

if not df_base.empty:
    # Lógica de filtrado
    if busqueda:
        df_mostrar = df_base[
            df_base['empresa'].str.contains(busqueda, case=False, na=False) | 
            df_base['rma_number'].str.contains(busqueda, case=False, na=False) |
            df_base['serial_number'].str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_mostrar = df_base

    # Estilizar la tabla antes de mostrarla
    def color_estado(val):
        color = '#d4edda' if val == 'FINALIZADO' else '#fff3cd'
        return f'background-color: {color}'

    columnas = ["rma_number", "n_rq", "empresa", "modelo", "serial_number", "informacion", "fecha_registro"]
    
    # Aplicamos estilo visual a la tabla
    st.dataframe(
        df_mostrar[columnas].style.applymap(color_estado, subset=['informacion']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No hay datos para mostrar.")
