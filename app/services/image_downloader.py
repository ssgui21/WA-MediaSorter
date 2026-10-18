import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

from app.services.image_analyzer import ImageAnalyzer
from app.repositories.history_repository import HistoryRepository


class DestinationValidationError(Exception):
    pass


class ImageDownloader:
    """
    Serviço responsável por validar destinos locais, tratar conflitos de nomenclatura,
    evitar arquivos duplicados via hash criptográfico e salvar mídias aprovadas.
    """

    def __init__(self, history_repo: Optional[HistoryRepository] = None):
        self.history_repo = history_repo or HistoryRepository()
        self.analyzer = ImageAnalyzer()

    @staticmethod
    def validate_destination(path_str: str) -> Tuple[bool, str]:
        """
        Valida a existência e a permissão de escrita de uma pasta de destino no Windows.
        Retorna (é_válido, mensagem_explicativa).
        """
        if not path_str or not path_str.strip():
            return False, "O caminho da pasta de destino não pode estar vazio."

        try:
            target_path = Path(path_str).resolve()
        except Exception as e:
            return False, f"Caminho inválido para o sistema operacional Windows: {str(e)}"

        # Verificar se a pasta existe ou pode ser criada
        if not target_path.exists():
            try:
                target_path.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                return False, (
                    f"A pasta '{target_path}' não existe e não foi possível criá-la por falta de permissão. "
                    "Verifique os privilégios do usuário ou escolha outro diretório (ex: sua pasta Documentos ou Downloads)."
                )
            except Exception as e:
                return False, f"Não foi possível criar o diretório de destino: {str(e)}"

        if not target_path.is_dir():
            return False, f"O caminho especificado '{target_path}' não é uma pasta válida."

        # Teste de permissão real de escrita criando e removendo um arquivo temporário de teste
        test_file = target_path / ".wa_mediasorter_test_write.tmp"
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("teste_permissao_ok")
            test_file.unlink(missing_ok=True)
        except PermissionError:
            return False, (
                f"Sem permissão de gravação na pasta '{target_path}'. "
                "Para corrigir, selecione uma pasta onde seu usuário tenha permissão total de escrita."
            )
        except Exception as e:
            return False, f"Falha no teste de escrita na pasta de destino: {str(e)}"

        return True, f"Pasta válida e pronta para gravação: {target_path}"

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Remove caracteres proibidos no Windows para evitar erros e ataques de path traversal.
        """
        clean = Path(filename).name # Garante que apenas o nome do arquivo seja considerado
        # Caracteres inválidos no Windows: < > : " / \ | ? *
        clean = re.sub(r'[<>:"/\\|?*]', '_', clean).strip()
        if not clean:
            clean = "imagem_whatsapp.jpg"
        return clean

    def resolve_unique_filename(self, destination_dir: Path, desired_name: str) -> Path:
        """
        Política clara de conflito de nomes: NÃO sobrescreve silenciosamente arquivos existentes.
        Gera sufixos sequenciais: foto.jpg -> foto_1.jpg -> foto_2.jpg.
        """
        clean_name = self.sanitize_filename(desired_name)
        target = destination_dir / clean_name
        if not target.exists():
            return target

        stem = target.stem
        suffix = target.suffix
        counter = 1

        while True:
            candidate = destination_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def save_image(
        self,
        image_bytes: bytes,
        original_filename: str,
        destination_dir_str: str,
        check_existing_hashes: bool = True
    ) -> Tuple[bool, Optional[str], Optional[str], bool]:
        """
        Salva o arquivo de imagem no destino validado.
        Retorna: (sucesso, caminho_salvo, mensagem_ou_erro, é_duplicado).
        """
        # 1. Validar pasta de destino
        valid, msg = self.validate_destination(destination_dir_str)
        if not valid:
            return False, None, msg, False

        dest_dir = Path(destination_dir_str).resolve()

        # 2. Validar integridade e formato real do arquivo (não confiar apenas na extensão)
        is_valid_img, mime_or_err, validation_msg = self.analyzer.validate_image_content(
            image_bytes, original_filename
        )
        if not is_valid_img:
            return False, None, f"Arquivo rejeitado na gravação: {validation_msg}", False

        # 3. Cálculo de Hash SHA-256 para prevenção de duplicatas
        content_hash = self.analyzer.calculate_sha256(image_bytes)

        if check_existing_hashes and self.history_repo.is_hash_known(content_hash):
            return False, None, f"Imagem idêntica já salva anteriormente (hash SHA-256: {content_hash[:8]}...).", True

        # 4. Resolução de conflito de nomes (não sobrescrever)
        target_path = self.resolve_unique_filename(dest_dir, original_filename)

        # 5. Gravação segura no disco
        try:
            with open(target_path, "wb") as f:
                f.write(image_bytes)
        except PermissionError:
            return False, None, f"Permissão negada ao gravar '{target_path.name}'.", False
        except OSError as e:
            return False, None, f"Erro de disco/espaço insuficiente ao salvar: {str(e)}", False
        except Exception as e:
            return False, None, f"Erro inesperado ao salvar imagem: {str(e)}", False

        # 6. Registrar hash no repositório de histórico para evitar futuras duplicatas
        self.history_repo.record_saved_hash(
            content_hash=content_hash,
            filename=target_path.name,
            saved_path=str(target_path)
        )

        return True, str(target_path), f"Imagem salva com sucesso como {target_path.name}", False
