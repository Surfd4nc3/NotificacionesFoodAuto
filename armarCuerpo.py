import smtplib
from email.mime.multipart import MIMEMultipart
from email .mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
import re
from configuracion_correo import (
    SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USA_TLS,
    REMITENTE_NOMBRE, REMITENTE_EMAIL
)
logger = logging.getLogger(__name__)


def is_valid_email(email_str):
    """Valida un formato de dirección de correo electrónico."""
    if not email_str or not isinstance(email_str, str):
        return False
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(regex, email_str):
        return True
    logger.warning(f"Formato de email inválido detectado: {email_str}")
    return False


def Crear_Cuerpo_Correo_HTML(CUERPO_EMAIL_PRODUCTOS, CLIENTE, datos_muestras, DATOS_TRAZAS=None):
    # CUERPO_EMAIL_PRODUCTOS se renombró para mayor claridad, ya que contendrá la lista de productos
    
    id_proceso = datos_muestras[0].get(
        'IDPROCESSO', 'N/A') if datos_muestras else 'N/A'
    
    # La variable url_ceimic_base ya no es necesaria para la tabla, pero se mantiene por si se usa en otro lado.
    url_ceimic_base = "https://clink.ceimic.com/clink/validator.php?lng=2&codigo="

    # --- Construir la sección de Trazas con viñetas ---
    trazas_html = ""
    if DATOS_TRAZAS is not None and len(DATOS_TRAZAS.strip()) > 0:
        trazas_por_muestra_dict = {}
        current_cdamostra = None

        for linea in DATOS_TRAZAS.strip().split('\n'):
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue

            if linea_limpia.startswith("Muestra"):
                match = re.match(r"Muestra (\d+):", linea_limpia)
                if match:
                    current_cdamostra = match.group(1)
                    trazas_por_muestra_dict[current_cdamostra] = []
            elif linea_limpia.startswith("-") and current_cdamostra:
                trazas_por_muestra_dict[current_cdamostra].append(linea_limpia[1:].strip())

        if trazas_por_muestra_dict:
            trazas_html = "<p>Trazas encontradas:</p><ul>"
            for cdamostra, trazas_list in trazas_por_muestra_dict.items():
                trazas_concatenadas = ", ".join(trazas_list)
                trazas_html += f"<li><strong>Muestra {cdamostra}:</strong> {trazas_concatenadas}</li>"
            trazas_html += "</ul>"
        else:
            trazas_html = "<p></p>"
    else:
        trazas_html = "<p></p>"

    # --- Construir la lista de Números de Informe/Productos con viñetas ---
    productos_html = ""
    if CUERPO_EMAIL_PRODUCTOS:
        productos_html = "<p>Le informamos que los informes de ensayo ya se encuentran en línea para su visualización y descarga, pertenecientes a:</p><ul>"
        items = re.findall(r'- Numero de informe\s*(.*?)(?=\s*- Numero de informe|\s*$)', CUERPO_EMAIL_PRODUCTOS, re.DOTALL)
        for item in items:
            productos_html += f"<li>Numero de informe {item.strip()}</li>"
        productos_html += "</ul>"
    else:
        productos_html = "<p>Le informamos que los informes de ensayo ya se encuentran en línea para su visualización y descarga.</p>"


    # Eliminar duplicados de datos_muestras
    vistas_muestras = set()
    muestras_unicas = []
    for muestra in datos_muestras:
        identificador_muestra = (muestra.get('CDAMOSTRA'), muestra.get('NRCONTROLE1'), muestra.get('NRCONTROLE2'))
        if identificador_muestra not in vistas_muestras:
            vistas_muestras.add(identificador_muestra)
            muestras_unicas.append(muestra)

    # === INICIO DE LA MODIFICACIÓN ===

    # Construir la tabla de informes (solo texto) y el texto del portal con enlace
    muestras_tabla_html = ""
    portal_info_html = "" 

    if muestras_unicas:
        muestras_tabla_html = """
        <p style="text-align: center; margin-top: 20px;">
            A continuación, el detalle de sus informes de ensayo:
        </p>
        <table style="width: 80%; max-width: 400px; border-collapse: collapse; margin: 0 auto; text-align: center;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px; border: 1px solid #dddddd;">Número de Informe</th>
                </tr>
            </thead>
            <tbody>
        """
        for muestra in muestras_unicas:
            num_muestra = muestra.get('NUMMUESTRA', 'N/A')
            display_num_informe = f"{num_muestra}"
            
            # Se añade directamente el número del informe como texto plano, sin enlace.
            muestras_tabla_html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #dddddd;">{display_num_informe}</td>
                </tr>
            """
        muestras_tabla_html += """
            </tbody>
        </table>
        """

        # Texto mejorado con hipervínculo para mostrar debajo de la tabla
        portal_info_html = """
        <p style="text-align: center; margin-top: 25px; font-size: 14px; color: #555555;">
            Para visualizar sus resultados y/o descargar su informe, ingrese a nuestro portal:<br>
            <a href="http://myclink.ceimic.com/" style="color: #004a99; font-weight: bold; text-decoration: none;">http://myclink.ceimic.com/</a>
        </p>
        """
    # === FIN DE LA MODIFICACIÓN ===


    # Estilos CSS en línea para asegurar la compatibilidad con la mayoría de clientes de correo
    html_cuerpo = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resultado de Informe de Ensayo</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol';
                line-height: 1.6;
                color: #333333;
                background-color: #f4f5f7;
                margin: 0;
                padding: 20px;
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 6px 25px rgba(0,0,0,0.08);
                border: 1px solid #dee2e6;
            }}
            .email-header {{
                background-color: #004a99; /* Azul corporativo */
                color: #ffffff;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                text-align: center;
                margin: -30px -30px 20px -30px; /* Ajuste para que ocupe todo el ancho del contenedor */
            }}
            .email-header h2 {{
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .email-content p {{
                margin-bottom: 15px;
                font-size: 15px;
                color: #555555;
            }}
            .email-content strong {{
                color: #004a99;
            }}
            .email-footer {{
                margin-top: 30px;
                padding-top: 20px;
                font-size: 13px;
                color: #777777;
                text-align: center;
                border-top: 1px solid #e9ecef;
            }}
            .email-footer p {{
                margin: 5px 0;
            }}
            a {{
                color: #004a99;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 10px;
                border: 1px solid #dddddd;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h2>Notificación de Informe de Ensayo</h2>
            </div>
            <div class="email-content">
                <p>Estimados <strong>{CLIENTE}</strong>,</p>
                {productos_html}
                {trazas_html}
                {muestras_tabla_html} 
                {portal_info_html}
            </div>
            <div class="email-footer">
                <p>Atentamente,</p>
                <p><strong>Ceimic Perú - Informe de Ensayo</strong></p>
                <p>Laboratorio Ceimic Perú</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_cuerpo



def EnnviarCorreo(ASUNTO, CUERPO, TO_EMAIL, CC_EMAIL, BCC_EMAIL):
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        logger.error("Falta información de configuración del servidor SMTP.")
        return False
    msg = MIMEMultipart('alternaative')

    msg['from'] = f"{REMITENTE_NOMBRE}"
    lista_to_validos = []
    if isinstance(TO_EMAIL, str):
        for email in TO_EMAIL.split(';'):
            email_limpio = email.strip()
            if is_valid_email(email_limpio):
                lista_to_validos.append(email_limpio)
    elif isinstance(TO_EMAIL, list):
        for email in TO_EMAIL:
            if is_valid_email(email):
                lista_to_validos.append(email.strip())

    if not lista_to_validos:
        logger.error(
            "No se proporcionaron direcciones de correo electrónico válidas para TO_EMAIL.")
        return False

    lista_cc_validos = []
    if isinstance(CC_EMAIL, str):
        for email in CC_EMAIL.split(';'):
            email_limpio = email.strip()
            if is_valid_email(email_limpio):
                lista_cc_validos.append(email_limpio)
    elif isinstance(CC_EMAIL, list):
        for email in CC_EMAIL:
            if is_valid_email(email):
                lista_cc_validos.append(email.strip())
    msg['Subject'] = ASUNTO

    lista_bcc_validos = []
    if isinstance(BCC_EMAIL, str):
        for email in BCC_EMAIL.split(';'):
            email_limpio = email.strip()
            if is_valid_email(email_limpio):
                lista_bcc_validos.append(email_limpio)
    elif isinstance(BCC_EMAIL, list):
        for email in BCC_EMAIL:
            if is_valid_email(email):
                lista_bcc_validos.append(email.strip())

    msg.attach(MIMEText(CUERPO, 'html', 'utf-8'))

    todos_los_destinatarios_finales = lista_to_validos + lista_cc_validos + lista_bcc_validos
    msg['To'] = ', '.join(lista_to_validos)
    msg['Cc'] = ', '.join(lista_cc_validos)
    msg['Bcc'] = ', '.join(lista_bcc_validos)

    if not todos_los_destinatarios_finales:
        logger.error("No hay destinatarios válidos (To, Cc, o Bcc) después de la validación. No se enviará el correo.")
        return False
    try:
        server=None
        logger.info(f"Conectando al servidor SMTP: {SMTP_SERVER}:{SMTP_PORT}")
        if SMTP_USA_TLS or SMTP_PORT==587:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.ehlo() # Saludo al servidor
            server.starttls() # Iniciar conexión TLS
            server.ehlo() # Saludo de nuevo después de TLS
        elif SMTP_PORT == 465: # Para SSL directo
             server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
             server.ehlo() # Saludo al servidor (opcional para SMTP_SSL pero no daña)
        else: # Conexión sin encriptar (no recomendado)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.ehlo()
        logger.info(f"Intentando login SMTP con usuario {SMTP_USER}")
        server.login(SMTP_USER, SMTP_PASSWORD)
        logger.info("Login SMTP exitoso.")
        
        server.sendmail(REMITENTE_EMAIL, todos_los_destinatarios_finales, msg.as_string())
        server.quit()
        logger.info(f"Correo enviado exitosamente con smtplib a: {', '.join(lista_to_validos)}")
        return True
    except smtplib.SMTPAuthenticationError as e_auth:
        logger.error(f"Error de AUTENTICACIÓN SMTP con smtplib: {e_auth}", exc_info=True)
        logger.error("CAUSA MÁS PROBABLE: Credenciales incorrectas o la cuenta requiere una 'Contraseña de Aplicación' debido a MFA en Office 365.")
        return False
    except smtplib.SMTPConnectError as e_conn:
        logger.error(f"Error de CONEXIÓN SMTP al servidor {SMTP_SERVER}:{SMTP_PORT}. Error: {e_conn}", exc_info=True)
        return False
    except smtplib.SMTPServerDisconnected as e_disconn:
        logger.error(f"Servidor SMTP desconectado inesperadamente. Error: {e_disconn}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Error general al enviar el correo con smtplib: {e}", exc_info=True)
        return False

