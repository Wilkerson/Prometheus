# Sistema de Captação e Gestão de Clientes — RUCH
> Planejamento técnico completo · Django + Python

---

## 1. Contexto do projeto

Sistema web para captação e gestão de clientes de produtos/serviços de tecnologia (Agentes IA, SaaS, CRM, ERP, Sites, Consultoria). Uma entidade parceira comercial acessa um painel restrito para inserir leads captados. O sistema gerencia o pipeline interno, calcula comissões e integra com sistema externo próprio via API REST.

### Fluxo principal

```
Parceiro envia lead → Recebida → Em Análise → Em Processamento ──→ API envia para sistema externo
                                                                            ↓
                                                          Sistema externo implanta o serviço
                                                                            ↓
                                              Concluída ←── Callback retorna status pro Prometheus
                                                  ↓
                                          Converte em Cliente → Produto Contratado → Comissão gerada
```

---

## 2. Stack tecnológico

- **Backend:** Python 3.12 + Django 5 + Django REST Framework
- **Banco de dados:** PostgreSQL 15
- **Cache / filas:** Redis + Celery
- **Autenticação:** JWT (djangorestframework-simplejwt) + API Key (sistemas externos)
- **Storage:** django-storages (AWS S3 / Cloudflare R2 / Google Cloud Storage)
- **Servidor:** Nginx + Gunicorn
- **Infra:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoramento:** Sentry + Uptime Kuma
- **Testes:** Django TestCase + SQLite em memória

---

## 3. Perfis de usuário e controle de acesso

| Perfil | Role | Acesso |
|---|---|---|
| Super Admin | `super_admin` | Acesso total — CRUD de usuários, parceiros, leads, clientes, comissões |
| Operador Interno | `operador` | CRM — gerencia leads, converte clientes, altera status, produtos contratados |
| Entidade Parceira | `parceiro` | Painel restrito — cadastra leads, vê apenas os seus, consulta suas comissões |
| Sistema Externo | API Key (`X-API-Key`) | Callback de status de leads e inserção de clientes via API |

O token JWT retorna `perfil`, `nome` e `email` no payload para controle no front-end.

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
  id, username, email, first_name, last_name, perfil [super_admin|operador|parceiro],
  is_active, date_joined

ENTIDADE_PARCEIRA
  id, usuario_id (FK OneToOne), nome_entidade, percentual_comissao, ativo, criado_em

LEAD
  id, parceiro_id (FK), operador_id (FK nullable), nome, email, telefone,
  produto_interesse [agentes_ia|saas|crm|erp|sites|consultoria],
  status [recebida|em_analise|em_processamento|concluida|perdida],
  criado_em, atualizado_em

LEAD_HISTORICO
  id, lead_id (FK), status_anterior, status_novo, usuario_id (FK nullable),
  observacao, criado_em

CLIENTE
  id, lead_id (FK OneToOne), nome, documento (CPF, opcional), cnpj (obrigatório, unique),
  email, telefone, arquivo (FileField, opcional), ativo, ativado_em

PRODUTO_CONTRATADO
  id, cliente_id (FK), produto, valor, status [ativo|suspenso|cancelado], contratado_em

COMISSAO
  id, parceiro_id (FK), venda_id (FK), valor_venda,
  percentual, valor_comissao, status [pendente|pago], gerado_em

TOKEN_INTEGRACAO
  id, nome, token (auto-gerado), ativo, criado_em
```

### Transições válidas de status do Lead

```
recebida        → em_analise, perdida
em_analise      → em_processamento, perdida
em_processamento → concluida, perdida  (concluida vem via callback do sistema externo)
concluida       → (status final)
perdida         → (status final)
```

---

## 8. Endpoints da API (base: /api/v1/)

### Autenticação
- `POST /auth/token/` — Login, retorna JWT com perfil/nome/email
- `POST /auth/token/refresh/` — Renova token
- `GET  /auth/me/` — Dados do usuário logado
- CRUD `/auth/usuarios/` — Gestão de usuários (Super Admin)

### Leads
- `POST /leads/` — Cadastra lead
- `GET  /leads/` — Lista leads (filtro por perfil)
- `GET  /leads/{id}/` — Detalhe com histórico completo
- `PATCH /leads/{id}/status/` — Atualiza status com validação de transição (operador/admin)
- `GET  /leads/{id}/historico/` — Timeline de mudanças de status
- `POST /leads/{id}/converter/` — Converte lead concluída em cliente (operador)
- `GET  /leads/calendario/?mes=YYYY-MM` — Leads agrupadas por dia
- `GET  /leads/sla/?dias=N` — Leads paradas há mais de N dias

### Painel do Parceiro
- `POST /parceiro/leads/` — Cadastra novo lead
- `GET  /parceiro/leads/` — Lista leads do parceiro
- `GET  /parceiro/leads/{id}/` — Detalhe de um lead
- `GET  /parceiro/dashboard/` — Resumo com totais por status e comissões

### Clientes
- CRUD `/clientes/` — Gestão de clientes (operador/admin)
- CRUD `/produtos-contratados/` — Produtos de cada cliente

### Comissões
- `GET /comissoes/` — Lista comissões (parceiro vê as próprias)

### Integração externa (autenticação via X-API-Key)
- `POST /integracao/cliente/` — Insere cliente via sistema externo
- `POST /integracao/lead/status/` — Callback do sistema externo (concluida/perdida)

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
28. [ ] Aplicar design system (JSON) quando fornecido

> **Stack front-end:** Zero Node.js. Tailwind CSS v4 via pytailwindcss (standalone binary), HTMX para interatividade server-driven, Alpine.js para estado local (dropdowns, modais, sidebar). Tudo servido pelo próprio Django.

---

*Planejamento gerado com Claude · RUCH Digital Technology*
