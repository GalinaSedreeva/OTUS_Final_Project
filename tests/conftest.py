import subprocess
import pytest
import os
import time


@pytest.fixture(scope="function")
def set_vpn_connection(request):
    """Фикстура для установки нужного состояния VPN перед тестом."""
    mode = request.param
    # wg_config_path = "/etc/wireguard/wg0.conf"
    wg_config_path = "/config/wg_confs/wg0.conf" 
    #wg_config_path = "/config/peer1.conf" 

    # Убедимся, что конфиг существует
    if not os.path.exists(wg_config_path):
        pytest.fail(f"Конфиг WireGuard не найден по пути {wg_config_path}")

    def is_wireguard_active():
        result = subprocess.run(["ip", "link", "show", "wg0"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        return result.returncode == 0

    # Очищаем текущее состояние
    if is_wireguard_active():
        subprocess.run(["wg-quick", "down", "wg0"], check=False)

    # Поднимаем соединение с сервером
    if mode == "enabled":
        subprocess.run(["chmod",  "600", "/config/wg_confs/wg0.conf", wg_config_path], check=True)
        subprocess.run(["wg-quick", "up", wg_config_path], check=True)
        time.sleep(2)  # даём время на установку соединения

    yield mode

    # Чистка после теста
	
    if is_wireguard_active():
       subprocess.run(["wg-quick", "down", "wg0"], check=False)