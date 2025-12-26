import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide", initial_sidebar_state="expanded")

# 2. CSS PROFESIONAL Y SUTIL
st.markdown("""
    <style>
    header, footer, .stDeployButton, #MainMenu { visibility: hidden; display: none !important; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Estilo de métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px !important;
    }

    /* Botones sutiles */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        transition: 0.3s;
    }
    
    /* Botón Guardar (Verde sutil al pasar el mouse) */
    div[data-testid="stHorizontalBlock"] div:nth-child(1) button:hover {
        border-color: #238636 !important;
        color: #3fb950 !important;
    }
    
    /* Botón Borrar (Rojo sutil al pasar el mouse) */
    div[data-testid="stHorizontalBlock"] div:nth-child(2) button:hover {
        border-color: #da3633 !important;
        color: #f85149 !important;
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
        st.markdown("<h2 style='text-align: center;'>Portal RMA </h2>", unsafe_allow_html=True)
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
                else: st.error("Credenciales inválidas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. EXCEL PROFESIONAL ---
def preparar_excel(df_input):
    df_export = df_input.copy()
    columnas_reporte = {
        "id_amigable": "Nº", "fecha_registro": "Fecha Ingreso", "rma_number": "RMA",
        "empresa": "Empresa", "modelo": "Modelo", "serial_number": "S/N",
        "informacion": "Estado", "enviado": "Enviado", "comentarios": "Comentarios"
    }
    cols_a_incluir = [c for c in columnas_reporte.keys() if c in df_export.columns]
    df_export = df_export[cols_a_incluir].rename(columns=columnas_reporte)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Reporte')
        workbook = writer.book
        worksheet = writer.sheets['Reporte']
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24', 'border': 1})
        for i, col in enumerate(df_export.columns):
            worksheet.set_column(i, i, 20)
            worksheet.write(0, i, col, header_format)
    return output.getvalue()

# 5. SIDEBAR (REGISTRO)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=140)
    with st.form("reg_sidebar", clear_on_submit=True):
        st.markdown("### ➕ Nuevo RMA")
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["🔴 En proceso", "🟢 FINALIZADO"])
        f_env = st.selectbox("Enviado", ["🔴 NO", "🟢 SI"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
                }).execute()
                st.rerun()
    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Control de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty:
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        
        # MANTENER 'id' pero ordenarlo para la tabla
        cols = ['id_amigable', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'enviado', 'comentarios', 'id']
        df = df_raw[cols]
        
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("En Reparación", len(df[df['informacion'].str.contains("🔴")]))
    m3.metric("Completados", len(df[df['informacion'].str.contains("🟢")]))

    c_search, c_excel = st.columns([3, 1])
    busq = c_search.text_input("Buscador", placeholder="🔍 Filtrar...", label_visibility="collapsed")
    c_excel.download_button("📥 Excel", preparar_excel(df), "RMA_Report.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    st.markdown("### 📋 Listado General")
    es_admin = st.session_state['rol'] == 'admin'
    
    config_tabla = {
        "id": None, # OCULTAR ID DE BASE DE DATOS
        "Seleccionar": st.column_config.CheckboxColumn("🗑️"),
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Ingreso", disabled=True),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["🔴 NO", "🟢 SI"]),
    }

    df_editado = st.data_editor(df_f, column_config=config_tabla, use_container_width=True, hide_index=True, disabled=not es_admin)

    if es_admin:
        col_s, col_b, _ = st.columns([1.2, 1.2, 3])
        
        if col_s.button("💾 GUARDAR CAMBIOS"):
            for _, row in df_editado.iterrows():
                upd = {
                    "rma_number": row['rma_number'], 
                    "informacion": row['informacion'], 
                    "enviado": row['enviado'],
                    "comentarios": row['comentarios']
                }
                supabase.table("inventario_rma").update(upd).eq("id", row['id']).execute()
            st.success("Cambios guardados")
            st.rerun()
        
        seleccionados = df_editado[df_editado["Seleccionar"] == True]
        if not seleccionados.empty and col_b.button("🗑️ BORRAR SELECCIÓN"):
            for id_db in seleccionados['id'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()
else:
    st.info("No hay datos.")
