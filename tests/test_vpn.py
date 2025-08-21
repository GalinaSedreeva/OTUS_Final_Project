import allure
import subprocess
import pytest
import requests
import paramiko

# Конфигурация
VPN_SERVER_IP = "172.20.0.10"
WEB_SERVER_IP = "http://172.21.0.20"
WG_INTERFACE = "wg0"
R_TIMEOUT = 5


# Вспомогательные функции с шагами

@allure.step("Выполняем команду: {command}")
def run_cmd(command):
    result = subprocess.run(
        command,
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return result

@allure.description("Тест 1: Проверяем, что без VPN web-сервер недоступен")
@pytest.mark.parametrize("set_vpn_connection", ["disabled"], indirect=True)
@allure.title("Проверка недоступности веб-сервера без VPN")
@allure.feature("Проверка доступности")
def test_webserver_unreachable_without_vpn(set_vpn_connection):
    # with allure.step("Отключаем VPN"):
    #     disconnect_vpn()

    with allure.step("Проверяем, что веб-сервер недоступен"):
        with pytest.raises(requests.exceptions.RequestException) as exc_info:
            requests.get(WEB_SERVER_IP, timeout=R_TIMEOUT)

        exception = exc_info.value
        assert isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RetryError
        )), f"Ожидалась ошибка подключения, получено: {type(exception).__name__}"


@allure.description("Тест 2: Запускаем VPN и проверяем, что клиент подключён")
@pytest.mark.parametrize("set_vpn_connection", ["enabled"], indirect=True)
@allure.title("Проверка подключения клиента через wg show")
@allure.feature("Соединение с VPN")
def test_vpn_client_connection(set_vpn_connection):
    
    with allure.step("Запрашиваем информацию о состоянии WireGuard (wg show)"):
        result = run_cmd("wg show")

    with allure.step("Проверяем успешное выполнение команды 'wg show'"):
        assert result.returncode == 0, f"Команда 'wg show' завершилась с ошибкой. STDERR: {result.stderr}"

    with allure.step("Проверяем наличие интерфейса wg0 и peer в выводе"):
        assert WG_INTERFACE in result.stdout, "Интерфейс wg0 не найден в выводе 'wg show'"
        assert "peer:" in result.stdout, "Поле 'peer:' отсутствует в выводе 'wg show'"


@allure.description("Тест 3: Проверяем доступность веб-сервера через VPN")
@allure.title("Проверка доступности веб-сервера через VPN")
@allure.feature("Доступность сервисов")
@pytest.mark.parametrize("set_vpn_connection", ["enabled"], indirect=True)
def test_webserver_reachable_with_vpn(set_vpn_connection):
    with allure.step("Проверяем доступность веб-сервера по HTTP"):
        response = requests.get(WEB_SERVER_IP, timeout=R_TIMEOUT)
        assert response.status_code == 200


@allure.description("Тест 4: Проверяем маршрутизацию через VPN")
@allure.title("Проверка маршрутов после подключения к VPN")
@allure.feature("Маршрутизация")
@pytest.mark.parametrize("set_vpn_connection", ["enabled"], indirect=True)
def test_vpn_routing(set_vpn_connection):
    with allure.step("Проверяем таблицу маршрутов"):
        result = run_cmd("ip route")
        assert "172.21.0.0/24" in result.stdout


@allure.description("Тест 5: Подключаемся к серверу по SSH и проверяем соединение на стороне сервера")
@allure.title("Проверка подключения на стороне сервера через SSH")
@allure.feature("Серверная проверка")
def test_server_side_connection():
    @allure.step(f"Устанавливаем SSH-соединение с {VPN_SERVER_IP}")
    def ssh_connect():
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=VPN_SERVER_IP, username="root", password="123")
        return ssh

    ssh = ssh_connect()

    with allure.step("Выполняем 'wg show' на сервере"):
        stdin, stdout, stderr = ssh.exec_command("wg show")
        output = stdout.read().decode()
        ssh.close()

    with allure.step("Проверяем наличие 'peer' в выводе на сервере"):
        assert "peer" in output


@allure.description("Тест 6: Проверяем установлен ли WireGuard")
@allure.title("Проверка установки WireGuard")
@allure.feature("Предусловия")
@pytest.mark.parametrize("set_vpn_connection", ["enabled"], indirect=True)
def test_wg_installed(set_vpn_connection):
    with allure.step("Проверяем установку WireGuard (wg --version)"):
        result = run_cmd("wg --version")
        assert result.returncode == 0, "WireGuard (wg) не установлен или не в PATH"


@allure.description("Тест 7: Проверяем правильный IP-адрес на интерфейсе wg0")
@allure.title("Проверка выставленного IP-адреса на интерфейсе wg0")
@allure.feature("IP-конфигурация")
@pytest.mark.parametrize("set_vpn_connection", ["enabled"], indirect=True)
def test_wg_address(set_vpn_connection):
    with allure.step("Получаем конфигурацию интерфейса wg0"):
        result = run_cmd("ip addr show wg0")

    with allure.step("Проверяем, назначен ли нужный IP-адрес"):
        assert "10.13.13.2/32" in result.stdout, "WireGuard должен назначить адрес 10.13.13.2/32 на интерфейс wg0"