// Restricting the area of the the map for display
var openStreetsMap = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; ' + '<a href="http://openstreetmap.org">OpenStreetMap</a>' + ' Contributors',
    });

function getBounds(bounds){
    return bounds
}

var map = L.map('map',{
    worldCopyJump: true,
    preferCanvas: true,
    minZoom: 5,
    maxZoom: 10,
    maxBounds: maxBounds,
    layers: [openStreetsMap]
}).setView([35.5, -136.5], 5);

let polylineMeasure = L.control.polylineMeasure ({position:'topleft', unit:'nauticalmiles', showBearings:true, clearMeasurementsOnStop: false, showClearControl: true, showUnitControl: false})
polylineMeasure.addTo(map);

// Add submit routes button to the leaflet. Sends the data back to flask as a json.
L.easyButton('<img src="./static/images/anchor.svg">',function() {
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
        }).then(function (time) {
            $.ajax({
                url: "/process_user_route",
                type: "GET",
                data: JSON.stringify(time),
                dataType: "json",
                success: show_users_time(time)
            })
        });
    } else {
        alert('Create a route to submit');
    }
}).addTo(map);

// Add submit routes button to the leaflet. Sends the data back to flask as a json.
L.easyButton('<img src="./static/images/check-square.svg">', function() {
    // This holds all of the polylines
    var polydata = polylineMeasure._arrPolylines;
    // Each line is a route the user created
    var lines = []
    for (i in polydata)
        lines.push(polydata[i].polylinePath._latlngs);
    // Don't allow submission without the user creating a route
    //https://stackoverflow.com/questions/53463808/jquery-ajax-call-inside-a-then-function
    if (lines.length > 0){
        //console.log(polydata)
        $.ajax({
            url: '/calculate_optimal_route',
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify(lines)
        }).then(function (test) {
            $.ajax({
                url: '/calculate_optimal_route',
                type: "GET",
                data: JSON.stringify(test),
                dataType: "json",
                success: plot_astar(test)
                // TODO Fix callback error
            })
        });
    } else {
        alert('Create a route to submit');
    }
}).addTo(map);

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

var overlayMaps = {
    'Seattle to Hawaii': seattleToHawaii,
    'Seattle to San Franciso': seattleToSf,
    'Seattle to Cabo': seattleToCabo,
    'San Francisco to Hawaii': sfToHawaii,
    'Hawaii to Cabo': hawaiiToCabo,
    'Hawaii to Seattle': hawaiiToSeattle
    };

L.control.layers(overlayMaps).addTo(map);

// TODO use selected layer to restrict the users to start and stop
map.on('baselayerchange', function (e) {
    console.log(e.layer);
});

function doStuff() {
    //console.log(map.getBounds());
    //console.log(start.latlng)
    //console.log(finish.latlng)
    console.log($('.leaflet-control-layers-selector:checked'))
}

function show_users_time(time){
    alert('Your route took ' + JSON.stringify(time['time']))
}

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

function plot_astar(latlngs){
    latlngs.forEach(function(point){
        console.log(point)
        L.circle(point,{radius: 2}).addTo(map);
    });
}

//;
// Show Coordinates on click
//map.on("contextmenu", function (event) {2
//  console.log("Coordinates: " + event.latlng.toString());
//  L.marker(event.latlng).addTo(map);
//});