from fabric import *
from invoke import Responder


class Server:
    def __init__(self, ip, port, username, password):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password


def read_config_from_file(path):
    f = open(path, 'r')
    current_list = servers
    for line in f:
        if line[:2] == '--':
            if line[2:-1] == 'main:':
                current_list = servers
            elif line[2:-1] == 'database:':
                current_list = database
        else:
            server_info = line[:-1].split(' ')
            current_list.append(
                Server(ip=server_info[0], port=server_info[1], username=server_info[2], password=server_info[3]))


def connect_server(server: Server):
    return Connection(server.ip, server.username, server.port, connect_kwargs={'password': server.password},
                      config=Config(overrides={"sudo": {"password": server.password}}))


def sudo(con: Connection, command):
    con.run('sudo ' + command, pty=True, watchers=[sudo_pass])


def automate_database():
    for server in database:
        con = connect_server(server)
        install_dependencies(con)
        install_python(con)
        install_pip(con)
        install_postgres(con)
        # config_postgres(con)


def install_app_dependencies(con):
    with con.cd(app_path + app_name):
        con.run('pip3 install cffi')
        con.run('pip3 install -U pip')
        con.run('pip3 install -U setuptools')
        con.run('pip3 install --no-cache-dir cairocffi')
        con.run('pip install WeasyPrint')
        con.run('pip install whitenoise')
        con.run('pip3 install -r requirements.txt')
        con.run('pip3 install gunicorn')


def automate_main_app():
    for server in servers:
        con = connect_server(server)
        install_dependencies(con)
        install_python(con)
        install_pip(con)
        clone_app(con)
        setup_venv(con)
        install_app_dependencies(con)
        setup_gunicorn(con)
        setup_nginx(con)


def install_dependencies(con):
    sudo(con, 'apt install -y git nginx')


def install_python(con):
    sudo(con, 'add-apt-repository ppa:deadsnakes/ppa')
    sudo(con, 'apt update')
    sudo(con, 'apt install -y g++ gcc')
    sudo(con, 'apt upgrade -y g++ gcc')
    sudo(con, 'apt install -y python3.6')


def install_pip(con):
    sudo(con, 'apt update')
    sudo(con, 'apt install -y python3-dev python3-setuptools build-essential python3-pip')
    sudo(con, 'apt install -y python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 '
              'libgdk-pixbuf2.0-0 libffi-dev shared-mime-info')
    sudo(con, 'pip3 install --upgrade pip')
    sudo(con, 'pip3 install --upgrade virtualenv')


def install_postgres(con):
    sudo(con, 'apt install -y postgresql postgresql-contrib')


# has problem running postgres scripts
def config_postgres(con):
    sudo(con, '-u postgres psql')
    # con.run('create user tempo with password "tempovolla";')
    # con.run('create database tempovola owner tempo;')
    # con.run('\\q')


def clone_app(con):
    try:
        with con.cd(app_path):
            con.run('git clone ' + git_path)
    except:
        print('could not clone, either the app was cloned before or a problem has occur')


def setup_venv(con):
    with con.cd(app_path + app_name):
        con.run('virtualenv venv')
        con.run('source venv/bin/activate')


def setup_gunicorn(con):
    f = open(gunicorn_service_path, 'r')
    content = f.read()
    con.run('echo ' + content + ' | sudo tee /etc/systemd/system/gunicorn.service', pty=True, watchers=[sudo_pass])
    f = open(gunicorn_socket_path, 'r')
    content = f.read()
    con.run('echo ' + content + ' | sudo tee /etc/systemd/system/gunicorn.socket', pty=True, watchers=[sudo_pass])
    sudo(con, 'systemctl start gunicorn')
    sudo(con, 'systemctl enable gunicorn')


def setup_nginx(con):
    f = open(nginx_sites_available_path, 'r')
    content = f.read()
    con.run('echo ' + content + ' | sudo tee /etc/nginx/sites-available/tempovola', pty=True, watchers=[sudo_pass])
    try:
        sudo(con, 'ln -s /etc/nginx/sites-available/tempovola /etc/nginx/sites-enabled/tempovola')
    except:
        print('nginx sites enabled already linked')
    sudo(con, 'systemctl restart nginx')
    sudo(con, 'systemctl enable nginx')


if __name__ == '__main__':
    servers: [Server] = []
    database: [Server] = []
    config_path = './config'
    gunicorn_service_path = './gunicorn_service'
    gunicorn_socket_path = './gunicorn_socket'
    nginx_sites_available_path = './nginx_sites'
    app_path = '~/Projects/'
    app_name = 'tempovola'
    git_path = 'https://github.com/sajadgilga/tempovola.git'
    read_config_from_file(config_path)
    sudo_pass = Responder(pattern=r'\[sudo\] password for ' + servers[0].username + ':',
                          response=servers[0].username + '\n')
    automate_database()
    automate_main_app()
