from __future__ import annotations

from src.adapters.mappings.canonical_mapping_adapter import MappingCompatibilityError
from src.services.readiness_service import ReadinessError


class DesktopErrorTranslator:
    def translate(self, exc: Exception, *, operation: str | None = None) -> str:
        if isinstance(exc, ReadinessError):
            return f"Le traitement local est indisponible. {exc.detail}" + (
                f" {exc.remediation}" if exc.remediation else ""
            )
        if isinstance(exc, MappingCompatibilityError):
            return f"Le fichier de correspondance n'est pas compatible. {exc.remediation}"
        if isinstance(exc, FileNotFoundError):
            return "Le fichier demande est introuvable."
        if isinstance(exc, PermissionError):
            return "L'application ne peut pas acceder au fichier ou au dossier demande."
        if isinstance(exc, ModuleNotFoundError):
            return "Une dependance locale manque. Verifiez la preparation de l'application."
        if isinstance(exc, ValueError):
            message = str(exc)
            if message.startswith("Unknown case"):
                return "Dossier introuvable."
            if message.startswith("Unknown document"):
                return "Document introuvable."
            if message.startswith("Unknown artifact"):
                return "Artifact introuvable."
            if message.startswith("Unknown deanonymization session"):
                return "Session de deanonymisation introuvable."
            if message == "Case deletion requires explicit confirmation":
                return "La suppression du dossier exige une confirmation explicite."
            return message
        if isinstance(exc, RuntimeError):
            if operation is not None:
                return f"Echec de l'operation '{operation}'. {exc}"
            return str(exc)
        if operation is not None:
            return f"Echec inattendu pendant '{operation}'. {exc}"
        return str(exc)
