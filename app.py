
import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="RMA System", layout="wide", page_icon="📦")

# 2. DISEÑO CSS (Estilo oscuro y rojo, sin logos)
st.markdown("""
    <style>
    header { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    h1, h2, h3, p, label { color: #e6edf3 !important; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 2px solid #eb1c24; }
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #30363d;
    }
    .stButton>button {
        background: #8b0000;
        color: white !important;
        border-radius: 8px !important;
        border: 1px solid #eb1c24 !important;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover { background: #eb1c24; }
    /* Estilo para el botón de eliminar (más brillante) */
    .stButton.delete-btn>button {
        background: #ff4b4b;
        border: 1px solid white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. SISTEMA DE LOGIN POR ROLES
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    st.markdown("<br><h2 style='text-align: center; color: #eb1c24 !important;'>SISTEMA DE GESTIÓN RMA</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<p style='text-align: center;'>Ingrese sus credenciales</p>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ENTRAR"):
                if u == "admin" and p == "Hik13579":
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'tecnico'})
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 4. CONEXIÓN Y UTILIDADES
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

def to_excel(df):
    output = io.BytesIO()
    # Limpiamos la columna de selección antes de exportar
    df_export = df.copy()
    if 'Seleccionar' in df_export.columns:
        df_export = df_export.drop(columns=['Seleccionar'])
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='RMA_Report')
    return output.getvalue()

# 5. REGISTRO (SIDEBAR)
with st.sidebar:
    st.markdown(f"👤 **Sesión:** {st.session_state['rol'].upper()}")
    st.markdown("---")
    st.markdown("### ➕ Registrar RMA")
    with st.form("reg", clear_on_submit=True):
        f_rma = st.text_input("Número RMA")
        f_ticket = st.text_input("Nº Ticket")
        f_rq = st.text_input("Nº RQ")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_com = st.text_area("Comentarios")
        
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                data = {
                    "rma_number": f_rma, "n_ticket": f_ticket, "n_rq": f_rq,
                    "empresa": f_emp, "modelo": f_mod, "serial_number": f_sn,
                    "informacion": f_est, "comentarios": f_com, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(data).execute()
                st.success("✅ Guardado")
                st.rerun()

    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 6. CUERPO PRINCIPAL
st.markdown("# 📦 Panel de Control RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()
    
    if not df_raw.empty:
        df_raw['fecha_registro'] = pd.to_datetime(df_raw['fecha_registro']).dt.date
        # --- NUEVO: Añadimos columna de selección si es admin ---
        if st.session_state['rol'] == 'admin':
            df_raw.insert(0, 'Seleccionar', False)
        df = df_raw
    else:
        df = pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("TOTAL", len(df))
    c2.metric("EN PROCESO", len(df[df['informacion'] == 'En proceso']))
    c3.metric("FINALIZADOS", len(df[df['informacion'] == 'FINALIZADO']))

    # DESCARGA EXCEL
    st.download_button(
        label="📥 Descargar Reporte (.xlsx)",
        data=to_excel(df),
        file_name=f"RMA_Report_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")

    # 7. TABLA EDITABLE Y ELIMINACIÓN POR SELECCIÓN
    st.subheader("Tabla de Gestión")
    if st.session_state['rol'] == 'admin':
        st.caption("Admin: Seleccione los registros con el cuadro de la izquierda para eliminar en lote.")
    
    busq = st.text_input("🔍 Buscar...", placeholder="RMA, Empresa, S/N...")
    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # Configuramos el editor
    config_columnas = {
        "id": st.column_config.TextColumn("ID", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha Registro", disabled=True, format="DD/MM/YYYY"),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["NO", "YES"])
    }
    
    # Si es admin, habilitamos la columna "Seleccionar"
    if st.session_state['rol'] == 'admin':
        config_columnas["Seleccionar"] = st.column_config.CheckboxColumn("Seleccionar", default=False)

    df_editado = st.data_editor(
        df_f,
        use_container_width=True,
        hide_index=True,
        column_config=config_columnas,
        disabled=["id", "fecha_registro"]
    )

    # BOTONES DE ACCIÓN
    col_save, col_del = st.columns([1, 1])

    with col_save:
        if st.button("💾 GUARDAR CAMBIOS"):
            for _, row in df_editado.iterrows():
                # No enviamos 'Seleccionar' a la DB
                upd_data = {
                    "rma_number": row['rma_number'], "n_ticket": row['n_ticket'],
                    "n_rq": row['n_rq'], "empresa": row['empresa'],
                    "modelo": row['modelo'], "serial_number": row['serial_number'],
                    "informacion": row['informacion'], "enviado": row['enviado'],
                    "comentarios": row['comentarios'], "fedex_number": row.get('fedex_number', '')
                }
                supabase.table("inventario_rma").update(upd_data).eq("id", row['id']).execute()
            st.success("Base de datos actualizada.")
            st.rerun()

    # Botón de eliminar solo para Admin
    if st.session_state['rol'] == 'admin':
        with col_del:
            # Filtramos cuáles están marcados para eliminar
            seleccionados = df_editado[df_editado['Seleccionar'] == True]
            if not seleccionados.empty:
                st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
                if st.button(f"🗑️ ELIMINAR {len(seleccionados)} REGISTROS"):
                    ids_a_borrar = seleccionados['id'].tolist()
                    for id_b in ids_a_borrar:
                        supabase.table("inventario_rma").delete().eq("id", id_b).execute()
                    st.warning("Registros eliminados correctamente.")
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("No hay registros en la base de datos.")
