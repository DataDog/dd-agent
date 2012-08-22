/* PupSocket.js
 * Abstraction for WebSocket.
 * Creates WebSocket connection and redirects incoming data to storage.
 *
 * Public interface:
 *  tryStart()      : creates WebSocket connection if unestablished.
 *  isEstablished() : returns a boolean value representing whether a WebSocket
 *                    connection was tried and established.
 *  isClosed()      : returns a boolean value representing whether the WebSocket 
 *                    connection was closed.
 */

var PupSocket = function(port, save) {
    var connEstablished = false,
        hitLimitOnce = false;

    // private methods --------------------------------------------------------------   
    var setEstablished = function(bool) {
        connEstablished = bool;
    };  

    // public interface -------------------------------------------------------------
    var pub = {};

    // accessor to whether WebSocket connection to pup server is established
    pub.isEstablished = function() {
        return connEstablished;
    };

    // tries to create a connection if not already established
    pub.tryStart = function(port) {
        if (this.isEstablished()) { return; }
        var ws = new WebSocket("ws://" + window.location.hostname + ":" + port + "/pupsocket");
        
        setEstablished(true);

        ws.onmessage = function(evt) {
            var incoming;
            try { incoming = JSON.parse(evt.data); }
            catch (err) {
                setEstablished(false);
                throw "There was an error parsing the incoming data: " + err;
            }

            var attempt = save(incoming);
            switch(attempt) {
                case 0:
                    // normal
                    break;
                case 1:
                    // malformed data
                    setEstablished(false);
                    throw "Malformed data sent to client";
                case 2: 
                    // display graph limit hit notice for 5 seconds
                    if (!hitLimitOnce) {
                        var hitLimit = document.getElementById("limit-error");
                        hitLimit.innerHTML = "You have reached the graph count limit. This limit is enforced for reasons of performance.";
                        setTimeout(function() {
                            hitLimit.innerHTML = "";
                        }, 5000);
                        hitLimitOnce = true;
                    }
                    break;
            }
        };

        ws.onclose = function() {
            setEstablished(false);
        };

        ws.onerror = function() {
            setEstablished(false);
            // perhaps restart
        };

        return pub;
    };

    // for PupController to determine whether it should run
    pub.isClosed = function() { return false === connEstablished; };

    return pub;
}(port, Store.save);
