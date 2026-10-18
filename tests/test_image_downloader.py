import os
import io
import pytest
from pathlib import Path
from PIL import Image

from app.services.image_downloader import ImageDownloader
from app.services.image_analyzer import ImageAnalyzer
from app.repositories.history_repository import HistoryRepository


@pytest.fixture
def temp_env(tmp_path):
    dest_dir = tmp_path / "downloads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    db_file = tmp_path / "test_history.db"
    history_repo = HistoryRepository(db_file)
    downloader = ImageDownloader(history_repo=history_repo)
    return {
        "dest_dir": dest_dir,
        "history_repo": history_repo,
        "downloader": downloader,
        "tmp_path": tmp_path
    }


def create_test_image_bytes(format="PNG", size=(50, 50), color="blue") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_valid_image_saving(temp_env):
    """Testa se uma imagem válida é aceita e salva com sucesso."""
    downloader = temp_env["downloader"]
    dest_dir = str(temp_env["dest_dir"])
    img_bytes = create_test_image_bytes("PNG")

    success, saved_path, msg, is_dup = downloader.save_image(
        image_bytes=img_bytes,
        original_filename="foto_teste.png",
        destination_dir_str=dest_dir
    )

    assert success is True
    assert saved_path is not None
    assert Path(saved_path).exists()
    assert is_dup is False


def test_reject_corrupted_or_invalid_file(temp_env):
    """Testa rejeição de arquivos corrompidos ou não-imagem."""
    downloader = temp_env["downloader"]
    dest_dir = str(temp_env["dest_dir"])
    corrupted_bytes = b"isto_nao_e_uma_imagem_valida"

    success, saved_path, msg, is_dup = downloader.save_image(
        image_bytes=corrupted_bytes,
        original_filename="corrompida.jpg",
        destination_dir_str=dest_dir
    )

    assert success is False
    assert saved_path is None
    assert "rejeitado" in msg.lower() or "inválidos" in msg.lower()


def test_reject_video_and_documents(temp_env):
    """Testa rejeição explícita de arquivos de vídeo e PDF."""
    analyzer = ImageAnalyzer()

    pdf_bytes = b"%PDF-1.4 Fake PDF Content"
    is_valid_pdf, _, msg_pdf = analyzer.validate_image_content(pdf_bytes, "documento.pdf")
    assert is_valid_pdf is False
    assert "pdf" in msg_pdf.lower() or "documento" in msg_pdf.lower()

    mp4_bytes = b"\x00\x00\x00\x18ftypisomFake MP4 video content"
    is_valid_mp4, _, msg_mp4 = analyzer.validate_image_content(mp4_bytes, "video.mp4")
    assert is_valid_mp4 is False
    assert "vídeo" in msg_mp4.lower() or "mp4" in msg_mp4.lower()


def test_duplicate_detection_by_hash(temp_env):
    """Testa detecção e prevenção de duplicatas via hash criptográfico SHA-256."""
    downloader = temp_env["downloader"]
    dest_dir = str(temp_env["dest_dir"])
    img_bytes = create_test_image_bytes("JPEG", color="green")

    # Primeira gravação: deve ter sucesso
    success1, path1, msg1, is_dup1 = downloader.save_image(
        image_bytes=img_bytes,
        original_filename="imagem_original.jpg",
        destination_dir_str=dest_dir
    )
    assert success1 is True
    assert is_dup1 is False

    # Segunda gravação da mesma imagem exata (mesmo com outro nome): deve detectar duplicata
    success2, path2, msg2, is_dup2 = downloader.save_image(
        image_bytes=img_bytes,
        original_filename="imagem_renomeada.jpg",
        destination_dir_str=dest_dir
    )
    assert success2 is False
    assert is_dup2 is True
    assert "idêntica já salva" in msg2.lower()


def test_filename_conflict_resolution(temp_env):
    """
    Testa política de conflito de nomes: se duas imagens diferentes tiverem o mesmo nome,
    a segunda NÃO deve sobrescrever a primeira, mas sim receber sufixo único (_1).
    """
    downloader = temp_env["downloader"]
    dest_dir = str(temp_env["dest_dir"])

    # Imagem 1 (vermelha)
    img_bytes_1 = create_test_image_bytes("PNG", color="red")
    success1, path1, _, _ = downloader.save_image(
        image_bytes=img_bytes_1,
        original_filename="foto.png",
        destination_dir_str=dest_dir
    )
    assert success1 is True
    assert Path(path1).name == "foto.png"

    # Imagem 2 (diferente da 1, amarela, com o mesmo nome 'foto.png')
    img_bytes_2 = create_test_image_bytes("PNG", color="yellow")
    success2, path2, _, _ = downloader.save_image(
        image_bytes=img_bytes_2,
        original_filename="foto.png",
        destination_dir_str=dest_dir
    )
    assert success2 is True
    assert Path(path2).name == "foto_1.png"
    # Ambos os arquivos devem existir no disco simultaneamente
    assert Path(path1).exists()
    assert Path(path2).exists()


def test_invalid_destination_validation():
    """Testa validação de destino com caminho inexistente ou vazio."""
    downloader = ImageDownloader()

    # Vazio
    valid1, msg1 = downloader.validate_destination("")
    assert valid1 is False
    assert "não pode estar vazio" in msg1.lower()
