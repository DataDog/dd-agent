/*
	Pup.js Unit Tests
*/


this.pupSuite = {
	setUp: function(test) {
		test.ok(true);
		test.expect(1);
		test.done();
	},

	/*
	 * PupSocket.js
	 * Manages Web Socket connection
	 */
	
	"try starting WS when no existing connection": function(test) {
		var examplePort = 8888;
 		PupSocket.tryStart(8888);
		test.ok(PupSocket.isEstablished());
		test.ok(!PupSocket.isClosed());
		test.expect(2);
		test.done();
	},

	"try starting WS when existing connection": function(test) {
		var examplePort = 8888;
		PupSocket.tryStart(8888);
		test.ok(PupSocket.isEstablished());
		PupSocket.tryStart(8888);
		test.ok(PupSocket.isEstablished());
		test.expect(2);
		test.done();
	}

	// TODO: Maybe more, but not of highest priorition.
	// Testing with an application might be considered more important
};
