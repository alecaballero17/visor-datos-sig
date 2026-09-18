USE VisorDatosSIG;
GO
/* Permite consultar codigos dentro de un lote aunque su IdLote este vacio
   o vinculado a otro poligono superpuesto. */
DECLARE @box geometry=(SELECT geometry::EnvelopeAggregate(Geom) FROM dbo.CodigosFijos WHERE Geom IS NOT NULL);
IF @box IS NOT NULL
BEGIN
    DECLARE @xmin float,@ymin float,@xmax float,@ymax float,@sql nvarchar(max);
    SELECT @xmin=MIN(p.STX)-0.001,@ymin=MIN(p.STY)-0.001,
           @xmax=MAX(p.STX)+0.001,@ymax=MAX(p.STY)+0.001
    FROM (VALUES (@box.STPointN(1)),(@box.STPointN(2)),(@box.STPointN(3)),(@box.STPointN(4))) g(p);
    SET @sql=N'CREATE SPATIAL INDEX SIX_CodigosFijos_Geom ON dbo.CodigosFijos(Geom) USING GEOMETRY_GRID WITH (BOUNDING_BOX=('
      +CONVERT(varchar(40),CONVERT(decimal(20,10),@xmin))+N','
      +CONVERT(varchar(40),CONVERT(decimal(20,10),@ymin))+N','
      +CONVERT(varchar(40),CONVERT(decimal(20,10),@xmax))+N','
      +CONVERT(varchar(40),CONVERT(decimal(20,10),@ymax))
      +N'),GRIDS=(LEVEL_1=HIGH,LEVEL_2=HIGH,LEVEL_3=HIGH,LEVEL_4=HIGH),CELLS_PER_OBJECT=64,DROP_EXISTING=ON);';
    EXEC sys.sp_executesql @sql;
END;
GO
