"""Install a per-user hourly sync task. Python 3.11+, Windows or systemd Linux."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def systemd_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-home', type=Path)
    args = parser.parse_args()
    target = (args.codex_home or Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))).resolve()
    script = Path(__file__).resolve().with_name('sync.py')
    components = [name for name in ('adhd', 'orchestration') if (script.parent / 'shared' / name).is_dir()]
    if not components:
        parser.error('No installable package found.')
    label = '-'.join(components)
    task_name = 'CodexSync-' + label
    unit_name = 'codex-sync-' + label
    command = [sys.executable, str(script), '--update', '--codex-home', str(target)]
    subprocess.run([sys.executable, str(script), '--check', '--codex-home', str(target)], check=True)
    if os.name == 'nt':
        windowless = Path(sys.executable).with_name('pythonw.exe')
        if not windowless.exists():
            parser.error('pythonw.exe is required for a windowless Windows sync task.')
        command[0] = str(windowless)
        def psquote(value):
            return "'" + str(value).replace("'", "''") + "'"
        arguments = subprocess.list2cmdline(command[1:])
        powershell = '\n'.join([
            "$ErrorActionPreference = 'Stop'",
            '$action = New-ScheduledTaskAction -Execute ' + psquote(command[0]) + ' -Argument ' + psquote(arguments),
            '$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name',
            '$hourly = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Hours 1)',
            '$login = New-ScheduledTaskTrigger -AtLogOn -User $userId',
            '$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited',
            '$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)',
            "Register-ScheduledTask -TaskName " + psquote(task_name) + " -Action $action -Trigger @($hourly,$login) -Principal $principal -Settings $settings -Force | Out-Null",
        ])
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', powershell], check=True)
        print(f'Installed {task_name}: hourly and at login, current user only.')
    elif sys.platform.startswith('linux'):
        unitdir = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'systemd/user'
        unitdir.mkdir(parents=True, exist_ok=True)
        service = '[Unit]\nDescription=Sync shared Codex policy\n\n[Service]\nType=oneshot\nExecStart=' + ' '.join(map(systemd_quote, command)) + '\nEnvironment=GIT_TERMINAL_PROMPT=0\nTimeoutStartSec=600\n'
        timer = '[Unit]\nDescription=Hourly shared Codex update\n\n[Timer]\nOnStartupSec=5min\nOnCalendar=hourly\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n'
        (unitdir / (unit_name + '.service')).write_text(service)
        (unitdir / (unit_name + '.timer')).write_text(timer)
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', '--now', unit_name + '.timer'], check=True)
        print('Installed user timer: five minutes after user service startup and hourly.')
    else:
        parser.error('Supported platforms: Windows or Linux with systemd user services.')


if __name__ == '__main__':
    main()
