# Sistema de Captação e Gestão de Clientes — RUCH
> Planejamento técnico completo · Django + Python

---

## Contexto do projeto

Sistema web para captação e gestão de clientes de produtos/serviços de tecnologia (Agentes IA, SaaS, CRM, ERP, Sites, Consultoria). Uma entidade parceira comercial acessa um painel restrito para inserir leads captados. O sistema gerencia o pipeline de vendas, calcula comissões e expõe uma API REST para integração com sistema externo próprio.

---

## 1. Stack tecnológico

- **Backend:** Python 3.12 + Django 5 + Django REST Framework
- **Banco de dados:** PostgreSQL 15
- **Cache / filas:** Redis + Celery
- **Autenticação:** JWT (djangorestframework-simplejwt)
- **Servidor:** Nginx + Gunicorn
- **Infra:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoramento:** Sentry + Uptime Kuma

---

## 2. Perfis de usuário

| Perfil | Acesso |
|---|---|
| Super Admin | Acesso total ao sistema |
| Operador interno | Módulos atribuídos |
| Entidade parceira | Cadastro de leads + visualização de comissões |
| Sistema externo | API Key para integração |

---

## 3. Módulos do sistema

### MVP (fase 1)
- Autenticação e controle de acesso por perfil
- CRM: gestão de leads e clientes
- Painel restrito da entidade parceira
- Cálculo de comissão percentual por venda
- API REST para integração com sistema externo

### Pós-MVP
- Módulo financeiro
- Suporte ao cliente / tickets
- Operacional / onboarding de serviços

---

## 4. Produtos/serviços ofertados

- Agentes de IA
- SaaS
- CRM
- ERP
- Sites
- Consultoria em tecnologia e automação

---

## 5. Arquitetura

```
Navegador (Admin / Parceiro / Sistema externo)
        ↓
    Nginx (SSL · rate limit · static files)
        ↓
  Django App — Gunicorn/WSGI
  ┌─────────────────────────────────────────┐
  │ Auth module │ CRM module │ API REST │ Admin │
  └─────────────────────────────────────────┘
        ↓              ↓              ↓
  PostgreSQL 15    Redis cache    Object Storage
        ↓
  Celery workers (tarefas assíncronas)
```

---

## 6. Modelos de dados (principais)

```
USUARIO
  id, nome, email, perfil, ativo, criado_em

ENTIDADE_PARCEIRA
  id, usuario_id (FK), nome_entidade, percentual_comissao, ativo

LEAD
  id, parceiro_id (FK), operador_id (FK), nome, email, telefone,
  produto_interesse, status [novo|qualificado|vendido|perdido], criado_em

CLIENTE
  id, lead_id (FK), nome, documento, email, telefone, status, ativado_em

PRODUTO_CONTRATADO
  id, cliente_id (FK), produto, valor, status, contratado_em

COMISSAO
  id, parceiro_id (FK), venda_id (FK), valor_venda,
  percentual, valor_comissao, status [pendente|pago], gerado_em

TOKEN_INTEGRACAO
  id, nome, token, ativo, criado_em
```

---

## 7. Endpoints da API (base: /api/v1/)

### Autenticação
- `POST /auth/token/` — Login, retorna JWT
- `POST /auth/token/refresh/` — Renova token

### Leads
- `POST /leads/` — Cadastra lead (parceiro)
- `GET /leads/` — Lista leads do parceiro
- `GET /leads/{id}/` — Detalhe do lead
- `PATCH /leads/{id}/status/` — Atualiza status (admin)

### Clientes
- `POST /clientes/` — Converte lead em cliente ativo
- `GET /clientes/` — Lista clientes (admin)
- `GET /clientes/{id}/` — Detalhe + produtos

### Comissões
- `GET /comissoes/` — Lista comissões (parceiro vê as próprias)

### Integração externa
- `POST /integracao/cliente/` — Insere cliente via API Key (sistema externo)

---

## 8. Planejamento de capacidade

| Fase | Prazo | Clientes | Infraestrutura |
|---|---|---|---|
| MVP | 0–6 meses | até 500 | VPS 2 vCPU / 4GB / 50GB |
| Crescimento | 6–18 meses | até 5.000 | VPS 4 vCPU / 8GB + Redis |
| Escala | 18+ meses | 50.000+ | Cloud + load balancer |

---

## 9. Próximos passos de desenvolvimento

> **Regra:** realizar commit do projeto após a implementação ou alteração de cada passo.

1. [x] Criar estrutura do projeto Django
2. [x] Configurar ambiente Docker (Dockerfile + docker-compose.yml)
3. [x] Configurar PostgreSQL e variáveis de ambiente (.env)
4. [x] Criar apps Django: `accounts`, `crm`, `comissoes`, `integracao`
5. [x] Implementar models conforme planejamento de dados
6. [x] Configurar autenticação JWT + perfis de acesso
7. [x] Implementar serializers e viewsets (DRF)
8. [ ] Implementar painel restrito da entidade parceira
9. [ ] Implementar cálculo automático de comissão
10. [ ] Testes e documentação da API (Swagger/drf-spectacular)
11. [ ] Implementar front-end (design system fornecido em JSON)

---

## 10. Front-end

A implementação do front-end será realizada **por último**, após a conclusão de todos os passos do back-end. O design system será fornecido em formato JSON e servirá como base para a construção das interfaces.

---

*Planejamento gerado com Claude · RUCH Digital Technology*
