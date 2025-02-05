#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import argparse
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint
from typing import TypedDict

import paramiko


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
    application_directory: str

    @classmethod
    def get_arguments(cls) -> GithubActionsDeployArgs:
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
        parser.add_argument(
            "--application_directory",
            help="Path to the root directory of the application. (This is where the starter script should be, 'start_containers.py')",
            type=str,
            required=True,
        )
        return GithubActionsDeployArgs(**vars(parser.parse_args()))


def run_background_deployment(ssh_client: paramiko.SSHClient, app_dir: str) -> None:
    logs_dir: str = f"{app_dir.rstrip("/")}/github_actions_startup_logs"
    _ = SshUtils.execute_command_on_remote(ssh_client, f'mkdir -p {logs_dir}')
    log_file_name: str = f'{re.sub(r"[:.\- ]", "_", str(datetime.now()))}.log'
    log_file_path: str = os.path.join(logs_dir, log_file_name)
    cmd: str = f"""\
        nohup bash -c 'cd {app_dir} \
            && git stash \
            && ./start_containers.py remove --hard --remove-images \
            && git pull origin main \
            && cp {app_dir.rstrip("/")}/phylomedb6-webapp/.env.production.bsccgenomics04 {app_dir.rstrip("/")}/phylomedb6-webapp/.env.production \
            && python3 ./start_containers.py start' > {log_file_path} 2>&1 &
"""
    res: SshCmdResult = SshUtils.execute_command_on_remote(ssh_client, cmd)
    pprint(res)


def main() -> int:
    args = GithubActionsDeployArgs.get_arguments()
    ssh_client: paramiko.SSHClient = SshUtils.get_ssh_client(
        server=args.server_address,
        username=args.username,
        ssh_key_file=args.ssh_key_file,
    )
    run_background_deployment(ssh_client, args.application_directory)
    ssh_client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
