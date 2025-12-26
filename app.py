import streamlit as st
from supabase import create_client
import pandas as pd
import io

# 1. CONFIGURACIÓN Y ESTILO
st.set_page_config(page_title="RMA Hikvision", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    header, footer, .stDeployButton, #MainMenu { visibility: hidden; display: none !important; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGIN
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg")
        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("ACCEDER", use_container_width=True):
                if u == "admin" and p == "Hik13579":
                    st.session_state.update({'autenticado': True, 'rol': 'admin'})
                    st.rerun()
                elif u == "user" and p == "Hik12345":
                    st.session_state.update({'autenticado': True, 'rol': 'user'})
                    st.rerun()
                else: 
                    st.error("Credenciales incorrectas")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

# 3. CONEXIÓN DB
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 4. SIDEBAR (REGISTRO)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.divider()
    with st.form("reg_sidebar", clear_on_submit=True):
        st.markdown("### ➕ Nuevo RMA")
        f_rma = st.text_input("Número RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_env = st.selectbox("Enviado", ["NO", "YES"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR REGISTRO", use_container_width=True):
            if f_rma and f_emp:
                try:
                    supabase.table("inventario_rma").insert({
                        "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                        "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
                    }).execute()
                    st.toast("✅ Registrado con éxito")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("RMA y Empresa son obligatorios")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. PANEL PRINCIPAL
st.title("📦 Control de Inventario RMA")

try:
    # Consulta de datos
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)

    if not df_raw.empty:
        # Preparación de visualización con Emojis
        df_view = df_raw.copy()
        df_view['informacion'] = df_view['informacion'].apply(lambda x: f"🔴 {x}" if "proceso" in x else f"🟢 {x}")
        df_view['enviado'] = df_view['enviado'].apply(lambda x: f"🔴 {x}" if x == "NO" else f"🟢 {x}")
        
        # Columna de índice amigable
        df_view['Nº'] = range(len(df_view), 0, -1)
        
        # Selección de columnas
        cols_base = ['Nº', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'enviado', 'comentarios', 'id']
        
        # Filtro de búsqueda
        busq = st.text_input("🔍 Buscar por RMA, Empresa o Serial...", placeholder="Escribe para filtrar...")
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]

        # Lógica de Admin (Edición)
        es_admin = st.session_state['rol'] == 'admin'
        if es_admin:
            df_view.insert(0, "Sel", False)
        
        # Configuración de columnas para el editor
        config = {
            "id": None, # Ocultar ID real de la DB
            "Sel": st.column_config.CheckboxColumn("🗑️"),
            "Nº": st.column_config.TextColumn("Nº", disabled=True),
            "fecha_registro": st.column_config.TextColumn("Fecha", disabled=True),
            "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"]),
            "enviado": st.column_config.SelectboxColumn("Enviado", options=["🔴 NO", "🟢 YES"]),
        }

        edited_df = st.data_editor(
            df_view, 
            column_config=config, 
            use_container_width=True, 
            hide_index=True, 
            disabled=not es_admin,
            key="main_editor"
        )

        # Botones de Acción para Admin
        if es_admin:
            c1, c2, c3 = st.columns([1, 1, 2])
            
            if c1.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                with st.spinner("Actualizando..."):
                    for _, row in edited_df.iterrows():
                        # Limpieza estricta de emojis antes de subir
                        info_clean = row['informacion'].replace("🔴 ", "").replace("🟢 ", "")
                        env_clean = row['enviado'].replace("🔴 ", "").replace("🟢 ", "")
                        
                        supabase.table("inventario_rma").update({
                            "informacion": info_clean, 
                            "enviado": env_clean,
                            "comentarios": row['comentarios'],
                            "rma_number": row['rma_number']
                        }).eq("id", row['id']).execute()
                st.success("Base de datos actualizada")
                st.rerun()
            
            if c2.button("🗑️ ELIMINAR", use_container_width=True):
                seleccionados = edited_df[edited_df["Sel"] == True]
                if not seleccionados.empty:
                    for id_db in seleccionados['id'].tolist():
                        supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                    st.rerun()
                else:
                    st.warning("Selecciona filas primero")

            # Botón de exportar a Excel (Para administración)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_raw.to_excel(writer, index=False, sheet_name='RMA_Report')
            
            c3.download_button(
                label="📥 DESCARGAR EXCEL",
                data=buffer.getvalue(),
                file_name="reporte_rma_hikvision.xlsx",
                mime="application/vnd.ms-excel"
            )

    else:
        st.info("No hay registros en la base de datos.")

except Exception as e:
    st.error(f"Error de conexión o datos: {e}")
