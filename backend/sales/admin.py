from django.contrib import admin
from .models import Sale, Withdrawal


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'barber', 'amount', 'status', 'created_at')
    list_filter = ('status', 'barber')
    search_fields = ('barber__username',)

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'note', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username',)

# Register your models here.
