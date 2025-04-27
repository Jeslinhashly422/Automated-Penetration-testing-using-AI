import os
import time
import docker

def create_container(config):
        client = docker.from_env()

        # Define the path to a host directory with ample storage
        host_directory = '/data/final'
        if not os.path.exists(host_directory):
                print(f"[ATTACKBOX] Data directory '{host_directory}' does not exist. Not binding to container.")
                host_directory = '.'

        existing_container = client.containers.list(filters={'name': config["attackbox"]}, all=True)

        if existing_container:
                container = existing_container[0]
        else:
                print(f"[ATTACKBOX] Creating new {config['attackbox']}. This will take a few minutes. If you interrupt this process, delete the {config['attackbox']} container and run the script again.")
                image = client.images.pull('kalilinux/kali-rolling')
                container = client.containers.run(
                        'kalilinux/kali-rolling',
                        detach=True,
                        tty=True,
                        name=config["attackbox"],
                        # Use bind mount to link the host directory to /data in the container
                        volumes={host_directory: {'bind': '/data', 'mode': 'rw'}} if host_directory != '.' else {},
                )
                # Set up the container
                setup_commands = (
                        'apt -y install kali-linux-headless sshpass curl && '
                        'ssh-keyscan -p 2223 leviathan.labs.overthewire.org >> ~/.ssh/known_hosts'
                )
                result = container.exec_run(f'/bin/bash -c "{setup_commands}"', stdout=True, stderr=True)
                print('[ATTACKBOX]', result.output.decode())  # Print the output to check for errors

                # Verify curl installation
                curl_check = container.exec_run('which curl')
                if curl_check.exit_code != 0:
                        print("[ATTACKBOX] Failed to install curl. Please check the logs.")

                container.stop()
                print(f"[ATTACKBOX] The {config['attackbox']} has been set up.")

        if container.status != 'running':
                container.start()
                # Create necessary devices and permissions
                container.exec_run('/bin/bash -c "mkdir -p /dev/net && mknod /dev/net/tun c 10 200 && chmod 600 /dev/net/tun"')
                time.sleep(3)

        return container
