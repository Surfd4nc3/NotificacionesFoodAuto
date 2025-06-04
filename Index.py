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
        muestras_formato_sql = '3246923'
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
            # almacentar el TOEMAIL de la lista de datos de muestra que no se repitan, estan ya separados por  ";" pero no quiero repetidos
            to_email = set()
            for muestra in datos_muestras:
                if 'TOEMAIL' in muestra and muestra['TOEMAIL']:
                    to_email.update(muestra['TOEMAIL'].split(';'))
            to_email = ';'.join(to_email)
            # print(f"To Email Correos: {to_email}")
            # ahora el CC Email
            cc_email = set()
            for muestra in datos_muestras:
                if 'CCEMAIL' in muestra and muestra['CCEMAIL']:
                    cc_email.update(muestra['CCEMAIL'].split(';'))
            cc_email = ';'.join(cc_email)
            # el asunto va "Resultado de ensayo " seguiddo de os ccdamostra de la lsita
            bcc_email = DESTINATARIO_BCC_POR_DEFECTO
            # asunto = f"Resultado de ensayo {'; '.join(str(muestra['NUMMUESTRA']) for muestra in datos_muestras)}"
            asunto = "CEIMIC | Notificación de informe de ensayo"

            codigos_muestras_para_trazas = [
                str(muestra['CDAMOSTRA']) for muestra in datos_muestras]

            # PARA ALMACENAR LOC NUMMUESTRA SEGUIDO DE CODIGO_PRODDUCTOR CCONCATENADDOS
            codigos_productos = set()
            for muestra in datos_muestras:
                if 'NUMMUESTRA' in muestra and 'CODIGO_PRODDUCTOR' in muestra:
                    codigos_productos.add(
                        f"- Numero de informe {muestra['NUMMUESTRA']}{f'-{muestra['CODIGO_PRODDUCTOR']}' if muestra.get('CODIGO_PRODDUCTOR') else ''}\n")
            codigos_productos_str = ''.join(codigos_productos)
            print(f"{codigos_productos_str}")

            # Llamar a extraer_trazas con la lista de códigos de muestras
            trazas_resultados = extraer_trazas(codigos_muestras_para_trazas)
            CUERPO_EMAIL = ''
            # validar con un if si trazas_resultados no trae ada o esta vacio y con un else ostrar las muestrass que se extraen de penddientes
            CUERPOO_TRAZAS = ''
            if trazas_resultados is not None and len(trazas_resultados) > 0:
                # Agrupar trazas por CDAMOSTRA
                trazas_por_muestra = defaultdict(list)
                for traza in trazas_resultados:
                    trazas_por_muestra[traza['CDAMOSTRA']].append(traza)

                CUERPOO_TRAZAS = "Trazas encontradas:\n"
                for cdamostra, trazas in trazas_por_muestra.items():
                    CUERPOO_TRAZAS += f"   Muestra {cdamostra}:\n"
                    for traza in trazas:
                        CUERPOO_TRAZAS += f"      - {traza['TRAZA']} ({traza['VALOR']})\n"
                # print(f" se encontraron trazas para las muestras pendientes, {len(trazas_resultados)} trazas encontradas.\n{CUERPO_EMAIL}")
            else:
                CUERPO_EMAIL = "Lista de Muestras Pendientes:\n"
                for muestra in datos_muestras:
                    CUERPO_EMAIL += f"   - {muestra['CDAMOSTRA']}\n"
                # print(f" se observan solo muestras totales pendientes, no se encontraron trazas.{CUERPO_EMAIL}")
            # Crear el cuerpo del correo
            print(f"imprimir cuerpo correo\n")
            cuerpo_correo = Crear_Cuerpo_Correo_HTML(
                codigos_productos_str, cliente, datos_muestras,CUERPOO_TRAZAS)
            # enviar correo
            to_email = DESTINATARIO_TO_POR_DEFECTO
            cc_email = DESTINATARIO_CC_POR_DEFECTO
            bcc_email = DESTINATARIO_BCC_POR_DEFECTO
            # ENVIAR EMAIL

            RESP_ENVIO = EnnviarCorreo(
                asunto,
                cuerpo_correo,
                to_email,
                cc_email,
                bcc_email

            )
            # POBLAR LA TABLA DE NOTIFICACIONESINFORMESPERFOODD
            if RESP_ENVIO:
                manejador_bdclink = ManejadorConexionSQL("BDClink_conn")
                conexion_bdclink = manejador_bdclink.conectar()

                if conexion_bdclink:
                    for muestra in datos_muestras:
                        insert_params = (
                            muestra['CDAMOSTRA'],
                            muestra['NRCONTROLE1'],
                            muestra['NRCONTROLE2'],
                            muestra['NRCONTROLE3'],
                            1,
                            None,
                            to_email,
                            cc_email,
                            bcc_email,
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
                # Este else ya lo tenías, ahora es para cuando el envío falla
                print(
                    f"El envío del correo falló para el cliente {cliente}. No se registrarán las muestras como procesadas.")

    else:
        print("Error al obtener los datos de pendientes o procesados.")
