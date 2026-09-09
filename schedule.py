"""Install a per-user hourly sync task. Python 3.11+, Windows or systemd Linux."""
import argparse
import os
from pathlib import Path
import shlex
import subprocess
import sys


def systemd_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def install_cron(command, target, label):
    """Install only this package's startup and hourly cron lines."""
    marker = f"# codex-sync-{label}"
    listed = subprocess.run(['crontab', '-l'], text=True, capture_output=True)
    if listed.returncode not in (0, 1):
        raise RuntimeError('could not read the current crontab')
    existing = [line for line in listed.stdout.splitlines() if marker not in line]
    log = target / 'model-routing' / 'sync.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    run = shlex.join([str(value) for value in command])
    redirect = shlex.quote(str(log))
    existing.extend([
        f'@reboot {run} >> {redirect} 2>&1 {marker} startup',
        f'17 * * * * {run} >> {redirect} 2>&1 {marker} hourly',
    ])
    subprocess.run(['crontab', '-'], input='\n'.join(existing) + '\n', text=True, check=True)


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
        service_path = unitdir / (unit_name + '.service')
        timer_path = unitdir / (unit_name + '.timer')
        service_path.write_text(service)
        timer_path.write_text(timer)
        try:
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', '--user', 'enable', '--now', unit_name + '.timer'], check=True)
            print('Installed user timer: five minutes after user service startup and hourly.')
        except (FileNotFoundError, subprocess.CalledProcessError):
            service_path.unlink(missing_ok=True)
            timer_path.unlink(missing_ok=True)
            try:
                install_cron(command, target, label)
            except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
                parser.error(f'no user systemd bus and cron fallback failed: {exc}')
            print('Installed crontab update: at boot and hourly.')
    else:
        parser.error('Supported platforms: Windows or Linux with systemd user services.')


if __name__ == '__main__':
    main()
