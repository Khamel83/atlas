SHELL := /bin/bash

.PHONY: bootstrap enable-timers preflight readui editui backup start claude-kickoff install-sops update-claude-commands

bootstrap:
	@mkdir -p scripts systemd docs /opt/oos/data /opt/oos/backups || true
	@echo "Bootstrap done."
	@echo "Next:"
	@echo "  1) cp ops/.env.template ops/.env && edit values"
	@echo "  2) sudo mkdir -p /etc/oos && sudo cp ops/.env /etc/oos/oos.env"
	@echo "  3) sudo cp ops/systemd/*.service ops/systemd/*.timer /etc/systemd/system && make enable-timers"
	@echo "  4) (Optional) seed schema: sqlite3 \$${OOS_DB:-/opt/oos/data/oos.db} < ops/schema.sql"
	@echo "  5) Install sops for secret management: make install-sops"

install-sops:
	@echo "Installing sops and age for secret management..."
	@if ! command -v sops >/dev/null 2>&1; then \
		echo "Installing sops..."; \
		wget -O /tmp/sops https://github.com/mozilla/sops/releases/latest/download/sops-latest-linux && \
		chmod +x /tmp/sops && \
		sudo mv /tmp/sops /usr/local/bin/; \
	fi
	@if ! command -v age >/dev/null 2>&1; then \
		echo "Installing age..."; \
		wget -O /tmp/age.tar.gz https://github.com/FiloSottile/age/releases/latest/download/age-latest-linux-amd64.tar.gz && \
		tar -xzf /tmp/age.tar.gz -C /tmp && \
		sudo mv /tmp/age/age /tmp/age/age-keygen /usr/local/bin/; \
	fi
	@echo "✅ sops and age installed"

enable-timers:
	sudo systemctl daemon-reload
	sudo systemctl enable --now export-to-sheets.timer writeback-from-sheets.timer backup-sqlite.timer

preflight:
	@set -a; source .env 2>/dev/null || true; set +a; scripts/preflight.sh

readui:
	@set -a; source .env 2>/dev/null || true; set +a; scripts/datasette.sh

editui:
	@set -a; source .env 2>/dev/null || true; set +a; scripts/sqlite_web.sh

backup:
	@set -a; source .env 2>/dev/null || true; set +a; scripts/backup_sqlite.sh

start: preflight claude-kickoff

claude-kickoff:
	@echo "Paste the following into Claude Code as your first message:"
	@echo "----8<----"; cat CLAUDE_BOOTSTRAP.md; echo "---->8----"

update-claude-commands:
	@set -a; source .env 2>/dev/null || true; set +a; \
	python3 scripts/update_slash_commands.py