## Rough development steps to take

1) Get Gribs (These will be stored for reference for route planner)
2) Convert Gribs
   * Convert using cfgrib?
     This was chosen because the cfgrib engine creates data as an xarray, which is built upon numpy and Pandas. With
     This I was able to dump a Pandas Dataframe to JSON. 
     
   * ~~Convert using pygrib?~~
     
   * ~~Convert from Binary to Geotiff using gdal_translate?     
      https://gis.stackexchange.com/questions/94568/converting-grib-to-geotiff-with-gdal-translate-in-python~~

   
3) Present the wind
    * ~~Build TMS using gdal to tiles
        * Create images and load them to the TMS
        * Use cartopy
        * Use IRIS
        * Use Matplotlib 
        * plot on leaflet using Time Dimension
        https://github.com/socib/Leaflet.TimeDimension#examples-and-basic-usage~~
          
    * Use windbarb leaflet plugin
        * plot on leaflet using Time Dimension
        https://github.com/socib/Leaflet.TimeDimension#examples-and-basic-usage~~
          
4) Give the Users a clear goal
    * Give starting a stopping points
    
5) Get user input
    * Using javascript plugin
    
6) Calculate users route time
    * Need to create boat polar diagram 
    * Create smaller test case, wind barbs start and finish
    

Longer Term TODO

polyline leaflet is creating great circle arcs but only arcing one way. 

