from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('prenom', 'nom', 'email', 'telephone', 'avocat', 'date_creation')
    search_fields = ('nom', 'prenom', 'email')
    list_filter = ('date_creation',)