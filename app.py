import streamlit as st
from supabase import create_client
import pandas as pd
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="RMA Hikvision", layout="wide")

# (Estilos CSS omitidos para brevedad, mantenlos igual que en tu versión)

# 2. LOGIN Y CONEXIÓN (Misma lógica)
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': None})

# ... (Funciones de login e init_db igual que antes) ...
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
supabase = init_db()

# 3. SIDEBAR (Ingreso de datos)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=140)
    with st.form("nuevo_rma", clear_on_submit=True):
        st.subheader("➕ Nuevo Ingreso")
        # Inputs...
        f_rma = st.text_input("RMA")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn  = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        f_env = st.selectbox("Enviado", ["NO", "YES"])
        f_com = st.text_area("Comentarios")
        if st.form_submit_button("REGISTRAR"):
            supabase.table("inventario_rma").insert({
                "rma_number": f_rma, "empresa": f_emp, "modelo": f_mod, 
                "serial_number": f_sn, "informacion": f_est, "enviado": f_env, "comentarios": f_com
            }).execute()
            st.rerun()

# 4. PANEL DE CONTROL (Visualización y Cambio Manual)
st.title("📦 Gestión de RMA")

try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        # Preparar visualización con emojis
        df_view = df.copy()
        df_view['informacion'] = df_view['informacion'].apply(lambda x: f"🔴 {x}" if "proceso" in str(x) else f"🟢 {x}")
        df_view['enviado'] = df_view['enviado'].apply(lambda x: f"🔴 {x}" if x == "NO" else f"🟢 {x}")
        
        # Búsqueda
        busq = st.text_input("🔍 Buscar por cualquier campo...")
        if busq:
            df_view = df_view[df_view.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)]

        # --- CONFIGURACIÓN DE EDICIÓN MANUAL ---
        es_admin = st.session_state['rol'] == 'admin'
        if es_admin:
            df_view.insert(0, "Sel", False)

        config_columnas = {
            "id": None, # Oculto
            "fecha_registro": st.column_config.TextColumn("Fecha", disabled=True),
            "Sel": st.column_config.CheckboxColumn("🗑️"),
            "informacion": st.column_config.SelectboxColumn("Estado", options=["🔴 En proceso", "🟢 FINALIZADO"], required=True),
            "enviado": st.column_config.SelectboxColumn("Enviado", options=["🔴 NO", "🟢 YES"], required=True),
            "rma_number": st.column_config.TextColumn("RMA #"),
            "empresa": st.column_config.TextColumn("Empresa"),
            "modelo": st.column_config.TextColumn("Modelo"),
            "serial_number": st.column_config.TextColumn("S/N"),
            "comentarios": st.column_config.TextColumn("Comentarios"),
        }

        # La tabla "Mágica" que permite cambios manuales
        edited_df = st.data_editor(
            df_view,
            column_config=config_columnas,
            use_container_width=True,
            hide_index=True,
            disabled=not es_admin # Si no es admin, solo lee
        )

        # 5. GUARDAR CAMBIOS MANUALES
        if es_admin:
            col1, col2, _ = st.columns([1, 1, 2])
            
            if col1.button("💾 APLICAR CAMBIOS MANUALES", type="primary"):
                with st.spinner("Actualizando registros..."):
                    for _, row in edited_df.iterrows():
                        # Limpiar emojis para la DB
                        info_db = str(row['informacion']).replace("🔴 ", "").replace("🟢 ", "")
                        env_db = str(row['enviado']).replace("🔴 ", "").replace("🟢 ", "")
                        
                        # UPDATE manual de TODOS los campos
                        supabase.table("inventario_rma").update({
                            "rma_number": row['rma_number'],
                            "empresa": row['empresa'],
                            "modelo": row['modelo'],
                            "serial_number": row['serial_number'],
                            "informacion": info_db,
                            "enviado": env_db,
                            "comentarios": row['comentarios']
                        }).eq("id", row['id']).execute()
                
                st.success("¡Todo actualizado!")
                st.rerun()

            if col2.button("🗑️ BORRAR SELECCIONADOS"):
                seleccionados = edited_df[edited_df["Sel"] == True]
                for id_db in seleccionados['id'].tolist():
                    supabase.table("inventario_rma").delete().eq("id", id_db).execute()
                st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
