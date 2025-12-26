import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import io

# 1. CONFIGURACIÓN
st.set_page_config(page_title="RMA Hikvision Pro", layout="wide")

# 2. CSS PROFESIONAL
st.markdown("""
    <style>
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
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

# 3. LOGIN Y CONEXIÓN
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

def preparar_excel(df):
    columnas_basura = ['id', 'id_amigable', 'Seleccionar']
    df_clean = df.drop(columns=[c for c in columnas_basura if c in df.columns])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_clean.to_excel(writer, index=False, sheet_name='Reporte_RMA')
    return output.getvalue()

# 4. SIDEBAR (Añadir Registros - Disponible para todos)
with st.sidebar:
    st.image("https://revistadigitalsecurity.com.br/wp-content/uploads/2019/10/New-Hikvision-logo-1024x724-1170x827.jpg", width=150)
    st.markdown(f"**Sesión:** {st.session_state['rol'].upper()}")
    
    with st.form("reg_form", clear_on_submit=True):
        st.markdown("### ➕ Nuevo Registro")
        f_rma = st.text_input("Número RMA")
        f_ticket = st.text_input("Nº Ticket")
        f_emp = st.text_input("Empresa")
        f_mod = st.text_input("Modelo")
        f_sn = st.text_input("S/N")
        f_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"])
        if st.form_submit_button("REGISTRAR"):
            if f_rma and f_emp:
                supabase.table("inventario_rma").insert({
                    "rma_number": f_rma, "n_ticket": f_ticket, "empresa": f_emp, 
                    "modelo": f_mod, "serial_number": f_sn, "informacion": f_est, "enviado": "NO"
                }).execute()
                st.success("Registrado")
                st.rerun()
    
    if st.button("🚪 Cerrar Sesión"):
        st.session_state.update({'autenticado': False, 'rol': None})
        st.rerun()

# 5. CARGA DE DATOS
st.title("📦 Control de Inventario")
try:
    res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['fecha_registro'] = pd.to_datetime(df['fecha_registro']).dt.date
        df['id_amigable'] = range(len(df), 0, -1)
        if st.session_state['rol'] == 'admin':
            df.insert(0, "Seleccionar", False)
except: df = pd.DataFrame()

if not df.empty:
    # Métricas
    m1, m2, m3 = st.columns(3)
    m1.metric("Total", len(df))
    m2.metric("En Proceso", len(df[df['informacion'] == 'En proceso']))
    m3.metric("Finalizados", len(df[df['informacion'] == 'FINALIZADO']))

    # Buscador y Excel
    c_search, c_excel = st.columns([3, 1])
    with c_search:
        busq = st.text_input("Buscador", placeholder="🔍 Filtrar...", label_visibility="collapsed")
    with c_excel:
        st.download_button("📥 Excel", preparar_excel(df), "RMA_Report.xlsx", use_container_width=True)

    df_f = df[df.apply(lambda r: r.astype(str).str.contains(busq, case=False).any(), axis=1)] if busq else df

    # --- TABLA ---
    es_admin = st.session_state['rol'] == 'admin'
    
    config = {
        "id": None, 
        "id_amigable": st.column_config.TextColumn("Nº", disabled=True),
        "fecha_registro": st.column_config.DateColumn("Fecha", disabled=True),
        "Seleccionar": st.column_config.CheckboxColumn("🗑️"),
        "informacion": st.column_config.SelectboxColumn("Estado", options=["En proceso", "FINALIZADO"]),
        "enviado": st.column_config.SelectboxColumn("Enviado", options=["NO", "YES"])
    }

    st.markdown("### 📋 Listado de Equipos")
    df_editado = st.data_editor(
        df_f,
        column_config=config,
        use_container_width=True,
        hide_index=True,
        disabled=not es_admin  # Solo Admin edita directamente
    )

    # ACCIONES ADMIN (Guardar/Borrar tabla)
    if es_admin:
        col_s, col_b, _ = st.columns([1, 1, 2])
        if col_s.button("💾 GUARDAR CAMBIOS TABLA"):
            for _, row in df_editado.iterrows():
                upd = {"rma_number": row['rma_number'], "informacion": row['informacion'], "enviado": row['enviado']}
                supabase.table("inventario_rma").update(upd).eq("id", row['id']).execute()
            st.rerun()
        
        seleccionados = df_editado[df_editado.get('Seleccionar', False) == True]
        if not seleccionados.empty and col_b.button(f"🗑️ BORRAR ({len(seleccionados)})"):
            for id_db in seleccionados['id'].tolist():
                supabase.table("inventario_rma").delete().eq("id", id_db).execute()
            st.rerun()

    # --- MODO DE MODIFICACIÓN PARA USER (MANERA ANTERIOR) ---
    st.markdown("---")
    with st.expander("🛠️ Modificar Registro Existente (Modo Manual)"):
        col_sel, col_form = st.columns([1, 2])
        
        # 1. Seleccionar el RMA a editar
        lista_rmas = df['rma_number'].tolist()
        rma_a_editar = col_sel.selectbox("Seleccione RMA para modificar:", ["Seleccionar..."] + lista_rmas)
        
        if rma_a_editar != "Seleccionar...":
            # Obtener datos actuales
            item = df[df['rma_number'] == rma_a_editar].iloc[0]
            
            with col_form.form("edit_manual"):
                m_ticket = st.text_input("Ticket", value=str(item.get('n_ticket', '')))
                m_emp = st.text_input("Empresa", value=item['empresa'])
                m_mod = st.text_input("Modelo", value=item['modelo'])
                m_est = st.selectbox("Estado", ["En proceso", "FINALIZADO"], 
                                   index=0 if item['informacion'] == "En proceso" else 1)
                m_env = st.selectbox("Enviado", ["NO", "YES"], 
                                   index=0 if item['enviado'] == "NO" else 1)
                
                if st.form_submit_button("ACTUALIZAR DATOS"):
                    upd_data = {
                        "n_ticket": m_ticket, "empresa": m_emp, 
                        "modelo": m_mod, "informacion": m_est, "enviado": m_env
                    }
                    supabase.table("inventario_rma").update(upd_data).eq("id", item['id']).execute()
                    st.success(f"RMA {rma_a_editar} actualizado correctamente.")
                    st.rerun()
else:
    st.info("No hay datos.")
