# BrandPilot AI deployment

Run BrandPilot only on an OMSAR-controlled Windows or Linux VM. The intended path is browser over HTTPS → reverse proxy → Streamlit → BrandPilot services → SQLite and server-side Ollama. Never publish Ollama's port.

## Common controls

- Use a least-privilege service account, firewall restrictions, and an approved HTTPS reverse proxy.
- Bind Streamlit and Ollama to loopback/private interfaces; never expose port 11434 publicly.
- Store environment configuration outside Git. Protect and back up SQLite and approved knowledge together.
- Apply OS updates, rotate logs, monitor disk space, and regularly test restores.

Initialize with `python scripts/init_db.py`, create the first administrator with `python scripts/create_admin.py`, and validate with `python -m unittest discover -s tests -v`.

## Linux (systemd)

Install Ollama and pull `qwen3:4b`. An illustrative unit is:

```ini
[Unit]
Description=BrandPilot AI
After=network.target ollama.service

[Service]
Type=simple
User=brandpilot
WorkingDirectory=/opt/brandpilot
EnvironmentFile=/etc/brandpilot.env
ExecStart=/opt/brandpilot/.venv/bin/streamlit run app.py --server.address=127.0.0.1 --server.port=8501
Restart=on-failure
PrivateTmp=true
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

Put Nginx or an approved proxy in front, enable TLS, then enable the service.

## Windows

Install Python and Ollama for a dedicated service account. Use Task Scheduler or an approved service wrapper to run:

```powershell
.\.venv\Scripts\streamlit.exe run app.py --server.address=127.0.0.1 --server.port=8501
```

Use IIS Application Request Routing or another approved reverse proxy for HTTPS. Configure startup after database initialization and admin bootstrap.

## Backup and restore

Run `python scripts/backup.py`; each run creates a UTC-timestamped directory under ignored `backups/`. To restore, stop BrandPilot, preserve the current files, copy the chosen database and knowledge backup into their configured locations, restore permissions, run tests and health checks, then restart. Never overwrite a live SQLite file while Streamlit is running.
