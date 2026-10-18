import hashlib
import io
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from PIL import Image

from app.config import MAGIC_NUMBERS, ALLOWED_IMAGE_EXTENSIONS


class ImageAnalysisError(Exception):
    pass


class InvalidImageError(ImageAnalysisError):
    pass


class ImageAnalyzer:
    """
    Serviço responsável pela inspeção, validação e análise visual de imagens.
    Não depende de APIs em nuvem pagas.
    """

    @staticmethod
    def calculate_sha256(content: bytes) -> str:
        """Calcula o hash criptográfico SHA-256 do conteúdo para deduplicação."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def validate_image_content(content: bytes, original_filename: str = "") -> Tuple[bool, str, str]:
        """
        Valida o tipo real do arquivo e sua integridade.
        Retorna (é_válido, tipo_mime_ou_erro, mensagem).
        Rejeita vídeos, áudios, documentos e arquivos corrompidos.
        """
        if not content or len(content) < 8:
            return False, "unknown", "Arquivo vazio ou muito pequeno para ser uma imagem."

        # Verificação rápida de assinaturas de tipos expressamente rejeitados (vídeos/documentos)
        rejected_signatures = [
            (b"%PDF", "application/pdf", "Documento PDF ignorado. O sistema aceita apenas imagens."),
            (b"\x00\x00\x00 ftyp", "video/mp4", "Arquivo de vídeo MP4 ignorado."),
            (b"\x00\x00\x00\x18ftyp", "video/mp4", "Arquivo de vídeo MP4 ignorado."),
            (b"\x1a\x45\xdf\xa3", "video/webm", "Arquivo de vídeo WebM/MKV ignorado."),
            (b"PK\x03\x04", "application/zip", "Arquivo compactado/documento ignorado."),
            (b"RIFF", "audio/wav", "Arquivo de áudio WAV ignorado.")
        ]
        
        # Testar se começa com assinaturas proibidas (exceto RIFF que pode ser WebP)
        for sig, mime, desc in rejected_signatures:
            if content.startswith(sig):
                if sig == b"RIFF" and b"WEBP" in content[8:16]:
                    break # É uma imagem WebP válida, continuar
                return False, mime, desc

        # Validação de magic bytes para imagens permitidas
        detected_mime = None
        for magic, mime in MAGIC_NUMBERS.items():
            if content.startswith(magic):
                if magic == b"RIFF" and not b"WEBP" in content[8:16]:
                    continue
                detected_mime = mime
                break

        # Validação profunda com Pillow (integridade dos dados e decodificação)
        try:
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
                format_detected = (img.format or "").upper()
                if format_detected not in {"JPEG", "JPG", "PNG", "WEBP", "BMP", "GIF", "TIFF"}:
                    return False, "invalid", f"Formato de imagem não suportado: {format_detected}"
        except Exception as e:
            return False, "corrupted", f"Imagem corrompida ou dados inválidos: {str(e)}"

        return True, detected_mime or "image/generic", "Imagem íntegra e válida."

    @staticmethod
    def analyze_text_criterion(
        caption: str,
        filename: str,
        keywords: List[str],
        match_mode: str = "any",
        case_sensitive: bool = False
    ) -> Tuple[bool, float, str]:
        """
        Avalia o critério textual na legenda e/ou nome do arquivo associado.
        match_mode: 'any' (pelo menos uma palavra), 'all' (todas), 'exact' (expressão exata).
        Retorna (met, confidence, details).
        """
        if not keywords:
            return False, 0.0, "Nenhuma palavra-chave configurada para o critério textual."

        full_text = f"{caption} {filename}"
        if not case_sensitive:
            full_text = full_text.lower()
            keywords = [k.lower().strip() for k in keywords if k.strip()]
        else:
            keywords = [k.strip() for k in keywords if k.strip()]

        if not keywords:
            return False, 0.0, "Nenhuma palavra-chave válida informada."

        if not full_text.strip():
            return False, 0.0, "Imagem não possui legenda nem metadados de texto para análise."

        matched_words = []
        for kw in keywords:
            if match_mode == "exact":
                if kw == full_text.strip():
                    matched_words.append(kw)
            else:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, full_text) or kw in full_text:
                    matched_words.append(kw)

        if match_mode == "all":
            met = len(matched_words) == len(keywords)
            confidence = len(matched_words) / len(keywords) if keywords else 0.0
            details = f"Palavras encontradas: {matched_words} de {keywords}"
        elif match_mode == "exact":
            met = len(matched_words) > 0
            confidence = 1.0 if met else 0.0
            details = f"Expressão exata correspondida: {matched_words}" if met else "Expressão exata não correspondida."
        else:  # 'any'
            met = len(matched_words) > 0
            confidence = min(1.0, len(matched_words) / max(1, len(keywords)))
            details = f"Palavras correspondidas ({len(matched_words)}): {matched_words}"

        return met, confidence, details

    @staticmethod
    def analyze_logo_criterion(
        image_bytes: bytes,
        reference_logo_path: Optional[str] = None
    ) -> Tuple[bool, bool, float, str]:
        """
        Procura a presença de uma imagem de logotipo/referência fornecida pelo usuário.
        Retorna (met, available, confidence, details).
        """
        if not reference_logo_path or not Path(reference_logo_path).exists():
            return False, False, 0.0, f"Imagem de referência de logotipo não configurada ou não encontrada em: {reference_logo_path}"

        try:
            # Tenta utilizar OpenCV se disponível para template matching em múltiplas escalas
            import cv2
            import numpy as np

            # Decodificar imagem principal
            np_arr = np.frombuffer(image_bytes, np.uint8)
            main_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if main_img is None:
                return False, False, 0.0, "Não foi possível decodificar a imagem para busca de logotipo."

            # Decodificar template
            logo_img = cv2.imread(reference_logo_path, cv2.IMREAD_COLOR)
            if logo_img is None:
                return False, False, 0.0, f"Não foi possível carregar a imagem de referência: {reference_logo_path}"

            # Redimensionar se o template for maior que a imagem
            h_main, w_main = main_img.shape[:2]
            h_logo, w_logo = logo_img.shape[:2]
            if h_logo > h_main or w_logo > w_main:
                # Redimensionar logo para caber na imagem
                scale = min(h_main / h_logo, w_main / w_logo) * 0.8
                logo_img = cv2.resize(logo_img, (0, 0), fx=scale, fy=scale)
                h_logo, w_logo = logo_img.shape[:2]

            # Template matching em escala de cinza
            gray_main = cv2.cvtColor(main_img, cv2.COLOR_BGR2GRAY)
            gray_logo = cv2.cvtColor(logo_img, cv2.COLOR_BGR2GRAY)

            res = cv2.matchTemplate(gray_main, gray_logo, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            confidence = max(0.0, min(1.0, float(max_val)))
            met = confidence >= 0.65
            details = f"Comparação de logotipo OpenCV TM_CCOEFF_NORMED. Similaridade máxima: {confidence:.2%}"
            return met, True, confidence, details

        except ImportError:
            # Fallback leve com Pillow (Histogram Comparison)
            try:
                main_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((128, 128))
                logo_pil = Image.open(reference_logo_path).convert("RGB").resize((128, 128))

                hist1 = main_pil.histogram()
                hist2 = logo_pil.histogram()

                # Coeficiente de correlação simples entre histogramas
                dot = sum(a * b for a, b in zip(hist1, hist2))
                norm1 = sum(a * a for a in hist1) ** 0.5
                norm2 = sum(b * b for b in hist2) ** 0.5
                sim = dot / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0

                confidence = max(0.0, min(1.0, float(sim)))
                met = confidence >= 0.75
                details = f"Comparação de histograma PIL (fallback). Coeficiente: {confidence:.2%}"
                return met, True, confidence, details
            except Exception as e:
                return False, False, 0.0, f"Erro ao analisar logotipo com Pillow: {str(e)}"
        except Exception as e:
            return False, False, 0.0, f"Erro durante a execução do comparador de logotipo: {str(e)}"

    @staticmethod
    def analyze_object_criterion(
        image_bytes: bytes,
        object_description: str,
        confidence_threshold: float = 0.5
    ) -> Tuple[bool, bool, float, str]:
        """
        Permite ao usuário descrever o que deseja identificar visualmente na imagem.
        Para respeitar os limites de R$ 0/mês e sem APIs pagas:
        - Se nenhum modelo neural local (ex: MobileNet/YOLO) estiver instalado/baixado,
          o analisador declara expressamente que o critério está INDISPONÍVEL (available=False),
          explicando o motivo e sem simular aprovações falsas.
        - Não confunde similaridade heurística com reconhecimento semântico real.
        """
        target = object_description.strip().lower()
        if not target:
            return False, False, 0.0, "Descrição do objeto/conteúdo visual não informada."

        # Verificação se há suporte a modelo local carregado
        # Como o MVP roda localmente em R$ 0 e não deve baixar modelos de 500MB sem consentimento,
        # informamos claramente o status do analisador semântico local.
        return False, False, 0.0, (
            f"Critério de objeto visual semântico ('{target}') requer modelo local pré-carregado. "
            "Para manter 100% gratuito e leve sem downloads não solicitados de redes neurais pesadas, "
            "este critério está registrado como indisponível no momento."
        )
