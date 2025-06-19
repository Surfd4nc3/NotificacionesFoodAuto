import os
import logging
# Importamos defaultdict para facilitar la agrupación
from collections import defaultdict
from conexion import ManejadorConexionSQL
from consultas import CONSULTA_EXTRAE_PENDDIENTES, INSERTA_PROCESADOS, GET_PROCESADOS, CONSULTA_TRAZAS
from armarCuerpo import Crear_Cuerpo_Correo_HTML, EnnviarCorreo
from configuracion_correo import DESTINATARIO_BCC_POR_DEFECTO, DESTINATARIO_TO_POR_DEFECTO, DESTINATARIO_CC_POR_DEFECTO


def pendientes():
    manejador_myLimsConxion = ManejadorConexionSQL("myLIMS_Novo_conn")
    conexionMylims = manejador_myLimsConxion.conectar()

    if conexionMylims:
        resultadosPendientes = manejador_myLimsConxion.ejecutar_consulta(
            CONSULTA_EXTRAE_PENDDIENTES)
        manejador_myLimsConxion.cerrar()
        return resultadosPendientes
    else:
        return None


def procesados():
    manejador_myLimsConxion = ManejadorConexionSQL("BDClink_conn")
    conexionMylims = manejador_myLimsConxion.conectar()

    if conexionMylims:
        resultadosProcesados = manejador_myLimsConxion.ejecutar_consulta(
            GET_PROCESADOS)
        manejador_myLimsConxion.cerrar()
        return resultadosProcesados
    else:
        return None


def extraer_trazas(cod_muestras):
    manejador_myLimsConxion = ManejadorConexionSQL("myLIMS_Novo_conn")
    conexionMylims = manejador_myLimsConxion.conectar()

    if conexionMylims:
        muestras_formato_sql = ",".join(
            f"'{str(traza)}'" for traza in cod_muestras)
        # muestras_formato_sql = '3246923'
        # Ahora formateamos la consulta CONSULTA_TRAZAS con los códigos de muestra
        trazas_query = CONSULTA_TRAZAS.format(
            cod_muestras=muestras_formato_sql)

        trazas_resultados = manejador_myLimsConxion.ejecutar_consulta(
            trazas_query)
        manejador_myLimsConxion.cerrar()
        return trazas_resultados
    else:
        return None


if __name__ == "__main__":
    resultados_pendientes = pendientes()
    resultados_procesados = procesados()

    if resultados_pendientes is not None and resultados_procesados is not None:
        pendientes_ids = {(row['CDAMOSTRA'], row['NRCONTROLE1'], row['NRCONTROLE2'],
                           row['NRCONTROLE3']) for row in resultados_pendientes}
        procesados_ids = {(row['CDAMOSTRA'], row['NRCONTROLE1'], row['NRCONTROLE2'],
                           row['NRCONTROLE3']) for row in resultados_procesados}

        pendientes_finales = [row for row in resultados_pendientes if (
            row['CDAMOSTRA'], row['NRCONTROLE1'], row['NRCONTROLE2'], row['NRCONTROLE3']) not in procesados_ids]

        print(f"Pendientes: {len(pendientes_finales)}")
        # --- Agrupando por RAZAOSOCIAL ---
        pendientes_por_cliente = defaultdict(list)
        for row in pendientes_finales:
            cliente = row['RAZAOSOCIAL']
            pendientes_por_cliente[cliente].append(row)

        print("\n--- Resultados Pendientes Agrupados por Cliente ---")
        for cliente, datos_muestras in pendientes_por_cliente.items():
            to_email = set()
            for muestra in datos_muestras:
                if 'TOEMAIL' in muestra and muestra['TOEMAIL']:
                    to_email.update(muestra['TOEMAIL'].split(';'))
            to_email = ';'.join(to_email)

            cc_email = set()
            for muestra in datos_muestras:
                if 'CCEMAIL' in muestra and muestra['CCEMAIL']:
                    cc_email.update(muestra['CCEMAIL'].split(';'))
            cc_email = ';'.join(cc_email)

            bcc_email = DESTINATARIO_BCC_POR_DEFECTO
            asunto = "CEIMIC | Notificación de informe de ensayo"

            codigos_muestras_para_trazas = [
                str(muestra['CDAMOSTRA']) for muestra in datos_muestras]

            # --- Para ALMACENAR LOS NUMMUESTRA SEGUIDO DE CODIGO_PRODDUCTOR CONCATENADOS ---
            # Vamos a construir un string que Crear_Cuerpo_Correo_HTML pueda parsear en una lista HTML
            cuerpo_email_productos_str = ''
            for muestra in datos_muestras:
                # Verificar que NUMMUESTRA no sea None
                if 'NUMMUESTRA' in muestra and muestra.get('NUMMUESTRA') is not None:
                    codigo_productor_display = f"-{muestra['CODIGO_PRODDUCTOR']}" if muestra.get(
                        'CODIGO_PRODDUCTOR') else ''
                    cuerpo_email_productos_str += f"- Numero de informe {muestra['NUMMUESTRA']}{codigo_productor_display}\n"

            # Llamar a extraer_trazas con la lista de códigos de muestras
            trazas_resultados = extraer_trazas(codigos_muestras_para_trazas)

            cuerpo_trazas_html = ''  # Nuevo nombre para el HTML de las trazas
            if trazas_resultados is not None and len(trazas_resultados) > 0:
                trazas_por_muestra = defaultdict(list)
                for traza in trazas_resultados:
                    trazas_por_muestra[traza['CDAMOSTRA']].append(traza)

                # Construir el string de trazas en un formato que se pueda convertir a HTML con viñetas en armarCuerpo.py
                cuerpo_trazas_html = ""
                for cdamostra, trazas in trazas_por_muestra.items():
                    # Encuentra el NUMMUESTRA correspondiente para este CDAMOSTRA
                    num_muestra_asociado = 'N/A'
                    for dm in datos_muestras:
                        # Asegúrate de comparar CDAMOSTRA como string si uno es int y el otro string
                        if str(dm.get('CDAMOSTRA')) == str(cdamostra):
                            num_muestra_asociado = dm.get('NUMMUESTRA', 'N/A')
                            # Si 'CODIGO_PRODDUCTOR' existe y no es None, lo añadimos al num_muestra_asociado
                            if dm.get('CODIGO_PRODDUCTOR'):
                                num_muestra_asociado = f"{num_muestra_asociado}-{dm['CODIGO_PRODDUCTOR']}"
                            break

                    # Construir la lista de trazas para esta muestra, separadas por comas
                    trazas_para_linea = []
                    for traza in trazas:
                        traza_nombre = traza.get('TRAZA', 'N/A')
                        traza_valor = traza.get('VALOR', 'N/A')
                        trazas_para_linea.append(
                            f"{traza_nombre} ({traza_valor})")

                    # Unir todas las trazas de esta muestra con comas
                    trazas_concatenadas = ", ".join(trazas_para_linea)

                    # Formatear la línea como "(NUMMUESTRA_CON_PRODUCTOR) Numero de informe: TRACE1 (VALUE1), TRACE2 (VALUE2)"
                    cuerpo_trazas_html += f"({num_muestra_asociado}) Numero de informe: {trazas_concatenadas}\n"
            else:
                cuerpo_trazas_html = ""  # Si no hay trazas, pasa un string vacío

            # Crear el cuerpo del correo
            print(f"imprimir cuerpo correo\n")
            cuerpo_correo = Crear_Cuerpo_Correo_HTML(
                cuerpo_email_productos_str,  # Se pasa la lista de productos formateada
                cliente,
                datos_muestras,  # Mantener esto para la tabla de abajo, ya que ya se encarga de los únicos
                cuerpo_trazas_html  # Se pasa el string de trazas formateado
            )
            # enviar correo
            to_email_final = DESTINATARIO_TO_POR_DEFECTO
            cc_email_final = DESTINATARIO_CC_POR_DEFECTO
            bcc_email_final = DESTINATARIO_BCC_POR_DEFECTO

            # ENVIAR EMAIL
            RESP_ENVIO = EnnviarCorreo(
                asunto,
                cuerpo_correo,
                to_email_final,
                cc_email_final,
                bcc_email_final
            )
            # POBLAR LA TABLA DE NOTIFICACIONESINFORMESPERFOODD
            if RESP_ENVIO:
                manejador_bdclink = ManejadorConexionSQL("BDClink_conn")
                conexion_bdclink = manejador_bdclink.conectar()

                if conexion_bdclink:
                    # Se insertan todas las muestras que estaban en pendientes_finales y se procesaron.
                    # Asumo que la lógica de "procesado" es registrar el intento de envío.
                    for muestra in datos_muestras:
                        insert_params = (
                            muestra['CDAMOSTRA'],
                            muestra['NRCONTROLE1'],
                            muestra['NRCONTROLE2'],
                            muestra['NRCONTROLE3'],
                            # Estado: Enviado (o el que corresponda a "procesado")
                            1,
                            None,  # DTENVIO, puedes poner datetime.now() aquí si quieres
                            to_email_final,  # Usar los emails finales utilizados para el envío
                            cc_email_final,
                            bcc_email_final,
                            cuerpo_correo,
                            asunto
                        )
                        manejador_bdclink.ejecutar_consulta(
                            INSERTA_PROCESADOS, insert_params)
                        print(
                            f"Correo enviado y registrado para {cliente} - {muestra['CDAMOSTRA']}")
                    # Cerrar la conexión UNA VEZ después de todas las inserciones del cliente
                    manejador_bdclink.cerrar()
                else:
                    print(
                        f"Error al conectar a la base de datos 'BDClink_conn' para insertar procesados para el cliente {cliente}.")
            else:
                print(
                    f"El envío del correo falló para el cliente {cliente}. No se registrarán las muestras como procesadas.")

    else:
        print("Error al obtener los datos de pendientes o procesados.")
