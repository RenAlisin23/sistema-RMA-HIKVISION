import streamlit as st
from supabase import create_client
import pandas as pd
import io

# 1. CONFIGURACIÓN Y ESTILO (Manteniendo la estética oscura)
st.set_page_config(page_title="RMA Hikvision", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    header, footer, .stDeployButton, #MainMenu { visibility: hidden; display: none !important; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    /* Estilo para los inputs de edición */
    .stTextInput input { background-color: #161b22; color: white; border: 1px solid #30363d; }
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

# 4. SIDEBAR (REGISTRO NUEVO)
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
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
                }).execute()
                st.toast("✅ Registrado con éxito")
                st.rerun()
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. PANEL PRINCIPAL
st.title("📦 Panel de Gestión de Inventario")

try:
    # 5.1 Obtener datos
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)

    if not df_raw.empty:
        # Preparar visualización
        df_view = df_raw.copy()
        
        # El buscador ahora es más potente (busca en IDs, Seriales, Nombres, etc.)
        busq = st.text_input("🔍 Buscador inteligente (ID, RMA, Empresa, S/N...)", placeholder="Ej: 105 o HIK-V30...")
        
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]

        # Aplicar Emojis visuales
        df_view['informacion'] = df_view['informacion'].apply(lambda x: f"🔴 {x}" if "proceso" in str(x) else f"🟢 {x}")
        df_view['enviado'] = df_view['enviado'].apply(lambda x: f"🔴 {x}" if x == "NO" else f"🟢 {x}")
        
        # 5.2 Lógica de Edición para ADMIN
        es_admin = st.session_state['rol'] == 'admin'
        if es_admin:
            df_view.insert(0, "Sel", False)
        
        # CONFIGURACIÓN DE COLUMNAS (Aquí es donde ocurre la magia del cambio manual)
        config = {
            "id": None, # Sigue oculto el UUID largo
            "Sel": st.column_config.CheckboxColumn("🗑️"),
            "fecha_registro": st.column_config.TextColumn("Fecha Registro", disabled=True),
            "rma_number": st.column_config.TextColumn("RMA #", help="Haz doble clic para editar"),
            "empresa": st.column_config.TextColumn("Empresa cliente"),
            "modelo": st.column_config.TextColumn("Modelo Equipo"),
            "serial_number": st.column_config.TextColumn("S/N (Serial)"),
            "informacion": st.column_config.SelectboxColumn("Estado Actual", options=["🔴 En proceso", "🟢 FINALIZADO"]),
            "enviado": st.column_config.SelectboxColumn("¿Ya se envió?", options=["🔴 NO", "🟢 YES"]),
            "comentarios": st.column_config.TextColumn("Comentarios adicionales"),
        }

        # Render de la tabla editable
        edited_df = st.data_editor(
            df_view, 
            column_config=config, 
            use_container_width=True, 
            hide_index=True, 
            disabled=not es_admin, # Solo Admin puede escribir
            key="editor_maestro"
        )

        # 5.3 BOTONES DE ACCIÓN (Guardado de cambios manuales)
        if es_admin:
            c1, c2, c3 = st.columns([1, 1, 2])
            
            if c1.button("💾 GUARDAR TODOS LOS CAMBIOS", type="primary", use_container_width=True):
                with st.spinner("Sincronizando con base de datos..."):
                    for _, row in edited_df.iterrows():
                        # Limpiar emojis antes de actualizar
                        info_db = str(row['informacion']).replace("🔴 ", "").replace("🟢 ", "")
                        env_db = str(row['enviado']).replace("🔴 ", "").replace("🟢 ", "")
                        
                        # ACTUALIZACIÓN MANUAL DE TODOS LOS CAMPOS
                        supabase.table("inventario_rma").update({
                            "rma_number": row['rma_number'],
                            "empresa": row['empresa'],
                            "modelo": row['modelo'],
                            "serial_number": row['serial_number'],
                            "informacion": info_db,
                            "enviado": env_db,
                            "comentarios": row['comentarios']
                        }).eq("id", row['id']).execute()
                
                st.success("✅ Cambios manuales aplicados con éxito")
                st.rerun()
            
            if c2.button("🗑️ ELIMINAR SELECCIÓN", use_container_width=True):
                sel = edited_df[edited_df["Sel"] == True]
                if not sel.empty:
                    for id_db in sel['id'].tolist():
                        supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                    st.rerun()
                else:
                    st.warning("Selecciona primero el checkbox 🗑️")

            # Excel (Exportación)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_raw.to_excel(writer, index=False)
            c3.download_button("📥 DESCARGAR REPORTE", data=buffer.getvalue(), file_name="inventario_rma.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

    else:
        st.info("No hay datos que mostrar. Registra un RMA en la barra lateral.")

except Exception as e:
    st.error(f"Hubo un error al procesar los datos: {e}")
