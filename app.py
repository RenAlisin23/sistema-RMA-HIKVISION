import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide")

# 2. CSS PARA OCULTAR TODO EL "CHROME" DE STREAMLIT
st.markdown("""
    <style>
    /* Ocultar Header, Footer y Menús */
    header, footer, .stDeployButton, #MainMenu {visibility: hidden; display: none !important;}
    
    /* Ocultar barra de herramientas y decoración superior */
    [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
        display: none !important;
        height: 0;
    }

    /* Ocultar el botón "Manage App" (específicamente para cuando estás logueado) */
    [data-testid="stStatusWidget"] { display: none !important; }
    button[title="View source"], .viewerBadge_container__1QSob { display: none !important; }

    /* Estética General Dark Mode */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    
    /* Sidebar Profesional */
    [data-testid="stSidebar"] { 
        background-color: #010409; 
        border-right: 2px solid #eb1c24; 
    }
    
    /* Métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
    }

    /* Botones Hikvision */
    .stButton>button {
        background: #8b0000;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover { background: #eb1c24; }
    
    /* Eliminar el espacio en blanco superior */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXIÓN Y LOGIN (Sin cambios)
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
                else: st.error("Credenciales inválidas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. EXCEL PROFESIONAL (Nº A LA IZQUIERDA) ---
def preparar_excel(df_input):
    df_export = df_input.copy()
    columnas_reporte = {
        "id_amigable": "Nº",
        "fecha_registro": "Fecha de Ingreso",
        "rma_number": "Número RMA",
        "n_ticket": "Ticket",
        "n_rq": "RQ",
        "empresa": "Empresa",
        "modelo": "Modelo",
        "serial_number": "S/N",
        "informacion": "Estado",
        "comentarios": "Comentarios"
    }
    cols_a_incluir = [c for c in columnas_reporte.keys() if c in df_export.columns]
    df_export = df_export[cols_a_incluir].rename(columns=columnas_reporte)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Reporte_RMA')
        workbook  = writer.book
        worksheet = writer.sheets['Reporte_RMA']
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1, 'valign': 'middle'})
        for i, col in enumerate(df_export.columns):
            max_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 4
            worksheet.set_column(i, i, max_len, cell_format)
            worksheet.write(0, i, col, header_format)
    return output.getvalue()

# 5. SIDEBAR
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown("### ➕ Registrar RMA")
    with st.form("reg", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_ticket = st.text_input("Nº Ticket")
        f_rq = st.text_input("Nº RQ")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_desc = st.text_area("Partes del modelo")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "n_ticket": f_ticket, "n_rq": f_rq, "empresa": f_emp, 
                    "modelo": f_mod, "serial_number": f_sn, "descripcion": f_desc,
                    "informacion": f_est, "comentarios": f_com, "enviado": "NO"
                }).execute()
                st.success("✅ Guardado")
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
        
        # DEFINIR ORDEN DE COLUMNAS (Nº primero)
        columnas_orden = ['id_amigable', 'fecha_registro', 'rma_number', 'n_rq', 'n_ticket', 'empresa', 'modelo', 'serial_number', 'informacion', 'comentarios']
        df = df_raw[[c for c in columnas_orden if c in df_raw.columns]]
        df.insert(len(df.columns), "id_db", df_raw['id']) # Guardar ID oculto al final
        
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
    else: df = pd.DataFrame()
except: df = pd.DataFrame()

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("En Reparación", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Completados", len(df[df['informacion'] == 'FINALIZADO']))

    c_search, c_excel = st.columns([3, 1])
    with c_search:
        busq = st.text_input("Buscador", placeholder="🔍 Filtrar registros...", label_visibility="collapsed")
    with c_excel:
        st.download_button("📥 Exportar a Excel", preparar_excel(df), "RMA_Report.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # TABLA
    st.markdown("### 📋 Listado General")
    es_admin = st.session_state['rol'] == 'admin'
    config_tabla = {
        "id_db": None, # Ocultamos el ID real de la base de datos
        "Seleccionar": st.column_config.CheckboxColumn("🗑️"),
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Ingreso", disabled=True),
        "rma_number": "Número RMA",
        "n_rq": "RQ",
        "n_ticket": "Ticket",
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
    }

    df_editado = st.data_editor(df_f, column_config=config_tabla, use_container_width=True, hide_index=True, disabled=not es_admin)

    if es_admin:
        col_s, col_b, _ = st.columns([1.2, 1.2, 3])
        if col_s.button("💾 GUARDAR CAMBIOS"):
            for _, row in df_editado.iterrows():
                upd = {"rma_number": row['rma_number'], "informacion": row['informacion'], "comentarios": row['comentarios']}
                supabase.table("inventario_rma").update(upd).eq("id", row['id_db']).execute()
            st.rerun()
        
        seleccionados = df_editado[df_editado.get('Seleccionar', False) == True]
        if not seleccionados.empty and col_b.button(f"🗑️ BORRAR SELECCIÓN"):
            for id_db in seleccionados['id_db'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # EDICIÓN MANUAL
    st.markdown("---")
    with st.expander("🛠️ Edición Manual (Buscar por Nº)"):
        col_id, col_form = st.columns([1, 3])
        id_sel = col_id.selectbox("Seleccione el Nº:", ["---"] + sorted([str(i) for i in df['id_amigable']], reverse=True))
        if id_sel != "---":
            item = df[df['id_amigable'] == int(id_sel)].iloc[0]
            with col_form.form("manual_edit_form"):
                m_rma = st.text_input("Número RMA", value=item['rma_number'])
                m_emp = st.text_input("Empresa", value=item['empresa'])
                m_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], index=0 if item['informacion']=="En proceso" else 1)
                m_com = st.text_area("Comentarios", value=str(item.get('comentarios', '')))
                if st.form_submit_button("ACTUALIZAR REGISTRO"):
                    supabase.table("inventario_rma").update({"rma_number": m_rma, "empresa": m_emp, "informacion": m_est, "comentarios": m_com}).eq("id", item['id_db']).execute()
                    st.rerun()
else:
    st.info("No hay datos.")
