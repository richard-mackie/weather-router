// Create the Map
var openStreetsMap = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; ' + '<a href="http://openstreetmap.org">OpenStreetMap</a>' + ' Contributors',
    });

var map = L.map('map',{
    worldCopyJump: true,
    preferCanvas: true,
    minZoom: 5,
    maxZoom: 10,
    maxBounds: maxBounds,
    layers: [openStreetsMap]
}).setView([35.5, -136.5], 5);

// Allows plotting of User route
let polylineMeasure = L.control.polylineMeasure ({
    position:'topleft',
    measureControlLabel: '↯',
    unit:'nauticalmiles',
    showBearings:true,
    clearMeasurementsOnStop: false,
    showClearControl: true,
    showUnitControl: false,
    measureControlTitleOn: 'Create Route',
    measureControlTitleOff: 'End Route',
    clearControlTitle: 'Clear Created Routes',
    clearControlClasses: []}
)
polylineMeasure.addTo(map);

// Calculate the User route time
L.easyButton('&#x23F1', function() {
    // This holds all of the polylines
    var polydata = polylineMeasure._arrPolylines;
    // Each line is a route the user created
    var lines = []

    for (i in polydata)
        lines.push(polydata[i].polylinePath._latlngs);
    // Don't allow submission without the user creating a route
    //https://stackoverflow.com/questions/53463808/jquery-ajax-call-inside-a-then-function
    if (lines.length > 0){
        console.log(polydata)
        $.ajax({
            url: "/process_user_route",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(lines)
        }).then(function (data) {
            $.ajax({
                url: "/process_user_route",
                type: "GET",
                data: JSON.stringify(data),
                dataType: "json",
                success: show_user_route_time(data['route_time'])
            })
        });
    } else {
        alert('Create a route to submit');
    }
}, 'Calculate Created Route Time').addTo(map);

// Calculate the Optimum Route
L.easyButton('&#x27A2', function() {
    // This holds all of the polylines
    var polydata = polylineMeasure._arrPolylines;
    // Each line is a route the user created
    var lines = []
    for (i in polydata)
        lines.push(polydata[i].polylinePath._latlngs);
    if (lines.length > 0){
        $.ajax({
            url: '/calculate_optimal_route',
            type: "POST",
            contentType: "application/json",
            beforeSend :function(){
                return confirm('Calculating the optimal route. This may take up to ' + JSON.stringify(timeout) + ' seconds.');},
            data: JSON.stringify(lines)
        }).then(function (data) {
            $.ajax({
                url: '/calculate_optimal_route',
                type: "GET",
                data: JSON.stringify(data),
                dataType: "json",
                success: plot_astar_route(data['route']) // TODO config this. If debugging use plot_astar_points otherwise use plot_astar_route
            }).then(
                show_optimal_route_time(data['route_time'])
            )
        });
    } else {
        alert('Create a route to submit');
    }
}, 'Display Optimal Route & Time').addTo(map);

// Optimum route
let polylineMeasure2 = L.control.polylineMeasure ({
    position:'topleft',
    unit:'nauticalmiles',
    showBearings:false,
    clearMeasurementsOnStop: false,
    showClearControl: true,
    showUnitControl: false,
    clearControlTitle: 'Clear Optimum Route',
    clearControlClasses: [],
    fixedLine: {                    // Styling for the solid line
        color: '#dc3620',              // Solid line color
        weight: 2                   // Solid line weight
    }})
polylineMeasure2.addTo(map);
// This hides the drawing portion of the Polyline measure
polylineMeasure2._measureControl.remove();

//Takes wind data in the form of a json and plots windbarbs with a speed and direction on the map
function plotWindBarbs(winddata){
    wind.data.forEach(function(p){
    if (maxBounds.contains([p.latitude, p.longitude])){
        // need to take - 360 of longitude due to noaa grib generation
        var icon = L.WindBarb.icon({deg: p.degree, speed: p.speed, pointRadius: 0, forceDir: false, strokeLength: 17, strokeWidth: 1});
        var marker = L.marker([p.latitude, p.longitude], {icon: icon}).addTo(map);
    }
    });
}

function show_user_route_time(time){
    alert('Your last created route took ' + JSON.stringify(time));
}

function show_optimal_route_time(time){
    alert('The optimal route took ' + JSON.stringify(time));
}

// This is used for plotting isochrones. Not being used atm.
function plot_isochrone(latlngs){
    //console.log(latlngs)
    var headings = latlngs[1].map(function(e, i) {
      return [e, latlngs[0][i]];
    });
    latlngs.forEach(function(line){
        //console.log(line[0])
        L.polyline(line, {color: 'red', weight: 1, noClip: true, smoothFactor: 1}).addTo(map);
        line.forEach(function (point){
            //console.log(point)
            L.circle(point,{radius: 2}).addTo(map);
        });
    });
    //console.log(headings)
    headings.forEach(function (heading){
        L.polyline(heading, {color: 'red', weight: 1, noClip: true, smoothFactor: 1}).addTo(map);
    });
}

// This is used for debugging
function plot_astar_points(latlngs){
    latlngs.forEach(function(point){
        L.circle(point,{radius: 2}).addTo(map);
    });
}

// This the final result
function plot_astar_route(latlngs){
    polylineMeasure2.seed([latlngs])
}

// Restricting the area of the the map for display
function getBounds(bounds){
    return bounds
}


// Starting Points
var seattleStart = L.circle([48.5, -125.10],{
    color: 'green',
    fillColor: '#62ff00',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Starting Line");

var sfStart = L.circle([37.7, -122.8],{
    color: 'green',
    fillColor: '#62ff00',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Starting Line");

var caboStart = L.circle([22.90, -109.91],{
    color: 'green',
    fillColor: '#62ff00',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Starting Line");

var hawaiiStart = L.circle([20.0, -155.05],{
    color: 'green',
    fillColor: '#62ff00',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Finish Line");


// Finish Points
var hawaiiFinish = L.circle([20.0, -155.05],{
    color: 'red',
    fillColor: '#b81335',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Finish Line");

var caboFinish = L.circle([22.90, -109.91],{
    color: 'red',
    fillColor: '#b81335',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Finish Line");

var seattleFinish = L.circle([48.5, -125.10],{
    color: 'red',
    fillColor: '#b81335',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Finish Line");

var sfFinish = L.circle([37.7, -122.8],{
    color: 'red',
    fillColor: '#b81335',
    fillOpacity: 0.3,
    radius: 50000}
).bindPopup("Finish Line");

var seattleToHawaii = L.layerGroup([seattleStart, hawaiiFinish]);
var seattleToSf = L.layerGroup([seattleStart, sfFinish]);
var seattleToCabo = L.layerGroup([seattleStart, caboFinish]);
var sfToHawaii = L.layerGroup([sfStart, hawaiiFinish]);
var hawaiiToCabo = L.layerGroup([hawaiiStart, caboFinish]);
var hawaiiToSeattle = L.layerGroup([hawaiiStart, seattleFinish]);
var hawaiiToSf = L.layerGroup([hawaiiStart, sfFinish]);
var CaboToHawaii = L.layerGroup([caboStart, hawaiiFinish]);

var overlayMaps = {
    'Seattle to Hawaii': seattleToHawaii,
    //'Seattle to San Franciso': seattleToSf,
    //'Seattle to Cabo': seattleToCabo,
    'San Francisco to Hawaii': sfToHawaii,
    'Cabo San Lucas to Hawaii':CaboToHawaii,
    'Hawaii to Seattle': hawaiiToSeattle,
    'Hawaii to San Francisco': hawaiiToSf,
    'Hawaii to Cabo San Lucas': hawaiiToCabo,
    };
L.control.layers(overlayMaps).addTo(map);

// TODO use selected layer to restrict the users to start and stop
map.on('baselayerchange', function (e) {
    console.log(e.layer);
});

