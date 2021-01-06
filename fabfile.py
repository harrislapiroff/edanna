import os

from fabric import task
from invocations.console import confirm


SERVER_DIR = '/var/minecraft/server'
SERVER_BETA_DIR = '/var/minecraft/server-beta'

# A mapping of configuration files to upload from our local `data` dir to the server
UPLOAD_FILES = [
    # server.properties has to be private because it includes the RCON password
    ('privatedata/server.properties', f'{SERVER_DIR}/server.properties'),
    ('privatedata/server-beta.properties', f'{SERVER_BETA_DIR}/server.properties'),
    # systemd service
    ('data/minecraft.service', '/etc/systemd/system/minecraft.service'),
    ('data/minecraft-beta.service', '/etc/systemd/system/minecraft-beta.service'),
]

# If you update the forge URL, don't forget to update minecraft.service
FORGE_URL = 'https://files.minecraftforge.net/maven/net/minecraftforge/forge/1.12.2-14.23.5.2854/forge-1.12.2-14.23.5.2854-installer.jar'
FORGE_INSTALLER = FORGE_URL.split('/')[-1]


# TODO: Add install/upload mods for beta dir OR just scrap the automated provisioning


@task
def install(c):
    "Install Minecraft from scratch"
    # If we upgrade to a newer version of Minecraft we can change this to a simpler
    # apt-get install default-jre. The issue now is that Forge 1.12.2 only supports the outdated Java 8
    c.run('echo "deb [check-valid-until=no] http://archive.debian.org/debian jessie-backports main" > /etc/apt/sources.list.d/jessie-backports.list')
    c.run('apt-get --yes update')
    c.run('apt-get --yes install -t jessie-backports  openjdk-8-jre-headless')
    c.run('apt-get --yes install screen')
    c.run(f'mkdir -p {SERVER_DIR}')
    with c.cd(SERVER_DIR):
        c.run('echo "eula=true" > eula.txt')

        # Add Forge jar
        c.run(f'wget {FORGE_URL}')

        # Run Forge install
        c.run(f'java -jar {FORGE_INSTALLER} --installServer')
        c.run(f'rm {FORGE_INSTALLER}')

    # Upload configuration files and mods
    upload_config(c)
    upload_mods(c)

    # Create a system user to run Forge
    c.run('mkdir -p /usr/lib/sysusers.d')
    c.run('echo \'u minecraft - "Minecraft Server User"\' > /usr/lib/sysusers.d/minecraft.conf')
    c.run('systemd-sysusers')

    # Allow the minecraft user to access files
    c.run(f'chown -R minecraft:minecraft {SERVER_DIR}')

    # Create a systemd unit to start Forge
    c.run('systemctl daemon-reload')
    c.run('systemctl start minecraft.service')
    c.run('systemctl enable minecraft.service')


@task
def upload_config(c):
    "Upload configuration files from local"
    for local, remote in UPLOAD_FILES:
        c.put(local, remote)


@task
def update_config(c):
    "Upload configuration files from local and restart the minecraft server"
    upload_config(c)
    c.run('systemctl daemon-reload')
    c.run('systemctl restart minecraft.service')
    c.run('systemctl enable minecraft.service')


def upload_mods(c):
    c.run(f'mkdir -p {SERVER_DIR}/mods/')
    for mod in os.listdir('mods'):
        c.put(f'mods/{mod}', f'{SERVER_DIR}/mods/{mod}')


@task
def update_mods(c):
    "Upload mods from local and restart the minecraft server"
    upload_mods(c)
    c.run('systemctl daemon-reload')
    c.run('systemctl restart minecraft.service')
    c.run('systemctl enable minecraft.service')


@task
def clean(c):
    "Delete all files related to Minecraft from the server"
    really = confirm('Really stop the Minecraft server and delete all files? This cannot be undone')
    if not really:
        return

    c.run('rm /etc/apt/sources.list.d/jessie-backports.list')
    c.run('systemctl stop minecraft.service')
    c.run('rm -rf /var/minecraft/server')
    c.run('rm /etc/systemd/system/minecraft.service')
    c.run('rm /usr/lib/sysusers.d/minecraft.conf')


@task
def start(c):
    c.run('systemctl start minecraft.service')
    c.run('systemctl enable minecraft.service')


@task
def restart(c):
    c.run('systemctl restart minecraft.service')
    c.run('systemctl enable minecraft.service')


@task
def stop(c):
    c.run('systemctl stop minecraft.service')


@task
def journalctl(c):
    c.run('journalctl -u minecraft.service -f')


@task
def screen(c):
    c.sudo('screen -dr mc', pty=True, user='minecraft')


@task
def screenbeta(c):
    c.sudo('screen -dr mcbeta', pty=True, user='minecraft')
