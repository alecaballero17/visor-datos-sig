USE VisorDatosSIG;
GO
/* El SHP no contiene estado del servicio. El valor inicial Normal del esquema
   no confirma que una vivienda tenga una conexion activa. */
IF COL_LENGTH('dbo.CodigosFijos','EstadoVerificado') IS NULL
    ALTER TABLE dbo.CodigosFijos ADD EstadoVerificado bit NOT NULL
        CONSTRAINT DF_CodigosFijos_EstadoVerificado DEFAULT(0) WITH VALUES;
GO
