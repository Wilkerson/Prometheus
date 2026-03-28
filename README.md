# Prometheus — RUCH Solutions

Sistema web de gestao empresarial com modulos de CRM, RH, Financeiro e mais. Gerencia clientes, colaboradores, pipeline de implantacao, comissoes, ferias, treinamentos, metas e pesquisas de engajamento.

---

## Requisitos

- **Python 3.12+** (desenvolvido com 3.14)
- **PostgreSQL 15+** (desenvolvido com 18)
- **Docker Desktop** (para Redis)
- **Git**

---

## 1. Clonar o repositorio

```bash
git clone git@github.com:Wilkerson/Prometheus.git
cd Prometheus
```

---

## 2. Criar e ativar o virtualenv

```bash
python -m venv venv

# Windows (Git Bash / PowerShell)
source venv/Scripts/activate

# Linux / macOS
source venv/bin/activate
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 4. Configurar o PostgreSQL

```bash
# Windows
"C:\Program Files\PostgreSQL\<versao>\bin\psql.exe" -h localhost -U postgres

# Linux / macOS
sudo -u postgres psql
```

```sql
CREATE USER prometheus WITH PASSWORD 'prometheus' CREATEDB;
CREATE DATABASE prometheus OWNER prometheus;
\q
```

---

## 5. Configurar variaveis de ambiente

```bash
cp .env.example .env
```

---

## 6. Subir Redis via Docker

```bash
docker run -d --name redis-prometheus -p 6379:6379 --restart unless-stopped redis:alpine
```

---

## 7. Aplicar migracoes e criar superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

---

## 8. Configurar grupos e permissoes

```bash
python manage.py setup_groups
```

Cria 6 grupos:
- **Administrador** — acesso total (132 permissoes)
- **Comercial** — clientes, produtos, planos, comissoes
- **Financeiro** — comissoes CRUD
- **Financeiro** (36) — lancamentos, cobrancas, despesas, NFs, folha, tributos, patrimonio, contas
- **RH / Pessoas** (68) — colaboradores, documentos, ferias, treinamentos, metas, eNPS
- **Colaborador** (12) — acesso limitado (solicitar ausencias, ver treinamentos, responder eNPS)
- **Empresa Parceira** (3) — clientes (ver/criar/editar)

---

## 9. Carregar dados de exemplo (opcional)

```bash
python manage.py loaddata fixtures/dev_seed.json
python manage.py loaddata fixtures/dev_seed_rh.json
python manage.py loaddata fixtures/dev_seed_financeiro.json
```

Cria dados realistas: usuarios vinculados a colaboradores, parceiros, produtos, planos, clientes, colaboradores com cargos/setores, treinamentos, metas, pesquisa eNPS, lancamentos, cobrancas, despesas, NFs, folha, tributos, ativos.

> **Senha dos usuarios de seed:** todos usam `testpass123`

---

## 10. Compilar Tailwind CSS

```bash
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --minify
```

Para desenvolvimento com watch:

```bash
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --watch
```

---

## 11. Rodar o servidor

Sao necessarios 3 terminais:

**Terminal 1 — Django:**
```bash
source venv/Scripts/activate
python manage.py runserver
```

**Terminal 2 — Celery Worker (processa tasks asincronas):**
```bash
source venv/Scripts/activate
celery -A prometheus worker -l info
```

**Terminal 3 — Celery Beat (agenda tasks periodicas):**
```bash
source venv/Scripts/activate
celery -A prometheus beat -l info
```

Acessar:
- **Sistema:** http://localhost:8000/
- **Login:** http://localhost:8000/login/
- **Admin Django:** http://localhost:8000/admin/

---

## 12. Rodar os testes

```bash
DJANGO_SETTINGS_MODULE=prometheus.settings.test python manage.py test apps
```

---

## Modulos do sistema

### Comercial (CRM)
- Clientes com pipeline de status (Recebida > Em Analise > Em Processamento > Concluida/Falha)
- Produtos e Planos com precos por parceiro
- Pipeline Kanban e calendario mensal
- Integracao com sistema externo (Zypher) via Celery

### Financeiro
- **Lancamentos** — core financeiro, receitas e despesas com regime caixa + competencia
- **Contas a Receber** — cobrancas por cliente com confirmacao de pagamento automatica
- **Contas a Pagar** — despesas com recorrencia (mensal/trimestral/anual) e geracao automatica
- **Notas Fiscais** — emitidas (clientes) e recebidas (fornecedores) com upload PDF
- **Folha de Pagamento** — geracao automatica por Celery Beat, fluxo calculado > aprovado > pago
- **Tributos** — tipo extensivel (Simples, Presumido, Real), controle de vencimentos
- **Patrimonio** — bens imoveis, moveis duraveis e de consumo, depreciacao calculada
- **Contas Bancarias** — saldo em tempo real calculado dos lancamentos

### RH / Pessoas
- **Colaboradores** — cadastro CLT/PJ, historico de cargos/salarios, foto
- **Cargos e Setores** — estrutura organizacional com faixas salariais
- **Documentos** — upload com controle de vencimento e alertas
- **Onboarding** — templates de checklist com progresso por fase
- **Ferias e Ausencias** — solicitacao pelo colaborador, aprovacao pelo RH, calendario
- **Treinamentos** — catalogo, inscricao, participacao, certificados
- **Metas e PDI** — ciclos de avaliacao, atingimento ponderado, acoes com prazos
- **eNPS** — pesquisas de satisfacao com calculo automatico do score
- **Relatorios** — dashboard com headcount, turnover, custo, alertas, eNPS
- **Acesso ao sistema** — criacao de usuario para colaborador com senha automatica + email

### Notificacoes
- Notificacoes no sistema com polling HTMX (sino no topbar)
- Preferencias por usuario (aceitar/recusar tipos)
- Emails automaticos (acesso criado, ausencia aprovada/rejeitada, eNPS, docs vencendo)
- Alertas periodicos via Celery Beat (documentos, ferias vencidas, PDI atrasado)

### Administracao
- CRUD de usuarios com permissoes individuais (mesma matriz dos grupos)
- CRUD de entidades parceiras
- CRUD de tokens de integracao (API Key)
- CRUD de grupos com matriz visual de permissoes

---

## Estrutura do projeto

```
Prometheus/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile / docker-compose.yml
├── PLANEJAMENTO.md
├── CLAUDE.md
├── prometheus/
│   ├── settings/ (base, dev, production, test)
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── accounts/       # Usuario + JWT + permissions + setup_groups
│   ├── crm/            # Cliente, Produto, Plano, Notificacao
│   ├── financeiro/     # Lancamento, Cobranca, Despesa, NF, Folha, Tributo, Ativo
│   ├── integracao/     # Token, API Key, callback Zypher
│   ├── rh/             # Colaborador, Cargo, Setor, Documentos, Onboarding,
│   │                   # Ferias, Treinamentos, Metas, PDI, eNPS, Relatorios
│   └── web/            # Views, mixins, context processors, URLs
├── templates/
│   ├── base.html       # Layout (sidebar accordion exclusivo + topbar + main)
│   ├── components/     # Logo, avatar (reutilizaveis)
│   ├── accounts/       # Login
│   ├── clientes/       # CRUD + pipeline + calendario
│   ├── financeiro/     # Lancamentos, cobrancas, despesas, NFs, folha, tributos, ativos, contas
│   ├── rh/             # Todos os submodulos de RH
│   ├── grupos/         # Matriz de permissoes (colapsavel por departamento)
│   └── public/         # Landing page
├── static/
│   ├── src/input.css   # Tailwind source (temas claro/escuro)
│   ├── css/output.css  # Tailwind compilado
│   └── img/logo.png    # Logo RUCH oficial
└── fixtures/
    ├── dev_seed.json       # Dados de dev (CRM)
    └── dev_seed_rh.json    # Dados de dev (RH)
```

---

## Stack tecnologico

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.14 + Django 5 + Django REST Framework |
| Banco | PostgreSQL 18 |
| Filas | Redis + Celery + Celery Beat |
| Front-end | Django Templates + HTMX + Alpine.js + Tailwind CSS v4 |
| Email | Console (dev) / SMTP (producao) |
| Storage | django-storages (S3 / Cloudflare R2 / GCS) |
| Deploy | Docker + Nginx + Gunicorn + GitHub Actions CI/CD |

---

## Sidebar (departamentos)

A sidebar e organizada por departamentos com accordion exclusivo (1 aberto por vez):

| Departamento | Status | Submenus |
|---|---|---|
| RH / Pessoas | Completo | Colaboradores, Documentos, Onboarding, Ferias, Treinamentos, Metas, PDI, eNPS, Relatorios, Cargos, Setores |
| Comercial | Implementado | Clientes, Pipeline, Calendario, Produtos, Planos |
| Financeiro | Fases 1-4 | Lancamentos, Contas a Receber, Contas a Pagar, NFs, Folha, Tributos, Patrimonio, Contas Bancarias |
| Marketing | Placeholder | — |
| Tecnologia | Placeholder | — |
| Juridico | Placeholder | — |
| Operacoes | Placeholder | — |
| Produto | Placeholder | — |

---

## Tema claro/escuro

Toggle na sidebar. **Nunca usar cores fixas** em templates autenticados:

| Variavel | Uso |
|---|---|
| `text-t1/t2/t3` | Texto principal/secundario/terciario |
| `bg-bg/bg2/bg3/bg4` | Fundos |
| `border-bdr/bdr2` | Bordas |
| `divide-bdr` | Divisores |

---

## Comandos uteis

```bash
# Servidor Django
python manage.py runserver

# Celery worker + beat
celery -A prometheus worker -l info
celery -A prometheus beat -l info

# Compilar Tailwind
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --minify

# Testes
DJANGO_SETTINGS_MODULE=prometheus.settings.test python manage.py test apps

# Grupos e permissoes
python manage.py setup_groups

# Alertas RH (manual)
python manage.py rh_alertas

# Gerar folha do mes (manual)
python manage.py gerar_folha_mensal

# Gerar despesas recorrentes (manual)
python manage.py gerar_recorrentes

# Fixtures
python manage.py loaddata fixtures/dev_seed.json fixtures/dev_seed_rh.json fixtures/dev_seed_financeiro.json
```

---

## Deploy (VPS + Easypanel)

```
Push no GitHub (main) → GitHub Actions (testes + build) → GHCR → Easypanel (rolling update)
```

Health check: `GET /health/` → `{"status": "ok", "db": "connected"}`

---

*RUCH Solutions — Prometheus*
