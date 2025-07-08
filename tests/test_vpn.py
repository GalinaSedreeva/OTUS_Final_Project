import subprocess
import paramiko
import requests
import pytest
import os

# Настройки
VPN_SERVER_IP = "172.20.0.10"
WEB_SERVER_IP =  "http://172.21.0.20"
WG_INTERFACE = "wg0"
R_TIMEOUT = 5

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def connect_vpn(): 
    run_cmd("wg-quick up /etc/wireguard/wg0.conf")

def disconnect_vpn(): 
    run_cmd("wg-quick down wg0")

# Тест 1: Проверяем, что без VPN web-сервер недоступен
def test_webserver_unreachable_without_vpn():
    disconnect_vpn()
    # result = run_cmd(f"curl -s http://{WEB_SERVER_IP}")
    # assert "Connection refused" in result.stderr or result.returncode != 0

    with pytest.raises(requests.exceptions.RequestException) as exc_info:
        # Отправляем GET-запрос с ограничением по времени
        requests.get(WEB_SERVER_IP, timeout=R_TIMEOUT)

    # Получаем возбуждённое исключение
    exception = exc_info.value

    # Проверяем типы ошибок, которые говорят о недоступности сервера
    assert isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RetryError
    )), f"Ожидалась ошибка подключения, получено: {type(exception).__name__}"

# Тест 2: Запускаем VPN и проверяем, что клиент подключён
def test_vpn_client_connection():
    connect_vpn()
    result = run_cmd("wg show")
#    assert WG_INTERFACE in result.stdout
    # Проверяем, что интерфейс существует и содержит нужный peer
    assert "wg0" in result.stdout
    assert "peer:" in result.stdout
   # disconnect_vpn()

# Тест 3: Проверяем доступность веб-сервера через VPN
def test_webserver_reachable_with_vpn():
   # connect_vpn()
    response = requests.get(WEB_SERVER_IP, timeout=R_TIMEOUT)
    assert response.status_code == 200

# Тест 4: Проверяем маршрутизацию через VPN
def test_vpn_routing():
    #connect_vpn()
    result = run_cmd("ip route")
    assert "172.21.0.0/24" in result.stdout
    disconnect_vpn()

# Тест 5: Подключаемся к серверу по SSH и проверяем соединение на стороне сервера
def test_server_side_connection():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    #os.chmod("/root/.ssh/id_rsa", 0o600)  # Установим правильные права

    ssh.connect(hostname=VPN_SERVER_IP, 
                username="root", 
                #key_filename="/root/.ssh/id_rsa" ) # Путь к приватному ключу внутри контейнера

                password="123")  # или использовать ключ
    stdin, stdout, stderr = ssh.exec_command("wg show")
    output = stdout.read().decode()
    ssh.close()
    assert "peer" in output