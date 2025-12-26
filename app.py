import streamlit as st
from supabase import create_client
import pandas as pd
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="RMA Hikvision", layout="wide", initial_sidebar_state="expanded")

# 2. CSS (Ocultar basura y estilo oscuro)
st.markdown("""
    <style>
    header, footer, .stDeployButton, #MainMenu { visibility: hidden; display: none !important; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 3. LOGIN Y CONEXIÓN
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

def pantalla_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=280)
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
                else: st.error("Error")

if not st.session_state['autenticado']:
    pantalla_login()
    st.stop()

@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_db()

# 4. SIDEBAR (REGISTRO)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=140)
    with st.form("reg_sidebar", clear_on_submit=True):
        st.markdown("### ➕ Nuevo RMA")
        f_rma = st.text_input("RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        # GUARDAMOS TEXTO PLANO EN LA DB PARA QUE NO HAYA ERRORES
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_env = st.selectbox("Enviado", ["NO", "YES"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("GUARDAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                    "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
                }).execute()
                st.rerun()
    if st.button("🚪 Salir"):
        st.session_state.update({'autenticado': False, 'rol': None}); st.rerun()

# 5. PANEL PRINCIPAL
st.title("📦 Control de Inventario")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # --- EL TRUCO PARA QUE CARGUEN ---
        # Si en la DB dice "En proceso", le ponemos el emoji para que el editor lo reconozca
        df['informacion'] = df['informacion'].apply(lambda x: f"🔴 {x}" if x == "En proceso" else f"🟢 {x}")
        df['enviado'] = df['enviado'].apply(lambda x: f"🔴 {x}" if x == "NO" else f"🟢 {x}")
        
        df['id_amigable'] = range(len(df), 0, -1)
        cols = ['id_amigable', 'fecha_registro', 'rma_number', 'empresa', 'modelo', 'serial_number', 'informacion', 'enviado', 'comentarios', 'id']
        df_view = df[cols]
        
        if st.session_state['rol'] == 'admin':
            df_view.insert(0, "Sel", False)
            es_admin = True
        else: es_admin = False

        busq = st.text_input("🔍 Buscar...")
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]

        # --- CONFIGURACIÓN DE TABLA (Debe coincidir EXACTAMENTE con los emojis de arriba) ---
        config = {
            "id": None,
            "Sel": st.column_config.CheckboxColumn("🗑️"),
            "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
            "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"]),
            "enviado": st.column_config.SelectboxColumn("Enviado", options=["🔴 NO", "🟢 YES"]),
        }

        edited_df = st.data_editor(df_view, column_config=config, use_container_width=True, hide_index=True, disabled=not es_admin)

        if es_admin:
            c1, c2, _ = st.columns([1, 1, 3])
            if c1.button("💾 GUARDAR"):
                for _, row in edited_df.iterrows():
                    # LIMPIAMOS EMOJIS antes de mandar a Supabase
                    info_db = row['informacion'].replace("🔴 ", "").replace("🟢 ", "")
                    env_db = row['enviado'].replace("🔴 ", "").replace("🟢 ", "")
                    
                    supabase.table("inventario_rma").update({
                        "informacion": info_db, 
                        "enviado": env_db,
                        "comentarios": row['comentarios'],
                        "rma_number": row['rma_number']
                    }).eq("id", row['id']).execute()
                st.success("Cambios guardados"); st.rerun()
            
            if c2.button("🗑️ BORRAR"):
                sel = edited_df[edited_df["Sel"] == True]
                for id_db in sel['id'].tolist():
                    supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
