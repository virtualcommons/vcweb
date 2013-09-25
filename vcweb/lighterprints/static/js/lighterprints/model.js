function LighterFootprintsModel(modelJson) {
    var self = this;
    var model = ko.mapping.fromJS(modelJson);
    function hasStatus(activity, status) {
        return activity.status() === status;
    }
    model.activityStatusCss = function(activity) {
        var statusCss = activity.status();
        if (activity.status() !== 'available') {
            statusCss += " disabled";
        }
        return statusCss;
    }
    model.isActivityDisabled = function(activity) {
        return activity.status() !== 'available';
    }
    model.isCompleted = function(activity) {
        return hasStatus(activity, 'completed');
    }
    model.isExpired = function(activity) {
        return hasStatus(activity, 'expired');
    }
    model.isUpcoming = function(activity) {
        return hasStatus(activity, 'upcoming');
    }
    model.isAvailable = function(activity) {
        return hasStatus(activity, 'available');
    }
    model.isLocked = function(activity) {
        return hasStatus(activity, 'locked');
    }
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
        var minutes = minutesLeft + "";
        if (minutesLeft.length == 1) {
            minutesLeft = "0" + minutesLeft;
        }
        model.minutesLeft(minutesLeft);
    };
    setInterval(model.minuteTick, 1000*60);
    // FIXME: hacky, figure out if there is a way to pass the observable in directly from the model object we get in
    // performActivity
    model.lastPerformedActivity = ko.observable();
    model.errorMessage = ko.observable();
    model.hasGroupActivity = ko.computed(function() {
        return model.groupActivity().length > 0;
    });
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
    model.hasChatMessages = ko.computed(function() {
        return model.chatMessages().length > 0;
    });
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
    model.postComment = function(targetModel) {
        var formData = $('#commentForm' + targetModel.pk()).serialize();
        $('.comment-popover').popover('hide');
        $.post('/lighterprints/api/comment', formData, function(response) {
            if (response.success) {
                ko.mapping.fromJSON(response.viewModel, model);
            }
        });
    };
    model.like = function(targetModel) {
        // FIXME: if targetModel.likes already contains this participant's pgr.pk, don't allow for this again
        if (targetModel.liked()) {
            console.debug("target model: " + targetModel + " is already well-liked");
            return;
        }
        targetModel.liked(true);
        $.post('/lighterprints/api/like', {participant_group_id: model.participantGroupId(), target_id: targetModel.pk()},
            function(data) {
                targetModel.liked(data.success);
            });
    };

    model.lockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.status() === 'locked' });
        });
    model.unlockedChallenges = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.status()  !== 'locked' });
        });
    model.availableActivities = ko.computed(function() {
            return ko.utils.arrayFilter(model.activities(), function(activity) { return activity.status() === 'available' });
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
        var placement = attribute.placement || "top";
        var trigger = attribute.trigger || "manual";
        var popOverTemplate = "<div id='"+attribute.id+"-popover'>" + $(cssSelectorForPopoverTemplate).html() + "</div>";
        $(element).popover({
            content: popOverTemplate,
            html: true,
            trigger: trigger,
            placement: placement
        });
        var popoverId = "comment-popover" + attribute.id;
        $(element).attr('id', popoverId);
        $(element).click(function() {
            $(this).popover('toggle');
            var thePopover = document.getElementById(attribute.id+"-popover");
            // FIXME: only apply bindings if we haven't done so once on this popover, otherwise clicking repeatedly on
            // the popover causes KO errors to be thrown
            childBindingContext = bindingContext.createChildContext(viewModel);
            ko.applyBindingsToDescendants(childBindingContext, thePopover);
        });
        return { controlsDescendantBindings: true };
    },
};
