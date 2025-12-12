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

Projeto composto por site e painel interno. O site apresenta a barbearia e permite iniciar agendamentos. O painel Dlux, feito para uso interno, centraliza a operação: agenda, finanças, histórico e perfil.

## Funcionalidades do Painel

- Agendamentos
  - Criação, edição, conclusão e cancelamento de serviços.
  - Pesquisa por cliente e visualização por status.
  - Fluxo rápido de agendamento com confirmação clara.
- Finanças
  - Indicadores diários e mensais baseados na conclusão dos serviços.
  - Faturamento por barbeiro e por períodos, com filtros simples.
- Histórico
  - Registro de ações de usuários e eventos relevantes.
- Perfil
  - Edição de dados de usuário e preferências.

## Gráficos e KPIs

- Agendamentos concluídos
  - Área temporal com intervalos (dia, 7, 15, 30 dias) e comparação opcional.
- Receita total
  - Visão consolidada com destaque para valores concluídos.
- Serviços mais agendados
  - Comparativo mensal opcional para identificar variações de demanda.
- Quantidade por barbeiro
  - Barras distribuídas destacando a produtividade por profissional.
- Retiradas por motivo
  - Funil que mostra concentração por categorias de retirada.

Todos os gráficos possuem controles simples e botões de minimizar padronizados para foco no conteúdo.

## Páginas do Painel

- Dashboard geral: visão rápida da operação.
- Agenda: gerenciamento de agendamentos e bloqueios de horário.
- Finanças: KPIs e gráficos de receita, serviços e produtividade.
- Histórico: trilha de auditoria com ações do sistema.
- Perfil: dados e configurações do usuário.

## Experiência

- Interface escura, moderna e responsiva.
- Controles intuitivos e consistentes entre cards e gráficos.
- Feedbacks visuais claros em ações críticas.

## Tecnologias

- Backend: Django, PostgreSQL.
- Frontend: Next.js e React.
- Gráficos: ApexCharts e CanvasJS.

## Notas de versão — v3.1.x

- Padronização dos botões de minimizar nos gráficos.
- Melhorias na página de Finanças e comparações.
- Limpeza de dados de teste para ambiente controlado.

## Licença

Este repositório utiliza licença pública conforme o badge acima.
