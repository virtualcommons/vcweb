<script type="text/javascript">

function createConnectionEvent() {
   return createMessageEvent("Initial connection");
}

function createReconnectionEvent() {
   return createMessageEvent("Reconnecting from disconnect", "reconnect");
}

function createMessageEvent(message, event_type) {
   if (! event_type) {
      event_type = "experimenter";
   }
   return {
      "type": event_type,
      "experimenter_id": {{request.user.experimenter.pk}},
      "experiment_id": {{experiment.pk}},
      "message": message
   };
}

function createChatEvent(message) {
   return createMessageEvent(message);
}

</script>
