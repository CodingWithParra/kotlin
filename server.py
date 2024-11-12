import requests
import time
import subprocess

# Configuración
prometheus_url = "http://localhost:9090/api/v1/query"  # Cambia localhost por la IP o URL de Prometheus TODO What do you mean?
consulta1 = '(100 - avg(rate(node_cpu_seconds_total{mode="idle"}[10s])) * 100)'  # Consulta de CPU
consulta2 = 'avg((node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes) * 100'  # Consulta de RAM
umbral_superior = 80  # Umbral superior para CPU y RAM.
umbral_inferior = 10  # Umbral inferior para CPU.
duracion_esperada = 60  # Tiempo en segundos que el valor debe estar en el umbral para ejecutar el script
intervalo_verificacion = 15  # Intervalo en segundos para cada consulta

# Función para consultar Prometheus
def consultar_prometheus(query):
    try:
        response = requests.get(prometheus_url, params={'query': query})
        response.raise_for_status()  # Verifica si la solicitud fue exitosa
        resultado = response.json()

        # Validar que la respuesta tenga datos
        if resultado['data']['result']: # TODO Qué debería tener resultado[data][result]
            valor = float(resultado['data']['result'][0]['value'][1])
            return valor
        else:
            return None
    except requests.RequestException as e:
        print(f"Error en la consulta a Prometheus: {e}")
        return None

# Variables para el tiempo acumulado en umbrales
tiempo_acumulado_superior = 0
tiempo_acumulado_inferior = 0
estado_actual = None

while True:
    uso_cpu = consultar_prometheus(consulta1)
    uso_ram = consultar_prometheus(consulta2)
    
    if uso_cpu is not None:
        print(f"Uso de CPU: {uso_cpu}%")
    else:
        print("No se pudo obtener el valor de uso de CPU de Prometheus.")

    if uso_ram is not None:
        print(f"Uso de RAM: {uso_ram}%")
    else:
        print("No se pudo obtener el valor de uso de RAM de Prometheus.")

    # Verifica si el uso de CPU o RAM está por encima del umbral superior
    if uso_cpu is not None and uso_ram is not None:
            if uso_cpu >= umbral_superior or uso_ram >= umbral_superior:
                # Cambia al estado "superior"
                if estado_actual != "superior":
                    tiempo_acumulado_inferior = 0  # Reinicia tiempo inferior
                    estado_actual = "superior"

                tiempo_acumulado_superior += intervalo_verificacion
                print(f"Tiempo acumulado sobre el umbral superior: {tiempo_acumulado_superior} segundos")

                # Ejecutar script si se ha superado la duración esperada en el umbral superior
                if tiempo_acumulado_superior >= duracion_esperada:
                    print("Umbral superior alcanzado durante el tiempo definido, ejecutando script superior...")
                    subprocess.run(["/home/juan/up_machine.sh"])  # Cambia por la ruta del script a ejecutar
                    tiempo_acumulado_superior = 0  # Reiniciar el contador después de ejecutar el script

            elif uso_cpu <= umbral_inferior:
                # Cambia al estado "inferior"
                if estado_actual != "inferior":
                    tiempo_acumulado_superior = 0  # Reinicia tiempo superior
                    estado_actual = "inferior"

                tiempo_acumulado_inferior += intervalo_verificacion
                print(f"Tiempo acumulado bajo el umbral inferior: {tiempo_acumulado_inferior} segundos")

                # Ejecutar script si se ha superado la duración esperada en el umbral inferior
                if tiempo_acumulado_inferior >= duracion_esperada:
                    resultado = subprocess.run(
                        "cat /home/juan/up_machine.sh | grep '^NEXT_MACHINE_NUM=' | cut -d'=' -f2 | tr -d '\"'",
                        shell=True,  # Permite usar el comando como una sola cadena
                        capture_output=True,
                        text=True  # Devuelve la salida como una cadena
                    )

                    # Obtiene el valor de la salida y elimina posibles espacios en blanco
                    valor_obtenido = resultado.stdout.strip()

                    # Compara el valor y ejecuta el script si es necesario
                    if valor_obtenido != "2":
                        print("Umbral inferior alcanzado durante el tiempo definido, ejecutando script inferior...")
                        subprocess.run(["/home/juan/down_machine.sh"])  # Cambia por la ruta del script a ejecutar
                        tiempo_acumulado_inferior = 0  # Reiniciar el contador después de ejecutar el script

                    else:
                        print("No se ha tumbado la maquina ya que es la unica existente")

    else:
        # Si no está en ningún umbral, reiniciar contadores y estado
        tiempo_acumulado_superior = 0
        tiempo_acumulado_inferior = 0
        estado_actual = None

    # Esperar el intervalo definido antes de la próxima consulta
    time.sleep(intervalo_verificacion)