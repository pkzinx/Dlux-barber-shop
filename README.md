<div align="center">
  <img width="150" height="150" src="./public/assets/img/icon-logo.png" alt="Logo Dlux" />
  <h1>Dlux Barbearia — Site + Painel</h1>
</div>

<div align="center">
  <img alt="License" src="https://img.shields.io/static/v1?label=license&message=CC0 1.0 Universal&color=3abcbf&labelColor=333333">
  <img src="https://img.shields.io/static/v1?label=Django&message=4.x&color=3abcbf&labelColor=333333" />
  <img src="https://img.shields.io/static/v1?label=NextJS&message=15.x&color=3abcbf&labelColor=333333" />
  <img src="https://img.shields.io/static/v1?label=Postgres&message=Railway&color=3abcbf&labelColor=333333" />
</div>

## Visão Geral

Solução completa para gestão de barbearias, composta por um **Site Institucional** (Front-end Next.js) para agendamentos e apresentação, e um **Painel Administrativo** (Back-end Django) robusto para controle total da operação. O sistema foi desenhado para centralizar agenda, finanças, gestão de clientes e serviços em uma interface escura ("dark mode"), moderna e responsiva.

---

## Funcionalidades do Painel

O Painel Dlux vai muito além de uma simples agenda. Ele atua como um ERP simplificado para a barbearia.

### 📅 Gestão de Agenda
- **Fluxo de Agendamento:** Visualização clara de horários livres e ocupados.
- **Bloqueios:** Capacidade de bloquear horários específicos para pausas ou imprevistos.
- **Status:** Controle de ciclo de vida do agendamento (Agendado, Concluído, Cancelado).

### 👥 Gestão de Clientes (CRM)
Uma poderosa ferramenta para retenção e fidelização.
- **Base de Dados:** Listagem completa com busca inteligente.
- **Métricas Individuais:** Visualize rapidamente o "Total Gasto", "Total de Visitas" e "Frequência Média" de cada cliente.
- **Filtros e Ordenação:**
  - *Mais Visitas:* Identifique seus clientes VIPs.
  - *Último Agendamento:* Encontre clientes inativos/sumidos para ações de resgate.
  - *Total Gasto:* Saiba quem traz mais receita.
- **Ações de Marketing (WhatsApp):**
  - Integração direta com WhatsApp.
  - **Mensagens Prontas:** Scripts pré-configurados para diferentes cenários:
    - *Manutenção:* Lembrete para renovar o corte.
    - *Resgate:* Para clientes sumidos há semanas.
    - *Recuperação:* Ofertas especiais para reconquista.
    - *Descontraído:* Mensagens com humor para engajamento.
- **Exportação:** Download da base em CSV (Nome+Telefone ou Completo) para uso em ferramentas externas.

### 💰 Finanças e Caixa
Controle financeiro detalhado e transparente.
- **KPIs em Tempo Real:** Faturamento do dia, mês, ticket médio e cancelamentos.
- **Retiradas de Caixa:** Sistema para registrar saídas (sangrias) categorizadas (Fornecedores, Aluguel, Produtos, etc) com observações.
- **Relatórios:** Tabelas de resumo por barbeiro (comissão/produtividade) e fluxo de caixa.
- **Exportação:** Gere relatórios CSV da visão financeira atual para contabilidade.

### ✂️ Gestão de Serviços
- **Catálogo Dinâmico:** Adicione, edite ou remova serviços.
- **Precificação e Duração:** Ajuste valores e tempo estimado de cada procedimento.
- **Controle de Visibilidade:** Ative ou inative serviços no site de agendamento instantaneamente.

### 🛡️ Perfis de Acesso
- **Admin:** Acesso irrestrito a todas as finanças, configurações e relatórios globais.
- **Barbeiro:** Visão focada na própria agenda e comissões, sem acesso a dados sensíveis do negócio.

---

## Gráficos e Inteligência de Dados

O painel oferece uma suíte de gráficos interativos para tomada de decisão, utilizando bibliotecas modernas para visualização de dados.

1.  **Linha do Tempo de Agendamentos (Timeline)**
    *   Visualize a densidade de atendimentos ao longo do dia, semana ou mês.
    *   Permite identificar gargalos e horários de pico.

2.  **Receita Total (Comparativo)**
    *   Gráfico de barras/linha mostrando a evolução do faturamento.
    *   **Função Comparar:** Sobreponha o desempenho do mês atual com o mês anterior para medir crescimento.

3.  **Ranking de Serviços**
    *   Descubra quais cortes ou tratamentos são os "carros-chefe".
    *   Compare a demanda de serviços específicos entre períodos diferentes.

4.  **Produtividade por Barbeiro**
    *   Gráfico de distribuição que mostra a fatia de atendimentos de cada profissional.
    *   Essencial para balancear a carga de trabalho da equipe.

*Todos os gráficos possuem controles de "Minimizar" para limpar a interface e focar no que importa.*

---

## Tecnologias e Arquitetura

### Backend (API & Painel)
- **Framework:** Django 4.x (Python)
- **Banco de Dados:** PostgreSQL
- **Template Engine:** Django Templates (com injeção de dados dinâmicos)
- **Autenticação:** Sistema de usuários do Django com permissões granulares.

### Frontend (Site de Agendamento)
- **Framework:** Next.js 15.x (React)
- **Estilização:** Styled-components / CSS Modules
- **Integração:** Consumo de API RESTful do backend.

### Infraestrutura
- **Hospedagem:** Preparado para deploy em plataformas como Railway/Vercel.
- **Túnel:** Suporte a Ngrok para desenvolvimento e testes locais acessíveis externamente.

---

## Comandos Essenciais

Para rodar o projeto localmente:

**Backend:**
```bash
# Ativar venv e rodar servidor
python3 manage.py runserver 0.0.0.0:8000
```

**Frontend:**
```bash
# Rodar em porta específica (ex: 3001)
npm run dev -- -p 3001
```

---

## Notas de Versão — v3.1.7

- **Refatoração de Serviços:** Novo painel de gestão de serviços com edição em linha e melhor UX.
- **Correções de Interface:** Ajustes nos modais e formulários para prevenir erros de linter e usabilidade.
- **Porta Padrão:** Frontend migrado para porta 3001 para evitar conflitos.
- **Estabilidade:** Correções em URLs de API (localhost -> 127.0.0.1) resolvendo erros 500 em conexões locais.

## Licença
Este projeto é distribuído sob a licença CC0 1.0 Universal.
