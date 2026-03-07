# AD Security Reporter (Defensive-Only)

Корпоративный desktop-инструмент внутреннего AD-аудита для домена `serbsky.lan` и DC `kp-dc01`.

## Defensive-only scope
Инструмент выполняет только администраторскую отчетность:
- аудит парольной политики и состояния учетных записей;
- аудит компьютеров AD и LastLogonDate/LastLogonTimestamp;
- экспорт отчетов в CSV/XLSX/HTML.

Запрещенные функции (не реализованы): извлечение секретов, NTDS dump, DCSync, brute-force, pass-the-hash, декодирование паролей и любые offensive-действия.

## Архитектура

```text
Report/
├── config/
│   ├── config.example.yaml
│   └── config.yaml
├── examples/
│   ├── sample_password_fingerprint_groups.csv
│   ├── password_audit_sample.csv
│   ├── password_audit_sample.html
│   ├── computers_lastlogon_sample.csv
│   └── computers_lastlogon_sample.html
├── logs/
├── pyinstaller/
│   └── ad_security_reporter.spec
├── scripts/
│   ├── ad_password_audit.py
│   └── ad_computers_lastlogon.py
├── src/ad_security_reporter/
│   ├── main.py
│   ├── config/settings.py
│   ├── connectors/
│   │   ├── powershell_connector.py
│   │   └── ad_queries.py
│   ├── core/
│   │   ├── password_audit.py
│   │   ├── computer_audit.py
│   │   └── logging_setup.py
│   ├── exporters/report_exporter.py
│   ├── gui/main_window.py
│   ├── models/pandas_model.py
│   └── assets/
│       ├── dark.qss
│       └── light.qss
├── run_gui.py
└── requirements.txt
```

## Report 1: Password Audit
Собирает:
- политику паролей домена (`Get-ADDefaultDomainPasswordPolicy`);
- пользователей и password-related признаки (`Get-ADUser -Properties ...`).

Вычисляет:
- `DaysSincePasswordChange`
- `DaysSinceLastLogon`
- `PasswordAgeStatus`
- `RiskGroup` (LOW/MEDIUM/HIGH/CRITICAL)

### RiskGroup логика
- **CRITICAL**: `PasswordNeverExpires=True`, либо пароль старше critical threshold, либо привилегированный аккаунт с устаревшим паролем.
- **HIGH**: `adminCount=1`, либо пароль старше high threshold, либо отключенная учетка с устаревшим паролем.
- **MEDIUM**: пароль старше medium threshold.
- **LOW**: остальные случаи.

Пороги задаются в `config.yaml`: 30/60/90/180 дней (настраиваемо).

### Safe mode для повторяющихся паролей
1. **SAFE DEFAULT MODE**: только AD-метаданные; совпадающие пароли не определяются.
2. **OPTIONAL AUDIT INPUT MODE**: администратор вручную импортирует CSV (`SamAccountName,PasswordFingerprintGroup`) из санкционированного внешнего password audit механизма.

## Report 2: Computers Last Logon
Собирает `Get-ADComputer` атрибуты, включая `LastLogonDate`, ОС, DN, OU, `PasswordLastSet`, IP.

Вычисляет:
- `DaysSinceLastLogon`
- `DaysSincePasswordSet`
- `StaleStatus` (`Active`, `Warning`, `Stale`, `Critical`)

Пороговая модель по умолчанию:
- Warning > 30
- Stale > 90
- Critical > 180

### LastLogon vs LastLogonTimestamp
- `LastLogon` точный, но хранится отдельно на каждом DC.
- `LastLogonTimestamp`/`LastLogonDate` реплицируются и практичны для отчетности.
- По умолчанию используется практичный режим `LastLogonDate`.

## Установка
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск в dev режиме
GUI:
```bash
PYTHONPATH=src python run_gui.py
```

Отдельные скрипты:
```bash
PYTHONPATH=src python scripts/ad_password_audit.py --config config/config.yaml --output-dir exports
PYTHONPATH=src python scripts/ad_computers_lastlogon.py --config config/config.yaml --output-dir exports
```

## Сборка .exe
Команда:
```bash
pyinstaller pyinstaller/ad_security_reporter.spec --noconfirm --clean
```

Результат: `dist/ADSecurityReporter/ADSecurityReporter.exe`

## Советы для доменной среды
- Запускать под учетной записью с правами чтения AD.
- На хосте должна быть доступна PowerShell и модуль `ActiveDirectory` (RSAT).
- Проверить доступность `kp-dc01` по сети и DNS.
- При ошибках проверять `logs/ad_security_reporter.log`.

## Тестирование
- Smoke-запуск GUI.
- Запуск отдельных скриптов.
- Проверка генерации экспорта CSV/XLSX/HTML.
- Проверка поведения при недоступном DC или отсутствии модуля AD.

## Дальнейшие улучшения
- Добавить опциональный exact-mode опроса нескольких DC для LastLogon.
- Добавить продвинутые виджеты фильтрации и пагинацию.
- Добавить асинхронный сбор данных через QThread/QRunnable.
- Подписывание сборки и централизованная доставка обновлений.
