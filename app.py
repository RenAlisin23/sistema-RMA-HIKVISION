import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide")

# 2. CSS PROFESIONAL
st.markdown("""
    <style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px !important;
    }
    [data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
    }
    .stButton>button:hover { border-color: #eb1c24; color: #eb1c24; }
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

# --- 4. EXCEL PROFESIONAL (ORDENADO Y ESPACIADO) ---
def preparar_excel(df_input):
    # Definimos el orden exacto de las columnas para el Excel
    columnas_finales = {
        "id_amigable": "Nº Registro",
        "fecha_registro": "Fecha Ingreso",
        "rma_number": "Número RMA",
        "n_ticket": "Ticket",
        "empresa": "Empresa / Cliente",
        "modelo": "Modelo Equipo",
        "serial_number": "S/N (Serie)",
        "informacion": "Estado Actual",
        "comentarios": "Observaciones"
    }
    
    # Filtrar solo lo que queremos mostrar y reordenar
    df_export = df_input[[col for col in columnas_finales.keys() if col in df_input.columns]].copy()
    df_export = df_export.rename(columns=columnas_finales)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Reporte_RMA')
        workbook  = writer.book
        worksheet = writer.sheets['Reporte_RMA']

        # FORMATOS
        fmt_header = workbook.add_format({'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24', 'border': 1, 'align': 'center'})
        fmt_cells = workbook.add_format({'border': 1, 'valign': 'middle'})
        fmt_id = workbook.add_format({'border': 1, 'align': 'center', 'bold': True, 'fg_color': '#f4f4f4'})

        # Aplicar formatos y anchos
        for i, col in enumerate(df_export.columns):
            # Ancho dinámico + margen de respiro
            width = max(df_export[col].astype(str).map(len).max(), len(col)) + 6
            worksheet.set_column(i, i, width, fmt_cells if i > 0 else fmt_id)
            worksheet.write(0, i, col, fmt_header)

    return output.getvalue()

# 5. SIDEBAR
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=140)
    st.markdown(f"**Usuario:** `{st.session_state['rol'].upper()}`")
    with st.form("nuevo_rma"):
        st.markdown("### ➕ Registrar")
        f_rma = st.text_input("Número RMA")
        f_tkt = st.text_input("Ticket")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "n_ticket": f_tkt, "empresa": f_emp, 
                    "modelo": f_mod, "serial_number": f_sn, "informacion": f_est, "comentarios": f_com
                }).execute()
                st.rerun()
    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Control Central de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)
    
    if not df_raw.empty:
        # 6.1 PROCESAMIENTO DE COLUMNAS
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        df_raw['id_amigable'] = range(len(df_raw), 0, -1)
        
        # DEFINIMOS EL ORDEN VISUAL (ID AMIGABLE PRIMERO A LA IZQUIERDA)
        # Excluimos 'id' (técnico) y 'alerta_enviado' (el que no quieres ver)
        columnas_ordenadas = [
            'id_amigable', 'fecha_registro', 'rma_number', 'n_ticket', 
            'empresa', 'modelo', 'serial_number', 'informacion', 'comentarios'
        ]
        
        # Solo tomamos las columnas que existen en el orden que queremos
        df = df_raw[[c for c in columnas_ordenadas if c in df_raw.columns]].copy()
        # Añadimos el 'id' oculto para poder hacer updates en la DB
        df['id_db'] = df_raw['id'] 
        
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
except: df = pd.DataFrame()

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("En Reparación", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df[df['informacion'] == 'FINALIZADO']))

    c_search, c_excel = st.columns([3, 1])
    with c_search:
        busq = st.text_input("Buscador", placeholder="🔍 Filtrar...", label_visibility="collapsed")
    with c_excel:
        st.download_button("📥 Reporte Excel Pro", preparar_excel(df), "RMA_Report.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # --- TABLA INTERACTIVA ---
    es_admin = st.session_state['rol'] == 'admin'
    config_visual = {
        "id_db": None, # OCULTAMOS EL ID REAL DE LA DB
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Ingreso", disabled=True),
        "rma_number": "Número RMA",
        "n_ticket": "Ticket",
        "empresa": "Empresa / Cliente",
        "modelo": "Modelo",
        "serial_number": "S/N",
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "comentarios": "Comentarios"
    }

    st.markdown("### 📋 Registros Activos")
    df_editado = st.data_editor(
        df_f, 
        column_config=config_visual, 
        use_container_width=True, 
        hide_index=True, 
        disabled=not es_admin
    )

    if es_admin:
        col_s, col_b, _ = st.columns([1, 1, 2])
        if col_s.button("💾 GUARDAR CAMBIOS"):
            for _, row in df_editado.iterrows():
                upd = {"rma_number": row['rma_number'], "informacion": row['informacion'], "comentarios": row['comentarios']}
                supabase.table("inventario_rma").update(upd).eq("id", row['id_db']).execute()
            st.rerun()
        
        seleccionados = df_editado[df_editado.get('Seleccionar', False) == True]
        if not seleccionados.empty and col_b.button(f"🗑️ BORRAR"):
            for id_db in seleccionados['id_db'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # --- MODIFICACIÓN MANUAL (USER Y ADMIN) ---
    st.markdown("---")
    with st.expander("🛠️ Modificar por Nº de Registro"):
        col_id, col_form = st.columns([1, 3])
        id_sel = col_id.selectbox("Seleccione Nº:", ["---"] + sorted([str(i) for i in df['id_amigable']], reverse=True))
        
        if id_sel != "---":
            item = df[df['id_amigable'] == int(id_sel)].iloc[0]
            with col_form.form("manual_edit"):
                st.write(f"Editando Registro Nº {id_sel}")
                m_rma = st.text_input("RMA", value=item['rma_number'])
                m_emp = st.text_input("Empresa", value=item['empresa'])
                m_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], index=0 if item['informacion']=="En proceso" else 1)
                m_com = st.text_area("Comentarios", value=str(item.get('comentarios', '')))
                if st.form_submit_button("ACTUALIZAR"):
                    supabase.table("inventario_rma").update({"rma_number":m_rma, "empresa":m_emp, "informacion":m_est, "comentarios":m_com}).eq("id", item['id_db']).execute()
                    st.rerun()
else:
    st.info("Sin registros.")
