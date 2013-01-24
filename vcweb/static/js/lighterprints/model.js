function LighterFootprintsModel(modelJson) {
    var self = this;
    var model = ko.mapping.fromJS(modelJson);
    // FIXME: hacky, figure out if there is a way to pass the observable in directly from the model object we get in
    // performActivity
    model.lastPerformedActivity = ko.observable();
    model.lastPerformedActivityPoints = ko.observable();
    model.errorMessage = ko.observable();
    model.hasChatMessages = function() {
        return model.chatMessages().length > 0;
    }
    model.submitChatMessage = function() {
        var formData = $('#chat-form').serialize();
        $.post('/lighterprints/api/message', formData, function(data) {
                ko.mapping.fromJS(data, model);
            });
        $('#chatText').val('');
        return false;
    };
    model.lockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.isLocked() });
        });
    model.unlockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return ! activity.isLocked() });
        });
    model.availableActivities = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.availableNow() });
        });
    model.hasAvailableActivities = ko.computed(function() {
            return model.availableActivities().length > 0;
        });
    return model;
}
