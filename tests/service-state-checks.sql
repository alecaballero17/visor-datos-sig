-- Ejecutar en VisorDatosSIG. No crea registros y revierte la transición ensayada.
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints
               WHERE parent_object_id = OBJECT_ID(N'dbo.CodigosFijos')
                 AND name = N'CK_CodigosFijos_Estado'
                 AND is_disabled = 0 AND is_not_trusted = 0
                 AND definition LIKE '%(0)%' AND definition LIKE '%(5)%')
    THROW 51000, 'La restriccion de estados no admite el catalogo 0 a 5.', 1;
PRINT 'PASS: restriccion activa y validada para estados 0 a 5';
DECLARE @total bigint = (SELECT COUNT_BIG(*) FROM dbo.CodigosFijos);
DECLARE @clasificados bigint = (SELECT COUNT_BIG(*) FROM dbo.CodigosFijos WHERE Estado BETWEEN 0 AND 5);
IF @total <> @clasificados THROW 51000, 'Hay estados fuera del catalogo.', 1;
PRINT 'PASS: todos los suministros pertenecen al catalogo';

BEGIN TRANSACTION;
DECLARE @id int = (SELECT TOP (1) IdCodigo FROM dbo.CodigosFijos WITH (UPDLOCK) WHERE Estado = 3 ORDER BY IdCodigo);
IF @id IS NOT NULL
BEGIN
    DECLARE @antes bigint = (SELECT COUNT_BIG(*) FROM dbo.CodigosFijos WHERE Estado = 0);
    UPDATE dbo.CodigosFijos SET Estado = 0, EstadoVerificado = 1, FechaCambioEstado = SYSUTCDATETIME()
    WHERE IdCodigo = @id AND Estado = 3;
    IF @@ROWCOUNT <> 1 THROW 51000, 'La transicion no actualizo exactamente un suministro.', 1;
    IF (SELECT COUNT_BIG(*) FROM dbo.CodigosFijos WHERE Estado = 0) <> @antes + 1
        THROW 51000, 'El contador de candidatos no coincide con la transicion.', 1;
    UPDATE dbo.CodigosFijos SET Estado = 0 WHERE IdCodigo = @id AND Estado = 3;
    IF @@ROWCOUNT <> 0 THROW 51000, 'La transicion repetida debe rechazarse.', 1;
    PRINT 'PASS: transicion 3 a 0, contador de candidatos y rechazo de repeticion';
END
ELSE PRINT 'SKIP: no existen suministros cortados para ensayar la transicion';
ROLLBACK;
PRINT 'PASS: ensayo revertido; registros conservados';
