from django.urls import path
from django.contrib.auth import views as auth_views
from .views import (
    painel_index,
    dashboard_barber,
    dashboard_admin,
    panel_appointments,
    panel_finances,
    panel_clients,
    finances_chart_data,
    finances_revenue_data,
    finances_services_breakdown_data,
    finances_barber_stats_data,
    finances_withdrawals_funnel_data,
    finances_no_show_rate_data,
    finances_clients_top_data,
    finances_occupancy_buckets_data,
    panel_profile,
    panel_history,
)
from services.views import panel_services

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('painel/', painel_index, name='painel_index'),
    path('painel/barbeiro/', dashboard_barber, name='dashboard_barber'),
    path('painel/admin/', dashboard_admin, name='dashboard_admin'),
    path('painel/agendamentos/', panel_appointments, name='panel_appointments'),
    path('painel/financas/', panel_finances, name='panel_finances'),
    path('painel/financas/chart-data/', finances_chart_data, name='finances_chart_data'),
    path('painel/financas/revenue-data/', finances_revenue_data, name='finances_revenue_data'),
    path('painel/financas/services-breakdown-data/', finances_services_breakdown_data, name='finances_services_breakdown_data'),
    path('painel/financas/barber-stats-data/', finances_barber_stats_data, name='finances_barber_stats_data'),
    path('painel/financas/withdrawals-funnel-data/', finances_withdrawals_funnel_data, name='finances_withdrawals_funnel_data'),
    path('painel/financas/no-show-rate/', finances_no_show_rate_data, name='finances_no_show_rate'),
    path('painel/financas/clients-top-data/', finances_clients_top_data, name='finances_clients_top_data'),
    path('painel/financas/occupancy-buckets/', finances_occupancy_buckets_data, name='finances_occupancy_buckets_data'),
    path('painel/clientes/', panel_clients, name='panel_clients'),
    path('painel/perfil/', panel_profile, name='panel_profile'),
    path('painel/historico/', panel_history, name='panel_history'),
    path('painel/servicos/', panel_services, name='panel_services'),
]
