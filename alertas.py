import pandas as pd
from datetime import datetime, timezone
from supabase import create_client
import resend
import os

# Configuración de conexión (Usaremos variables seguras)
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
resend.api_key = os.environ.get("RESEND_API_KEY")

def enviar_alertas():
    supabase = create_client(URL, KEY)
    
    # 1. Obtener correos de la tabla lista_contactos
    res_contactos = supabase.table("lista_contactos").select("email").execute()
    destinatarios = [c['email'] for c in res_contactos.data]
    
    if not destinatarios:
        print("No hay destinatarios configurados.")
        return

    # 2. Obtener equipos que NO han sido enviados 
    res_rma = supabase.table("inventario_rma").select("*").neq("enviado", "YES").execute()
    df = pd.DataFrame(res_rma.data)

    if df.empty:
        print("No hay equipos pendientes de envío.")
        return

    # 3. Cálculo de los 30 días
    # Convertimos la fecha a formato 
    df['fecha_registro'] = pd.to_datetime(df['fecha_registro'], utc=True)
    hoy = datetime.now(timezone.utc)
    
    # Calculamos la diferencia
    df['dias_HQ'] = (hoy - df['fecha_registro']).dt.days

    # Filtramos: Solo los que tienen 30 días o más
    vencidos = df[df['dias_HQ'] >= 30]

    if not vencidos.empty:
        filas_html = ""
        for _, fila in vencidos.iterrows():
            filas_html += f"""
                <tr>
                    <td style='padding:8px; border:1px solid #ddd;'>{fila['rma_number']}</td>
                    <td style='padding:8px; border:1px solid #ddd;'>{fila['serial_number']}</td>
                    <td style='padding:8px; border:1px solid #ddd;'>{fila['empresa']}</td>
                    <td style='padding:8px; border:1px solid #ddd; color:red;'><b>{fila['dias_HQ']} días</b></td>
                </tr>
            """

        # Enviamos el correo a través de Resend
        resend.Emails.send({
            "from": "RMA Tracker <onboarding@resend.dev>",
            "to": destinatarios,
            "subject": f"ATENCIÓN: {len(vencidos)} equipos con +30 días",
            "html": f"""
                <h2>Reporte de Equipos de más de 30 dias</h2>
                <p>Los siguientes equipos superaron el límite de 30 días en HQ:</p>
                <table style='border-collapse:collapse; width:100%;'>
                    <tr style='background:#f2f2f2;'><th>RMA</th><th>S/N</th><th>Empresa</th><th>Días</th></tr>
                    {filas_html}
                </table>
            """
        })
        print(f"Alerta enviada a {len(destinatarios)} personas.")

if __name__ == "__main__":
    enviar_alertas()
