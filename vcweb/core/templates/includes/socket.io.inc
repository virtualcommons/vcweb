<script type="text/javascript" src="/static/js/socket.io.js"></script>
<script type="text/javascript">
    WEB_SOCKET_SWF_LOCATION="/static/flash/WebSocketMain.swf"
</script>

<script type="text/javascript">

function createConnectionEvent() {
   return createMessageEvent("Initial connection", "connect");
}

function createReconnectionEvent() {
   return createMessageEvent("Reconnecting from disconnect", "reconnect");
}

function createMessageEvent(payload, event_type) {
   if (! event_type) {
      event_type = "chat";
   }
   return {
      "type": event_type,
      "participant_id": "%{participant_id}",
      "group_id": "%{group_id}",
      "message": payload
   };
}

function createChatEvent(message) {
   return createMessageEvent(message, "chat");
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
         s.send(createReconnectEvent());
   });

   return s;
}
</script>
