import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide")

# 2. CSS PROFESIONAL Y SUTIL
st.markdown("""
    <style>
    /* OCULTAR ELEMENTOS INNECESARIOS DE STREAMLIT */
    header, footer, .stDeployButton, #MainMenu {visibility: hidden; display: none !important;}
    [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
    
    /* CUERPO DE LA APP */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* SIDEBAR (Asegurar que sea visible pero elegante) */
    [data-testid="stSidebar"] { 
        background-color: #010409; 
        border-right: 1px solid #30363d; 
    }
    
    /* BOTONES SUTILES Y ATRACTIVOS */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        font-weight: 500;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
        transform: translateY(-1px);
    }
    
    /* BOTÓN GUARDAR (Verde sutil al hover) */
    div[data-testid="stFormSubmitButton"] button:hover {
        border-color: #238636 !important;
        color: #3fb950 !important;
    }

    /* ESTILO DE MÉTRICAS */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px !important;
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
        st.markdown("<h2 style='text-align: center;'>Portal RMA Professional</h2>", unsafe_allow_html=True)
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
    # Limpiar emojis para el Excel
    df_export['informacion'] = df_export['informacion'].str.replace("🔴 ", "").str.replace("🟢 ", "")
    
    columnas_reporte = {
        "id_amigable": "Nº", "fecha_registro": "Fecha Ingreso", "rma_number": "Número RMA",
        "n_ticket": "Ticket", "n_rq": "RQ", "empresa": "Empresa", "modelo": "Modelo",
        "serial_number": "S/N", "informacion": "Estado", "comentarios": "Comentarios"
    }
    df_export = df_export[[c for c in columnas_reporte.keys() if c in df_export.columns]].rename(columns=columnas_reporte)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Reporte')
        workbook, worksheet = writer.book, writer.sheets['Reporte']
        header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24', 'border': 1, 'align': 'center'})
        cell_fmt = workbook.add_format({'border': 1})
        for i, col in enumerate(df_export.columns):
            worksheet.set_column(i, i, 20, cell_fmt)
            worksheet.write(0, i, col, header_fmt)
    return output.getvalue()

# 5. SIDEBAR (PARA AGREGAR)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### 📝 Nuevo Registro")
    with st.form("reg_form", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["🔴 En proceso", "🟢 FINALIZADO"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR EN SISTEMA"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "comentarios": f_com
                }).execute()
                st.success("Registrado con éxito")
                st.rerun()
    
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Control de Inventario RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)
    if not df_raw.empty:
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        
        # ORDENAR COLUMNAS: ID AMIGABLE A LA IZQUIERDA
        columnas_orden = ['id_amigable', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'comentarios']
        df = df_raw[[c for c in columnas_orden if c in df_raw.columns]].copy()
        df['id_db'] = df_raw['id']
        
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

if not df.empty:
    # Métricas sutiles
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("En Reparación", len(df[df['informacion'].str.contains("🔴")]))
    m3.metric("Finalizados", len(df[df['informacion'].str.contains("🟢")]))

    col_bus, col_ex = st.columns([3, 1])
    busq = col_bus.text_input("Filtrar...", placeholder="Busca por RMA, empresa o serie...", label_visibility="collapsed")
    col_ex.download_button("📥 Descargar Excel", preparar_excel(df), "Reporte_RMA.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # TABLA CON ESTADOS DE COLORES
    st.markdown("### 📋 Registros")
    es_admin = st.session_state['rol'] == 'admin'
    
    config_tabla = {
        "id_db": None,
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Ingreso", disabled=True),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"], required=True),
        "rma_number": "RMA",
        "empresa": "Cliente",
        "Seleccionar": st.column_config.CheckboxColumn("🗑️")
    }

    df_editado = st.data_editor(df_f, column_config=config_tabla, use_container_width=True, hide_index=True, disabled=not es_admin)

    if es_admin:
        c1, c2, _ = st.columns([1, 1, 2])
        if c1.button("💾 Guardar Cambios"):
            for _, row in df_editado.iterrows():
                supabase.table("inventario_rma").update({
                    "rma_number": row['rma_number'], "informacion": row['informacion'], "comentarios": row['comentarios']
                }).eq("id", row['id_db']).execute()
            st.success("Base de datos actualizada")
            st.rerun()
        
        sel = df_editado[df_editado.get('Seleccionar', False) == True]
        if not sel.empty and c2.button("🗑️ Eliminar"):
            for id_db in sel['id_db'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # EDICIÓN MANUAL RÁPIDA
    st.markdown("---")
    with st.expander("🛠️ Modificar por Nº de Registro"):
        c_id, c_form = st.columns([1, 3])
        id_sel = c_id.selectbox("Seleccione Nº:", ["---"] + sorted([str(i) for i in df['id_amigable']], reverse=True))
        if id_sel != "---":
            item = df[df['id_amigable'] == int(id_sel)].iloc[0]
            with c_form.form("manual"):
                m_rma = st.text_input("RMA", value=item['rma_number'])
                m_est = st.selectbox("Estado", ["🔴 En proceso", "🟢 FINALIZADO"], 
                                   index=0 if "🔴" in item['informacion'] else 1)
                m_com = st.text_area("Comentarios", value=str(item.get('comentarios', '')))
                if st.form_submit_button("ACTUALIZAR"):
                    supabase.table("inventario_rma").update({"rma_number":m_rma, "informacion":m_est, "comentarios":m_com}).eq("id", item['id_db']).execute()
                    st.rerun()
else:
    st.info("No hay datos registrados.")
