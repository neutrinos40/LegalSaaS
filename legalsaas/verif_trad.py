import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'legalsaas.settings')

import django
django.setup()

from django.utils.translation import activate, gettext

activate('en')
for s in ['Réviser le document', 'Nouvelle mise en demeure', 'Valider',
          'Documents IA', 'Télécharger .pdf', 'Générer le brouillon']:
    print(s, '=>', gettext(s))
