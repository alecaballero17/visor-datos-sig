USE VisorDatosSIG;
GO

/* Ajusta la cuadricula al area real de las capas. La cuadricula mundial del
   esquema inicial agrupa demasiadas geometrias del municipio en una celda. */
DECLARE @tabla sysname, @indice sysname, @envolvente geometry, @sql nvarchar(max);
DECLARE @xmin float, @ymin float, @xmax float, @ymax float;
DECLARE capas CURSOR LOCAL FAST_FORWARD FOR
    SELECT tabla, indice FROM (VALUES
        ('Manzanas', 'SIX_Manzanas_Geom'),
        ('Lotes', 'SIX_Lotes_Geom')
    ) c(tabla, indice);
OPEN capas;
FETCH NEXT FROM capas INTO @tabla, @indice;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @envolvente = NULL;
    SET @sql = N'SELECT @box=geometry::EnvelopeAggregate(Geom) FROM dbo.'
        + QUOTENAME(@tabla) + N' WHERE Geom IS NOT NULL;';
    EXEC sys.sp_executesql @sql, N'@box geometry OUTPUT', @box=@envolvente OUTPUT;
    IF @envolvente IS NOT NULL
    BEGIN
        SELECT @xmin=MIN(p.STX)-0.001, @ymin=MIN(p.STY)-0.001,
               @xmax=MAX(p.STX)+0.001, @ymax=MAX(p.STY)+0.001
          FROM (VALUES (@envolvente.STPointN(1)), (@envolvente.STPointN(2)),
                       (@envolvente.STPointN(3)), (@envolvente.STPointN(4))) g(p);
        SET @sql = N'CREATE SPATIAL INDEX ' + QUOTENAME(@indice)
            + N' ON dbo.' + QUOTENAME(@tabla) + N'(Geom) USING GEOMETRY_GRID WITH (BOUNDING_BOX=('
            + CONVERT(varchar(40), CONVERT(decimal(20,10), @xmin)) + N','
            + CONVERT(varchar(40), CONVERT(decimal(20,10), @ymin)) + N','
            + CONVERT(varchar(40), CONVERT(decimal(20,10), @xmax)) + N','
            + CONVERT(varchar(40), CONVERT(decimal(20,10), @ymax))
            + N'), GRIDS=(LEVEL_1=HIGH,LEVEL_2=HIGH,LEVEL_3=HIGH,LEVEL_4=HIGH),'
            + N'CELLS_PER_OBJECT=64,DROP_EXISTING=ON);';
        EXEC sys.sp_executesql @sql;
    END;
    FETCH NEXT FROM capas INTO @tabla, @indice;
END;
CLOSE capas;
DEALLOCATE capas;
GO

/* Calcula una sola vez el punto interior de cada lote y utiliza los indices
   espaciales existentes. Conserva los criterios de desempate del script 05. */
CREATE OR ALTER PROCEDURE dbo.sp_ActualizarLoteCodigosFijos
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    SELECT IdLote, Geom.STPointOnSurface() AS Punto
      INTO #PuntosLote
      FROM dbo.Lotes
     WHERE Geom IS NOT NULL AND IdManzana IS NULL;

    UPDATE l
       SET IdManzana = a.IdManzana
      FROM dbo.Lotes l
      JOIN #PuntosLote p ON p.IdLote = l.IdLote
      CROSS APPLY (
          SELECT TOP (1) m.IdManzana
            FROM dbo.Manzanas m WITH (INDEX(SIX_Manzanas_Geom))
           WHERE m.Geom.STIntersects(p.Punto) = 1
           ORDER BY m.IdManzana
      ) a;

    UPDATE c
       SET IdLote = a.IdLote
      FROM dbo.CodigosFijos c
      OUTER APPLY (
          SELECT TOP (1) l.IdLote
            FROM dbo.Lotes l WITH (INDEX(SIX_Lotes_Geom))
           WHERE l.Geom.STIntersects(c.Geom) = 1
           ORDER BY l.Geom.STArea(), l.IdLote
      ) a
     WHERE ISNULL(c.IdLote, -1) <> ISNULL(a.IdLote, -1);

    SELECT COUNT(*) AS TotalCodigos, COUNT(IdLote) AS AsociadosALote,
           COUNT(*) - COUNT(IdLote) AS SinLote
      FROM dbo.CodigosFijos;
    SELECT COUNT(*) AS TotalLotes, COUNT(IdManzana) AS AsociadosAManzana,
           COUNT(*) - COUNT(IdManzana) AS SinManzana
      FROM dbo.Lotes;
END;
GO
