import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import resend
import os

# Configuración (GitHub Actions llenará esto solo)
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
resend.api_key = os.environ.get("RESEND_API_KEY")

def enviar_alertas():
    supabase = create_client(URL, KEY)
    
    # 1. Obtener destinatarios
    res_contactos = supabase.table("lista_contactos").select("email").execute()
    destinatarios = [c['email'] for c in res_contactos.data]
    
    if not destinatarios:
        print("Error: No hay destinatarios en 'lista_contactos'.")
        return

    # 2. Obtener equipos donde enviado sea distinto a 'YES'
    # Esto asegura que si está vacío, 'NO' o cualquier cosa distinta a 'YES', se incluya.
    res_rma = supabase.table("inventario_rma").select("*").neq("enviado", "YES").execute()
    df = pd.DataFrame(res_rma.data)

    if df.empty:
        print("Todo al día: No hay equipos pendientes.")
        return

    # 3. Lógica de tiempo
    df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], utc=True)
    hoy = datetime.now(timezone.utc)
    df['dias_HQ'] = (hoy - df['fecha_registro']).dt.days

    # Filtro de 30 días
    vencidos = df[df['dias_HQ'] >= 30]

    if not vencidos.empty:
        filas_html = ""
        for _, fila in vencidos.iterrows():
            filas_html += f"""
                <tr>
                    <td style='padding:10px; border:1px solid #444; color:#eee;'>{fila['rma_number']}</td>
                    <td style='padding:10px; border:1px solid #444; color:#eee;'>{fila['empresa']}</td>
                    <td style='padding:10px; border:1px solid #444; color:red;'><b>{fila['dias_HQ']} días</b></td>
                </tr>
            """

        # Envió de correo
        resend.Emails.send({
            "from": "RMA Alerta <onboarding@resend.dev>",
            "to": destinatarios,
            "subject": f"⚠️ URGENTE: {len(vencidos)} equipos estancados (+30 días)",
            "html": f"""
                <div style='background-color:#111; color:#fff; padding:20px; font-family:sans-serif;'>
                    <h2 style='color:#eb1c24;'>Reporte Crítico de Equipos</h2>
                    <p>Los siguientes equipos siguen en el taller y ya superaron los 30 días:</p>
                    <table style='border-collapse:collapse; width:100%; border:1px solid #444;'>
                        <tr style='background:#222; color:#eb1c24;'>
                            <th style='padding:10px; border:1px solid #444;'>RMA</th>
                            <th style='padding:10px; border:1px solid #444;'>Empresa</th>
                            <th style='padding:10px; border:1px solid #444;'>Días</th>
                        </tr>
                        {filas_html}
                    </table>
                    <p style='margin-top:20px; font-size:11px; color:#888;'>
                        Este aviso se repetirá diariamente hasta que el estado cambie a 'YES' en la base de datos.
                    </p>
                </div>
            """
        })
        print(f"Alerta insistente enviada a {len(destinatarios)} correos.")

if __name__ == "__main__":
    enviar_alertas()
