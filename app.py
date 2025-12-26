import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN DE ALTO NIVEL
st.set_page_config(page_title="RMA Management Pro", layout="wide")

# 2. CSS PROFESIONAL (Enterprise Dark Mode)
st.markdown("""
    <style>
    header { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    
    /* Estilo de métricas */
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px !important;
    }
    
    /* Botones Pro */
    .stButton>button {
        background-color: #21262d;
        color: #c9d1d9;
        border: 1px solid #30363d;
        border-radius: 6px;
        transition: 0.2s;
    }
    .stButton>button:hover {
        border-color: #eb1c24;
        color: #eb1c24;
        background-color: #161b22;
    }
    
    /* Botón Guardar/Eliminar destacados */
    div.stButton > button:first-child {
        border-left: 4px solid #eb1c24;
    }
    
    /* Sidebar refinado */
    [data-testid="stSidebar"] {
        background-color: #010409;
        border-right: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. LOGIN Y CONEXIÓN
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
                    st.session_state.update({'autenticado': True, 'rol': 'tecnico'})
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 4. LÓGICA DE EXCEL (SOLO DATOS REALES)
def preparar_excel(df):
    # Columnas que NO queremos en el Excel
    columnas_basura = ['id', 'id_amigable', 'Seleccionar']
    df_clean = df.drop(columns=[c for c in columnas_basura if c in df.columns])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Reporte_RMA')
    return output.getvalue()

# 5. REGISTRO (SIDEBAR)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=120)
    st.caption(f"Conectado como: {st.session_state['rol'].upper()}")
    st.markdown("---")
    with st.form("reg", clear_on_submit=True):
        f_rma = st.text_input("RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        if st.form_submit_button("REGISTRAR EQUIPO"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": "NO"
                }).execute()
                st.rerun()
    if st.button("Cerrar Sesión"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. PANEL DE DATOS
st.title("📦 Control de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro']).dt.date
        df['id_amigable'] = range(len(df), 0, -1)
        # Añadimos columna de selección para borrar (Solo para la vista)
        df.insert(0, "Seleccionar", False)
except:
    df = pd.DataFrame()

if not df.empty:
    # Métricas Superiores
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Equipos", len(df))
    m2.metric("En Proceso", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df[df['informacion'] == 'FINALIZADO']))

    # Acciones de Tabla
    c_search, c_excel = st.columns([3, 1])
    busq = c_search.text_input("🔍 Filtrar por cualquier campo...", placeholder="Ej: RMA123, Empresa X...")
    c_excel.download_button("📥 Exportar Excel", preparar_excel(df), "RMA_Report.xlsx")

    # Filtrado
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # --- TABLA INTERACTIVA (EDICIÓN CLIC A CLIC) ---
    st.markdown("### 🛠️ Editor de Registros")
    st.caption("Haz clic en una celda para editar. Marca 'Seleccionar' para eliminar registros.")
    
    # Configuración de columnas para el editor
    config = {
        "id": None, # Oculta el ID de base de datos
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha", disabled=True),
        "Seleccionar": st.column_config.CheckboxColumn("🗑️", default=False),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["NO", "YES"])
    }

    df_editado = st.data_editor(
        df_f,
        column_config=config,
        use_container_width=True,
        hide_index=True,
    )

    # BOTONES DE ACCIÓN POST-EDICIÓN
    col_save, col_del, col_space = st.columns([1, 1, 2])
    
    with col_save:
        if st.button("💾 GUARDAR CAMBIOS"):
            # Lógica para actualizar los equipos que cambiaron
            for _, row in df_editado.iterrows():
                upd = {
                    "rma_number": row['rma_number'], "empresa": row['empresa'],
                    "modelo": row['modelo'], "informacion": row['informacion'],
                    "enviado": row['enviado'], "comentarios": row.get('comentarios', ''),
                    "fedex_number": row.get('fedex_number', '')
                }
                supabase.table("inventario_rma").update(upd).eq("id", row['id']).execute()
            st.success("¡Datos actualizados!")
            st.rerun()

    with col_del:
        if st.session_state['rol'] == 'admin':
            seleccionados = df_editado[df_editado['Seleccionar'] == True]
            if not seleccionados.empty:
                if st.button(f"🗑️ ELIMINAR ({len(seleccionados)})"):
                    for id_db in seleccionados['id'].tolist():
                        supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                    st.warning("Registros eliminados")
                    st.rerun()
else:
    st.info("No hay registros en la base de datos.")
