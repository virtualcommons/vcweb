function LighterFootprintsModel(modelJson) {
    var self = this;
    var model = ko.mapping.fromJS(modelJson);
    model.minuteTick = function() {
        var hoursLeft = model.hoursLeft();
        var minutesLeft = model.minutesLeft() - 1;
        if (minutesLeft < 0) {
            minutesLeft = 59;
            hoursLeft--;
            if (hoursLeft < 0) {
                hoursLeft = 23;
            }
        }
        model.hoursLeft(hoursLeft);
        model.minutesLeft(minutesLeft);
    };
    setInterval(model.minuteTick, 1000*60);
    // FIXME: hacky, figure out if there is a way to pass the observable in directly from the model object we get in
    // performActivity
    model.lastPerformedActivity = ko.observable();
    model.lastPerformedActivityPoints = ko.observable();
    model.errorMessage = ko.observable();
    model.groupActivityTemplate = function(groupActivity) {
        return groupActivity.parameter_name();
    };
    model.teamActivity = ko.computed(function() {
        return ko.utils.arrayFilter(model.groupActivity(), function(groupActivity) {
            return groupActivity.parameter_name().indexOf("chat_message") != 0;
        });
    });
    model.chatMessages = ko.computed(function() {
            return ko.utils.arrayFilter(model.groupActivity(), function(groupActivity) { return groupActivity.parameter_name().indexOf("chat_message") === 0 });
        });
    model.hasChatMessages = function() {
        return model.chatMessages().length > 0;
    }
    model.submitChatMessage = function() {
        var formData = $('#chat-form').serialize();
        $.post('/lighterprints/api/message', formData, function(response) {
                if (response.success) {
                    console.debug("successful post - updated view model: ");
                    ko.mapping.fromJS(response.viewModel, model);
                }
                else {
                    console.debug("unable to post message to server");
                    console.debug(response);
                }
            });
        $('#chatText').val('');
        return false;
    };
    model.lockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.locked() });
        });
    model.unlockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return ! activity.locked() });
        });
    model.availableActivities = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.availableNow() });
        });
    model.hasAvailableActivities = ko.computed(function() {
            return model.availableActivities().length > 0;
        });
    model.closeCommentPopover = function(targetModel) {
        $('.comment-popover').popover('hide');
    };
    return model;
}
ko.bindingHandlers.popover = {
    init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
        var attribute = ko.utils.unwrapObservable(valueAccessor());
        var cssSelectorForPopoverTemplate = attribute.content;
        var popOverTemplate = "<div id='"+attribute.id+"-popover'>" + $(cssSelectorForPopoverTemplate).html() + "</div>";
        $(element).popover({
            content: popOverTemplate,
            html: true,
            trigger: 'manual'
        });
        var popoverId = "comment-popover" + attribute.id;
        $(element).attr('id', popoverId);
        $(element).click(function() {
            $(this).popover('toggle');
            var thePopover = document.getElementById(attribute.id+"-popover");
            childBindingContext = bindingContext.createChildContext(viewModel);
            ko.applyBindingsToDescendants(childBindingContext, thePopover);
        });
    },
};
