"""Excepciones propias: errores globales que detienen la auditoría."""


class ErrorAuditoria(Exception):
    """Error base de la herramienta."""


class UsuarioNoEncontrado(ErrorAuditoria):
    """El usuario de GitHub no existe."""


class LimiteDeTasa(ErrorAuditoria):
    """GitHub ha limitado las peticiones."""


class TokenInvalido(ErrorAuditoria):
    """GitHub rechazó el token (401)."""


class ErrorSalida(ErrorAuditoria):
    """No se puede generar o escribir la salida pedida (p. ej. --inject sin marcadores)."""
