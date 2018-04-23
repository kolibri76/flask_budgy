//Google map integration for geoposition of transactions
var lat = document.getElementById("geo_lat");
var lng = document.getElementById("geo_lng");
var err = document.getElementById("geo_error");
var marker_draggable = (document.currentScript.getAttribute('marker_draggable') == 'true');
var marker;


//get location via browser on user request
function getLocation() {

    //if geo is available call showMap()
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(showMap, showError);
    //if no geo show error
    } else {
        z.innerHTML = "Geolocation is not supported by this browser.";
    }
}

//draw map if geo is available
function showMap(position) {

    //use actual geo position if availalbe
    if (typeof position !== 'undefined') {
        lat.value = position.coords.latitude;
        lng.value = position.coords.longitude;
    }
    //use records geo loction if actual geo location is not available, draw map with center on geo and place marker
    if ( (lat.value !== "") && (lng.value !== "") ) {
        var myCenter = new google.maps.LatLng(lat.value,lng.value);
        var mapCanvas = document.getElementById("map");
        var mapOptions = {center: myCenter, zoom: 14};
        var map = new google.maps.Map(mapCanvas, mapOptions);
        marker = new google.maps.Marker({position:myCenter, map: map, draggable:marker_draggable});
        //listen for marker position change
        marker.addListener('dragend', writePosition);
        marker.setMap(map);

    }
}

//write back geolocation values
function writePosition(event) {
    lat.value = event.latLng.lat();
    lng.value = event.latLng.lng();
}

// handle browser geolocation errors
function showError(error) {
    switch(error.code) {
        case error.PERMISSION_DENIED:
            err.innerHTML = "User denied request for Geolocation."
            break;
        case error.POSITION_UNAVAILABLE:
            err.innerHTML = "Geolcation unavailable."
            break;
        case error.TIMEOUT:
            err.innerHTML = "Request timed out."
            break;
        case error.UNKNOWN_ERROR:
            err.innerHTML = "Unknown error occurred."
            break;s
    }
}