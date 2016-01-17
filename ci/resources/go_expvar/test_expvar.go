/* Demo of the expvar package. You register metrics by creating NewT, then
   update it.

   You can access the exposed metrics via HTTP at /debug/vars, you'll get a JSON
   object with your exposed variables and some pre defined system ones.

   You can use monitoring system such as Nagios and OpenNMS to monitor the
   system and plot the change of data over time.

   After you run the server, try "curl http://localhost:8079?user=lassie" several times and then
   "curl http://localhost:8079/debug/vars | python -m json.tool".
*/
package main

import (
	"expvar"
	"fmt"
	"io"
	"net/http"
	"runtime"
)

// Two metrics, these are exposed by "magic" :)
// Number of calls to our server.
var numCalls = expvar.NewInt("num_calls")

// Last user.
var lastUser = expvar.NewString("last_user")

func HelloServer(w http.ResponseWriter, req *http.Request) {
	user := req.FormValue("user")

	// Update metrics
	numCalls.Add(1)
	lastUser.Set(user)

	msg := fmt.Sprintf("G'day %s\n", user)
	io.WriteString(w, msg)
}

func main() {
	// In some situations, the CI tests for the go_expvar check would fail due
	// to the Golang runtime not haivng run GC yet. The reason this is needed
	// is that get_gc_collection_histogram() function in go_expvar.py
	// short-circuits if there have been no GCs. This causes the pause_ns
	// metric to not be present, thus causing tests to fail. So trigger GC.
	runtime.GC()

	http.HandleFunc("/", HelloServer)
	http.ListenAndServe(":8079", nil)
}
