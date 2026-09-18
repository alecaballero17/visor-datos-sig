USE VisorDatosSIG;
GO
IF COL_LENGTH('dbo.BitacoraAcceso','Login') < 508
    ALTER TABLE dbo.BitacoraAcceso ALTER COLUMN Login nvarchar(254) NOT NULL;
GO
IF COL_LENGTH('dbo.Usuarios','Email') IS NULL
    ALTER TABLE dbo.Usuarios ADD Email nvarchar(254) NULL;
GO
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.Usuarios') AND name='UX_Usuarios_Email')
    CREATE UNIQUE INDEX UX_Usuarios_Email ON dbo.Usuarios(Email) WHERE Email IS NOT NULL;
GO
