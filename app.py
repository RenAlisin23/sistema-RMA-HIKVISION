import streamlit as st
from supabase import create_client
import pandas as pd

# 1. CONEXIÓN CON BASE DE DATOS
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase = create_client(URL, KEY)
except:
    st.error("Error: No se encontraron las llaves de conexión en Secrets.")

st.set_page_config(page_title="Gestión RMA Hikvision", layout="wide")

# Estilo personalizado se puede mejorar la forma de presentación
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("Sistema de Control de Inventario RMA")

# --- SECCIÓN 1: REGISTRO DE NUEVOS EQUIPOS -----------------------------------------------------------------------------------------
with st.expander("REGISTRAR NUEVO INGRESO", expanded=False):
    with st.form("formulario_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            rma = st.text_input("RMA Number")
            n_rq = st.text_input("Nº RQ")
            empresa = st.text_input("Empresa")
        with col2:
            ticket = st.text_input("Nº Ticket")
            modelo = st.text_input("Modelo")
            sn = st.text_input("Serial Number (S/N)")
        with col3:
            info = st.selectbox("Información", ["En proceso", "FINALIZADO"])
            coments = st.text_area("Comentarios")
        
        enviar = st.form_submit_button("Guardar en Base de Datos")
        
        if enviar:
            if not rma or not empresa:
                st.warning("El RMA y la Empresa son obligatorios.")
            else:
                nuevo_dato = {
                    "rma_number": rma, "n_rq": n_rq, "empresa": empresa,
                    "n_ticket": ticket, "modelo": modelo, "serial_number": sn,
                    "informacion": info, "comentarios": coments, "enviado": "NO"
                }
                supabase.table("inventario_rma").insert(nuevo_dato).execute()
                st.success(f"Equipo {rma} registrado con éxito.")
                st.rerun()

st.divider()

# --- SECCIÓN 2: BUSCADOR Y TABLA DE LECTURA ---
st.subheader("🔍 Buscador de Equipos")
busqueda = st.text_input("Buscar por Empresa, RMA o Serial Number...", placeholder="Ejemplo: DNT o RB_PE...")

# Obtener datos de Supabase
res = supabase.table("inventario_rma").select("*").order("fecha_registro", desc=True).execute()

if res.data:
    df = pd.DataFrame(res.data)
    
    # Lógica del Buscador 
    if busqueda:
        # Esto busca la palabra en cualquiera de las 3 columnas y muestra todas las coincidencias
        df_filtrado = df[
            df['empresa'].str.contains(busqueda, case=False, na=False) | 
            df['rma_number'].str.contains(busqueda, case=False, na=False) |
            df['serial_number'].str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_filtrado = df

    # Mostrar la tabla (Solo lectura)
    columnas_visibles = ["rma_number", "n_rq", "empresa", "modelo", "serial_number", "informacion", "fecha_registro"]
    
    st.write(f"Mostrando {len(df_filtrado)} registros:")
    st.dataframe(
        df_filtrado[columnas_visibles], 
        use_container_width=True,
        hide_index=True 
    )
else:
    st.info("La base de datos está vacía.")
