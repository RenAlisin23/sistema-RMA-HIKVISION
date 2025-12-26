import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN - Sidebar expandido por defecto
st.set_page_config(
    page_title="RMA Hikvision Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 2. CSS: BOTONES SUTILES Y BARRA LATERAL VISIBLE
st.markdown("""
    <style>
    /* Ocultar solo basura de Streamlit, NO el botón de la barra lateral */
    .stDeployButton, footer, #MainMenu { display: none !important; }

    /* Fondo oscuro profesional */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* Sidebar con un toque de color sutil */
    [data-testid="stSidebar"] { 
        background-color: #010409; 
        border-right: 1px solid #30363d; 
    }

    /* Botones Atractivos (Gris/Azul sutil) */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        transition: 0.2s;
    }
    .stButton>button:hover {
        border-color: #58a6ff;
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. LÓGICA DE ROLES (Admin vs User)
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=250)
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ACCEDER"):
                if u == "admin" and p == "Hik13579":
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'user'})
                    st.rerun()
                else: st.error("Acceso incorrecto")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 4. CONEXIÓN BASE DE DATOS
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 5. BARRA LATERAL (REGISTRO) - SIEMPRE VISIBLE
with st.sidebar:
    st.markdown("### 📝 Nuevo Registro")
    with st.form("registro", clear_on_submit=True):
        f_rma = st.text_input("RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("Serie")
        f_est = st.selectbox("Estado", ["🔴 En proceso", "🟢 FINALIZADO"])
        f_env = st.selectbox("Enviado", ["🔴 NO", "🟢 SI"])
        f_com = st.text_area("Notas")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
                }).execute()
                st.rerun()
    
    if st.button("Cerrar Sesión"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Control de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['id_amigable'] = range(len(df), 0, -1)
        # ID a la izquierda
        cols_order = ['id_amigable', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'enviado', 'comentarios']
        df_view = df[cols_order].copy()
        
        if st.session_state['rol'] == 'admin':
            df_view.insert(0, "Sel", False)
            es_admin = True
        else:
            es_admin = False

        # Buscador
        busq = st.text_input("🔍 Buscar...")
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case
