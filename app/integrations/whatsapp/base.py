from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

from app.models.item import MediaItem


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    AWAITING_AUTH = "awaiting_auth"
    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class WhatsAppGroup(BaseModel):
    id: str
    name: str
    participant_count: Optional[int] = None
    description: Optional[str] = None


class BaseWhatsAppClient(ABC):
    """
    Interface abstrata do cliente de integração com o WhatsApp.
    Permite desacoplar a interface e o motor de regras da tecnologia específica.
    """

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Retorna o estado atual da conexão e detalhes relevantes."""
        pass

    @abstractmethod
    def connect(self) -> Dict[str, Any]:
        """Inicia a tentativa de conexão / autenticação."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Encerra a sessão com segurança, limpando recursos voláteis."""
        pass

    @abstractmethod
    def get_auth_qr(self) -> Optional[str]:
        """Retorna os dados do QR code ou imagem para escaneamento se aplicável."""
        pass

    @abstractmethod
    def list_groups(self) -> List[WhatsAppGroup]:
        """Lista os grupos acessíveis na conta conectada."""
        pass

    @abstractmethod
    def select_group(self, group_id: str) -> bool:
        """Define o grupo selecionado para leitura de mídia."""
        pass

    @abstractmethod
    def fetch_group_images(self, group_id: str, limit: int = 30) -> List[Tuple[MediaItem, bytes]]:
        """
        Obtém imagens acessíveis no grupo selecionado.
        Retorna tuplas (MediaItem, bytes_da_imagem).
        """
        pass
