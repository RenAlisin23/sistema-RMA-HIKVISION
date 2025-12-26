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
    /* Estilo para los headers de las tablas */
    [data-testid="stHeader"] { background-color: #161b22; }
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
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. PANEL PRINCIPAL
st.title("📦 Control de Inventario RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df_raw = pd.DataFrame(res.data)

    if not df_raw.empty:
        df_view = df_raw.copy()
        df_view['informacion_vis'] = df_view['informacion'].apply(lambda x: f"🔴 {x}" if "proceso" in str(x).lower() else f"🟢 {x}")
        df_view['enviado_vis'] = df_view['enviado'].apply(lambda x: f"🔴 {x}" if x == "NO" else f"🟢 {x}")
        df_view['Nº'] = range(len(df_view), 0, -1)
        
        busq = st.text_input("🔍 Buscar por RMA, Empresa o Serial...", placeholder="Escribe para filtrar...")
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]

        es_admin = st.session_state['rol'] == 'admin'
        if es_admin:
            df_view.insert(0, "Sel", False)
        
        # --- MEJORA DE CABEZAL DE TABLAS ---
        config = {
            "id": None,
            "Sel": st.column_config.CheckboxColumn("🗑️"),
            "Nº": st.column_config.TextColumn("🆔 Nº", disabled=True),
            "fecha_registro": st.column_config.TextColumn("📅 FECHA INGRESO", disabled=True),
            "rma_number": st.column_config.TextColumn("NÚMERO RMA"),
            "empresa": st.column_config.TextColumn("CLIENTE / EMPRESA"),
            "modelo": st.column_config.TextColumn("MODELO"),
            "serial_number": st.column_config.TextColumn("S/N (SERIAL)"),
            "informacion_vis": st.column_config.SelectboxColumn("ESTADO", options=["🔴 En proceso", "🟢 FINALIZADO"]),
            "enviado_vis": st.column_config.SelectboxColumn("ENVIADO", options=["🔴 NO", "🟢 YES"]),
            "comentarios": st.column_config.TextColumn("COMENTARIOS"),
            "fedex_number": st.column_config.TextColumn("GUÍA / FEDEX"),
            "descripcion": st.column_config.TextColumn("DETALLE TÉCNICO"),
        }

        # Mostrar tabla (Editor solo para admin)
        edited_df = st.data_editor(
            df_view, 
            column_config=config, 
            use_container_width=True, 
            hide_index=True, 
            disabled=not es_admin,
            key="main_editor"
        )

        # Lógica de guardado masivo para Admin
        if es_admin:
            c1, c2, c3 = st.columns([1, 1, 2])
            if c1.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                for _, row in edited_df.iterrows():
                    info_clean = row['informacion_vis'].replace("🔴 ", "").replace("🟢 ", "")
                    env_clean = row['enviado_vis'].replace("🔴 ", "").replace("🟢 ", "")
                    supabase.table("inventario_rma").update({
                        "informacion": info_clean, "enviado": env_clean,
                        "comentarios": row['comentarios'], "rma_number": row['rma_number']
                    }).eq("id", row['id']).execute()
                st.success("Base de datos actualizada"); st.rerun()

            if c2.button("ELIMINAR SELECCIÓN", use_container_width=True):
                for id_db in edited_df[edited_df["Sel"] == True]['id'].tolist():
                    supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                st.rerun()

        # --- LÓGICA DE ACTUALIZACIÓN MANUAL (ADMIN Y USER) ---
        st.divider()
        st.subheader("📝 Actualización Rápida de Registro")
        
        with st.form("form_actualizacion_manual"):
            col_sel, col_est, col_env = st.columns([1, 2, 2])
            with col_sel:
                # Elige el Nº amigable que ves en la tabla
                num_amigable = st.selectbox("Seleccione Nº", df_view['Nº'].tolist())
            
            # Obtener datos actuales de la fila seleccionada
            fila_sel = df_view[df_view['Nº'] == num_amigable].iloc[0]
            id_tecnico = fila_sel['id']
            
            with col_est:
                n_est = st.selectbox("Estado Actual", ["En proceso", "FINALIZADO"], 
                                     index=0 if "proceso" in str(fila_sel['informacion']).lower() else 1)
            with col_env:
                n_env = st.selectbox("Enviado", ["NO", "YES"], 
                                     index=0 if fila_sel['enviado'] == "NO" else 1)
            
            n_fedex = st.text_input("Número de Guía / FedEx", value=fila_sel.get('fedex_number', ""))
            n_desc = st.text_area("Descripción Técnica / Detalle", value=fila_sel.get('descripcion', ""))
            n_com = st.text_area("Comentarios generales", value=fila_sel.get('comentarios', ""))

            if st.form_submit_button(f"ACTUALIZAR REGISTRO Nº {num_amigable}", use_container_width=True):
                upd_data = {
                    "informacion": n_est, 
                    "enviado": n_env, 
                    "comentarios": n_com, 
                    "fedex_number": n_fedex, 
                    "descripcion": n_desc
                }
                supabase.table("inventario_rma").update(upd_data).eq("id", id_tecnico).execute()
                st.success(f"Registro Nº {num_amigable} actualizado correctamente")
                st.rerun()

    else:
        st.info("No hay registros en la base de datos.")

except Exception as e:
    st.error(f"Error de conexión o datos: {e}")
