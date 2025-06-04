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


def Crear_Cuerpo_Correo_HTML(CUERPO_EMAIL, CLIENTE, datos_muestras, DATOS_TRAZAS=None):

    id_proceso = datos_muestras[0].get(
        'IDPROCESSO', 'N/A') if datos_muestras else 'N/A'
    url_ceimic_base = "https://clink.ceimic.com/clink/validator.php?lng=2&codigo="

    # Construir la sección de trazas
    trazas_html = "<p></p>"
    if DATOS_TRAZAS is not None and len(DATOS_TRAZAS.strip()) > 0: # Verificar si DATOS_TRAZAS tiene contenido
        trazas_html = f"<p>Traza de las muestras:</p>{DATOS_TRAZAS}"
    
    # Construir la tabla de muestras y enlaces
    muestras_tabla_html = ""
    if datos_muestras:
        muestras_tabla_html = """
        <p style="text-align: center; margin-top: 20px;">
            A continuación, el detalle de sus informes de ensayo:
        </p>
        <table style="width: 100%; border-collapse: collapse; margin: 0 auto; text-align: center;">
            <thead>
                <tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px; border: 1px solid #dddddd;">Número de Informe</th>
                    <th style="padding: 10px; border: 1px solid #dddddd;">Acceso al Informe</th>
                </tr>
            </thead>
            <tbody>
        """
        
        # Usar un conjunto para almacenar tuplas de identificadores de muestra ya procesados
        muestras_procesadas = set()

        for muestra in datos_muestras:
            cdamostra = muestra.get('CDAMOSTRA')
            nrcontrole1 = muestra.get('NRCONTROLE1')
            nrcontrole2 = muestra.get('NRCONTROLE2')

            # Crear una tupla con los identificadores para verificar duplicados
            identificador_muestra = (cdamostra, nrcontrole1, nrcontrole2)

            # Si la muestra ya fue procesada, saltar a la siguiente
            if identificador_muestra in muestras_procesadas:
                continue
            
            # Si no ha sido procesada, añadirla al conjunto y procesar
            muestras_procesadas.add(identificador_muestra)

            num_muestra = muestra.get('NUMMUESTRA', 'N/A')
            chave_publicacao = muestra.get('CHAVEPUBLICACAO')
            
            link_informe = "No disponible"
            if chave_publicacao:
                url_validator = f"{url_ceimic_base}{chave_publicacao}"
                link_informe = f'<a href="{url_validator}" style="color: #004a99; text-decoration: none; font-weight: bold;">Ver Informe</a>'
            
            muestras_tabla_html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #dddddd;">{num_muestra}</td>
                    <td style="padding: 10px; border: 1px solid #dddddd;">{link_informe}</td>
                </tr>
            """
        muestras_tabla_html += """
            </tbody>
        </table>
        """

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
            .button-link {{
                display: inline-block;
                background-color: #28a745; /* Un verde vibrante para el botón */
                color: #ffffff !important; /* !important para asegurar que el color del texto sea blanco */
                padding: 12px 25px;
                border-radius: 5px;
                text-decoration: none;
                font-weight: bold;
                margin-top: 20px;
                transition: background-color 0.3s ease;
            }}
            .button-link:hover {{
                background-color: #218838;
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
            tr:nth-child(even) {{
                background-color: #f9f9f9;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h2>Notificación de Informe de Ensayo</h2>
            </div>
            <div class="email-content">
                <p>Estimado(a) <strong>{CLIENTE}</strong>,</p>
                <p>Le informamos que los informes de ensayo ya se encuentran en línea para su visualización y descarga, pertenecientes a:</p>

                <p>{CUERPO_EMAIL}</p>
                {trazas_html}
                {muestras_tabla_html} 
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

