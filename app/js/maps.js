function initialize() {



  var myLatlng = new google.maps.LatLng(56.9147,23.9805);
  var mapOptions = {
    center: new google.maps.LatLng(56.9187,23.9875),
    zoom: 14,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    scrollwheel: false,
  };

  var map = new google.maps.Map(document.getElementById("map-canvas"),
                                mapOptions);

  // var image = '../images/maris.jpg';


  var marker = new google.maps.Marker({
      position: myLatlng,
      map: map,
      // icon: image
      title: 'BroPro SIA'

  });

  var lineCoordinates = [
          new google.maps.LatLng(56.917814,23.986609),
          new google.maps.LatLng(56.914949,23.981534)
              ];

  var lineSymbol = {
      path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
  };


  var line = new google.maps.Polyline({
      path: lineCoordinates,
      icons: [{
          icon: lineSymbol,
      offset: '100%'
      }],
      map: map
  });

}

function loadScript() {
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = 'https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false&' +
      'callback=initialize';
  document.body.appendChild(script);
}

window.onload = loadScript;

