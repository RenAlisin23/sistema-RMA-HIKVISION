import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN - Barra lateral siempre expandida para el registro
st.set_page_config(
    page_title="RMA Hikvision Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 2. CSS PROFESIONAL (BOTONES SUTILES Y OCULTAR DEPLOY/MANAGE)
st.markdown("""
    <style>
    /* Ocultar elementos de Streamlit */
    header, footer, .stDeployButton, #MainMenu { visibility: hidden; display: none !important; }
    [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }

    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { 
        background-color: #010409; 
        border-right: 1px solid #30363d; 
    }

    /* Botones sutiles estilo Dark Mode */
    .stButton>button {
        background-color: #21262d;
        color: #e6edf3;
        border: 1px solid #30363d;
        border-radius: 8px;
        transition: 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        border-color: #8b949e;
        background-color: #30363d;
    }

    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN Y LOGIN
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=280)
        st.markdown("<h2 style='text-align: center;'>Portal RMA</h2>", unsafe_allow_html=True)
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

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. EXCEL (Nº A LA IZQUIERDA Y SIN EMOJIS) ---
def preparar_excel(df_input):
    df_export = df_input.copy()
    # Limpiar colores para el Excel
    for col in ['informacion', 'enviado']:
        if col in df_export.columns:
            df_export[col] = df_export[col].str.replace("🔴 ", "").str.replace("🟢 ", "")
    
    columnas_reporte = {
        "id_amigable": "Nº", "fecha_registro": "Fecha", "rma_number": "RMA",
        "empresa": "Cliente", "modelo": "Modelo", "serial_number": "S/N",
        "informacion": "Estado", "enviado": "Enviado", "comentarios": "Comentarios"
    }
    
    df_export = df_export[[c for c in columnas_reporte.keys() if c in df_export.columns]].rename(columns=columnas_reporte)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='RMA_Report')
        workbook, worksheet = writer.book, writer.sheets['RMA_Report']
        header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1})
        for i, col in enumerate(df_export.columns):
            worksheet.set_column(i, i, 18, cell_fmt)
            worksheet.write(0, i, col, header_fmt)
    return output.getvalue()

# 5. SIDEBAR (REGISTRO - SOLO CON 'ENVIADO')
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### 📥 Nuevo Registro")
    with st.form("form_reg", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["🔴 En proceso", "🟢 FINALIZADO"])
        f_env = st.selectbox("¿Enviado?", ["🔴 NO", "🟢 SI"])
        f_com = st.text_area("Comentarios")
        
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, 
                    "enviado": f_env, "comentarios": f_com
                }).execute()
                st.rerun()
    
    st.markdown("---")
    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Gestión de Inventario RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty:
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        
        # Nº SIEMPRE A LA IZQUIERDA
        columnas = ['id_amigable', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'enviado', 'comentarios']
        df = df_raw[[c for c in columnas if c in df_raw.columns]].copy()
        df['id_db'] = df_raw['id']
        
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

if not df.empty:
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Equipos Totales", len(df))
    c2.metric("En Proceso", len(df[df['informacion'].str.contains("🔴")]))
    c3.metric("Enviados (SI)", len(df[df['enviado'].str.contains("🟢")]))

    col_bus, col_ex = st.columns([3, 1])
    filtro = col_bus.text_input("Buscador", placeholder="Filtrar por cualquier dato...", label_visibility="collapsed")
    col_ex.download_button("📥 Exportar Excel", preparar_excel(df), "RMA_Data.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(filtro, case=False).any(), axis=1)] if filtro else df

    # TABLA CON ESTADOS ROJO/VERDE
    st.markdown("### 📋 Listado")
    es_admin = st.session_state['rol'] == 'admin'
    
    config = {
        "id_db": None,
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha", disabled=True),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["🔴 NO", "🟢 SI"]),
        "Seleccionar": st.column_config.CheckboxColumn("🗑️")
    }

    df_editado = st.data_editor(df_f, column_config=config, use_container_width=True, hide_index=True, disabled=not es_admin)

    if es_admin:
        b1, b2, _ = st.columns([1, 1, 2])
        if b1.button("💾 GUARDAR"):
            for _, row in df_editado.iterrows():
                supabase.table("inventario_rma").update({
                    "rma_number": row['rma_number'], 
                    "informacion": row['informacion'], 
                    "enviado": row['enviado'],
                    "comentarios": row['comentarios']
                }).eq("id", row['id_db']).execute()
            st.rerun()
        
        sel = df_editado[df_editado.get('Seleccionar', False) == True]
        if not sel.empty and b2.button("🗑️ BORRAR"):
            for id_db in sel['id_db'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()
else:
    st.info("Sin registros.")
