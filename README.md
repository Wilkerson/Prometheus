# Prometheus — RUCH Digital Technology

Sistema web de captacao e gestao de clientes, pipeline de implantacao e comissoes para entidades parceiras.

---

## Requisitos

Antes de comecar, certifique-se de ter instalado:

- **Python 3.12+** (desenvolvido com 3.14)
- **PostgreSQL 15+** (desenvolvido com 18)
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
```

Ativar:

```bash
# Windows (Git Bash / PowerShell)
source venv/Scripts/activate
# ou
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

Verificar que esta ativo:

```bash
echo $VIRTUAL_ENV
# Deve mostrar o caminho do venv dentro do projeto
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## 4. Configurar o PostgreSQL

Conectar como superusuario do PostgreSQL:

```bash
# Windows (ajustar caminho conforme versao)
"C:\Program Files\PostgreSQL\<versao>\bin\psql.exe" -h localhost -U postgres

# Linux / macOS
sudo -u postgres psql
```

Criar usuario e banco:

```sql
CREATE USER prometheus WITH PASSWORD 'prometheus' CREATEDB;
CREATE DATABASE prometheus OWNER prometheus;
\q
```

> A permissao `CREATEDB` e necessaria para que o Django crie o banco de testes automaticamente.

---

## 5. Configurar variaveis de ambiente

Copiar o arquivo de exemplo:

```bash
cp .env.example .env
```

As variaveis padroes ja funcionam para desenvolvimento local:

```
DJANGO_SETTINGS_MODULE=prometheus.settings.dev
SECRET_KEY=troque-por-uma-chave-segura
DB_NAME=prometheus
DB_USER=prometheus
DB_PASSWORD=prometheus
DB_HOST=localhost
DB_PORT=5432
```

> **Importante:** gere uma `SECRET_KEY` propria. Voce pode usar:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## 6. Aplicar migracoes

```bash
python manage.py migrate
```

---

## 7. Criar superusuario

```bash
python manage.py createsuperuser
```

Preencha username, email e senha quando solicitado.

---

## 8. Carregar dados de exemplo (opcional)

Para popular o banco com dados realistas de desenvolvimento:

```bash
python manage.py loaddata fixtures/dev_seed.json
```

Cria: 5 usuarios, 3 parceiros, 7 produtos, 6 planos com precos, 10 clientes em diferentes status, historico de movimentacoes e 1 token de integracao.

> **Senha dos usuarios de seed:** todos usam `testpass123` (hash pre-gerado).

---

## 9. Compilar Tailwind CSS

O projeto usa Tailwind CSS v4 via `pytailwindcss` (sem Node.js):

```bash
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --minify
```

> Na primeira execucao, o binario do Tailwind sera baixado automaticamente.

Para desenvolvimento com watch (recompila ao salvar templates):

```bash
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --watch
```

---

## 10. Rodar o servidor

```bash
python manage.py runserver
```

Acessar:

- **Sistema:** http://localhost:8000/
- **Login:** http://localhost:8000/login/
- **Admin Django:** http://localhost:8000/admin/
- **Swagger API:** http://localhost:8000/api/docs/

---

## 11. Rodar os testes

```bash
DJANGO_SETTINGS_MODULE=prometheus.settings.test python manage.py test apps
```

> Os testes usam PostgreSQL (cria um banco temporario `test_prometheus`).

---

## Estrutura do projeto

```
Prometheus/
├── manage.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── PLANEJAMENTO.md          # Estado completo do projeto
├── CLAUDE.md                # Instrucoes para Claude Code
├── prometheus/              # Configuracoes Django
│   ├── settings/
│   │   ├── base.py          # Configuracoes compartilhadas
│   │   ├── dev.py           # Desenvolvimento
│   │   ├── production.py    # Producao
│   │   └── test.py          # Testes
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py / asgi.py
├── apps/
│   ├── accounts/            # Usuario customizado + JWT + permissions
│   ├── crm/                 # Cliente, Endereco, Produto, Plano, PlanoProduto, ClienteHistorico
│   ├── comissoes/           # Comissao (gerada automaticamente via signal)
│   ├── integracao/          # TokenIntegracao, API Key auth, callback
│   └── web/                 # Views de template, mixins, context processors
├── templates/               # Django templates
│   ├── base.html            # Layout 3 colunas (sidebar + main + right panel)
│   ├── accounts/            # Login
│   ├── clientes/            # CRUD + pipeline + calendario
│   ├── produtos/            # CRUD
│   ├── planos/              # CRUD
│   ├── comissoes/           # Listagem
│   ├── dashboard/           # Dashboard com metricas
│   └── public/              # Landing page
└── static/
    ├── src/input.css         # Tailwind source (temas claro/escuro)
    ├── css/output.css        # Tailwind compilado
    └── js/app.js             # CSRF + loading indicator
```

---

## Stack tecnologico

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.14 + Django 5 + Django REST Framework |
| Banco | PostgreSQL |
| Filas | Redis + Celery |
| Front-end | Django Templates + HTMX + Alpine.js + Tailwind CSS v4 |
| Auth API | JWT (djangorestframework-simplejwt) |
| Auth Web | Django sessions (login/logout) |
| Storage | django-storages (S3 / Cloudflare R2 / GCS) |
| Deploy | Docker + Nginx + Gunicorn |

---

## Tema claro/escuro

O sistema suporta tema claro e escuro com toggle no painel lateral direito.

**Regra para desenvolvedores:** nunca usar classes de cor fixa do Tailwind (`text-gray-*`, `bg-gray-*`, `bg-white`, etc.) em templates autenticados. Usar sempre as variaveis de tema:

| Variavel | Uso |
|---|---|
| `text-t1` | Texto principal |
| `text-t2` | Texto secundario |
| `text-t3` | Texto terciario |
| `bg-bg` | Fundo da pagina |
| `bg-bg2` | Fundo de cards |
| `bg-bg3` | Fundo de inputs/hover |
| `bg-bg4` | Fundo de elementos elevados |
| `border-bdr` | Bordas |
| `border-bdr2` | Bordas mais visiveis |
| `divide-bdr` | Divisores de tabela |

---

## Controle de acesso

Baseado em **permissoes Django** (groups + permissions), nao apenas no campo `perfil`.

- Sidebar e views sao controlados por `user.has_perm()`
- Superuser (`is_superuser=True`) ve tudo automaticamente
- Grupos sao criados no Django Admin (`/admin/auth/group/`)

---

## Comandos uteis

```bash
# Ativar venv
source venv/Scripts/activate

# Rodar servidor
python manage.py runserver

# Compilar Tailwind
python -m pytailwindcss -i static/src/input.css -o static/css/output.css --minify

# Criar migracoes apos alterar models
python manage.py makemigrations

# Aplicar migracoes
python manage.py migrate

# Rodar testes
DJANGO_SETTINGS_MODULE=prometheus.settings.test python manage.py test apps

# Validar configuracao
python manage.py check

# Shell Django
python manage.py shell
```

---

## Docker (desenvolvimento local)

Para subir o ambiente completo com Docker:

```bash
docker compose up -d --build
```

Servicos: PostgreSQL, Redis, Django (Gunicorn), Celery worker, Celery beat.

---

## Deploy em producao (VPS + Easypanel)

### Fluxo de deploy

```
Dev faz push pro GitHub (branch main)
    |
GitHub Actions roda testes + builda imagem Docker
    |
Push da imagem pro GitHub Container Registry (ghcr.io)
    |
Easypanel puxa nova imagem e faz rolling update (zero downtime)
```

### Configurar o Easypanel

1. Instalar Easypanel na VPS: `curl -sSL https://get.easypanel.io | sh`
2. Criar um projeto no painel
3. Adicionar servico **App** apontando para `ghcr.io/wilkerson/prometheus:latest`
4. Adicionar servico **PostgreSQL** e **Redis** no mesmo projeto
5. Configurar variaveis de ambiente no painel:

```
DJANGO_SETTINGS_MODULE=prometheus.settings.production
SECRET_KEY=<chave-segura-gerada>
ALLOWED_HOSTS=seudominio.com.br
CSRF_TRUSTED_ORIGINS=https://seudominio.com.br
DB_HOST=<host-do-postgres-easypanel>
DB_NAME=prometheus
DB_USER=prometheus
DB_PASSWORD=<senha-segura>
REDIS_URL=redis://<host-do-redis-easypanel>:6379/0
CELERY_BROKER_URL=redis://<host-do-redis-easypanel>:6379/1
SECURE_SSL_REDIRECT=True
```

6. Configurar dominio e SSL (automatico via Let's Encrypt)
7. Health check: `/health/` (retorna JSON com status do DB)

### CI/CD (GitHub Actions)

O workflow `.github/workflows/ci.yml` roda automaticamente a cada push em `main`:

1. **test** — roda testes com PostgreSQL no GitHub Actions
2. **build** — builda imagem Docker e envia pro GitHub Container Registry

Para o Easypanel atualizar automaticamente, configure um webhook ou use polling de imagem.

### Health check

```
GET /health/
→ {"status": "ok", "db": "connected"}     (200)
→ {"status": "error", "db": "disconnected"} (503)
```

---

## Contribuindo

1. Crie uma branch a partir de `main`
2. Faca as alteracoes seguindo as regras de tema (variaveis, nao cores fixas)
3. Rode os testes antes de commitar
4. Compile o Tailwind se alterou templates
5. Abra um PR para `main`
6. Apos merge, o CI/CD builda e publica a imagem automaticamente

---

*RUCH Digital Technology*
