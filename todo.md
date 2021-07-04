## Rough development steps to take

1) Get Gribs (These will be stored for reference for route planner)
   
For the presentation of the wind 
2) Convert from Binary to Geotiff using gdal_translate 
    https://gis.stackexchange.com/questions/94568/converting-grib-to-geotiff-with-gdal-translate-in-python
3) Build tms using gdal to tiles
4) plot on leaflet using 
    https://github.com/socib/Leaflet.TimeDimension#examples-and-basic-usage

For the route planning
5) use pygrib to read the values
6) use the input from the map to select lat and long

