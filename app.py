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
    .stButton>button:hover {
        border-color: #eb1c24;
        color: #eb1c24;
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
                else: st.error("Credenciales inválidas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# --- 4. EXCEL PROFESIONAL (Nº A LA IZQUIERDA Y BIEN FORMATEADO) ---
def preparar_excel(df_input):
    df_export = df_input.copy()
    
    # Mapeo de nombres para el reporte final
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
    
    # Seleccionar solo las columnas necesarias en el orden correcto
    cols_a_incluir = [c for c in columnas_reporte.keys() if c in df_export.columns]
    df_export = df_export[cols_a_incluir].rename(columns=columnas_reporte)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Reporte_RMA')
        
        workbook  = writer.book
        worksheet = writer.sheets['Reporte_RMA']

        # Estilos: Encabezado Rojo Hikvision y bordes
        header_format = workbook.add_format({
            'bold': True, 'font_color': 'white', 'fg_color': '#eb1c24',
            'border': 1, 'align': 'center', 'valign': 'middle'
        })
        cell_format = workbook.add_format({'border': 1, 'valign': 'middle'})
        
        # Ajustar ancho de columnas automáticamente
        for i, col in enumerate(df_export.columns):
            max_len = max(df_export[col].astype(str).map(len).max(), len(col)) + 4
            worksheet.set_column(i, i, max_len, cell_format)
            worksheet.write(0, i, col, header_format)

    return output.getvalue()

# 5. SIDEBAR (REGISTRO)
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
        f_desc = st.text_area("Ingrese partes del modelo aplicadas")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                data = {
                    "rma_number": f_rma, 
                    "n_ticket": f_ticket,
                    "n_rq": f_rq,
                    "empresa": f_emp, 
                    "modelo": f_mod, 
                    "serial_number": f_sn, 
                    "descripcion": f_desc,
                    "informacion": f_est, 
                    "comentarios": f_com, 
                    "enviado": "NO", 
                    "fedex_number": ""
                }
                supabase.table("inventario_rma").insert(data).execute()
                st.success("✅ Guardado")
                st.rerun()
    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL PRINCIPAL
st.title("📦 Control de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro']).dt.date
        df['id_amigable'] = range(len(df), 0, -1)
        # ID Amigable primero a la izquierda
        cols = ['id_amigable'] + [c for c in df.columns if c not in ['id_amigable', 'id']]
        df = df[cols]
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
except: df = pd.DataFrame()

if not df.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Equipos Totales", len(df))
    m2.metric("En Reparación", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Completados", len(df[df['informacion'] == 'FINALIZADO']))

    # BUSCADOR Y EXCEL ALINEADOS
    c_search, c_excel = st.columns([3, 1])
    with c_search:
        busq = st.text_input("Buscador", placeholder="🔍 Filtrar registros...", label_visibility="collapsed")
    with c_excel:
        st.download_button("📥 Exportar a Excel", preparar_excel(df), "RMA_Report.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # --- TABLA CON NOMBRES DE COLUMNA BUENOS ---
    st.markdown("### 📋 Listado General")
    es_admin = st.session_state['rol'] == 'admin'
    
    config_tabla = {
        "Seleccionar": st.column_config.CheckboxColumn("🗑️"),
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Ingreso", disabled=True),
        "rma_number": "Número RMA",
        "n_rq": "RQ",
        "n_ticket": "Ticket",
        "empresa": "Empresa",
        "modelo": "Modelo",
        "serial_number": "S/N",
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "comentarios": "Comentarios"
    }

    df_editado = st.data_editor(
        df_f, 
        column_config=config_tabla, 
        use_container_width=True, 
        hide_index=True, 
        disabled=not es_admin
    )

    if es_admin:
        col_s, col_b, _ = st.columns([1.2, 1.2, 3])
        if col_s.button("💾 GUARDAR CAMBIOS"):
            for _, row in df_editado.iterrows():
                upd = {
                    "rma_number": row['rma_number'], 
                    "informacion": row['informacion'], 
                    "comentarios": row['comentarios']
                }
                supabase.table("inventario_rma").update(upd).eq("id", row['id']).execute()
            st.rerun()
        
        seleccionados = df_editado[df_editado.get('Seleccionar', False) == True]
        if not seleccionados.empty and col_b.button(f"🗑️ BORRAR SELECCIÓN"):
            for id_db in seleccionados['id'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # --- MODIFICACIÓN MANUAL POR Nº ---
    st.markdown("---")
    with st.expander("🛠️ Edición Manual (Buscar por Nº)"):
        col_id, col_form = st.columns([1, 3])
        id_sel = col_id.selectbox("Seleccione el Nº:", ["---"] + sorted([str(i) for i in df['id_amigable']], reverse=True))
        
        if id_sel != "---":
            item = df[df['id_amigable'] == int(id_sel)].iloc[0]
            with col_form.form("manual_edit_form"):
                st.write(f"Modificando Registro Nº {id_sel}")
                m_rma = st.text_input("Número RMA", value=item['rma_number'])
                m_emp = st.text_input("Empresa", value=item['empresa'])
                m_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], index=0 if item['informacion']=="En proceso" else 1)
                m_com = st.text_area("Comentarios", value=str(item.get('comentarios', '')))
                if st.form_submit_button("ACTUALIZAR REGISTRO"):
                    supabase.table("inventario_rma").update({
                        "rma_number": m_rma, 
                        "empresa": m_emp, 
                        "informacion": m_est, 
                        "comentarios": m_com
                    }).eq("id", item['id']).execute()
                    st.rerun()
else:
    st.info("No hay datos en el sistema.")
