from rest_framework import viewsets, permissions, generics, status
from rest_framework.response import Response
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from typing import Optional

from .models import Service
from .serializers import ServiceSerializer


ALLOWED_ADMIN_USERNAMES = {"alafy", "kaue"}


class IsServiceAdmin(permissions.BasePermission):
    """
    Apenas usuários admin (superuser) ou barbeiros permitidos podem criar/editar.
    Demais usuários autenticados podem apenas ler (GET/HEAD/OPTIONS).
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        username = (request.user.username or "").lower()
        return request.user.is_superuser or username in ALLOWED_ADMIN_USERNAMES


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by('title')
    serializer_class = ServiceSerializer
    permission_classes = [IsServiceAdmin]

    def create(self, request, *args, **kwargs):
        if Service.objects.count() >= 50:
            return Response({'detail': 'Limite de 50 serviços atingido.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)


class PublicServiceListView(generics.ListAPIView):
    """
    Endpoint público (sem autenticação) para o site listar serviços ativos.
    """

    queryset = Service.objects.filter(active=True).order_by('title')
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


@login_required
def panel_services(request: HttpRequest):
    username = (request.user.username or "").lower()
    if not (request.user.is_superuser or username in ALLOWED_ADMIN_USERNAMES):
        return HttpResponseForbidden("Acesso restrito aos admins da barbearia.")

    def _parse_price(raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        value = raw.replace(".", "").replace(",", ".").strip()
        try:
            return float(value)
        except Exception:
            return None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            if Service.objects.count() >= 50:
                messages.error(request, "Limite de 50 serviços atingido.")
                return redirect("panel_services")
            title = request.POST.get("title", "").strip()
            price = _parse_price(request.POST.get("price"))
            duration = request.POST.get("duration_minutes")
            # Por padrão, serviços novos são ativos (checkbox marcado = "on", não marcado = None)
            # Se não vier "on", assume True para garantir que apareça no site
            active = request.POST.get("active") == "on" or request.POST.get("active") is None
            if not title or price is None or not duration:
                messages.error(request, "Preencha título, preço e duração (preço em formato 20 ou 20,00).")
            else:
                try:
                    duration_int = int(duration)
                    new_service = Service.objects.create(
                        title=title,
                        price=price,
                        duration_minutes=duration_int,
                        active=True,  # Sempre criar como ativo para aparecer no site
                    )
                    messages.success(request, f"Serviço '{title}' criado e já visível no site.")
                except (ValueError, TypeError) as e:
                    messages.error(request, f"Erro ao criar serviço: duração inválida.")
            return redirect("panel_services")

        if action == "update":
            try:
                service_id = int(request.POST.get("service_id"))
                service = Service.objects.get(id=service_id)
            except (TypeError, ValueError, Service.DoesNotExist):
                messages.error(request, "Serviço não encontrado.")
                return redirect("panel_services")

            service.title = request.POST.get("title", service.title).strip()
            new_price = _parse_price(request.POST.get("price"))
            if new_price is not None:
                service.price = new_price
            service.duration_minutes = request.POST.get("duration_minutes", service.duration_minutes)
            service.active = request.POST.get("active") == "on"
            service.save()
            messages.success(request, f"Serviço '{service.title}' atualizado.")
            return redirect("panel_services")

    services = Service.objects.all().order_by("title")
    try:
        if services.count() >= 45:
            messages.warning(request, "Aviso: você possui 45 ou mais serviços. O limite é 50.")
    except Exception:
        pass
    return render(
        request,
        "panel_services.html",
        {
            "services": services,
        },
    )

# Create your views here.
