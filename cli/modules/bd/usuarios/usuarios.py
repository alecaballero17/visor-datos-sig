"""Usuarios y roles del sistema (mismo hash PBKDF2-SHA256 que AuthService)."""
from __future__ import annotations

import hashlib
import secrets

from cli.core import sql, ui

ITERACIONES = 100_000


def _hash(clave: str) -> tuple[str, str]:
    salt = secrets.token_bytes(32)
    h = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), salt, ITERACIONES, dklen=32)
    return "0x" + h.hex().upper(), "0x" + salt.hex().upper()


def _pedir_clave() -> str:
    clave = ui.preguntar("Contrasena nueva (min. 8)", secreto=True)
    if len(clave) < 8:
        raise ui.Fallo("La contrasena debe tener al menos 8 caracteres.")
    if ui.preguntar("Repita la contrasena", secreto=True) != clave:
        raise ui.Fallo("Las contrasenas no coinciden.")
    return clave


def listar() -> None:
    """Usuarios con sus roles."""
    filas = sql.filas("""
        SELECT u.IdUsuario, u.Login, u.Nombre, ISNULL(u.Email, ''), CASE u.Activo WHEN 1 THEN 'si' ELSE 'no' END,
               ISNULL(STUFF((SELECT ', ' + r.NombreRol FROM dbo.UsuariosRoles ur JOIN dbo.Roles r ON r.IdRol = ur.IdRol
                             WHERE ur.IdUsuario = u.IdUsuario FOR XML PATH('')), 1, 2, ''), '')
        FROM dbo.Usuarios u ORDER BY u.IdUsuario""")
    ui.tabla(filas, ["Id", "Login", "Nombre", "Email", "Activo", "Roles"])


def _roles() -> list[str]:
    return [f[0] for f in sql.filas("SELECT NombreRol FROM dbo.Roles WHERE Estado = 1 ORDER BY IdRol")]


def _login() -> str:
    login = ui.preguntar("Login")
    if not login or sql.escalar(f"SELECT COUNT(*) FROM dbo.Usuarios WHERE Login = N'{sql.lit(login)}'") == "0":
        raise ui.Fallo(f"No existe el usuario '{login}'.")
    return login


def crear() -> None:
    """Crea un usuario y le asigna un rol."""
    login = ui.preguntar("Login")
    if not login:
        return
    nombre = ui.preguntar("Nombre completo", login)
    email = ui.preguntar("Email (opcional)")
    roles = _roles()
    rol = roles[ui.elegir("Rol", roles, roles.index("Consultor") if "Consultor" in roles else 0)]
    h, s = _hash(_pedir_clave())
    email_sql = f"N'{sql.lit(email)}'" if email else "NULL"
    sql.ejecutar(f"""SET XACT_ABORT ON; BEGIN TRAN;
        INSERT dbo.Usuarios(Login, Nombre, PasswordHash, PasswordSalt, Iteraciones, Activo, FechaRegistro, Email)
        VALUES (N'{sql.lit(login)}', N'{sql.lit(nombre)}', {h}, {s}, {ITERACIONES}, 1, SYSUTCDATETIME(), {email_sql});
        INSERT dbo.UsuariosRoles(IdUsuario, IdRol)
        SELECT SCOPE_IDENTITY(), IdRol FROM dbo.Roles WHERE NombreRol = N'{sql.lit(rol)}';
        COMMIT;""", mostrar=False)
    ui.ok(f"Usuario '{login}' creado con rol {rol}.")


def cambiar_clave() -> None:
    """Restablece la contrasena de un usuario."""
    login = _login()
    h, s = _hash(_pedir_clave())
    sql.ejecutar(f"UPDATE dbo.Usuarios SET PasswordHash = {h}, PasswordSalt = {s}, Iteraciones = {ITERACIONES} "
                 f"WHERE Login = N'{sql.lit(login)}'", mostrar=False)
    ui.ok(f"Contrasena de '{login}' actualizada.")


def activar() -> None:
    """Activa o desactiva un usuario."""
    login = _login()
    activo = ui.elegir("Estado", ["Activo", "Inactivo"]) == 0
    sql.ejecutar(f"UPDATE dbo.Usuarios SET Activo = {1 if activo else 0} WHERE Login = N'{sql.lit(login)}'", mostrar=False)
    ui.ok(f"'{login}' {'activado' if activo else 'desactivado'}.")


def asignar_rol() -> None:
    """Agrega o quita un rol."""
    login = _login()
    roles = _roles()
    rol = roles[ui.elegir("Rol", roles)]
    quitar = ui.elegir("Accion", ["Agregar", "Quitar"]) == 1
    if quitar:
        q = f"""DELETE ur FROM dbo.UsuariosRoles ur JOIN dbo.Usuarios u ON u.IdUsuario = ur.IdUsuario
                JOIN dbo.Roles r ON r.IdRol = ur.IdRol WHERE u.Login = N'{sql.lit(login)}' AND r.NombreRol = N'{sql.lit(rol)}'"""
    else:
        q = f"""INSERT dbo.UsuariosRoles(IdUsuario, IdRol)
                SELECT u.IdUsuario, r.IdRol FROM dbo.Usuarios u CROSS JOIN dbo.Roles r
                WHERE u.Login = N'{sql.lit(login)}' AND r.NombreRol = N'{sql.lit(rol)}'
                  AND NOT EXISTS (SELECT 1 FROM dbo.UsuariosRoles x WHERE x.IdUsuario = u.IdUsuario AND x.IdRol = r.IdRol)"""
    sql.ejecutar(q, mostrar=False)
    ui.ok(f"Rol {rol} {'quitado de' if quitar else 'asignado a'} '{login}'.")


def roles() -> None:
    """Roles y cantidad de usuarios."""
    ui.tabla(sql.filas("""SELECT r.IdRol, r.NombreRol, ISNULL(r.Descripcion, ''), COUNT(ur.IdUsuario)
        FROM dbo.Roles r LEFT JOIN dbo.UsuariosRoles ur ON ur.IdRol = r.IdRol
        GROUP BY r.IdRol, r.NombreRol, r.Descripcion ORDER BY r.IdRol"""), ["Id", "Rol", "Descripcion", "Usuarios"])
