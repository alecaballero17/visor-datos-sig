USE VisorDatosSIG;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE NombreRol='Consultor')
    INSERT dbo.Roles(NombreRol,Descripcion,Estado) VALUES('Consultor','Consulta del visor cartográfico',1);
GO

IF OBJECT_ID(N'dbo.BitacoraAcceso',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.BitacoraAcceso(
        IdBitacora BIGINT IDENTITY PRIMARY KEY,
        Fecha DATETIME2 NOT NULL CONSTRAINT DF_BitacoraAcceso_Fecha DEFAULT(SYSDATETIME()),
        Login NVARCHAR(50) NOT NULL,
        Exitoso BIT NOT NULL,
        Ip NVARCHAR(64) NULL,
        Detalle NVARCHAR(500) NULL
    );
    CREATE INDEX IX_BitacoraAcceso_Fecha ON dbo.BitacoraAcceso(Fecha DESC);
END;
GO

IF OBJECT_ID(N'dbo.BitacoraMigracion',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.BitacoraMigracion(
        IdMigracion BIGINT IDENTITY PRIMARY KEY,
        FechaInicio DATETIME2 NOT NULL CONSTRAINT DF_BitacoraMig_Fecha DEFAULT(SYSDATETIME()),
        FechaFin DATETIME2 NULL,
        Usuario NVARCHAR(50) NOT NULL,
        Capa NVARCHAR(50) NOT NULL,
        Archivo NVARCHAR(260) NOT NULL,
        TablaDestino NVARCHAR(128) NOT NULL,
        Modalidad NVARCHAR(20) NOT NULL,
        Procesados INT NOT NULL DEFAULT(0),
        Exitosos INT NOT NULL DEFAULT(0),
        Omitidos INT NOT NULL DEFAULT(0),
        Fallidos INT NOT NULL DEFAULT(0),
        Estado NVARCHAR(20) NOT NULL DEFAULT('Iniciada'),
        Detalle NVARCHAR(MAX) NULL
    );
END;
GO
