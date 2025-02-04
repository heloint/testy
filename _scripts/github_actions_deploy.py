#!/usr/bin/env python3
from __future__ import annotations

import paramiko
import argparse
from typing import TypedDict
from dataclasses import dataclass

class SshCmdResult(TypedDict):
    resultcode: int
    stdout: str
    stderr: str

class SshUtils:
    @classmethod
    def get_ssh_client(
        cls, server: str, username: str, ssh_key_file: str
    ) -> paramiko.SSHClient:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(server, username=username, key_filename=ssh_key_file)
        return ssh_client

    @classmethod
    def execute_command_on_remote(
        cls, ssh_client: paramiko.SSHClient, command
    ) -> SshCmdResult:
        _, stdout, stderr = ssh_client.exec_command(command)
        return_code = stdout.channel.recv_exit_status()
        stdout_output = stdout.read().decode().strip()
        stderr_output = stderr.read().decode().strip()
        return {
            "resultcode": return_code,
            "stdout": stdout_output,
            "stderr": stderr_output,
        }


@dataclass
class GithubActionsDeployArgs:
    server_address: str
    username: str
    ssh_key_file: str

    @classmethod
    def get_arguments(cls) ->  GithubActionsDeployArgs:
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description="""
    Runs healthcheck on the bsccgenomics02 virtual machine, checking the running docker containers.
    """,
        )
        parser.add_argument(
            "--server_address",
            help="Remote address of the target server.",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--username",
            help="Username on the target server.",
            type=str,
            required=True,
        )
        parser.add_argument(
            "--ssh_key_file",
            help="Password on the target server.",
            type=str,
            required=True,
        )
        return GithubActionsDeployArgs(**vars(parser.parse_args()))

def run_deployment(ssh_client: paramiko.SSHClient) -> None:
    # 1. cd into /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster
    # 2. git stash
    # 3. ./start_containers.py remove --hard --remove-images
    # 4. git pull main
    # 5. Change credentials. (cp /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster/phylomedb6-webapp/.env.production.bsccgenomics04 /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster/phylomedb6-webapp/.env.production)
    # 6. ./start_containers.py start
    cmd: str = """\
        cd /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster \
            && git stash \
            && ./start_containers.py remove --hard --remove-images \
            && git pull origin main \
            && cp /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster/phylomedb6-webapp/.env.production.bsccgenomics04 /var/www/web/phylomedb6-reconstruction/phylomedb6-app-cluster/phylomedb6-webapp/.env.production \
            && python3 ./start_containers.py start
"""
    res: SshCmdResult = SshUtils.execute_command_on_remote(
        ssh_client, cmd
    )
    print(res)


def main() -> int:
    args = GithubActionsDeployArgs.get_arguments()
    ssh_client: paramiko.SSHClient = SshUtils.get_ssh_client(
        server=args.server_address,
        username=args.username,
        ssh_key_file=args.ssh_key_file,
    )
    run_deployment(ssh_client)
    ssh_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
