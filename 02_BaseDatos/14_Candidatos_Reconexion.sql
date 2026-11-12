USE VisorDatosSIG;
GO
-- 0=Para reconexión, 1=Normal, 2=Para corte, 3=Cortado, 4/5=Bajas.
-- Solo actualiza la restricción; no agrega ni cambia registros.
SET XACT_ABORT ON;
BEGIN TRANSACTION;
IF EXISTS (SELECT 1 FROM sys.check_constraints
           WHERE name = N'CK_CodigosFijos_Estado'
             AND parent_object_id = OBJECT_ID(N'dbo.CodigosFijos'))
    ALTER TABLE dbo.CodigosFijos DROP CONSTRAINT CK_CodigosFijos_Estado;
ALTER TABLE dbo.CodigosFijos WITH CHECK
    ADD CONSTRAINT CK_CodigosFijos_Estado CHECK (Estado BETWEEN 0 AND 5);
COMMIT;
GO
