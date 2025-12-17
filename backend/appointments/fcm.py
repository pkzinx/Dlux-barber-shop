import os
import importlib

# Atrasar import do firebase_admin para evitar warnings de linter quando pacote não está disponível
firebase_admin = None
credentials = None
messaging = None
_firebase_initialized = False


def _ensure_firebase():
    global _firebase_initialized
    global firebase_admin, credentials, messaging
    if _firebase_initialized:
        return True
    # Tenta importar firebase_admin apenas quando necessário
    if firebase_admin is None:
        try:
            firebase_admin = importlib.import_module('firebase_admin')
            # Importa submódulos
            credentials = importlib.import_module('firebase_admin.credentials')
            messaging = importlib.import_module('firebase_admin.messaging')
        except Exception:
            return False
    try:
        # Credenciais: defina FIREBASE_CREDENTIALS ou JSON path via env
        cred_path = os.environ.get('FIREBASE_CREDENTIALS')
        if cred_path and os.path.isfile(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            # Alternativa: usar credenciais padrão do ambiente
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return True
    except Exception:
        return False


from typing import Optional, Dict

def send_push(token: str, title: str, body: str, data: Optional[Dict] = None) -> bool:
    """Envia notificação push via FCM. Retorna True se enviado, False caso contrário."""
    if not _ensure_firebase():
        return False
    try:
        msg = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data={**(data or {})}
        )
        messaging.send(msg)
        return True
    except Exception:
        return False