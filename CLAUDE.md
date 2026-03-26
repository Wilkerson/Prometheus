# CLAUDE.md — Instrucoes para o Claude Code

## Inicio de sessao

Ao iniciar uma sessao neste projeto, SEMPRE:
1. Ler `PLANEJAMENTO.md` para ter o estado completo do projeto
2. Ler as memorias em `~/.claude/projects/.../memory/`
3. Informar o Wilkerson com um resumo curto: o que ja foi feito, onde paramos, proximos passos
4. Perguntar o que ele quer fazer

## Regras do projeto

- **Sempre atualizar PLANEJAMENTO.md** ao fazer qualquer alteracao no projeto
- **Sempre commitar** apos cada passo implementado
- **Sempre rodar testes** antes de commitar (`DJANGO_SETTINGS_MODULE=prometheus.settings.test python manage.py test apps`)
- **Sempre compilar Tailwind** se templates mudaram (`python -m pytailwindcss -i static/src/input.css -o static/css/output.css --minify`)
- **Sempre validar Django** (`python manage.py check`)
- **Push** precisa ser feito pelo Wilkerson no terminal dele (SSH com passphrase)

## Stack

- Python 3.14 + Django 5 + DRF + PostgreSQL 18 + Redis/Celery
- Front: Django Templates + HTMX + Alpine.js + Tailwind CSS v4 (pytailwindcss)
- Docker + Nginx + Gunicorn
- Storage: django-storages (S3/R2/GCS)

## Estrutura

```
prometheus/          # Settings (base/dev/production/test)
apps/
  accounts/          # Usuario customizado + JWT + permissions
  crm/               # Cliente, ClienteHistorico, EntidadeParceira, ProdutoContratado
  comissoes/         # Comissao (signal auto)
  integracao/        # TokenIntegracao, API Key auth, callback
  web/               # Views de template, mixins, context processors
templates/           # Django templates (base, clientes, dashboard, comissoes, public)
static/              # Tailwind src/output, JS, CSS
```

## Controle de acesso

Baseado em permissoes Django (groups + permissions), NAO no campo perfil.
Sidebar e views usam `user.has_perm()`. Superuser ve tudo.

## Banco local

```
PostgreSQL: user=prometheus, password=prometheus, db=prometheus
Superusuario Django: admin / admin123
```

## Linguagem

Comunicar em portugues BR informal. Wilkerson chama Claude de "amigao".
