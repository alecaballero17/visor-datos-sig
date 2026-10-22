USE VisorDatosSIG;
GO

IF NOT EXISTS(SELECT 1 FROM dbo.Roles WHERE NombreRol='Conector')
    INSERT dbo.Roles(NombreRol,Descripcion,Estado)
    VALUES('Conector','Rol para reconectar servicios cortados',1);
GO

IF OBJECT_ID(N'dbo.OrdenesTrabajo',N'U') IS NULL
BEGIN
    CREATE TABLE dbo.OrdenesTrabajo(
        IdOrden BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_OrdenesTrabajo PRIMARY KEY,
        IdCodigo INT NOT NULL,
        TipoTrabajo VARCHAR(20) NOT NULL,
        IdEmpleado INT NOT NULL,
        IdAsignador INT NOT NULL,
        Estado VARCHAR(20) NOT NULL CONSTRAINT DF_OrdenesTrabajo_Estado DEFAULT('Pendiente'),
        FechaAsignacion DATETIME2 NOT NULL CONSTRAINT DF_OrdenesTrabajo_Fecha DEFAULT(SYSDATETIME()),
        FechaActualizacion DATETIME2 NOT NULL CONSTRAINT DF_OrdenesTrabajo_FechaActualizacion DEFAULT(SYSDATETIME()),
        CONSTRAINT FK_OrdenesTrabajo_Codigo FOREIGN KEY(IdCodigo) REFERENCES dbo.CodigosFijos(IdCodigo),
        CONSTRAINT FK_OrdenesTrabajo_Empleado FOREIGN KEY(IdEmpleado) REFERENCES dbo.Usuarios(IdUsuario),
        CONSTRAINT FK_OrdenesTrabajo_Asignador FOREIGN KEY(IdAsignador) REFERENCES dbo.Usuarios(IdUsuario),
        CONSTRAINT CK_OrdenesTrabajo_Tipo CHECK(TipoTrabajo IN('Corte','Reconexion')),
        CONSTRAINT CK_OrdenesTrabajo_Estado CHECK(Estado IN('Pendiente','Completada','Cancelada'))
    );
    CREATE INDEX IX_OrdenesTrabajo_Empleado ON dbo.OrdenesTrabajo(IdEmpleado,Estado,FechaAsignacion DESC);
    CREATE INDEX IX_OrdenesTrabajo_Codigo ON dbo.OrdenesTrabajo(IdCodigo,FechaAsignacion DESC);
END;
GO

IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'dbo.OrdenesTrabajo') AND name=N'UX_OrdenesTrabajo_Codigo_Pendiente')
    CREATE UNIQUE INDEX UX_OrdenesTrabajo_Codigo_Pendiente
        ON dbo.OrdenesTrabajo(IdCodigo) WHERE Estado='Pendiente';
GO
