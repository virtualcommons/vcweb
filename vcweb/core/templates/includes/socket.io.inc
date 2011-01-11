<script type="text/javascript" src="/static/js/socket.io.js"></script>

<script type="text/javascript">

function createConnectionEvent() {
   return {
      "type": "connect",
      "participant_id": %{participant_id},
      "group_id": %{group_id}
   };
}

function createChatEvent(message) {
   return {
      "type": "chat",
      "participant_id": %{participant_id},
      "group_id": %{group_id},
      "message": message
   };
}

function connect(host, port) {
   if ( !host ) {
      console.debug("Tried to connect to invalid host, connecting to vcweb.asu.edu instead.");
      host = "vcweb.asu.edu";
   }
   if ( !port ) {
      console.debug("using default port 8888");
      port = 8888;
   }
   var s = new io.socket(host, {"port": port});
   s.connect();
   s.on("connect", function() {
         s.send(createConnectionEvent());
   });
   s.on('disconnect', function(data) {
         console.debug("received disconnect, reconnecting.");
         s.connect();
   });

   return s;
}
</script>
