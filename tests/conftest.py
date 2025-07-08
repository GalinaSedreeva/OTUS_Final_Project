import subprocess
import pytest

# ================== Глобальная фикстура для управления VPN ==================

@pytest.fixture(scope="session", autouse=True)
def manage_vpn_connection():
    """
    Фикстура, которая автоматически подключает VPN после окончания всех тестов.
    """
def connect_vpn(): 
    run_cmd("wg-quick up /etc/wireguard/wg0.conf")

    yield  
    # После всех тестов соединение надо возобновить
    connect_vpn()