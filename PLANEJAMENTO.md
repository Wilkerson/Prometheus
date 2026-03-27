# Sistema de Captação e Gestão de Clientes — RUCH
> Planejamento técnico completo · Django + Python

---

## 1. Contexto do projeto

Sistema web para captação e gestão de clientes de produtos/serviços de tecnologia (Agentes IA, SaaS, CRM, ERP, Sites, Consultoria). Uma entidade parceira comercial acessa um painel restrito para inserir leads captados. O sistema gerencia o pipeline interno, calcula comissões e integra com sistema externo próprio via API REST.

### Fluxo principal

```
Parceiro cadastra Cliente → Recebida → Em Analise → Em Processamento ──→ API envia para sistema externo
                                                                                  ↓
                                                              Sistema externo implanta o servico
                                                                                  ↓
                                                Concluida ←── Callback retorna status pro Prometheus
                                                                                  ↓
                                                              Produto Contratado → Comissao gerada
```

> O modelo Lead foi eliminado. O Cliente e o unico modelo que percorre o pipeline de status.

---

## 2. Stack tecnológico

- **Backend:** Python 3.12 + Django 5 + Django REST Framework
- **Banco de dados:** PostgreSQL (obrigatório em todos os ambientes — dev, teste e produção)
- **Cache / filas:** Redis + Celery
- **Autenticação:** JWT (djangorestframework-simplejwt) + API Key (sistemas externos)
- **Storage:** django-storages (AWS S3 / Cloudflare R2 / Google Cloud Storage)
- **Servidor:** Nginx + Gunicorn
- **Infra:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoramento:** Sentry + Uptime Kuma
- **Front-end:** Django Templates + HTMX + Alpine.js + Tailwind CSS v4
- **Testes:** Django TestCase + PostgreSQL

---

## 2.1. Identidade visual

Paleta de cores baseada na logo RUCH:

| Token | Hex | Uso |
|---|---|---|
| `primary-600` (principal) | `#2d4a3e` | Verde escuro RUCH — botoes, sidebar, links |
| `primary-500` | `#3d6b5a` | Verde medio — hover, destaques |
| `primary-900` | `#15241e` | Footer, sidebar escura |
| `ruch-bg` | `#384f46` | Background escuro (hero, CTA) |
| `ruch-light` | `#b8bfba` | Cinza suave (textos secundarios) |

---

## 2.2. Configuração do PostgreSQL (obrigatório antes de rodar o projeto)

O projeto **não funciona com SQLite**. O PostgreSQL deve estar instalado e configurado antes de qualquer coisa.

### Passo a passo

**1. Instalar o PostgreSQL** (caso não esteja instalado):
- Windows: baixar de https://www.postgresql.org/download/windows/
- Linux: `sudo apt install postgresql postgresql-contrib`
- macOS: `brew install postgresql`

**2. Criar o usuário e banco de dados:**

Abrir o terminal/prompt e conectar como superusuário do PostgreSQL:

```bash
# Windows (ajustar caminho conforme versão instalada)
"C:\Program Files\PostgreSQL\<versao>\bin\psql.exe" -h localhost -U postgres

# Linux / macOS
sudo -u postgres psql
```

Executar os seguintes comandos SQL:

```sql
CREATE USER prometheus WITH PASSWORD 'prometheus' CREATEDB;
CREATE DATABASE prometheus OWNER prometheus;
\q
```

> **Nota:** a permissão `CREATEDB` é necessária para que o Django consiga criar o banco de testes automaticamente ao rodar `python manage.py test`.

**3. Configurar o `.env`:**

Copiar o arquivo de exemplo e ajustar se necessário:

```bash
cp .env.example .env
```

As variáveis de banco no `.env` devem corresponder ao que foi criado acima:

```
DB_NAME=prometheus
DB_USER=prometheus
DB_PASSWORD=prometheus
DB_HOST=localhost
DB_PORT=5432
```

**4. Aplicar migrações e criar superusuário:**

```bash
python manage.py migrate
python manage.py createsuperuser
```

**5. Rodar o servidor:**

```bash
python manage.py runserver
```

Acessar: `http://localhost:8000/login/`

---

## 3. Controle de acesso (baseado em permissões Django)

O sistema usa o **sistema nativo de permissões do Django** (groups + permissions) para controlar acesso. Cada funcionalidade — tanto na sidebar quanto nas views — é exibida/bloqueada com base nas permissões reais do usuário (`user.has_perm()`), não apenas no campo `perfil`.

### Como funciona

- **Superuser** (`is_superuser=True`) tem acesso total automaticamente
- **Grupos** são criados no Django Admin (`/admin/`) com as permissões desejadas
- **Sidebar** exibe apenas os itens que o usuário tem permissão de acessar
- **Views** usam `PermissionRequiredMixin` para bloquear acesso sem permissão
- **Dashboard** exibe cards/seções condicionalmente (`can_view_leads`, `can_view_comissoes`)

### Mapa de permissões por funcionalidade

| Funcionalidade | Permissão necessária |
|---|---|
| Dashboard (leads) | `crm.view_lead` |
| Dashboard (comissões) | `comissoes.view_comissao` |
| Ver leads / calendário | `crm.view_lead` |
| Criar lead | `crm.add_lead` |
| Pipeline / alterar status | `crm.change_lead` |
| Ver clientes | `crm.view_cliente` |
| Ver comissões | `comissoes.view_comissao` |
| Admin Django | Apenas `is_superuser` |

### Perfis sugeridos (exemplos de grupos)

| Grupo | Permissões |
|---|---|
| Entidades Parceiras | `crm.view_lead`, `crm.add_lead`, `comissoes.view_comissao` |
| Operadores | Todas de `crm.*` + `comissoes.view_comissao` |
| Administradores | Todas as permissões |

> Grupos e permissões são configurados no Django Admin (`/admin/auth/group/`). O token JWT na API continua retornando `perfil`, `nome` e `email` no payload.

---

## 4. Módulos do sistema

### MVP (fase 1) — implementado
- Autenticação JWT + controle de acesso por perfil
- CRM: gestão de leads com pipeline de status e histórico
- Painel restrito da entidade parceira com dashboard
- Cálculo automático de comissão via signal
- Integração bidirecional com sistema externo (envio + callback)
- Calendário de leads e monitoramento de SLA
- Upload de arquivos com suporte a storage na nuvem

### Pós-MVP (fase 2)
- Módulo financeiro
- Suporte ao cliente / tickets
- Operacional / onboarding de serviços

---

## 5. Produtos/serviços ofertados

- Agentes de IA
- SaaS
- CRM
- ERP
- Sites
- Consultoria em tecnologia e automação

---

## 6. Arquitetura

```
Navegador (Admin / Parceiro)          Sistema Externo
        ↓                                   ↓
    Nginx (SSL · rate limit · static)    API Key (X-API-Key)
        ↓                                   ↓
  ┌──────────────────────────────────────────────────────┐
  │                Django App — Gunicorn/WSGI             │
  │                                                      │
  │  accounts     crm          comissoes     integracao  │
  │  (JWT+roles)  (leads,      (cálculo     (callback,  │
  │               clientes,    automático)   envio API)  │
  │               histórico,                             │
  │               calendário)                            │
  └──────────────────────────────────────────────────────┘
        ↓              ↓              ↓             ↓
  PostgreSQL 15   Redis/Celery   Object Storage   Sistema
                  (tasks async)  (S3/R2/GCS)      Externo
```

---

## 7. Modelos de dados

```
USUARIO (AbstractUser)
  id, username, email, first_name, last_name, avatar,
  is_active, date_joined
  (controle de acesso 100% por grupos/permissoes Django)

ENTIDADE_PARCEIRA
  id, usuario_id (FK OneToOne), nome_entidade, percentual_comissao, ativo, criado_em

ENDERECO
  id, cep, logradouro, numero, complemento (opcional), bairro, cidade, uf
  (CEP auto-preenche logradouro/bairro/cidade/uf via ViaCEP)

PRODUTO (catalogo global — gerenciado pela RUCH)
  id, nome, descricao, tier [basico|intermediario|avancado], ativo, criado_em

PLANO (vinculado a um parceiro, com precos personalizados)
  id, nome, parceiro_id (FK), ativo, criado_em
  → M2M com Produto via PLANO_PRODUTO

PLANO_PRODUTO (tabela intermediaria)
  id, plano_id (FK), produto_id (FK), preco

CLIENTE (todos os campos obrigatorios, exceto operador e complemento)
  id, parceiro_id (FK), operador_id (FK nullable), nome, cnpj (unique),
  email, telefone, endereco_id (FK OneToOne -> Endereco),
  planos (M2M -> Plano),
  status [recebida|em_analise|em_processamento|concluida|perdida],
  arquivo ("Produtos ou Servicos"), ativo, criado_em, atualizado_em

CLIENTE_HISTORICO
  id, cliente_id (FK), status_anterior, status_novo, usuario_id (FK nullable),
  observacao, criado_em

COMISSAO (gerada automaticamente ao concluir cliente — soma dos planos)
  id, parceiro_id (FK), cliente_id (FK), valor_venda,
  percentual, valor_comissao, status [pendente|pago], gerado_em

TOKEN_INTEGRACAO
  id, nome, token (auto-gerado), ativo, criado_em

DEPARTAMENTO (app: rh) — system-managed, sem CRUD manual
  id, nome (unique), slug (unique), descricao, icone, ordem, ativo, criado_em, atualizado_em
  Seedados: comercial, financeiro, rh, marketing, tecnologia

SETOR (app: rh) — subdivisao do departamento, gerenciado pelo usuario
  id, nome, departamento_id (FK), descricao, ativo, criado_em, atualizado_em
  unique_together: (nome, departamento)

CARGO (app: rh)
  id, nome, departamento_id (FK), nivel [diretor|gerente|especialista|analista|assistente|estagiario],
  faixa_salarial_min, faixa_salarial_max, descricao, requisitos, ativo, criado_em, atualizado_em
  unique_together: (nome, departamento)

COLABORADOR (app: rh)
  id, nome_completo, cpf (unique), data_nascimento, endereco_id (FK OneToOne -> Endereco),
  telefone, email_pessoal, contato_emergencia_nome, contato_emergencia_telefone,
  tipo_contrato [clt|pj], data_admissao, data_desligamento (nullable),
  cargo_id (FK), departamento_id (FK), setor_id (FK nullable), remuneracao, carga_horaria_semanal,
  status [ativo|afastado|desligado],
  # CLT: pis_nit, ctps_numero, ctps_serie, banco_deposito, regime_trabalho
  # PJ: cnpj_pj, razao_social, banco_pagamento_pj, chave_pix
  usuario_id (FK OneToOne nullable -> Usuario),
  criado_em, atualizado_em

HISTORICO_COLABORADOR (app: rh)
  id, colaborador_id (FK), tipo [admissao|promocao|transferencia|reajuste|afastamento|retorno|desligamento],
  cargo_anterior, cargo_novo, departamento_anterior, departamento_novo,
  remuneracao_anterior, remuneracao_nova, observacao, registrado_por_id (FK), criado_em
```

### Transicoes validas de status do Cliente

```
recebida           → em_analise, perdida
em_analise         → em_processamento, perdida
em_processamento   → concluida, falha_implantacao  (via callback do Zypher)
concluida          → (status final)
falha_implantacao  → em_processamento  (pode retentar envio ao Zypher)
perdida            → (status final)
```

---

## 8. Endpoints da API (base: /api/v1/)

### Autenticação
- `POST /auth/token/` — Login, retorna JWT com perfil/nome/email
- `POST /auth/token/refresh/` — Renova token
- `GET  /auth/me/` — Dados do usuário logado
- CRUD `/auth/usuarios/` — Gestão de usuários (Super Admin)

### Clientes
- CRUD `/clientes/` — Gestao de clientes (com pipeline de status)
- `PATCH /clientes/{id}/status/` — Atualiza status com validacao de transicao
- `GET  /clientes/{id}/historico/` — Timeline de mudancas de status
- `GET  /clientes/calendario/?mes=YYYY-MM` — Clientes agrupados por dia
- `GET  /clientes/sla/?dias=N` — Clientes parados ha mais de N dias
- CRUD `/produtos-contratados/` — Produtos de cada cliente

### Painel do Parceiro
- `POST /parceiro/clientes/` — Cadastra novo cliente
- `GET  /parceiro/clientes/` — Lista clientes do parceiro
- `GET  /parceiro/clientes/{id}/` — Detalhe de um cliente
- `GET  /parceiro/dashboard/` — Resumo com totais por status e comissoes

### Comissoes
- `GET /comissoes/` — Lista comissoes (parceiro ve as proprias)

### Integracao externa (autenticacao via X-API-Key)
- `POST /integracao/cliente/` — Insere cliente via sistema externo
- `POST /integracao/cliente/status/` — Callback do sistema externo (concluida/perdida)

---

## 8.1. Páginas Web (rotas do front-end)

### Página pública (sem autenticação)
- `GET /` — Landing page com info para parceiros, produtos, como funciona e CTA para login

### Autenticação
- `GET /login/` — Tela de login (split layout com branding RUCH)
- `POST /logout/` — Logout

### Paginas autenticadas (painel interno)
- `GET /dashboard/` — Dashboard com stats, pipeline, clientes recentes e SLA
- `GET /clientes/` — Listagem com busca/filtros HTMX por status e produto
- `GET /clientes/novo/` — Cadastro de cliente
- `GET /clientes/{id}/` — Detalhe com timeline de status + acoes CRUD
- `POST /clientes/{id}/status/` — Alteracao de status via HTMX
- `GET /clientes/{id}/editar/` — Edicao do cliente
- `POST /clientes/{id}/excluir/` — Exclusao com confirmacao
- `GET /clientes/pipeline/` — Kanban por status
- `GET /clientes/calendario/` — Calendario mensal
- `GET /comissoes/` — Listagem de comissoes

---

## 9. Storage de arquivos

Suporte a 3 providers configuráveis via variável `STORAGE_PROVIDER`:

| Provider | Backend | Uso |
|---|---|---|
| `local` | Django MEDIA_ROOT | Desenvolvimento |
| `s3` | AWS S3 / Cloudflare R2 (boto3) | Produção (AWS ou Cloudflare) |
| `gcs` | Google Cloud Storage | Produção (GCP) |

Para Cloudflare R2: usar provider `s3` com `STORAGE_S3_ENDPOINT_URL`.

---

## 10. Integração com sistema externo

| Evento | Direção | Como |
|---|---|---|
| Lead entra em processamento | Prometheus → Externo | Task Celery `enviar_lead_sistema_externo` (POST com retry) |
| Implantação concluída/perdida | Externo → Prometheus | Callback `POST /integracao/lead/status/` com API Key |

---

## 11. Planejamento de capacidade

| Fase | Prazo | Clientes | Infraestrutura |
|---|---|---|---|
| MVP | 0–6 meses | até 500 | VPS 2 vCPU / 4GB / 50GB |
| Crescimento | 6–18 meses | até 5.000 | VPS 4 vCPU / 8GB + Redis |
| Escala | 18+ meses | 50.000+ | Cloud + load balancer |

---

## 12. Passos de desenvolvimento

> **Regra:** realizar commit do projeto após a implementação ou alteração de cada passo.

### Back-end
1. [x] Criar estrutura do projeto Django e apps (`accounts`, `crm`, `comissoes`, `integracao`)
2. [x] Configurar ambiente Docker (Dockerfile + docker-compose + Nginx)
3. [x] Configurar PostgreSQL, variáveis de ambiente e split de settings (base/dev/production/test)
4. [x] Implementar models e admin (Usuario, EntidadeParceira, Lead, Cliente, ProdutoContratado, Comissao, TokenIntegracao)
5. [x] Configurar autenticação JWT customizada + permissions por perfil (SuperAdmin, Operador, Parceiro)
6. [x] Implementar serializers e viewsets com validações (DRF)
7. [x] Implementar pipeline de leads com transições validadas e LeadHistorico (timeline)
8. [x] Implementar painel restrito da entidade parceira com dashboard
9. [x] Implementar cálculo automático de comissão (signal post_save)
10. [x] Implementar integração bidirecional com sistema externo (envio Celery + callback API Key)
11. [x] Implementar calendário de leads e monitoramento de SLA
12. [x] Implementar upload de arquivos com suporte a storage na nuvem (S3/R2/GCS)
13. [x] Implementar testes automatizados (23 testes cobrindo fluxo completo)
14. [ ] Documentação da API (Swagger/drf-spectacular) — ajustes finais
15. [ ] CI/CD com GitHub Actions

### Front-end (Django Templates + HTMX + Alpine.js + Tailwind CSS v4)
16. [x] Configurar Tailwind CSS v4 (pytailwindcss) + HTMX + Alpine.js
17. [x] Criar app `web` com views, mixins, context processors e URLs
18. [x] Implementar layout base (sidebar responsiva, topbar, messages, loading)
19. [x] Implementar tela de login
20. [x] Implementar dashboard com stats, pipeline e leads recentes
21. [x] Implementar listagem de leads com busca/filtros HTMX em tempo real
22. [x] Implementar detalhe do lead com timeline e alteração de status via HTMX
23. [x] Implementar formulário de criação de lead
24. [x] Implementar pipeline Kanban (visualização por colunas de status)
25. [x] Implementar calendário de leads por mês
26. [x] Implementar listagem e detalhe de clientes
27. [x] Implementar listagem de comissões com filtros
28. [x] Aplicar identidade visual RUCH (paleta de cores extraída do logo)
29. [x] Implementar landing page pública com seções para parceiros + CTA login
30. [x] Redesenhar tela de login com branding RUCH (split layout)
31. [x] Refatorar controle de acesso para usar permissoes Django (groups + permissions)
32. [x] Refatorar model Cliente: remover documento, adicionar endereco/cep, arquivo = "Produtos ou Servicos"
33. [x] Remover modulo de conversao de lead em cliente (lead ja chega convertida do parceiro)
34. [x] Implementar CRUD completo de clientes na dashboard (criar, editar, excluir com permissoes)
35. [x] Eliminar model Lead — unificar pipeline de status no model Cliente
36. [x] Tornar todos os campos do Cliente obrigatorios com validacao e mensagens de erro
37. [x] Criar model Endereco separado (CEP, logradouro, numero, complemento, bairro, cidade, UF)
38. [x] Implementar auto-preenchimento de endereco via ViaCEP (Alpine.js no front)
39. [x] Redesenhar area privada com dark theme (layout 3 colunas: sidebar + main + right panel)
40. [x] Implementar toggle de tema claro/escuro com persistencia no localStorage
41. [x] Criar models Produto, Plano e PlanoProduto (catalogo + precos por parceiro)
42. [x] Refatorar Cliente: remover produto_interesse e ProdutoContratado, adicionar M2M com Plano
43. [x] Refatorar comissao: gerada ao concluir cliente (soma dos planos), nao por ProdutoContratado
44. [x] Implementar CRUD web de Produtos e Planos com permissoes
45. [x] Adicionar links Produtos e Planos na sidebar por permissao
46. [x] Selecao multipla de planos no cadastro de cliente (adicionar/remover dinamico com Alpine.js)
47. [x] Limpar referencias a produto_interesse dos templates
48. [x] Preparar projeto para deploy: Dockerfile multi-stage, Gunicorn config, health check,
       entrypoint, production settings, CI/CD GitHub Actions, docker-compose atualizado
49. [x] CRUD de Usuarios na dashboard (criar, editar, grupos, ativar/desativar, excluir)
50. [x] CRUD de Entidades Parceiras na dashboard (criar, editar percentual, ativar/desativar)
51. [x] Acao "Marcar como pago" nas comissoes (sem precisar do admin Django)
52. [x] CRUD de Tokens de integracao na dashboard (criar, excluir, visualizar token)
53. [x] Sidebar com secao "Administracao" separada (Usuarios, Parceiros, Tokens API)
54. [x] CRUD de Grupos com matriz visual de permissoes (modulo x CRUD checkboxes)
55. [x] Simplificar atribuicao de grupo na criacao/edicao de usuario (select unico)
56. [x] Remover campo perfil do model Usuario — controle 100% por grupos/permissoes
57. [x] Adicionar status falha_implantacao (Zypher NOK) + transicao retry para em_processamento
58. [x] Validacao de formato de arquivo no upload de cliente (28 formatos aceitos)
59. [x] Avatar do usuario: upload local, Gravatar automatico, iniciais como fallback
60. [x] Sidebar colapsavel com grupos accordion (Clientes, Catalogo, Financeiro, Administracao)
61. [x] Modulo de Notificacoes Fase 1: model, signals automaticos, right panel, historico
62. [x] Modulo de Notificacoes Fase 2: preferencias do usuario + polling HTMX a cada 30s
63. [x] Modulo RH Fase 1: app rh, models Departamento/Cargo/Colaborador/HistoricoColaborador, CRUD web completo, sidebar RH/Pessoas
64. [x] Refatorar Departamento como system-managed + criar model Setor (subdivisao operacional)
65. [x] Reorganizar sidebar por departamentos (Comercial, Financeiro, RH, placeholders futuros)
66. [x] Permissoes individuais por usuario (mesma matriz dos grupos, colapsavel, HTMX dinamico)
67. [x] Grupos de permissoes alinhados aos departamentos (Administrador, Comercial, Financeiro, RH, Empresa Parceira)
68. [x] Fixtures de dev para RH (setores, cargos, colaboradores, historico)
69. [x] Modulo RH Fase 2: Documentos (upload, vencimento, alertas) + Onboarding (templates, checklist, progresso)
70. [x] Modulo RH Fase 3: Ferias/Ausencias (solicitacao, aprovacao, calendario) + Treinamentos (CRUD, inscricao, participacao)
71. [x] Modulo RH Fase 4: Metas/PDI (ciclos, atingimento ponderado, acoes) + eNPS (pesquisas, calculo score, respostas)
72. [ ] Modulo RH Fase 5: Relatorios e indicadores + Integracoes
73. [ ] Implementar modulos futuros por departamento (ver mapa abaixo)
41. [ ] Aplicar design system (JSON) quando fornecido

> **Stack front-end:** Zero Node.js. Tailwind CSS v4 via pytailwindcss (standalone binary), HTMX para interatividade server-driven, Alpine.js para estado local (dropdowns, modais, sidebar). Tudo servido pelo próprio Django.

---

## 13. Mapa de departamentos do sistema

Cada departamento corresponde a um grupo de menu na sidebar e a um grupo de permissoes.
Novos modulos sao implementados como submenus dentro do departamento correspondente.

| # | Departamento | Status | Submenus atuais | Submenus futuros |
|---|---|---|---|---|
| 1 | **Comercial** | Implementado | Clientes, Pipeline, Calendario, +Novo, Produtos, Planos | — |
| 2 | **Financeiro** | Implementado (parcial) | Comissoes | Folha, Contas a Pagar/Receber |
| 3 | **RH / Pessoas** | Implementado (Fase 1) | Colaboradores, Cargos, Setores | Ferias, Treinamento, Metas, eNPS |
| 4 | **Marketing** | Placeholder | — | Campanhas, Leads de marketing, Analytics |
| 5 | **Tecnologia** | Placeholder | — | Projetos, Roadmap, Infraestrutura |
| 6 | **Juridico** | Placeholder | — | Contratos, Compliance, LGPD |
| 7 | **Operacoes** | Placeholder | — | Onboarding de servicos, Suporte, SLA |
| 8 | **Produto** | Placeholder | — | Gestao de produto, Roadmap, Backlog |

**Menu Administracao** (customizado, nao e departamento):
Usuarios, Parceiros, Tokens API, Grupos, Admin Django

### Notas arquiteturais
- Departamentos sao seedados via migration (system-managed, sem CRUD manual)
- Cada departamento implementado ganha um grupo de permissoes correspondente no `setup_groups`
- O modulo `organization` mencionado no doc de referencia do RH **nao foi criado** — Cargo/Departamento/Setor ficam no app `rh`
- O submodulo 2 do doc (Cargos e estrutura) **ja foi implementado** na Fase 1
- API REST dos modulos de RH ainda nao foi criada (apenas CRUD web)

---

*Planejamento gerado com Claude · RUCH Digital Technology*
