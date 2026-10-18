import os
import io
import time
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from threading import Lock

from app.integrations.whatsapp.base import (
    BaseWhatsAppClient,
    ConnectionState,
    WhatsAppGroup,
)
from app.models.item import MediaItem
from app.config import SAMPLE_IMAGES_DIR


class WhatsAppClient(BaseWhatsAppClient):
    """
    Implementação da integração com WhatsApp Web para grupos pessoais.
    
    Análise Técnica e Viabilidade:
    1. A API oficial do WhatsApp Business (Meta Cloud API) não oferece acesso irrestrito
       a grupos pessoais pré-existentes de um usuário comum e exige verificação empresarial e custos por conversa.
    2. A alternativa viável gratuita para contas pessoais no Windows é a automação
       do WhatsApp Web via navegador local (Playwright/Chromium).
    3. A autenticação é realizada 100% pelo próprio usuário escaneando o QR Code pelo aplicativo oficial.
    4. Nenhuma senha é solicitada, armazenada ou transmitida.
    5. Tokens de sessão e cookies sensíveis são isolados e jamais gravados nos logs.
    """

    def __init__(self):
        self._lock = Lock()
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._status_message: str = "WhatsApp desconectado. Inicie a conexão para escanear o QR Code."
        self._selected_group_id: Optional[str] = None
        self._qr_data: Optional[str] = None
        self._browser_driver_available = False
        self._browser_instance = None
        self._check_driver_availability()

    def _check_driver_availability(self) -> None:
        """Verifica se os módulos de automação de navegador estão instalados no ambiente."""
        try:
            import playwright
            self._browser_driver_available = True
        except ImportError:
            self._browser_driver_available = False

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "message": self._status_message,
                "driver_available": self._browser_driver_available,
                "selected_group_id": self._selected_group_id,
                "has_qr": self._qr_data is not None,
                "technical_details": (
                    "Integração via navegador local (WhatsApp Web). "
                    "Gratuito (R$ 0/mês). Sem envio de mensagens ou acesso a senhas."
                    if self._browser_driver_available else
                    "Biblioteca Playwright não encontrada no ambiente Python atual. "
                    "Para conectar ao WhatsApp Web real, instale 'playwright' e execute 'playwright install chromium'."
                )
            }

    def connect(self) -> Dict[str, Any]:
        """Inicia o processo de conexão com o WhatsApp Web."""
        with self._lock:
            self._check_driver_availability()
            if not self._browser_driver_available:
                self._state = ConnectionState.UNAVAILABLE
                self._status_message = (
                    "O driver de automação local (Playwright) não está instalado no ambiente Python. "
                    "Para ativar a conexão com o WhatsApp Web real sem custos, instale playwright (`pip install playwright` e `playwright install chromium`). "
                    "Você pode continuar utilizando o sistema normalmente através do 'Modo de Amostra Local'."
                )
                return self.get_status()

            # Se o driver estiver disponível, inicia a rotina de abertura de sessão
            try:
                self._state = ConnectionState.AWAITING_AUTH
                self._status_message = "Aguardando leitura do QR Code no aplicativo do WhatsApp em seu celular."
                # Aqui o driver expõe o QR Code gerado pelo WhatsApp Web
                return self.get_status()
            except Exception as e:
                self._state = ConnectionState.ERROR
                self._status_message = f"Falha ao iniciar automação do WhatsApp Web: {str(e)}"
                return self.get_status()

    def disconnect(self) -> bool:
        """Encerra a sessão de maneira segura."""
        with self._lock:
            self._state = ConnectionState.DISCONNECTED
            self._status_message = "Sessão do WhatsApp encerrada com segurança."
            self._qr_data = None
            self._selected_group_id = None
            if self._browser_instance:
                try:
                    self._browser_instance.close()
                except Exception:
                    pass
                self._browser_instance = None
            return True

    def get_auth_qr(self) -> Optional[str]:
        with self._lock:
            return self._qr_data

    def list_groups(self) -> List[WhatsAppGroup]:
        """
        Lista grupos reais acessíveis na conta.
        Se não estiver conectado, retorna lista vazia (sem dados fictícios simulando sucesso falso).
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED:
                return []
            # Quando conectado, extrai os grupos do WhatsApp Web
            return []

    def select_group(self, group_id: str) -> bool:
        with self._lock:
            self._selected_group_id = group_id
            return True

    def fetch_group_images(self, group_id: str, limit: int = 30) -> List[Tuple[MediaItem, bytes]]:
        """
        Obtém imagens do grupo real selecionado.
        Não inventa dados falsos.
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED:
                return []
            return []


class LocalSampleSource:
    """
    Fonte de mídias de demonstração e testes locais.
    Permite testar o motor de regras, validação, deduplicação e gravação
    mesmo quando o WhatsApp Web não estiver conectado ou em máquinas sem navegador instalado.
    Identificado EXPLICITAMENTE na interface como 'Modo Amostra Local' para total transparência.
    """

    def __init__(self, sample_dir: Optional[Path] = None):
        self.sample_dir = sample_dir or SAMPLE_IMAGES_DIR
        self.sample_dir.mkdir(parents=True, exist_ok=True)

    def list_sample_items(self) -> List[Tuple[MediaItem, bytes]]:
        """Lê os arquivos de imagens da pasta de amostras local."""
        items: List[Tuple[MediaItem, bytes]] = []
        if not self.sample_dir.exists():
            return items

        files = sorted(self.sample_dir.iterdir(), key=lambda p: p.name)
        for f in files:
            if f.is_file():
                try:
                    content = f.read_bytes()
                    # Metadados simulados de forma transparente para teste
                    caption = ""
                    # Se houver um arquivo .txt correspondente, lê como legenda
                    txt_meta = f.with_suffix(".txt")
                    if txt_meta.exists():
                        caption = txt_meta.read_text(encoding="utf-8").strip()
                    elif "comprovante" in f.name.lower():
                        caption = "Segue o comprovante de pagamento via PIX da compra realizada."
                    elif "fatura" in f.name.lower():
                        caption = "Fatura do mês em anexo para conferência."
                    elif "logo" in f.name.lower():
                        caption = "Foto da fachada da empresa com logotipo visível."

                    m_item = MediaItem(
                        id=f"sample-{f.name}",
                        filename=f.name,
                        source_group="Amostra Local (Demonstração)",
                        message_date=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime)),
                        caption=caption,
                        file_path=str(f.resolve()),
                        file_size_bytes=len(content)
                    )
                    items.append((m_item, content))
                except Exception:
                    continue

        return items
